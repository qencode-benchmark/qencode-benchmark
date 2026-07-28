#!/usr/bin/env python3
"""
check_vqe_reproducibility.py  —  QEncode VQE reproducibility scorecard (v1)

Will your VQE give the same answer if someone else runs it — or if you run it again?

Four things have to be true. This tool checks the ones it can see and tells you
honestly about the ones it can't.

  1. DETERMINISTIC ARITHMETIC.  Threaded BLAS (the linear algebra under NumPy/SciPy)
     sums floating-point numbers in whatever order the CPU cores finish. That perturbs
     an energy in its last bits, and a gradient-free optimizer (COBYLA, Nelder-Mead,
     Powell, SPSA) — which picks its next step by COMPARING energies — can then land in
     a different local minimum. Fixing your random seed does NOT help: the
     non-determinism is in the arithmetic, not the RNG.  → checkable, drives the verdict.

  2. RECORDED VERSIONS.  A result that only reproduces on your exact package versions
     isn't reproducible unless those versions are written down.  → we show them and look
     for a pin file.

  3. A RECORDED SEED.  → we can't see your code; this one is on you.

  4. A RECORDED CODE VERSION.  A clean git commit means the code that ran can be
     recovered.  → checkable if you're in a git repo.

We found #1 in our own published benchmark numbers, and #2 the hard way. The story:
https://www.qencode-benchmark.org/blog/vqe-reproducibility-threading-bug

Free to use and share. Needs only NumPy and SciPy. 'threadpoolctl' is optional and
gives a measured BLAS thread count.

  python check_vqe_reproducibility.py            # scorecard for this setup
  python check_vqe_reproducibility.py --record   # also write a provenance receipt
  python check_vqe_reproducibility.py --live     # also attempt a live reproduction
"""
import os, sys, json, subprocess, platform, argparse, glob

REPO_URL = "https://www.qencode-benchmark.org"
BLOG_URL = "https://www.qencode-benchmark.org/blog/vqe-reproducibility-threading-bug"
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
QUANTUM_LIBS = ("numpy", "scipy", "pennylane", "qiskit", "openfermion",
                "pyscf", "cirq", "qulacs", "tequila")
PIN_FILES = ("requirements.txt", "requirements-v4.txt", "environment.yml",
             "environment.yaml", "pyproject.toml", "Pipfile", "poetry.lock",
             "conda-lock.yml", "uv.lock")


# ── worker: small VQE inside a subprocess whose thread env is already fixed ───
def _worker(repeats, qubits, layers, maxiter):
    import numpy as np
    from scipy.optimize import minimize
    n, L, dim = qubits, layers, 2 ** qubits
    rng = np.random.default_rng(0)
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
    cc = rng.uniform(0.5, 1.5, size=n)
    for q in range(n):
        for P in (X, Y, Z):
            H += cc[q] * (op_on(P, q) @ op_on(P, (q + 1) % n))
    H = (H + H.conj().T) / 2
    e_exact = float(np.linalg.eigvalsh(H)[0])
    def apply_ry(state, q, t):
        c, s = np.cos(t / 2), np.sin(t / 2)
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
    def energy(p):
        st = np.zeros(dim, dtype=complex); st[0] = 1.0; i = 0
        for _ in range(L):
            for q in range(n): st = apply_ry(st, q, p[i]); i += 1
            for q in range(n - 1): st = apply_cnot(st, q, q + 1)
        for q in range(n): st = apply_ry(st, q, p[i]); i += 1
        return float(np.real(np.vdot(st, H @ st)))
    x0 = rng.uniform(-0.1, 0.1, size=n * (L + 1))
    out = [float(minimize(energy, x0.copy(), method="COBYLA",
                          options={"maxiter": maxiter, "rhobeg": 0.3}).fun)
           for _ in range(repeats)]
    print(json.dumps({"energies": out, "e_exact": e_exact}))


