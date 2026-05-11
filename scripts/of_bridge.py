#!/usr/bin/env python3
"""
of_bridge.py — OpenFermion ↔ PennyLane Hamiltonian bridge (Phase 2)
====================================================================
Used by generate_entry_v3.py for:
  - Parity mapping   (PL 0.44 does not support it natively)
  - Corrected BK     (avoids PL 0.44 constant-drop + wrong taper_hf)

Flow:
  PySCF CASCI active-space integrals
    → OpenFermion InteractionOperator → FermionOperator
    → QubitOperator  (JW / BK / Parity via OpenFermion transforms)
    → PennyLane Hamiltonian

Built-in verification:
  After building the qubit Hamiltonian, exact diagonalisation is performed
  and the ground state energy is checked against the PySCF CASCI value.
  Raises ValueError if the deviation exceeds `verify_tol` (default 1e-4 Ha).

Spin-orbital convention (OpenFermion interleaved ordering):
  spin-orbital 0 = spatial-orbital 0, alpha (↑)
  spin-orbital 1 = spatial-orbital 0, beta  (↓)
  spin-orbital 2 = spatial-orbital 1, alpha
  spin-orbital 3 = spatial-orbital 1, beta
  ...

2e integral convention:
  PySCF ao2mo.restore(1, ...) → eri[p,q,r,s] = (pq|rs) chemist notation
  OpenFermion InteractionOperator two_body_tensor[p,q,r,s] → physicist <pq|rs>
  Conversion: <pq|rs>_phys = (pr|qs)_chem
              h2_of[p,q,r,s] = eri_chem[p,r,q,s]
              i.e., h2_of = eri.transpose(0, 2, 1, 3)
"""
from __future__ import annotations

import numpy as np
from typing import Tuple

__all__ = [
    "build_qubit_hamiltonian",
    "parity_hf_state",
    "verify_hamiltonian",
]


# ─── OpenFermion QubitOperator → PennyLane Hamiltonian ────────────────────────

def _qubitop_to_pl(qubit_op) -> Tuple:
    """
    Convert an OpenFermion QubitOperator to a PennyLane Hamiltonian.

    Returns (H, n_qubits) where n_qubits = max qubit index + 1.
    Empty operator or all-zero coefficients returns identity on wire 0.
    """
    import pennylane as qml
    from functools import reduce
    import operator as op_mod

    coeffs = []
    ops = []
    max_wire = -1

    for pauli_term, coeff in qubit_op.terms.items():
        coeff_r = float(np.real(coeff))
        if abs(coeff_r) < 1e-12:
            continue

        if not pauli_term:
            # Scalar / identity term
            ops.append(qml.Identity(0))
            coeffs.append(coeff_r)
            continue

        pauli_ops = []
        for wire_idx, pauli_char in sorted(pauli_term):
            max_wire = max(max_wire, wire_idx)
            if pauli_char == "X":
                pauli_ops.append(qml.PauliX(wire_idx))
            elif pauli_char == "Y":
                pauli_ops.append(qml.PauliY(wire_idx))
            elif pauli_char == "Z":
                pauli_ops.append(qml.PauliZ(wire_idx))

        if len(pauli_ops) == 1:
            ops.append(pauli_ops[0])
        else:
            ops.append(reduce(op_mod.matmul, pauli_ops))
        coeffs.append(coeff_r)

    if not ops:
        return qml.Hamiltonian(np.array([0.0]), [qml.Identity(0)]), 1

    n_qubits = max_wire + 1
    return qml.Hamiltonian(np.array(coeffs), ops), n_qubits


# ─── PySCF CASCI integrals → OpenFermion FermionOperator ─────────────────────

