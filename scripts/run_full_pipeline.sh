#!/usr/bin/env bash
# ============================================================
# QEncode Full Fix & Release Pipeline
# Run from: /mnt/d/qencode-db  with conda activate qencode
#
# Steps:
#   1.  N2  — VQE (fixed code: StatevectorEstimator + decompose)
#   2.  H2  — Re-run JW hw-eff with multi-restart
#   3.  LiH — Delete wrong entries, regenerate [2,2], run VQE
#   3a. H2O — Generate 6 entries [4,4] if missing, run VQE
#   3b. Assign trust levels (suite_v2.yaml: H2, LiH, HF, BeH2, H2O + N2 research)
#   4.  Canonical index rebuild
#   5.  Generate leaderboard CSVs (accuracy, cost, balanced, research)
#   6.  Publish to live website
# ============================================================
set -e

PY=/home/jlaba/miniconda3/envs/qencode/bin/python
REPO=/mnt/d/qencode-db
DB=$REPO/releases/v2/db
LOG=$REPO/artifacts/pipeline_$(date +%Y%m%d_%H%M%S).log

mkdir -p $REPO/artifacts
exec > >(tee -a "$LOG") 2>&1

echo "========================================"
echo " QEncode Full Pipeline — $(date)"
echo " Log: $LOG"
echo "========================================"

# ── STEP 1: N2 VQE ──────────────────────────────────────────
echo ""
echo "STEP 1/6: N2 VQE (6 entries, fixed code)"
echo "  Estimated: 5–30 min with StatevectorEstimator"
echo "----------------------------------------"
$PY $REPO/scripts/run_vqe_v2.py \
  --db-dir $DB \
  --pattern "N2_sto3g_*_v2__sha256_*.json" \
  --optimizer COBYLA \
  --maxiter 2000 \
  --seed 123
echo "✅ STEP 1 complete"

# ── STEP 2: H2 JW hw-eff re-run with multi-restart ──────────
echo ""
echo "STEP 2/6: H2 JW hw-eff (multi-restart, should fix gap)"
echo "----------------------------------------"
$PY $REPO/scripts/run_vqe_v2.py \
  --file "$DB/H2_sto3g_JW_hardware_efficient_v2__sha256_c6ba55cf79cb4f42.json" \
  --optimizer COBYLA \
  --maxiter 800 \
  --seed 42
echo "✅ STEP 2 complete"

# ── STEP 3: LiH — delete wrong, regenerate, VQE ────────────
echo ""
echo "STEP 3/6: LiH regenerate with active_space [2,2]"
echo "  Deleting 31 wrong 12-qubit entries..."
echo "----------------------------------------"
rm -f $DB/LiH_sto3g_*_v2__sha256_*.json
echo "  Deleted. Regenerating 6 correct 4-qubit entries..."

for MAPPING in jordan_wigner parity bravyi_kitaev; do
  echo "  Generating: $MAPPING uccsd"
  $PY $REPO/scripts/generate_entry_v2.py \
    --repo-root $REPO \
    --out-dir $DB \
    --molecule LiH \
    --basis sto3g \
    --mapping $MAPPING \
    --ansatz-type uccsd \
    --ansatz-reps 1 \
    --active-space 2,2 \
    --compute-exact

  echo "  Generating: $MAPPING hardware_efficient"
  $PY $REPO/scripts/generate_entry_v2.py \
    --repo-root $REPO \
    --out-dir $DB \
    --molecule LiH \
    --basis sto3g \
    --mapping $MAPPING \
    --ansatz-type hardware_efficient \
    --ansatz-reps 2 \
    --active-space 2,2 \
    --compute-exact
done

echo "  Running VQE on new LiH entries..."
$PY $REPO/scripts/run_vqe_v2.py \
  --db-dir $DB \
  --pattern "LiH_sto3g_*_v2__sha256_*.json" \
  --optimizer COBYLA \
  --maxiter 1500 \
  --seed 123
echo "✅ STEP 3 complete"

# ── STEP 3a: H2O — generate entries (if missing) + VQE ──────
echo ""
echo "STEP 3a/6: H2O [4,4] — 8-qubit, 6 entries"
echo "----------------------------------------"
H2O_COUNT=$(ls $DB/H2O_sto3g_*_v2__sha256_*.json 2>/dev/null | wc -l)
if [ "$H2O_COUNT" -lt 6 ]; then
  echo "  Generating H2O entries (found $H2O_COUNT, need 6)..."
  for MAPPING in jordan_wigner parity bravyi_kitaev; do
    echo "  Generating: $MAPPING uccsd"
    $PY $REPO/scripts/generate_entry_v2.py \
      --repo-root $REPO \
      --out-dir $DB \
      --molecule H2O \
      --basis sto3g \
      --mapping $MAPPING \
      --ansatz-type uccsd \
      --ansatz-reps 1 \
      --active-space 4,4 \
      --compute-exact

    echo "  Generating: $MAPPING hardware_efficient"
    $PY $REPO/scripts/generate_entry_v2.py \
      --repo-root $REPO \
      --out-dir $DB \
      --molecule H2O \
      --basis sto3g \
      --mapping $MAPPING \
      --ansatz-type hardware_efficient \
      --ansatz-reps 2 \
      --active-space 4,4 \
      --compute-exact
  done
else
  echo "  All 6 H2O entries already exist — skipping generation"
fi

echo "  Running VQE on H2O entries (8 qubits, 1 restart)..."
$PY $REPO/scripts/run_vqe_v2.py \
  --db-dir $DB \
  --pattern "H2O_sto3g_*_v2__sha256_*.json" \
  --optimizer COBYLA \
  --maxiter 2000 \
  --seed 123
echo "✅ STEP 3a complete"

# ── STEP 3b: Assign trust levels ────────────────────────────
echo ""
echo "STEP 3b/6: Assign trust levels (certified/validated/experimental)"
echo "  Using suite_v2.yaml so LiH, HF, H2O, N2 are evaluated correctly"
echo "----------------------------------------"
$PY $REPO/scripts/assign_trust_levels.py \
  --db-dir $DB \
  --suite $REPO/benchmarks/standard/suite_v2.yaml
echo "✅ STEP 3b complete"

# ── STEP 4: Rebuild canonical index ─────────────────────────
echo ""
echo "STEP 4/6: Rebuild canonical_index.json (all 30 entries)"
echo "----------------------------------------"
$PY $REPO/scripts/select_canonical_v2.py --db-dir $DB
echo "✅ STEP 4 complete"

# ── STEP 5: Generate leaderboard CSVs ───────────────────────
echo ""
echo "STEP 5/6: Generate leaderboard CSVs"
echo "----------------------------------------"
$PY /home/jlaba/qencode-db/scripts/generate_leaderboard.py \
  --db-dir $DB \
  --sqlite $DB/benchmarks.db \
  --out-dir $REPO/datasets/leaderboard
echo "✅ STEP 5 complete"

# ── STEP 6: Publish to live website ─────────────────────────
echo ""
echo "STEP 6/6: Publish to qencode-benchmark.org"
echo "----------------------------------------"
$PY $REPO/scripts/publish_leaderboard_live.py
echo "✅ STEP 6 complete"

echo ""
echo "========================================"
echo " ALL DONE — $(date)"
echo " Full log saved to: $LOG"
echo "========================================"
