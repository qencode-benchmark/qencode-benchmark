#!/usr/bin/env python3
"""
check_vqe_reproducibility.py  —  QEncode reproducibility checker (v1)

Will your VQE give the same answer if you run it again?

Threaded linear-algebra libraries (the BLAS under NumPy/SciPy) sum floating-point
numbers in whatever order the CPU cores finish. That changes an energy in its last
bits. A gradient-free optimizer (COBYLA, Nelder-Mead, Powell, SPSA) picks its next
step by COMPARING energies, so that noise can push it into a different local minimum
of a multi-modal landscape — and you get a different published number depending on
the machine, or even the load. Fixing your random seed does NOT protect you: the
non-determinism is in the arithmetic, not the RNG.

What this tool does, in order of reliability:
  1. Checks your CONFIGURATION — is your BLAS multi-threaded? This is the necessary
     condition, and it is always answerable. This drives the verdict.
  2. Runs a small VQE several times at 1 thread and shows it is bit-identical — a
     concrete demonstration of the determinism you get after the fix. If the
     multi-threaded runs happen to disagree too, it flags that as live confirmation.
  3. Shows you the one-line fix.

It will not pretend a passing live check means you are safe: whether the failure
reproduces depends on core count, BLAS build, problem size, and load. The verdict
is based on your configuration, which is the honest signal.

Free to use and share. https://www.qencode-benchmark.org
Needs only NumPy and SciPy, which every VQE user already has. 'threadpoolctl' is
optional and gives a precise BLAS thread count.
"""
import os, sys, json, subprocess, platform, argparse

REPO_URL = "https://www.qencode-benchmark.org"
BLOG_URL = "https://www.qencode-benchmark.org/blog/vqe-reproducibility-threading-bug"
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
GRADIENT_FREE = ("COBYLA", "Nelder-Mead", "Powell", "SPSA", "simplex")


# ── worker: runs INSIDE a subprocess whose thread env is already fixed ────────
def _worker(repeats, qubits, layers, maxiter):
    import numpy as np
    from scipy.optimize import minimize

    n, L, dim = qubits, layers, 2 ** qubits
    rng = np.random.default_rng(0)          # FIXED — same seed, to make the point

    I2 = np.eye(2, dtype=complex)
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)

    def op_on(op, q):
        m = np.array([[1.0 + 0j]])
        for i in range(n):
            m = np.kron(m, op if i == q else I2)
        return m

    H = np.zeros((dim, dim), dtype=complex)
    c1 = rng.uniform(0.5, 1.5, size=n)
    for q in range(n):
        for P in (X, Y, Z):
            H += c1[q] * (op_on(P, q) @ op_on(P, (q + 1) % n))
    H = (H + H.conj().T) / 2
    e_exact = float(np.linalg.eigvalsh(H)[0])

    def apply_ry(state, q, theta):
        c, s = np.cos(theta / 2), np.sin(theta / 2)
        st = np.moveaxis(state.reshape([2] * n), q, 0)
        a, b = st[0].copy(), st[1].copy()
        st[0], st[1] = c * a - s * b, s * a + c * b
        return np.moveaxis(st, 0, q).reshape(dim)

    def apply_cnot(state, ctrl, tgt):
        st = np.moveaxis(state.reshape([2] * n), ctrl, 0)
        sub = np.moveaxis(st[1], tgt if tgt < ctrl else tgt - 1, 0)
        sub[[0, 1]] = sub[[1, 0]]
        st[1] = np.moveaxis(sub, 0, tgt if tgt < ctrl else tgt - 1)
        return np.moveaxis(st, 0, ctrl).reshape(dim)

    def energy(params):
        st = np.zeros(dim, dtype=complex); st[0] = 1.0
        i = 0
        for _ in range(L):
            for q in range(n):
                st = apply_ry(st, q, params[i]); i += 1
            for q in range(n - 1):
                st = apply_cnot(st, q, q + 1)
        for q in range(n):
            st = apply_ry(st, q, params[i]); i += 1
        return float(np.real(np.vdot(st, H @ st)))

    x0 = rng.uniform(-0.1, 0.1, size=n * (L + 1))
    out = [float(minimize(energy, x0.copy(), method="COBYLA",
                          options={"maxiter": maxiter, "rhobeg": 0.3}).fun)
           for _ in range(repeats)]
    print(json.dumps({"energies": out, "e_exact": e_exact}))


