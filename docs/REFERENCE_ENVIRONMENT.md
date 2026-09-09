# A container closes the cross-machine gap. A package list does not.

[`CROSS_MACHINE.md`](CROSS_MACHINE.md) ends with an open question. Every entry in the
suite reproduces bit-for-bit on the machine that generated it and on no other, and forcing
the BLAS kernel fixes the electronic-structure half but not the variational half. The
remaining suspects were below the packages: the two machines run different C libraries,
and a probe found `expm1` differing between them. The document's conclusion was that
bit-for-bit reproduction "needs identical arithmetic all the way down, i.e. a container
image with a fixed C library". That was a prediction. This is the measurement.

## The image

`Dockerfile.reference`. It differs from the ordinary `Dockerfile` in three ways, each
chosen from something that was measured to matter:

| | why |
|---|---|
| base pinned by **digest**, not tag | `python:3.11-slim` drifts. The digest gives Python 3.11.15, the interpreter every published entry records, and glibc 2.41 on both machines |
| `OPENBLAS_CORETYPE=Haswell` | OpenBLAS picks its kernel from the CPU at run time, so an AVX-512 host and an AVX2 host sum in a different order. Haswell is the highest kernel both target machines can execute |
| `NPY_DISABLE_CPU_FEATURES=AVX512…` | NumPy dispatches on the host CPU independently of OpenBLAS. Harmless on a machine that has no AVX-512 |

Threads are pinned to one, as in the ordinary image, and `PYTHONHASHSEED=0` removes
dictionary-ordering as a variable.

**The image is built once and moved**, `docker save | ssh … podman load`, rather than
built twice from the same Dockerfile. Two builds can pick up different Debian package
builds, and the point of this exercise is to remove variables rather than assume they are
absent.

`tools/reference_fingerprint.py` reports what an environment actually is: the C library,
the BLAS kernel the library says it selected, and the content hash of every shared object
on the numerical path. Run inside the image on both machines, everything matches except
the host processor and its instruction flags:

    libc                     glibc 2.41 / glibc 2.41
    openblas_core            Haswell / Haswell
    libc.so.6                fa430b8f298f817a / fa430b8f298f817a
    libm.so.6                6d567d53e895273c / 6d567d53e895273c
    numpy's libopenblas      0bd815d04b6b5499 / 0bd815d04b6b5499
    scipy's libopenblas      9b91f6ba8fdba9cf / 9b91f6ba8fdba9cf
    pyscf's libopenblas      79ec02b53f573cd7 / 79ec02b53f573cd7
    host_cpu                 AMD Ryzen Threadripper 2990WX / Intel Xeon Silver 4316
    host_avx512              none / avx512bw, avx512cd, …

## The measurement

Six entries, generated on both machines on the same day from the same commit with the
same seeds and one BLAS thread, twice over: once in the ordinary pinned environment and
once inside the image. The six are the ones that had already been shown to move, plus H₂
as a control that converges exactly.

| entry | without the container | with the container |
|---|---|---|
| C₄H₄ Jordan–Wigner UCCSD | differs by 6.01 × 10⁻³ Ha | **identical** |
| NH₃ Jordan–Wigner UCCSD | differs by 1.14 × 10⁻⁴ Ha | **identical** |
| H₄ Jordan–Wigner HEA | differs by 3.30 × 10⁻⁵ Ha | **identical** |
| LiH Jordan–Wigner UCCSD | differs by 7.80 × 10⁻⁶ Ha | **identical** |
| water dimer Jordan–Wigner HEA | differs by 1.29 × 10⁻¹⁰ Ha | **identical** |
| H₂ Jordan–Wigner UCCSD | differs by 4.44 × 10⁻¹⁶ Ha | **identical** |

**Zero of six reproduce without the image. Six of six reproduce with it**, hash for hash,
across an AMD AVX2 processor and an Intel AVX-512 processor.

That includes C₄H₄, which is the hardest case in the suite: it moves 6 mHa between
machines, its CASSCF orbital gauge is kernel-dependent to the point of changing the number
of tapered qubits, and it is flagged **marginal** in the cross-machine table for exactly
this reason. Inside the image it is bit-identical.