def _pyscf_to_fermion_op(mf, n_electrons: int, n_orbitals: int):
    """
    Extract CASCI active-space integrals from a PySCF RHF object and build an
    OpenFermion FermionOperator by direct spin-orbital expansion.

    Parameters
    ----------
    mf         : PySCF RHF mean-field object (already converged)
    n_electrons: number of active electrons
    n_orbitals : number of active spatial orbitals

    Returns
    -------
    fermion_op : OpenFermion FermionOperator
    n_modes    : number of spin orbitals (= 2 * n_orbitals)

    Spin-orbital convention (interleaved):
        spatial orbital p, spin σ ∈ {0(α), 1(β)}  →  spin-orbital index 2p+σ

    Hamiltonian form:
        H = e_core
          + Σ_{p,q,σ}   h1eff[p,q]   a†_{2p+σ} a_{2q+σ}
          + ½ Σ_{p,q,r,s,σ,τ}  h2e[p,q,r,s]  a†_{2p+σ} a†_{2r+τ} a_{2s+τ} a_{2q+σ}

    where h2e[p,q,r,s] = (pq|rs) in chemist notation (= ⟨pq|rs⟩ in physicist).
    The FermionOperator accumulates all terms explicitly; OpenFermion's JW/BK
    transforms then impose the correct fermionic anticommutation relations.

    Why not InteractionOperator?
        InteractionOperator expects *spin-orbital* tensors (shape 2n×2n for 1e,
        (2n)^4 for 2e).  Passing spatial-only tensors (n×n, n^4) silently builds
        a Hamiltonian for half the modes, giving wrong ground-state energies.
        Building FermionOperator directly avoids this pitfall entirely.
    """
    from pyscf import mcscf, ao2mo
    from openfermion import FermionOperator

    ncas    = n_orbitals
    nelec   = n_electrons
    n_modes = 2 * ncas

    # ── Active-space integrals ────────────────────────────────────────────────
    cas            = mcscf.CASCI(mf, ncas, nelec)
    h1eff, e_core  = cas.get_h1eff()                      # (ncas,ncas), scalar
    h2e            = ao2mo.restore(1, cas.get_h2eff(), ncas)  # (ncas,)^4 chemist

    # ── Build FermionOperator by direct spin-orbital expansion ────────────────
    fop = FermionOperator('', float(e_core))

    # — One-body terms —
    for p in range(ncas):
        for q in range(ncas):
            coeff = float(h1eff[p, q])
            if abs(coeff) < 1e-12:
                continue
            for sigma in (0, 1):
                fop += FermionOperator(
                    ((2*p + sigma, 1), (2*q + sigma, 0)), coeff
                )

    # — Two-body terms —
    # ½ Σ_{pqrs,σ,τ} (pq|rs)_chem  a†_{2p+σ} a†_{2r+τ} a_{2s+τ} a_{2q+σ}
    for p in range(ncas):
        for q in range(ncas):
            for r in range(ncas):
                for s in range(ncas):
                    coeff = 0.5 * float(h2e[p, q, r, s])
                    if abs(coeff) < 1e-12:
                        continue
                    for sigma in (0, 1):
                        for tau in (0, 1):
                            fop += FermionOperator(
                                ((2*p + sigma, 1),
                                 (2*r + tau,   1),
                                 (2*s + tau,   0),
                                 (2*q + sigma, 0)),
                                coeff,
                            )

    return fop, n_modes


# ─── Qubit transforms ─────────────────────────────────────────────────────────

def _apply_transform(fermion_op, mapping: str, n_modes: int):
    """
    Apply a qubit encoding transform to a FermionOperator.

    Supported mappings: jordan_wigner, bravyi_kitaev, parity.
    Returns an OpenFermion QubitOperator.
    """
    mapping = mapping.lower().replace("-", "_").replace(" ", "_")
    aliases = {"jw": "jordan_wigner", "bk": "bravyi_kitaev", "p": "parity"}
    mapping = aliases.get(mapping, mapping)

    if mapping == "jordan_wigner":
        from openfermion.transforms import jordan_wigner
        return jordan_wigner(fermion_op)

    elif mapping == "bravyi_kitaev":
        from openfermion.transforms import bravyi_kitaev
        return bravyi_kitaev(fermion_op)

    elif mapping == "parity":
        try:
            from openfermion.transforms import binary_code_transform, parity_code
            return binary_code_transform(fermion_op, parity_code(n_modes))
        except ImportError as exc:
            raise ImportError(
                "Parity mapping requires openfermion >= 1.3 with binary_code_transform. "
                "Upgrade: pip install --upgrade openfermion"
            ) from exc

    else:
        raise ValueError(
            f"Unknown mapping: {mapping!r}. "
            "Choose jordan_wigner (jw), bravyi_kitaev (bk), or parity (p)."
        )


# ─── HF reference state in qubit basis ───────────────────────────────────────

def parity_hf_state(n_electrons: int, n_orbitals: int) -> np.ndarray:
    """
    Return the Hartree-Fock reference state in the parity basis (BEFORE tapering).

    The parity encoding maps occupation-number state |f_0,...,f_{n-1}> to
    a parity-cumsum state |p_0,...,p_{n-1}> where p_k = Σ_{i=0}^{k} f_i  mod 2.

    The JW HF state fills the lowest n_electrons spin-orbitals in interleaved
    alpha/beta OpenFermion ordering:
        f_k = 1  if  k < n_electrons,  else 0
    """
    n_modes  = 2 * n_orbitals
    jw_state = np.array([1 if k < n_electrons else 0 for k in range(n_modes)], dtype=int)
    parity   = np.cumsum(jw_state) % 2
    return parity


# ─── Ground-state verification ────────────────────────────────────────────────

