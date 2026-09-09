#!/usr/bin/env bash
# Verify a QEncode entry inside the published reference environment.
#
#   scripts/verify_in_reference.sh releases/v4/db/<entry>.json
#   scripts/verify_in_reference.sh --regenerate LiH jordan_wigner uccsd hf
#
# WHAT THIS DOES AND DOES NOT PROVE
#
# The image makes a result independent of the processor it runs on. Measured on
# 2026-09-09: six entries generated on an AMD AVX2 machine and an Intel AVX-512 machine
# agreed on none of six outside the image, by up to 6 mHa, and on six of six inside it.
# See docs/REFERENCE_ENVIRONMENT.md.
#
# It does NOT make the published entries reproduce bit for bit. They were generated on
# bare metal under a different C library, before this image existed, so re-running one
# inside the image gives a slightly different number -- up to 6 mHa for the worst case.
# That is why the default here is certification mode: the question a third party can
# actually settle is whether the entry still clears the threshold.
#
# The bit-for-bit claim is available to you in the other direction, with --regenerate:
# generate an entry inside the image, and anyone else who runs the same command inside
# the same image gets the same hash, whatever processor they own.
set -euo pipefail

IMAGE="${QENCODE_REFERENCE_IMAGE:-ghcr.io/qencode-benchmark/qencode-reference:v4}"
ENGINE="${QENCODE_CONTAINER_ENGINE:-}"

if [ -z "$ENGINE" ]; then
  if command -v docker >/dev/null 2>&1; then ENGINE=docker
  elif command -v podman >/dev/null 2>&1; then ENGINE=podman
  else echo "need docker or podman on PATH" >&2; exit 1
  fi
fi

usage() {
  sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

[ $# -eq 0 ] && usage 1
[ "$1" = "-h" ] || [ "$1" = "--help" ] && usage 0

if [ "$1" = "--regenerate" ]; then
  shift
  MOL=${1:?molecule}; MAP=${2:-jordan_wigner}; ANS=${3:-uccsd}; ORB=${4:-hf}
  OUT="$(pwd)/reference-out"
  mkdir -p "$OUT"
  echo "image:  $IMAGE"
  echo "engine: $ENGINE"
  echo
  "$ENGINE" run --rm -v "$OUT:/work/out:z" "$IMAGE" \
      --molecule "$MOL" --mapping "$MAP" --ansatz-type "$ANS" --orbital-opt "$ORB" \
      --out-dir /work/out
  echo
  echo "Anyone running that command inside this image gets the entry hash printed above,"
  echo "on any x86-64 processor. That is the reproducibility claim, and it is checkable"
  echo "by running it yourself rather than by trusting us."
  exit 0
fi

ENTRY=$1; shift
[ -f "$ENTRY" ] || { echo "no such entry: $ENTRY" >&2; exit 1; }

ENTRY_ABS=$(cd "$(dirname "$ENTRY")" && pwd)/$(basename "$ENTRY")
MODE="certification"
for a in "$@"; do
  case $a in --mode=*) MODE=${a#--mode=} ;; esac
done

echo "image:  $IMAGE"
echo "engine: $ENGINE"
echo "entry:  $(basename "$ENTRY")"
echo "mode:   $MODE"
echo
"$ENGINE" run --rm \
    -v "$ENTRY_ABS:/work/entry.json:ro" \
    --entrypoint python "$IMAGE" \
    /work/scripts/verify_entry.py /work/entry.json --mode "$MODE" --allow-dirty
