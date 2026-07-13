# Dissociation Curves (Suite v4.3)

Potential energy curves for diatomics and hydrogen chains, computed with the
QEncode pipeline. Each file contains, per bond length:
- hf, ccsd_t, casscf, casci  (classical reference energies, PySCF cc-pVDZ)
- vqe, gap_mha, n_ops        (ADAPT-VQE via commutator gradients)

VQE target is the active-space CASCI energy. Curves use CASSCF orbitals
(stable across the full dissociation, where Hartree-Fock breaks down).

Molecules: HF, LiH, H4, H6 (chains), N2 (triple bond).