def verify_hamiltonian(H, e_casci: float, tol: float = 1e-4, label: str = "") -> float:
    """
    Exact-diagonalise H and compare ground state energy to e_casci.

    Returns the exact ground state energy.
    Raises ValueError if |gs_energy - e_casci| > tol.
    """
    import pennylane as qml

    wires   = sorted(H.wires)
    mat     = qml.matrix(H, wire_order=wires)
    gs_e    = float(np.linalg.eigvalsh(mat)[0])
    dev     = abs(gs_e - e_casci)
    info    = f" [{label}]" if label else ""
    if dev > tol:
        raise ValueError(
            f"OF bridge verification FAILED{info}: "
            f"gs={gs_e:.8f} Ha, CASCI={e_casci:.8f} Ha, "
            f"deviation={dev:.2e} Ha (tol={tol:.1e} Ha)\n"
            "  Possible causes: wrong integral transpose, "
            "spin-orbital ordering mismatch, or unsupported pyscf version."
        )
    return gs_e


# ─── Main public interface ────────────────────────────────────────────────────

def build_qubit_hamiltonian(
    mf,
    n_electrons:  int,
    n_orbitals:   int,
    mapping:      str,
    e_casci:      float,
    verify_tol:   float = 1e-4,
) -> Tuple:
    """
    Build a PennyLane Hamiltonian from PySCF active-space integrals via OpenFermion.

    Parameters
    ----------
    mf          : PySCF RHF mean-field object (already converged, NOT re-run here)
    n_electrons : number of active electrons
    n_orbitals  : number of active spatial orbitals
    mapping     : 'jordan_wigner' | 'jw' | 'bravyi_kitaev' | 'bk' | 'parity' | 'p'
    e_casci     : CASCI ground-state energy from PySCF (used for verification)
    verify_tol  : max allowed |gs - e_casci| deviation in Ha (default 1e-4)

    Returns
    -------
    H        : qml.Hamiltonian
    n_qubits : int  (number of qubits before any tapering)
    gs_exact : float  (exact GS energy from diagonalisation, for diagnostics)

    Raises
    ------
    ValueError   if the verification check fails
    ImportError  if openfermion is not installed or parity transform unavailable
    """
    # 1. Extract integrals → FermionOperator
    fermion_op, n_modes = _pyscf_to_fermion_op(mf, n_electrons, n_orbitals)

    # 2. Apply qubit encoding
    qubit_op = _apply_transform(fermion_op, mapping, n_modes)

    # 3. Convert to PennyLane Hamiltonian
    H, n_qubits = _qubitop_to_pl(qubit_op)

    # 4. Verify ground state energy matches CASCI
    mol_label = f"{mapping.upper()} {n_electrons}e/{n_orbitals}o"
    gs_exact  = verify_hamiltonian(H, e_casci, tol=verify_tol, label=mol_label)

    return H, n_qubits, gs_exact


# ─── Smoke test (run with: python scripts/of_bridge.py) ──────────────────────

if __name__ == "__main__":
    """
    Quick smoke test: builds H2 JW + BK + Parity Hamiltonians via the bridge
    and checks ground-state energies against a reference CASCI value.

    Run on Ubuntu:
      conda activate qencode
      python scripts/of_bridge.py
    """
    print("=" * 60)
    print("  of_bridge smoke test — H2 sto-3g")
    print("=" * 60)

    from pyscf import gto, scf
    import pennylane as qml

    ANG_TO_BOHR = 1.8897259886

    # H2 geometry (same as molecules_v3.json)
    atom_str = "H 0.0 0.0 0.0; H 0.0 0.0 0.735"
    mol_pyscf = gto.Mole()
    mol_pyscf.atom    = atom_str
    mol_pyscf.basis   = "sto-3g"
    mol_pyscf.charge  = 0
    mol_pyscf.spin    = 0
    mol_pyscf.verbose = 0
    mol_pyscf.build()

    mf_h2 = scf.RHF(mol_pyscf).run()

    # Reference CASCI energy (H2 [2e, 2o] sto-3g)
    from pyscf import mcscf
    mc = mcscf.CASCI(mf_h2, 2, 2)
    mc.run()
    e_casci_h2 = float(mc.e_tot)
    print(f"  PySCF CASCI: {e_casci_h2:.10f} Ha")
    print()

    all_ok = True
    for mapping in ("jordan_wigner", "bravyi_kitaev", "parity"):
        try:
            H, nq, gs = build_qubit_hamiltonian(
                mf_h2, 2, 2, mapping, e_casci_h2, verify_tol=1e-4
            )
            deviation = abs(gs - e_casci_h2)
            print(f"  {mapping:<20}: {nq} qubits, gs={gs:.8f} Ha, "
                  f"dev={deviation:.2e} Ha  [OK]")
            if mapping == "parity":
                ps = parity_hf_state(2, 2)
                print(f"    parity HF state (before taper): {ps.tolist()}")
        except Exception as ex:
            print(f"  {mapping:<20}: FAILED — {ex}")
            all_ok = False

    print()
    print("  " + ("ALL CHECKS PASSED" if all_ok else "SOME CHECKS FAILED"))
    print("=" * 60)
