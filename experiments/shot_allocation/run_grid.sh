#!/bin/bash
set -u
cd "$HOME/qencode/qencode-db" || exit 1
source "$HOME/venv45/bin/activate" || exit 1
export QENCODE_REPO="$HOME/qencode/qencode-db"
OUT="$HOME/qencode/neyman_v3"
JOBS="$HOME/qencode/neyman3_jobs.txt"
PAR=30
mkdir -p "$OUT"
: > "$JOBS"
for MOL in BeH2 H2O H4 NH3 LiH water_dimer C4H4 N2 benzene H6; do
  for STATE in start mid converged; do
    for BUDGET in 10000 100000 1000000; do
      echo "$MOL $STATE $BUDGET $OUT" >> "$JOBS"
    done
  done
done
N=$(wc -l < "$JOBS")
echo "=== neyman v2: $N jobs, $PAR at a time, $(nproc) cores ==="
date
xargs -P "$PAR" -L 1 python "$HOME/qencode/neyman_v2.py" < "$JOBS"
echo "=== done ==="; date
echo "results: $(ls "$OUT"/*.json 2>/dev/null | wc -l) files"
