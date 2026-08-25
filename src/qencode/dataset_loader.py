"""
Load benchmark entries and molecule catalog.

Unified module for entry loading (load_entry.py) and catalog (catalog.py).
"""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from qiskit import qpy
from qiskit.qasm2 import loads as qasm2_loads
from qiskit.quantum_info import SparsePauliOp, Statevector

try:
    from qiskit import transpile as _qiskit_transpile
    _SV_BASIS_GATES = ["id", "rz", "sx", "x", "cx"]
except ImportError:
    _qiskit_transpile = None  # type: ignore
    _SV_BASIS_GATES = []

EPS0 = 1e-9


def _transpile_for_sv(circ):
    """Transpile a circuit to basic gates so statevector sim avoids slow matrix expm.

    PauliEvolutionGates (used by UCCSD ansatzes) require scipy.sparse.linalg.expm
    which is O(n^3) per gate. Transpiling to {rz, sx, x, cx} replaces them with
    explicit gates that statevector sim can evaluate in O(n) per gate, giving a
    10000x+ speedup for 12-qubit UCCSD circuits.
    Returns the transpiled circuit, or the original if transpilation fails.
    """
    if _qiskit_transpile is None:
        return circ
    # Only transpile if the circuit likely has high-level / non-basis gates
    # (avoid unnecessary overhead for already-basic circuits)
    try:
        return _qiskit_transpile(circ, basis_gates=_SV_BASIS_GATES, optimization_level=0)
    except Exception:
        return circ


# ----- Hamiltonian & circuits from entry JSON -----


def load_hamiltonian(data: Dict[str, Any]) -> SparsePauliOp:
    terms = data["artifacts"]["qubit_hamiltonian"]["pauli_terms"]
    paulis = [t["pauli"] for t in terms]
    coeffs = []
    for t in terms:
        if "coeff" in t:
            coeffs.append(complex(t["coeff"]))
        else:
            r = float(t.get("coeff_real", 0))
            i = float(t.get("coeff_imag", 0))
            coeffs.append(complex(r, i))
    return SparsePauliOp(paulis, coeffs)


def load_hf(data: Dict[str, Any]):
    c = data["artifacts"]["circuits"]
    b64 = c.get("hf_qpy_b64")
    if b64:
        buf = io.BytesIO(base64.b64decode(b64))
        hf = qpy.load(buf)[0]
        hf = hf.remove_final_measurements(inplace=False)
        return hf
    qasm = c.get("hartree_fock_qasm")
    if qasm:
        hf = qasm2_loads(qasm)
        hf = hf.remove_final_measurements(inplace=False)
        return hf
    return None


def load_ansatz_template(data: Dict[str, Any]):
    c = data["artifacts"]["circuits"]
    b64 = c.get("ansatz_template_qpy_b64")
    if b64:
        buf = io.BytesIO(base64.b64decode(b64))
        ans = qpy.load(buf)[0]
        ans = ans.remove_final_measurements(inplace=False)
        return ans, "qpy_b64"
    hx = c.get("ansatz_template_qpy_hex")
    if hx:
        buf = io.BytesIO(bytes.fromhex(hx))
        ans = qpy.load(buf)[0]
        ans = ans.remove_final_measurements(inplace=False)
        return ans, "qpy_hex"
    qasm = c.get("ansatz_template_qasm")
    if qasm:
        ans = qasm2_loads(qasm)
        ans = ans.remove_final_measurements(inplace=False)
        return ans, "qasm2"
    raise ValueError("No ansatz template found (expected qpy_b64 / qpy_hex / qasm).")


def bind_all_parameters(circ, values: Dict) -> Any:
    out = circ.assign_parameters(values, inplace=False)
    try:
        gp = out.global_phase
        if hasattr(gp, "bind"):
            new_gp = gp.bind(values)
            out.global_phase = float(new_gp)
        else:
            out.global_phase = float(gp)
    except Exception:
        pass
    return out


def expectation_energy(H: SparsePauliOp, circ) -> float:
    sv = Statevector.from_instruction(circ)
    val = sv.expectation_value(H)
    return float(np.real(val))


def pick_evaluation_mode(
    H: SparsePauliOp, hf, ansatz, ansatz_includes_hf: Optional[bool] = None
) -> Tuple[Any, str, Dict[str, float]]:
    stats: Dict[str, float] = {}

    # Transpile ansatz to basic gates before any statevector evaluation.
    # UCCSD and other ansatzes may store PauliEvolutionGates which require
    # scipy.sparse.linalg.expm (O(n^3) per gate). Transpiling once to {rz,sx,x,cx}
    # avoids per-evaluation matrix exponentials, giving 10000x+ speedup on large circuits.
    ansatz_sv = _transpile_for_sv(ansatz)

    # Fast-path: if ansatz_includes_hf is explicitly set, skip expensive stats evals
    # (the 3 statevector calls below are just for diagnostic stats / auto-detection).
    if ansatz_includes_hf is True:
        return ansatz_sv, "ansatz_only_explicit_includes_hf", stats
    if ansatz_includes_hf is False and hf is not None:
        comp = hf.compose(ansatz_sv, inplace=False)
        comp = comp.remove_final_measurements(inplace=False)
        return comp, "hf_plus_ansatz_explicit", stats

    # Auto-detection path: run diagnostic evaluations to determine if HF is embedded.
    e_hf = None
    if hf is not None:
        hf_sv = _transpile_for_sv(hf)
        e_hf = expectation_energy(H, hf_sv)
        stats["E_hf"] = e_hf
    bind0 = {p: 0.0 for p in list(ansatz_sv.parameters)}
    a0 = bind_all_parameters(ansatz_sv, bind0)
    e_a0 = expectation_energy(H, a0)
    stats["E_ansatz_0"] = e_a0
    rng = np.random.default_rng(123)
    x = rng.normal(0, 0.3, size=len(ansatz_sv.parameters))
    bindr = {p: float(v) for p, v in zip(list(ansatz_sv.parameters), x)}
    ar = bind_all_parameters(ansatz_sv, bindr)
    stats["E_ansatz_rand"] = expectation_energy(H, ar)

    if hf is not None:
        comp = hf.compose(ansatz_sv, inplace=False)
        comp = comp.remove_final_measurements(inplace=False)
        c0 = bind_all_parameters(comp, {p: 0.0 for p in list(comp.parameters)})
        e_c0 = expectation_energy(H, c0)
        stats["E_comp_0"] = e_c0
        if (abs(e_c0) < EPS0) and (e_hf is not None) and (abs(e_a0 - e_hf) < 1e-6):
            return ansatz_sv, "ansatz_only_detected_initial_state", stats
        return comp, "hf_plus_ansatz", stats
    return ansatz_sv, "ansatz_only_no_hf_in_entry", stats


