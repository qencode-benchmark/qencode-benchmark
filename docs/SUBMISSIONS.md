# Benchmark submissions

There are two ways to get a result onto QEncode, and the free one is not a lesser version
of the paid one — it runs the same pipeline and produces the same artifact.

---

## Run it yourself — free, no account

The full pipeline is open source. You generate the entry, you keep it, and you can publish
it or not.

```bash
pip install qencode-benchmark
qencode run --molecule LiH --mapping jordan_wigner --ansatz-type uccsd --out-dir out
```

The output is a JSON entry carrying the Hamiltonian, the optimal parameters, classical
references, circuit and T-gate counts, the complete software environment, and a SHA-256
content hash over all of it. Anyone can re-check it:

```bash
python scripts/verify_entry.py out/<entry_id>.json
```

Full walkthrough: [`../QUICKSTART.md`](../QUICKSTART.md).

**To have a self-run entry listed on the public leaderboard**, open an issue or email
the entry JSON to **support@qencode-benchmark.org**. It must have been produced by the
unmodified pipeline at the current suite definitions, and it will be re-run on the
reference environment before listing — the same check every entry in the database has
been through.

Entries that miss the 10 mHa threshold are published in the research tier rather than
rejected. A research-tier entry is a real result that met the method's limit on a hard
system; nothing is discarded for being unflattering.

---

## Managed certification — paid

If you need an independently produced, signed artifact for a paper, grant application or
hardware evaluation, QEncode runs the benchmark on its own reference environment and
returns:

- the entry JSON, produced by the same pipeline you could run yourself
- an **Ed25519 signature** over the content hash
- a verification page and a badge, both publicly checkable
- a validation summary and leaderboard-eligibility determination

What you are buying is independent execution and a signature — **not a different or
better benchmark, and not a guaranteed outcome.** The criterion is identical, and managed
certification cannot make an entry certify that would not certify when self-run.

Pricing and application: <https://www.qencode-benchmark.org/pricing> ·
<https://www.qencode-benchmark.org/apply>

---

## What certification means

An entry is *certified* when its gap to the active-space CASCI reference is below
**10 mHartree**. That is the whole criterion — see [`TRUST_POLICY.md`](TRUST_POLICY.md)
for what it attests, what it does not, and the markers (chemical accuracy, certification
margin, the CCSD(T) badge) that are reported alongside but are not certification.

Ranking, eligibility per category and the dated amendments are in
[`LEADERBOARD_RULES_V2.md`](LEADERBOARD_RULES_V2.md).

---

## Contact

**support@qencode-benchmark.org** — questions, a result you would like listed, or a
molecule you think belongs in the suite. Issues and pull requests are welcome; see
[`../CONTRIBUTING.md`](../CONTRIBUTING.md).
