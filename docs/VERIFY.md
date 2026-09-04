# Verifying a QEncode entry

Every published entry can be independently rebuilt. This is how — and, just as important,
what a successful verification does and does not prove.

```bash
python scripts/verify_entry.py releases/v4/db/<entry_id>.json
```

That re-runs the complete pipeline from the entry's own recorded configuration and compares
the result against the stored energy, and checks the SHA-256 content hash for tampering.
No flags are needed on the reference environment.

---

## The two modes, and why there are two

```bash
python scripts/verify_entry.py <entry>.json --mode strict          # default
python scripts/verify_entry.py <entry>.json --mode certification
```

| mode | asserts | holds where |
|---|---|---|
| `strict` | the regenerated energy matches the published one to `--tolerance` (default 10⁻⁶ Ha) | the reference pinned environment |
| `certification` | the regenerated entry still meets the 10 mHa threshold; energy movement is reported but not gated on | any machine |

**This distinction is not bureaucratic — it is the honest limit of the numerics.** A
gradient-free optimiser picks its next step by comparing two nearly equal energies, so a
last-bit arithmetic difference can flip a comparison and send the run into a different
local minimum. Two simulator backends agreeing to 10⁻¹³ Ha on a single evaluation have
landed 11 mHa apart after COBYLA. A different machine is a larger perturbation than that.

Measured by re-running 40 entries on an environment with drifted package versions:

| | energy movement |
|---|---|
| median | 6.7 × 10⁻⁸ Ha |
| 90th percentile | 2.1 × 10⁻³ Ha |
| maximum | 1.4 × 10⁻² Ha |

**17 of 40 exceeded the 10⁻⁶ Ha strict tolerance while still certifying.** That gap is
precisely what the two modes separate. If you are checking our work from your own machine,
`--mode certification` is the one that should pass. If it does not, that is a real finding
and we would like to hear about it.

---

## Verifying from a machine that is not ours

The generator refuses to write an entry from a dirty git tree, or from an environment whose
packages differ from the pins. That is right when *producing* an entry and wrong when
*checking* one, so both overrides pass through:

```bash
python scripts/verify_entry.py <entry>.json \
    --mode certification --allow-dirty --allow-env-drift
```

Neither override touches the single-thread BLAS check, which cannot be bypassed — it is the
one that silently changes results rather than merely annotating them.

To see the command an entry would be re-run with, without running it:

```bash
python scripts/verify_entry.py <entry>.json --dry-run
```

---

## Hash-only check

The content hash proves the JSON has not been edited since publication. It re-runs nothing,
so it is instant:

```bash
python scripts/verify_entry.py <entry>.json --hash-only
```

The hash covers the canonical entry with volatile fields stripped — timestamps, the entry
id, the hash itself, the git commit and the signature. A test asserts that the verifier's
exclusion set matches the pipeline's, because two copies of that list drifting apart would
make the tamper check silently check a different hash.

---

## Which suite, which script

| suite | basis | entries | environment | generator |
|---|---|---|---|---|
| **v4** (current) | cc-pVDZ | `releases/v4/db/` | `requirements-v4.txt` | `scripts/generate_entry_v4.py` |
| v3.1 (frozen) | 6-31G | `releases/v3.1/db/` | `requirements-v3.txt` | `scripts/generate_entry_v3.py` |

`verify_entry.py` reads `schema_version` from the entry and selects the right generator
itself, so the same command works for both.

---

## What has actually been checked

All 54 published v4 entries have been re-run end to end. That sweep found three faults —
all in the verifier, none in the results — including one that made 29 of the 54 impossible
to verify at all. The full account is in [VERIFICATION_SWEEP.md](VERIFICATION_SWEEP.md).

Verification now runs continuously: a six-entry regression subset on every push, and 40
entries weekly in certification mode. See `.github/workflows/ci.yml`.

**Two entries are known not to re-certify on a drifted environment** —
`C4H4_ccpvdz_PAR_HEA` and `C4H4_ccpvdz_JW_HEA`, published at 6.1 and 9.6 mHa, regenerate at
20.5 and 19.0 mHa. Both reproduce exactly on the reference environment, which is what
certification attests. They are flagged rather than withdrawn, and the weekly job knows
about them. See the dated amendments in [LEADERBOARD_RULES_V2.md](LEADERBOARD_RULES_V2.md).

---

## Raw entry JSON

Every entry is publicly readable without a clone:

```
https://raw.githubusercontent.com/qencode-benchmark/qencode-benchmark/HEAD/releases/v4/db/<entry_id>.json
```

Each leaderboard row links to its entry page, which shows the full artifact and the same
raw JSON.

---

## Related

- [`TRUST_POLICY.md`](TRUST_POLICY.md) — the single definition of *certified*
- [`VERIFICATION_SWEEP.md`](VERIFICATION_SWEEP.md) — the full-database re-run
- [`LEADERBOARD_RULES_V2.md`](LEADERBOARD_RULES_V2.md) — ranking rules and dated amendments
- [`../SCHEMA.md`](../SCHEMA.md) — every field in an entry
