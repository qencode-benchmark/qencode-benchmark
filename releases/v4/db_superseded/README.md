# Superseded entries

These entries were published and are now replaced. They are kept, not deleted, because
they were cited and because a reader holding one needs to be able to find out why it
changed. Each is listed below with the entry that replaces it.

## 2026-09-07 — Z2 symmetry sector fix

Every entry here used a fermion-to-qubit mapping other than Jordan-Wigner. The pipeline
derived the Z2 tapering sector with `pennylane.qchem.optimal_sector`, which hard-codes the
Jordan-Wigner Hartree-Fock occupation string and matches generator support against an
unordered set of wires. Both are wrong for parity and Bravyi-Kitaev.

Two consequences, and an entry here has one or both:

* **Wrong sector.** The tapered Hamiltonian was the restriction of H to a symmetry sector
  that does not contain the ground state, with a minimum 0.30 to 0.76 Ha above CASCI. A
  "constant correction" then added that difference back to every energy, which made the
  numbers look right and hid the fault.
* **Wrong Hartree-Fock reference.** `qchem.taper_hf` builds the reference state with the
  Jordan-Wigner transform whatever the mapping, so the circuit did not start from the
  Hartree-Fock determinant. Entries with this fault alone kept a correct Hamiltonian and a
  correct gap; only the starting state was mislabelled.

Full account: `docs/SECTOR_FIX.md`. The fix is commit ab7185b.

| superseded entry | replaced by | what was wrong |
|---|---|---|
| `BeH2_ccpvdz_PAR_HEA_v4_tapered__sha256_f1deabb249cd79ee.json` | `BeH2_ccpvdz_PAR_HEA_v4_tapered__sha256_c3c5a76f6786a95b.json` | wrong sector |
| `BeH2_ccpvdz_PAR_UCCSD_v4_tapered__sha256_f71541a4f8d3e964.json` | `BeH2_ccpvdz_PAR_UCCSD_v4_tapered__sha256_fee27caf9110d47f.json` | wrong sector |
| `C4H4_ccpvdz_PAR_HEA_v4_casscf_tapered__sha256_0de79dd1611d708a.json` | `C4H4_ccpvdz_PAR_HEA_v4_casscf_tapered__sha256_8b12a22329451c03.json` | wrong sector, wrong HF reference |
| `H2O_ccpvdz_PAR_HEA_v4_tapered__sha256_442576f5b48d4354.json` | `H2O_ccpvdz_PAR_HEA_v4_tapered__sha256_b50cee1c91dc0410.json` | wrong HF reference |
| `H2_ccpvdz_BK_HEA_v4_tapered__sha256_6e206ec6f1f02ea4.json` | `H2_ccpvdz_BK_HEA_v4_tapered__sha256_aa7360a68d23f35c.json` | wrong sector |
| `H2_ccpvdz_BK_UCCSD_v4_tapered__sha256_d3f280f5c8f32ccc.json` | `H2_ccpvdz_BK_UCCSD_v4_tapered__sha256_ffcf6a5b220b54b6.json` | wrong sector |
| `H2_ccpvdz_PAR_HEA_v4_tapered__sha256_47f0004357aeddae.json` | `H2_ccpvdz_PAR_HEA_v4_tapered__sha256_ffbef22125a8b6c9.json` | wrong sector |
| `H2_ccpvdz_PAR_UCCSD_v4_tapered__sha256_b321a0331d6d13eb.json` | `H2_ccpvdz_PAR_UCCSD_v4_tapered__sha256_f208cd1e8667c4bc.json` | wrong sector |
| `H4_ccpvdz_PAR_HEA_v4_tapered__sha256_22ff67c44e248590.json` | `H4_ccpvdz_PAR_HEA_v4_tapered__sha256_45b7b6da4d0a0e63.json` | wrong HF reference |
| `HF_ccpvdz_BK_HEA_v4_tapered__sha256_0d0d66a5769d58ec.json` | `HF_ccpvdz_BK_HEA_v4_tapered__sha256_0ac7d9bfa8215995.json` | wrong sector |
| `HF_ccpvdz_BK_UCCSD_v4_tapered__sha256_42ad3163dd5bcf87.json` | `HF_ccpvdz_BK_UCCSD_v4_tapered__sha256_9175dd737dc93bed.json` | wrong sector |
| `HF_ccpvdz_PAR_HEA_v4_tapered__sha256_007a1905c579328a.json` | `HF_ccpvdz_PAR_HEA_v4_tapered__sha256_5b2d8909e49305a9.json` | wrong sector |
| `HF_ccpvdz_PAR_UCCSD_v4_tapered__sha256_17bfa6743a814ba6.json` | `HF_ccpvdz_PAR_UCCSD_v4_tapered__sha256_b7153d9bdf4c7b85.json` | wrong sector |
| `LiH_ccpvdz_PAR_HEA_v4_tapered__sha256_e94da71e7eb3b98e.json` | `LiH_ccpvdz_PAR_HEA_v4_tapered__sha256_b4373017ff3b1438.json` | wrong HF reference |
| `N2_ccpvdz_PAR_HEA_v4_casscf_tapered__sha256_1a06482cb89e4a67.json` | `N2_ccpvdz_PAR_HEA_v4_casscf_tapered__sha256_1092269e3f92c847.json` | wrong sector, wrong HF reference |
| `N2_ccpvdz_PAR_HEA_v4_casscf_tapered__sha256_9eb43e15f4eea410.json` | `N2_ccpvdz_PAR_HEA_v4_casscf_tapered__sha256_0b03cbea39d46669.json` | wrong sector, wrong HF reference |
| `NH3_ccpvdz_PAR_HEA_v4_tapered__sha256_aa3769fb20846ec5.json` | `NH3_ccpvdz_PAR_HEA_v4_tapered__sha256_985901ca28fa7f97.json` | wrong sector, wrong HF reference |
| `water_dimer_ccpvdz_PAR_HEA_v4_tapered__sha256_f4a38868cf406997.json` | `water_dimer_ccpvdz_PAR_HEA_v4_tapered__sha256_f69363eea8e031ae.json` | wrong HF reference |