# ── detection ─────────────────────────────────────────────────────────────────
def _versions():
    # Read installed-distribution metadata — do NOT import the modules. Importing
    # pyscf/qiskit/cirq just to read a version string can take a minute; this is instant.
    from importlib import metadata
    aliases = {"pennylane": ("pennylane", "PennyLane"),
               "cirq": ("cirq", "cirq-core"),
               "tequila": ("tequila", "tequila-basic")}
    out = {}
    for m in QUANTUM_LIBS:
        for dist in aliases.get(m, (m,)):
            try:
                out[m] = metadata.version(dist)
                break
            except Exception:
                continue
    return out

def _blas_threads():
    try:
        import threadpoolctl
        pools = threadpoolctl.threadpool_info()
        if pools:
            return max(p.get("num_threads", 1) for p in pools), \
                   "measured (threadpoolctl): " + \
                   ", ".join(sorted({p.get("internal_api", "?") for p in pools}))
    except Exception:
        pass
    pin = None
    for v in THREAD_VARS:
        if os.environ.get(v):
            try: pin = int(os.environ[v])
            except ValueError: pass
    if pin is not None:
        return pin, "inferred from environment"
    return (os.cpu_count() or 1), "inferred (no pin set → BLAS defaults to all cores; " \
                                  "install 'threadpoolctl' for a measured value)"

def _find_pin_file():
    for f in PIN_FILES:
        for hit in glob.glob(f):
            try:
                txt = open(hit).read()
                if hit.endswith((".lock",)) or "==" in txt or ": " in txt:
                    return hit
            except Exception:
                pass
    return None