So the prediction holds, and the answer to "what would it take" is now measured rather
than argued: a container image with a fixed C library and a fixed BLAS kernel is
sufficient. A list of package versions is not, and the difference between the two is up to
6 mHa, which is most of a certification margin.

## What this does not do

**The image does not reproduce the published suite.** The published entries were generated
on bare metal, under glibc 2.34 or 2.39 and a natively-selected kernel. Regenerated inside
the image they differ:

| entry | container vs published |
|---|---|
| C₄H₄ Jordan–Wigner UCCSD | 6.01 × 10⁻³ Ha |
| NH₃ Jordan–Wigner UCCSD | 1.14 × 10⁻⁴ Ha |
| H₄ Jordan–Wigner HEA | 3.72 × 10⁻⁴ Ha |
| LiH Jordan–Wigner UCCSD | 7.80 × 10⁻⁶ Ha |
| water dimer Jordan–Wigner HEA | 1.30 × 10⁻¹⁰ Ha |
| H₂ Jordan–Wigner UCCSD | 4.44 × 10⁻¹⁶ Ha |

This is the cost of adopting it, and it is the same cost the kernel-pinning option
carried: **the suite would have to be regenerated inside the image** for the published
entries to reproduce there. Every entry would get a new hash. No energy would move by
enough to change a tier, on this sample, but every certified number would shift in its last
digits and the paper cites those numbers.

So this is a decision, not a patch, and it belongs after the paper rather than before it:

1. **Adopt and regenerate.** The suite becomes bit-for-bit reproducible by anyone who pulls
   the image, which is the strongest claim the project could make about itself. Costs a
   full regeneration and re-hashing.
2. **Adopt for new entries only.** Cheap, but the suite then contains two kinds of entry
   and the distinction has to be explained forever.
3. **Publish the image as a verification environment without regenerating.** Anyone can
   check that two machines agree with each other inside it, which is the reproducibility
   claim, while the published entries keep their own provenance and their existing
   same-machine guarantee.

Option 3 is available immediately and costs nothing, and it is what the image is for until
the suite is unfrozen.

## Using it

The image is published to the GitHub container registry and built by
`.github/workflows/publish-reference-image.yml`, which refuses to push it if the
determinism settings did not survive the build or if generating the same entry twice
inside it gives two different hashes.

    docker pull ghcr.io/qencode-benchmark/qencode-reference:v4

`scripts/verify_in_reference.sh` wraps the two things a third party would want to do.

**Check that a published entry still certifies.**

    scripts/verify_in_reference.sh releases/v4/db/<entry>.json

This runs in certification mode, which is the honest question for a published entry: it
was generated on bare metal before this image existed, so it will not reproduce bit for
bit inside it. Example output for LiH UCCSD — the energy moves 7.8 × 10⁻⁶ Ha and the entry
still certifies by three orders of magnitude.

**Check the bit-for-bit claim yourself.**

    scripts/verify_in_reference.sh --regenerate H2 jordan_wigner uccsd hf

Generate an entry inside the image. Anyone who runs that command inside the same image
gets the same entry hash, on any x86-64 processor. That is the reproducibility claim, and
it is checkable by running it rather than by trusting the claim.

The distinction matters and it is the whole reason this document exists. "Reproducible"
in this project now means two different things with two different guarantees: a published
entry reproduces bit for bit **on the machine that made it** and certifies anywhere, and
an entry generated in the image reproduces bit for bit **anywhere**.

## Reproducing this

    docker build -f Dockerfile.reference -t qencode-reference:v4 .
    docker save qencode-reference:v4 | gzip -1 > image.tar.gz
    # move image.tar.gz to the other machine, then
    gunzip -c image.tar.gz | podman load

    docker run --rm --entrypoint python qencode-reference:v4 /work/tools/reference_fingerprint.py
    docker run --rm -v "$PWD/out:/work/out:z" qencode-reference:v4 \
        --molecule LiH --mapping jordan_wigner --ansatz-type uccsd --orbital-opt hf \
        --out-dir /work/out

The record is `experiments/reference_env/records/container_vs_bare_2026-09-09.json`.
