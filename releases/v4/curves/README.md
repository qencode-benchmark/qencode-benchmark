# Dissociation Curves (Suite v4.3)

Potential energy curves for diatomics and hydrogen chains, computed with the
QEncode pipeline. Each file contains, per bond length:
- hf, ccsd_t, casscf, casci  (classical reference energies, PySCF cc-pVDZ)
- vqe, gap_mha, n_ops        (ADAPT-VQE via commutator gradients)

VQE target is the active-space CASCI energy. Curves use CASSCF orbitals
(stable across the full dissociation, where Hartree-Fock breaks down).

| file | molecule | active space | points | R range (Å) | n_ops |
|---|---|---|---|---|---|
| h2_dissociation.json  | H2  | [2,2] | 16 | 0.40 – 2.60 | 1 (flat) |
| hf_dissociation.json  | HF  | [2,2] | 16 | 0.70 – 2.50 | 1 – 2  |
| lih_dissociation.json | LiH | [4,4] | 16 | 1.00 – 3.40 | 1 – 3  |
| h4_dissociation.json  | H4  | [4,4] | 16 | 0.60 – 2.60 | 2 – 12 |
| h6_dissociation.json  | H6  | [6,6] | 16 | 0.60 – 2.60 | 7 – 40 |
| n2_dissociation.json  | N2  | [6,6] | 16 | 0.90 – 2.60 | 6 – 40 |

## Notes

**Operator count peaks mid-stretch.** For the larger active spaces the ADAPT
ansatz is cheapest at equilibrium and at full dissociation, and most expensive
in between (N2 peaks at R=1.35 Å, H6 at R=1.40 Å). Points that hit the 40-operator
cap do not reach the certification threshold and are reported as-is.

**`ccsd_t` is null where CCSD(T) did not converge.** This affects the three
longest bond lengths of N2 and H6. The value is left null rather than
substituted — the non-convergence is a property of the method at those
geometries, not a gap in the data.

Only diatomics and hydrogen chains are included: these have a single
well-defined bond coordinate. Polyatomics (H2O, NH3, BeH2, benzene, H2CO,
C4H6) have no single scan coordinate and are not covered here.
