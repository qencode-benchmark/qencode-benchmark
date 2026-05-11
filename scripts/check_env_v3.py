#!/usr/bin/env python3
"""
Phase 0: QEncode v3 environment verification.

Run this on your execution machine (Ubuntu) BEFORE starting any v3 runs.
Checks all required and optional packages, signing key presence, and
optionally runs an H2 smoke test through the PySCF → PennyLane pipeline.

Usage:
  python scripts/check_env_v3.py
  python scripts/check_env_v3.py --smoke-test   # also validates H2 CASCI + PL Hamiltonian

Exit code: 0 = all required deps present, 1 = one or more required missing.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Optional, Tuple

REPO = Path(__file__).resolve().parent.parent

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg: str)   -> str: return f"{GREEN}  [OK]{RESET}  {msg}"
def warn(msg: str) -> str: return f"{YELLOW}  [WARN]{RESET} {msg}"
def fail(msg: str) -> str: return f"{RED}  [FAIL]{RESET} {msg}"


def _version(pkg_name: str) -> Optional[str]:
    try:
        from importlib.metadata import version
        return version(pkg_name)
    except Exception:
        return None


def check_import(pkg_import: str, pkg_meta: str, required: bool = True) -> Tuple[bool, str]:
    """Try to import a package and return (success, version_string)."""
    try:
        mod = importlib.import_module(pkg_import)
        ver = _version(pkg_meta) or getattr(mod, "__version__", "unknown")
        return True, ver
    except ImportError as e:
        return False, str(e)


# ── Dependency manifest ───────────────────────────────────────────────────────
# (import_name, pip_name, required, note)
DEPS = [
    # Core science
    ("numpy",          "numpy",                    True,  ""),
    ("scipy",          "scipy",                    True,  "COBYLA / L-BFGS-B optimizer"),
    ("pyscf",          "pyscf",                    True,  "CASCI reference energies + CCSD(T)"),
    # PennyLane stack
    ("pennylane",      "pennylane",                True,  "v3 VQE + tapering"),
    ("pennylane.qchem","pennylane",                True,  "qchem submodule - Z2 symmetry tapering"),
    ("openfermion",    "openfermion",              True,  "FermionOperator to QubitOperator (PL bridge)"),
    # Signing
    ("cryptography",   "cryptography",             True,  "Ed25519 signing"),
    # Optional (v2 pipeline — still needed for running old entries)
    ("qiskit",         "qiskit",                   False, "v2 pipeline / backward compat"),
    ("qiskit_nature",  "qiskit-nature",            False, "v2 entry generation"),
    # Nice-to-have
    ("h5py",           "h5py",                     False, "FCIDUMP / HDF5 export (Phase 3)"),
    ("yaml",           "pyyaml",                   False, "suite YAML parsing"),
]


def check_deps() -> bool:
    print(f"\n{BOLD}--- Dependency Check -------------------------------------------{RESET}")
    all_required_ok = True
    for imp, pkg, required, note in DEPS:
        success, info = check_import(imp, pkg, required)
        tag = "required" if required else "optional"
        note_str = f"  ({note})" if note else ""
        if success:
            print(ok(f"{pkg:<28} {info:<12}  [{tag}]{note_str}"))
        else:
            if required:
                print(fail(f"{pkg:<28} NOT FOUND  [required]{note_str}"))
                print(f"         Install: pip install {pkg}")
                all_required_ok = False
            else:
                print(warn(f"{pkg:<28} not found  [optional]{note_str}"))
    return all_required_ok


def check_signing_key() -> bool:
    print(f"\n{BOLD}--- Signing Key ------------------------------------------------{RESET}")
    key_candidates = [
        REPO / "keys" / "signing_key.pem",
        REPO / "keys" / "private_key.pem",
        Path.home() / ".qencode" / "signing_key.pem",
    ]
    for p in key_candidates:
        if p.exists():
            print(ok(f"Signing key found: {p}"))
            # Try loading it
            try:
                from cryptography.hazmat.primitives.serialization import load_pem_private_key
                data = p.read_bytes()
                key = load_pem_private_key(data, password=None)
                klass = type(key).__name__
                print(ok(f"Key loaded OK ({klass})"))
                return True
            except Exception as e:
                print(warn(f"Key file exists but could not load: {e}"))
                return False
    # No key file — check env var
    import os
    if os.environ.get("QENCODE_SIGNING_KEY_B64"):
        print(ok("QENCODE_SIGNING_KEY_B64 env var is set (key in environment)"))
        return True
    print(warn("No signing key found - certification signing will be skipped"))
    print(f"         Expected at: {key_candidates[0]}")
    print(f"         Or set env:  QENCODE_SIGNING_KEY_B64=<base64-pem>")
    return True  # not fatal for v3 development


def check_molecule_catalog() -> bool:
    print(f"\n{BOLD}--- Molecule Catalog -------------------------------------------{RESET}")
    v3_path = REPO / "molecules_v3.json"
    v2_path = REPO / "molecules_v2.json"
    if v3_path.exists():
        print(ok(f"molecules_v3.json found: {v3_path}"))
        try:
            import json
            catalog = json.loads(v3_path.read_text())
            entries = catalog.get("entries", [])
            names = [e["molecule"] for e in entries]
            print(ok(f"  Molecules: {', '.join(sorted(set(names)))}"))
        except Exception as e:
            print(warn(f"  Could not parse catalog: {e}"))
        return True
    elif v2_path.exists():
        print(warn("molecules_v3.json not found - falling back to molecules_v2.json"))
        return True
    else:
        print(fail("No molecule catalog found (molecules_v3.json or molecules_v2.json)"))
        return False


def smoke_test_pyscf_casci() -> bool:
    """Run a minimal PySCF CASCI on H2 to verify the reference energy pipeline."""
    print(f"\n{BOLD}--- Smoke Test: PySCF CASCI (H2, sto-3g, 2e2o) ----------------{RESET}")
    try:
        from pyscf import gto, scf, mcscf  # type: ignore
        mol = gto.Mole()
        mol.atom = "H 0 0 0; H 0 0 0.735"
        mol.basis = "sto-3g"
        mol.charge = 0
        mol.spin = 0
        mol.verbose = 0
        mol.build()

        mf = scf.RHF(mol).run()
        e_hf = mf.e_tot
        print(ok(f"HF energy:    {e_hf:.10f} Ha"))

        # CASCI: full active space for H2 (2 electrons, 2 orbitals)
        mc = mcscf.CASCI(mf, 2, (1, 1))  # nelec must be tuple (n_alpha, n_beta)
        mc.run()
        e_casci = mc.e_tot
        print(ok(f"CASCI energy: {e_casci:.10f} Ha  (2e, 2o active space)"))

        # CCSD
        from pyscf import cc  # type: ignore
        mycc = cc.CCSD(mf).run()
        e_ccsd = mycc.e_tot
        e_ccsdT = e_ccsd + mycc.ccsd_t()
        print(ok(f"CCSD energy:  {e_ccsd:.10f} Ha"))
        print(ok(f"CCSD(T):      {e_ccsdT:.10f} Ha"))

        # Sanity: CASCI should be below HF for H2
        assert e_casci < e_hf, f"CASCI should be below HF: {e_casci} vs {e_hf}"
        print(ok("PySCF CASCI smoke test PASSED"))
        return True

    except Exception as e:
        print(fail(f"PySCF CASCI smoke test FAILED: {e}"))
        return False


def smoke_test_pennylane(casci_energy: Optional[float] = None) -> bool:
    """Build an H2 Hamiltonian with PennyLane qchem and check Z2 tapering."""
    print(f"\n{BOLD}--- Smoke Test: PennyLane qchem + Z2 tapering (H2, sto-3g) ----{RESET}")
    try:
        import pennylane as qml  # type: ignore
        from pennylane import qchem  # type: ignore

        import numpy as _np
        symbols = ["H", "H"]
        coords_bohr = _np.array([0.0, 0.0, 0.0,   0.0, 0.0, 1.3889])  # ~0.735 A in Bohr
        H, n_qubits = qchem.molecular_hamiltonian(
            symbols,
            coords_bohr,
            basis="sto-3g",
            mapping="jordan_wigner",
            active_electrons=2,
            active_orbitals=2,
        )
        print(ok(f"PL Hamiltonian built: {n_qubits} qubits, {len(H.ops)} terms"))

        # Z2 symmetry tapering
        generators = qchem.symmetry_generators(H)
        paulixops   = qchem.paulix_ops(generators, n_qubits)
        sectors     = qchem.optimal_sector(H, generators, 2)  # 2 electrons
        H_tapered   = qchem.taper(H, generators, paulixops, sectors)
        n_tap = len(H_tapered.wires)
        print(ok(f"Tapered Hamiltonian: {n_tap} qubits (reduced from {n_qubits})"))

        # Tapered HF reference state
        hf_tapered = qchem.taper_hf(generators, paulixops, sectors, num_electrons=2, num_wires=n_qubits)
        print(ok(f"Tapered HF state:    {hf_tapered.tolist()}"))

        # Quick energy check: NumPy exact solver on tapered H
        import pennylane.numpy as pnp  # type: ignore
        from pennylane import matrix as qml_matrix  # type: ignore
        H_mat = qml_matrix(H_tapered, wire_order=sorted(H_tapered.wires))
        import numpy as np
        eigvals = np.linalg.eigvalsh(H_mat)
        e_exact_pl = float(eigvals[0])
        print(ok(f"PL exact ground energy: {e_exact_pl:.10f} Ha"))

        print(ok("PennyLane qchem smoke test PASSED"))
        return True

    except Exception as e:
        print(fail(f"PennyLane qchem smoke test FAILED: {e}"))
        import traceback; traceback.print_exc()
        return False


def check_suite_and_schema() -> bool:
    print(f"\n{BOLD}--- v3 Configuration Files -------------------------------------{RESET}")
    files = [
        REPO / "benchmarks" / "v3" / "suite_v3.yaml",
        REPO / "schema" / "schema_v3.json",
        REPO / "molecules_v3.json",
    ]
    ok_count = 0
    for p in files:
        if p.exists():
            print(ok(f"{p.relative_to(REPO)}"))
            ok_count += 1
        else:
            print(warn(f"Missing: {p.relative_to(REPO)}"))
    return ok_count == len(files)


def main() -> None:
    ap = argparse.ArgumentParser(description="QEncode v3 environment check")
    ap.add_argument("--smoke-test", action="store_true",
                    help="Run PySCF CASCI + PennyLane smoke tests (takes ~10s)")
    ap.add_argument("--no-colour", action="store_true",
                    help="Disable ANSI colour output")
    args = ap.parse_args()

    if args.no_colour:
        global GREEN, YELLOW, RED, RESET, BOLD
        GREEN = YELLOW = RED = RESET = BOLD = ""

    print(f"\n{BOLD}" + "="*65)
    print("  QEncode v3 - Phase 0 Environment Check")
    print(f"  Python {sys.version}")
    print(f"  Repo:   {REPO}")
    print("="*65 + RESET)

    deps_ok   = check_deps()
    sign_ok   = check_signing_key()
    cat_ok    = check_molecule_catalog()
    cfg_ok    = check_suite_and_schema()

    smoke_ok = True
    if args.smoke_test:
        smoke_ok = smoke_test_pyscf_casci() and smoke_test_pennylane()

    print(f"\n{BOLD}--- Summary ----------------------------------------------------{RESET}")
    results = [
        ("Required dependencies",  deps_ok),
        ("Signing key",            sign_ok),
        ("Molecule catalog",       cat_ok),
        ("v3 config files",        cfg_ok),
    ]
    if args.smoke_test:
        results.append(("Smoke tests", smoke_ok))

    all_ok = True
    for label, status in results:
        if status:
            print(ok(f"{label}"))
        else:
            print(fail(f"{label}"))
            all_ok = False

    if all_ok:
        print(f"\n{GREEN}{BOLD}  [GO] - environment is ready for Phase 1{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{RED}{BOLD}  [NO-GO] - fix the items above before proceeding{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