def _git_state():
    try:
        head = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return None, None  # not a repo / git absent
    try:
        dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            stderr=subprocess.DEVNULL, text=True).strip())
    except Exception:
        dirty = None
    return head, dirty


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
    ap = argparse.ArgumentParser(description="QEncode VQE reproducibility scorecard")
    ap.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--qubits", type=int, default=11)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--maxiter", type=int, default=400)
    ap.add_argument("--record", action="store_true",
                    help="write a provenance receipt (qencode_reproducibility.json)")
    ap.add_argument("--live", action="store_true",
                    help="also attempt a live reproduction (small VQE, 1 vs N threads). "
                         "May not trigger even when the config is at risk; the scorecard "
                         "does not depend on it.")
    args = ap.parse_args()
    if args.worker:
        _worker(args.repeats, args.qubits, args.layers, args.maxiter)
        return

    c = (lambda code: code if sys.stdout.isatty() else "")
    B, R = c("\033[1m"), c("\033[0m")
    G, Y, X, C, D = c("\033[92m"), c("\033[93m"), c("\033[91m"), c("\033[96m"), c("\033[90m")
    PASS, FAIL, INFO, UNK = f"{G}[✓]{R}", f"{X}[✗]{R}", f"{C}[i]{R}", f"{Y}[?]{R}"

    print(f"\n{B}QEncode — VQE reproducibility scorecard{R}")
    print("Will your VQE give the same answer if someone else runs it? Four checks.\n")

    try:
        import numpy  # noqa
    except Exception:
        print(f"{X}NumPy is not installed — this tool needs NumPy and SciPy.{R}")
        print("  pip install numpy scipy"); sys.exit(2)

    ncores = os.cpu_count() or 1
    versions = _versions()
    blas, blas_src = _blas_threads()
    threaded = blas > 1
    pin_file = _find_pin_file()
    head, dirty = _git_state()

    print(f"  {platform.platform()}   |   python {platform.python_version()}   |   {ncores} cores\n")

    # ── the scorecard ────────────────────────────────────────────────────────
    print(f"{B}Determinism — what we can check for you{R}")
    if threaded:
        print(f"  {FAIL} BLAS single-threaded")
        print(f"      {blas} threads ({blas_src})")
        print(f"      {X}AT RISK{R}: gradient-free optimizers (COBYLA, Nelder-Mead, Powell,")
        print(f"      SPSA) can return different energies run to run. Seed does not help.")
    else:
        print(f"  {PASS} BLAS single-threaded ({blas} thread — summation order fixed)")

    print(f"\n{B}Provenance — what you must record (we can only see so much){R}")
    vshow = ", ".join(f"{k} {v}" for k, v in versions.items()) or "(none detected)"
    if pin_file:
        print(f"  {PASS} versions recorded — found {pin_file}")
        print(f"      {D}installed now: {vshow}{R}")
        print(f"      {D}(verify the pins in {pin_file} match the above){R}")
    else:
        print(f"  {INFO} exact versions — no pin file found in this directory")
        print(f"      installed now: {vshow}")
        print(f"      {Y}record these{R} (requirements.txt with ==, or environment.yml)")
    print(f"  {UNK} random seed — can't see your code; make sure you set AND record one")
    if head is None:
        print(f"  {INFO} code version — not a git repository here; track your code so the")
        print(f"      exact version that produced a result can be recovered")
    elif dirty:
        print(f"  {FAIL} code version — git tree has uncommitted changes @ {head}")
        print(f"      {Y}commit first{R} so the recorded code matches what ran")
    else:
        print(f"  {PASS} code version — clean git tree @ {head}")

    # ── bottom line ──────────────────────────────────────────────────────────
    print(f"\n{B}{'─'*62}{R}")
    if threaded:
        print(f"{X}{B}  Your arithmetic is NON-DETERMINISTIC.{R}  Fix threads (below).")
    else:
        print(f"{G}{B}  Your arithmetic is deterministic.{R}")
    print(f"  Full reproducibility also needs the three provenance items above.")
    print(f"{B}{'─'*62}{R}")

    if threaded:
        print(f"\n{B}The fix — put this block before you import numpy:{R}")
        print(f"  import os")
        for v in THREAD_VARS:
            print(f"  os.environ[\"{v}\"] = \"1\"")
        print(f"  import numpy as np   # everything after this is deterministic")
        print(f"  {D}(after importing numpy it does nothing — BLAS has already started){R}")

    # ── optional provenance receipt ──────────────────────────────────────────
    if args.record:
        import datetime
        receipt = {
            "tool": "qencode-reproducibility-checker",
            "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cpu_count": ncores,
            "blas_threads": blas,
            "blas_threads_deterministic": not threaded,
            "package_versions": versions,
            "pin_file_present": pin_file,
            "git_commit": head,
            "git_clean": (dirty is False) if head else None,
        }
        with open("qencode_reproducibility.json", "w") as f:
            json.dump(receipt, f, indent=2)
        print(f"\n{G}Wrote qencode_reproducibility.json{R} — save it alongside your results "
              f"so\n  the environment that produced them can be verified later.")

    # ── optional live reproduction ───────────────────────────────────────────
    if args.live:
        many = max(2, ncores)
        print(f"\n{B}Live check{R} (small VQE, COBYLA, same seed; ~1-2 min):")
        single, e1 = _run_worker(1, args.repeats, args.qubits, args.layers, args.maxiter)
        if single is None:
            print(f"  {Y}(skipped — worker error: {e1}){R}")
        else:
            se = single["energies"]; ss = (max(se) - min(se)) * 1000
            print(f"  1 thread : " + " ".join(f"{x:.6f}" for x in se) +
                  (f"   {G}identical{R}" if ss < 1e-4 else f"   {Y}varies{R}"))
            if threaded:
                multi, e2 = _run_worker(many, args.repeats, args.qubits, args.layers, args.maxiter)
                if multi:
                    me = multi["energies"]; ms = (max(me) - min(me)) * 1000
                    print(f"  {many:>2} threads: " + " ".join(f"{x:.6f}" for x in me) +
                          (f"   {X}DIFFERS — live confirmation{R}" if ms >= 1e-4
                           else f"   {Y}no variance triggered here{R}"))
                    if ms < 1e-4:
                        print(f"  {D}(not triggering here does not clear you — effect grows with"
                              f" cores, size, load){R}")

    print(f"\nHow we found this in our own numbers, and the full story:")
    print(f"  {C}{BLOG_URL}{R}\n  {C}{REPO_URL}{R}\n")


if __name__ == "__main__":
    main()
