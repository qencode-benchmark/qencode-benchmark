# QEncode benchmark runner — the pinned, deterministic environment in one image.
#
# The point of this image is not convenience alone. A VQE result is only
# reproducible if the arithmetic is deterministic and the software stack is
# recorded, so this image fixes both: it installs the exact pins from
# pyproject.toml and restricts the linear-algebra backend to a single thread
# before NumPy is ever imported.
#
#   docker build -t qencode .
#   docker run --rm -v "$PWD/out:/work/out" qencode \
#     --molecule H2 --mapping jordan_wigner --ansatz-type uccsd --out-dir /work/out
#
# Anything after the image name is passed straight to the entry generator, so
#   docker run --rm qencode --help
# prints the full option list.

FROM python:3.11-slim

# libgomp1 is the OpenMP runtime PySCF's wheels link against.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*

# Single-threaded BLAS. Set as image environment so it is already in place
# before the interpreter starts — after NumPy loads, these are ignored because
# the thread pool has already been built.
#
# Multi-threaded BLAS combines partial sums in whatever order threads finish,
# which perturbs an energy in its last bits. A gradient-free optimizer such as
# COBYLA chooses its next step by comparing energies, so that noise can send it
# into a different local minimum. Pinning to one thread is what makes a run
# repeatable. See: qencode-benchmark.org/blog/vqe-reproducibility-threading-bug
ENV OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    VECLIB_MAXIMUM_THREADS=1 \
    PYTHONUNBUFFERED=1

WORKDIR /work

# Dependencies first, from the pins alone, so edits to the pipeline do not
# invalidate the layer that takes minutes to build.
COPY requirements-v4.txt .
RUN pip install --no-cache-dir -r requirements-v4.txt

# The package, then everything the pipeline reads at runtime.
COPY pyproject.toml README.md ./
COPY src/ src/
COPY scripts/ scripts/
COPY tools/ tools/
COPY molecules_v4.json molecules_v3.json ./
COPY schema/ schema/

# Deps are already present and pinned above; --no-deps keeps pip from resolving
# them a second time.
RUN pip install --no-cache-dir --no-deps .

# QENCODE_REPO makes the checkout explicit rather than inferred, so the pipeline
# reads the catalogue and the version pins from the files copied above rather
# than from the copies bundled inside the wheel.
ENV QENCODE_REPO=/work

# Entries land here; mount a volume over it to keep them.
RUN mkdir -p /work/out

# `qencode run` and `python scripts/generate_entry_v4.py` are the same code; the
# script remains as a compatibility shim for documented commands.
ENTRYPOINT ["qencode", "run"]
CMD ["--help"]