# ── configuration probe ──────────────────────────────────────────────────────
def _detect():
    info = {"platform": platform.platform(), "python": platform.python_version(),
            "cpu_count": os.cpu_count() or 1, "numpy": None,
            "blas_threads": None, "blas_source": None,
            "thread_env": {v: os.environ.get(v) for v in THREAD_VARS if os.environ.get(v)}}
    try:
        import numpy as np
        info["numpy"] = np.__version__
    except Exception:
        return info
    try:
        import threadpoolctl
        pools = threadpoolctl.threadpool_info()
        if pools:
            info["blas_threads"] = max(p.get("num_threads", 1) for p in pools)
            info["blas_source"] = "measured (threadpoolctl): " + \
                ", ".join(sorted({p.get("internal_api", "?") for p in pools}))
    except Exception:
        pass
    if info["blas_threads"] is None:
        # infer: an explicit pin wins; otherwise BLAS defaults to all cores
        pin = None
        for v in THREAD_VARS:
            if os.environ.get(v):
                try: pin = int(os.environ[v])
                except ValueError: pass
        info["blas_threads"] = pin if pin is not None else info["cpu_count"]
        info["blas_source"] = "inferred from environment (install 'threadpoolctl' " \
                              "for a measured value)"
    return info


def _run_worker(threads, repeats, qubits, layers, maxiter):
    env = dict(os.environ)
    for v in THREAD_VARS:
        env[v] = str(threads)
    try:
        p = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--worker",
             "--repeats", str(repeats), "--qubits", str(qubits),
             "--layers", str(layers), "--maxiter", str(maxiter)],
            env=env, capture_output=True, text=True, timeout=1200)
        if p.returncode != 0:
            return None, (p.stderr or p.stdout)[-400:]
        return json.loads(p.stdout.strip().splitlines()[-1]), None
    except Exception as e:
        return None, str(e)