def load_entry(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    H = load_hamiltonian(data)
    hf = load_hf(data)
    ansatz, ans_source = load_ansatz_template(data)
    ansatz_includes_hf = data.get("artifacts", {}).get("circuits", {}).get("ansatz_includes_hf")
    chosen, mode, stats = pick_evaluation_mode(H, hf, ansatz, ansatz_includes_hf)
    return data, H, hf, ansatz, chosen, mode, ans_source, stats


# ----- Molecule catalog -----


def atoms_to_pyscf(atoms: List[Dict[str, Any]]) -> str:
    parts = []
    for at in atoms:
        x, y, z = at["xyz"][:3]
        parts.append(f"{at['element']} {x} {y} {z}")
    return "; ".join(parts)


def load_catalog(repo_root: Path) -> Dict[str, Any]:
    v2 = repo_root / "molecules_v2.json"
    v1 = repo_root / "molecules_v1.json"
    if v2.exists():
        data = json.loads(v2.read_text(encoding="utf-8"))
        data["_format"] = "v2"
        return data
    if v1.exists():
        data = json.loads(v1.read_text(encoding="utf-8"))
        data["_format"] = "v1"
        return data
    raise FileNotFoundError(
        f"No molecule catalog found. Add molecules_v1.json or molecules_v2.json in {repo_root}"
    )


def load_catalog_v2_only(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / "molecules_v2.json"
    if not path.exists():
        raise FileNotFoundError(
            f"molecules_v2.json not found in {repo_root}. Add it for v2 entry generation."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    data["_format"] = "v2"
    return data


def resolve_molecule(
    catalog: Dict[str, Any],
    molecule: str,
    variant: Optional[str] = None,
) -> Dict[str, Any]:
    fmt = catalog.get("_format", "v1")
    if fmt == "v2":
        entries = catalog.get("entries", catalog.get("molecules", []))
        v = variant or "default"
        for m in entries:
            if m.get("molecule") == molecule and m.get("variant", "default") == v:
                return {
                    "geometry": m["geometry"],
                    "charge": int(m.get("charge", 0)),
                    "spin": int(m.get("spin", 0)),
                }
        raise ValueError(
            f"Unknown molecule/variant in catalog: molecule={molecule!r} variant={v!r}"
        )
    for m in catalog.get("molecules", []):
        if m.get("name") != molecule:
            continue
        atoms = m.get("atoms")
        if not atoms:
            raise ValueError(f"Molecule {molecule!r} has no 'atoms' in catalog.")
        geometry = atoms_to_pyscf(atoms)
        multiplicity = int(m.get("multiplicity", 1))
        spin = multiplicity - 1
        charge = int(m.get("charge", 0))
        return {"geometry": geometry, "charge": charge, "spin": spin}
    raise ValueError(f"Unknown molecule in catalog: {molecule!r}")


def list_molecules(catalog: Dict[str, Any]) -> List[str]:
    fmt = catalog.get("_format", "v1")
    if fmt == "v2":
        entries = catalog.get("entries", catalog.get("molecules", []))
        return sorted({m["molecule"] for m in entries if m.get("molecule")})
    return sorted({m["name"] for m in catalog.get("molecules", []) if m.get("name")})


def list_molecule_variants(catalog: Dict[str, Any]) -> List[Tuple[str, str]]:
    fmt = catalog.get("_format", "v1")
    if fmt == "v2":
        entries = catalog.get("entries", catalog.get("molecules", []))
        out = []
        for m in entries:
            mol = m.get("molecule")
            var = m.get("variant", "default")
            if mol:
                out.append((mol, var))
        return sorted(out, key=lambda x: (x[0].lower(), x[1].lower()))
    names = list_molecules(catalog)
    return [(n, "default") for n in names]


__all__ = [
    "load_hamiltonian",
    "load_hf",
    "load_ansatz_template",
    "bind_all_parameters",
    "expectation_energy",
    "pick_evaluation_mode",
    "load_entry",
    "atoms_to_pyscf",
    "load_catalog",
    "load_catalog_v2_only",
    "resolve_molecule",
    "list_molecules",
    "list_molecule_variants",
]
