#!/usr/bin/env python3
import argparse
import base64
import io
import json
from pathlib import Path
from typing import Any, Dict, Tuple, Optional

import numpy as np
from qiskit import qpy
from qiskit.qasm2 import loads as qasm2_loads
from qiskit.quantum_info import SparsePauliOp, Statevector


EPS0 = 1e-9


def load_hamiltonian(data: Dict[str, Any]) -> SparsePauliOp:
    terms = data["artifacts"]["qubit_hamiltonian"]["pauli_terms"]
    paulis = [t["pauli"] for t in terms]
    coeffs = [complex(t["coeff"]) for t in terms]
    return SparsePauliOp(paulis, coeffs)


def load_hf(data: Dict[str, Any]):
    qasm = data["artifacts"]["circuits"].get("hartree_fock_qasm")
    if not qasm:
        return None
    hf = qasm2_loads(qasm)
    hf = hf.remove_final_measurements(inplace=False)
    return hf


def load_ansatz_template(data: Dict[str, Any]):
    c = data["artifacts"]["circuits"]

    # Preferred: QPY base64
    b64 = c.get("ansatz_template_qpy_b64")
    if b64:
        buf = io.BytesIO(base64.b64decode(b64))
        ans = qpy.load(buf)[0]
        ans = ans.remove_final_measurements(inplace=False)
        return ans, "qpy_b64"

    # Alternate: QPY hex
    hx = c.get("ansatz_template_qpy_hex")
    if hx:
        buf = io.BytesIO(bytes.fromhex(hx))
        ans = qpy.load(buf)[0]
        ans = ans.remove_final_measurements(inplace=False)
        return ans, "qpy_hex"

    # Fallback: OpenQASM2
    qasm = c.get("ansatz_template_qasm")
    if qasm:
        ans = qasm2_loads(qasm)
        ans = ans.remove_final_measurements(inplace=False)
        return ans, "qasm2"

    raise ValueError("No ansatz template found (expected qpy_b64 / qpy_hex / qasm).")


def bind_all_parameters(circ, values: Dict) -> Any:
    """
    Bind *all* parameters, including parameters hiding inside global_phase.
    """
    # First bind circuit parameters
    out = circ.assign_parameters(values, inplace=False)

    # Then try to bind global_phase if it’s a ParameterExpression
    try:
        gp = out.global_phase
        # In some versions gp has .bind() with a dict
        if hasattr(gp, "bind"):
            new_gp = gp.bind(values)
            out.global_phase = float(new_gp)
        else:
            # sometimes it's numeric already
            out.global_phase = float(gp)
    except Exception:
        # Don't crash if global_phase binding isn't needed
        pass

    return out


def expectation_energy(H: SparsePauliOp, circ) -> float:
    sv = Statevector.from_instruction(circ)
    val = sv.expectation_value(H)
    return float(np.real(val))


def pick_evaluation_mode(H: SparsePauliOp, hf, ansatz) -> Tuple[Any, str, Dict[str, float]]:
    """
    Decide whether to use:
      - hf + ansatz   (normal case)
      - ansatz only   (if ansatz already includes HF initial state)
    """
    stats: Dict[str, float] = {}

    e_hf = None
    if hf is not None:
        e_hf = expectation_energy(H, hf)
        stats["E_hf"] = e_hf

    # theta=0 on ansatz-only
    bind0 = {p: 0.0 for p in list(ansatz.parameters)}
    a0 = bind_all_parameters(ansatz, bind0)
    e_a0 = expectation_energy(H, a0)
    stats["E_ansatz_0"] = e_a0

    # theta=random on ansatz-only (quick sanity)
    rng = np.random.default_rng(123)
    x = rng.normal(0, 0.3, size=len(ansatz.parameters))
    bindr = {p: float(v) for p, v in zip(list(ansatz.parameters), x)}
    ar = bind_all_parameters(ansatz, bindr)
    e_ar = expectation_energy(H, ar)
    stats["E_ansatz_rand"] = e_ar

    # hf+ansatz energies (if hf exists)
    if hf is not None:
        comp = hf.compose(ansatz, inplace=False)
        comp = comp.remove_final_measurements(inplace=False)

        c0 = bind_all_parameters(comp, {p: 0.0 for p in list(comp.parameters)})
        e_c0 = expectation_energy(H, c0)
        stats["E_comp_0"] = e_c0

        # If composing produces ~0 but ansatz-only matches HF, it means ansatz already includes HF
        if (abs(e_c0) < EPS0) and (e_hf is not None) and (abs(e_a0 - e_hf) < 1e-6):
            return ansatz, "ansatz_only_detected_initial_state", stats

        # Otherwise normal
        return comp, "hf_plus_ansatz", stats

    # No HF stored: use ansatz only
    return ansatz, "ansatz_only_no_hf_in_entry", stats


def load_entry(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    H = load_hamiltonian(data)
    hf = load_hf(data)
    ansatz, ans_source = load_ansatz_template(data)

    chosen, mode, stats = pick_evaluation_mode(H, hf, ansatz)

    return data, H, hf, ansatz, chosen, mode, ans_source, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()

    path = Path(args.file)
    data, H, hf, ansatz, chosen, mode, ans_source, stats = load_entry(path)

    print(f"✅ Loaded: {path.resolve()}")
    if args.summary:
        problem = data.get("problem", {}) or {}
        mol = problem.get("molecule", "UNKNOWN")
        basis = problem.get("basis", "UNKNOWN")
        ans_type = problem.get("ansatz_type", "UNKNOWN")

        print(f"   molecule={mol} basis={basis} ansatz={ans_type} source={ans_source}")
        print(f"   H:  num_qubits={H.num_qubits} terms={len(H.coeffs)}")

        if hf is not None:
            print(f"   HF: num_qubits={hf.num_qubits} depth={hf.depth()} ops={sum(hf.count_ops().values())}")
        else:
            print("   HF: (none)")

        print(f"   Ansatz:   num_qubits={ansatz.num_qubits} depth={ansatz.depth()} params={len(ansatz.parameters)}")
        print(f"   Chosen:   num_qubits={chosen.num_qubits} depth={chosen.depth()} params={len(chosen.parameters)}")
        print(f"   Mode: {mode}")

        if "E_hf" in stats:
            print(f"   Energy <HF|H|HF> = {stats['E_hf']:.12f}")
        print(f"   Energy <ansatz(theta=0)|H|ansatz(theta=0)> = {stats['E_ansatz_0']:.12f}")
        if "E_comp_0" in stats:
            print(f"   Energy <(HF+ansatz)(theta=0)|H|(HF+ansatz)(theta=0)> = {stats['E_comp_0']:.12f}")
        print(f"   Energy <chosen(theta=random)|H|chosen(theta=random)> = {stats['E_ansatz_rand']:.12f}")


if __name__ == "__main__":
    main()