def main():
    ap = argparse.ArgumentParser(description="QEncode VQE reproducibility checker")
    ap.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--qubits", type=int, default=11)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--maxiter", type=int, default=400)
    ap.add_argument("--live", action="store_true",
                    help="also run a live VQE several times at 1 vs N threads and "
                         "compare. This is an ATTEMPT to reproduce the failure on "
                         "this machine; whether it triggers depends on your BLAS "
                         "build, core count, and load, so it may show nothing even "
                         "when your config is at risk. The verdict does not depend "
                         "on it.")
    args = ap.parse_args()

    if args.worker:
        _worker(args.repeats, args.qubits, args.layers, args.maxiter)
        return

    c = (lambda code: code if sys.stdout.isatty() else "")
    B, R = c("\033[1m"), c("\033[0m")
    G, Y, X, C = c("\033[92m"), c("\033[93m"), c("\033[91m"), c("\033[96m")
    line = B + "─" * 62 + R

    print(f"\n{B}QEncode — VQE reproducibility checker{R}")
    print("Will your VQE give the same answer twice? Let's check this setup.\n")

    env = _detect()
    if env["numpy"] is None:
        print(f"{X}NumPy is not installed — this tool needs NumPy and SciPy.{R}")
        print("  pip install numpy scipy"); sys.exit(2)

    print(f"  platform     : {env['platform']}")
    print(f"  cpu cores    : {env['cpu_count']}")
    print(f"  numpy        : {env['numpy']}")
    print(f"  BLAS threads : {env['blas_threads']}   ({env['blas_source']})")
    if env["thread_env"]:
        print(f"  thread env   : {env['thread_env']}")

    threaded = env["blas_threads"] is not None and env["blas_threads"] > 1

    # ── 1. CONFIGURATION VERDICT (always reliable) ───────────────────────────
    print(f"\n{line}")
    if threaded:
        print(f"{X}{B}  AT RISK — your BLAS is multi-threaded ({env['blas_threads']} threads){R}")
        print(f"  This is the condition for non-reproducibility. If you optimize with")
        print(f"  a gradient-free method — {', '.join(GRADIENT_FREE[:4])} — the same run,")
        print(f"  same seed, same code can land on a different energy on a different")
        print(f"  machine or under different load. Fixing the seed does not help.")
        print(f"  (If you use analytic gradients — L-BFGS-B, Adam with parameter-shift")
        print(f"   — you are far less exposed, but pinning threads is still correct.)")
    else:
        print(f"{G}{B}  OK on this front — your BLAS is single-threaded{R}")
        print(f"  Summation order is fixed, so your linear algebra is deterministic.")
        print(f"  (This only covers the threading issue; it is not a general guarantee")
        print(f"   of reproducibility.)")
    print(line)

    # ── 2. LIVE DEMONSTRATION (opt-in; unreliable by nature, see --live help) ─
    if args.live:
        many = max(2, env["cpu_count"])
        print(f"\nLive check: a small VQE (COBYLA, same seed), "
              f"{args.repeats}x at 1 thread"
              f"{' and '+str(args.repeats)+'x at '+str(many)+' threads' if threaded else ''}"
              f".  ~1-2 min.\n")

        single, e1 = _run_worker(1, args.repeats, args.qubits, args.layers, args.maxiter)
        if single is None:
            print(f"{Y}  (live check skipped — worker error: {e1}){R}")
        else:
            se = single["energies"]; ss = (max(se) - min(se)) * 1000
            print(f"  {B} 1 thread {R}: " + "  ".join(f"{x:.6f}" for x in se))
            print(f"      spread = {ss:.4f} mHa  "
                  + (f"{G}(identical — this is the determinism the fix gives you){R}"
                     if ss < 1e-4 else f"{Y}(unexpected non-determinism at 1 thread){R}"))
            if threaded:
                multi, e2 = _run_worker(many, args.repeats, args.qubits, args.layers, args.maxiter)
                if multi is not None:
                    me = multi["energies"]; ms = (max(me) - min(me)) * 1000
                    print(f"  {B}{many} threads{R}: " + "  ".join(f"{x:.6f}" for x in me))
                    print(f"      spread = {ms:.4f} mHa  "
                          + (f"{X}(LIVE CONFIRMATION — threading changed the result){R}"
                             if ms >= 1e-4 else
                             f"{Y}(no variance triggered at this size — see note){R}"))
                    if ms < 1e-4:
                        print(f"\n  {Y}Note:{R} we did not trigger a failure here, but that does")
                        print(f"  NOT clear you — the effect grows with core count, problem")
                        print(f"  size, BLAS build, and load. Your configuration is still at")
                        print(f"  risk (see verdict above).")

    # ── 3. THE FIX ───────────────────────────────────────────────────────────
    if threaded:
        print(f"\n{B}The fix — put this block before you import numpy:{R}")
        print(f"  import os")
        for v in THREAD_VARS:
            print(f"  os.environ[\"{v}\"] = \"1\"")
        print(f"  import numpy as np   # everything after this is now deterministic")
        print(f"\n  Setting it AFTER importing numpy does nothing — BLAS has already")
        print(f"  built its thread pool. Verify by running this checker again:")
        print(f"  the verdict should flip to single-threaded.")

    if not args.live and threaded:
        print(f"\n  (Run with {B}--live{R} to also attempt a live reproduction on this "
              f"machine —\n   note it may not trigger even when your config is at risk.)")

    print(f"\nHow we found this in our own published numbers, and fixed the whole suite:")
    print(f"  {C}{BLOG_URL}{R}")
    print(f"  {C}{REPO_URL}{R}\n")


if __name__ == "__main__":
    main()
