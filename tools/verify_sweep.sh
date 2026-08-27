#!/bin/bash
# Re-verify every published entry, from a clean checkout, in the pinned environment, with
# NO override flags.
#
# QEncode's central claim is that any published result can be independently rebuilt. Until
# a298c51 the verifier could not even re-run the 29 entries that store ansatz_type "hea",
# so the whole database has never been checked. This checks it.
#
# Each job is a full VQE re-run, single-threaded, parallel across entries only -- the same
# isolation rule the rest of the suite uses, so no run can perturb another's arithmetic.
# Failures are recorded as failures. Nothing is retried with overrides.
set -u
cd "$HOME/qencode/qencode-db" || exit 1
source "$HOME/venv45/bin/activate" || exit 1

OUT="$HOME/qencode/verify_sweep"
LOGS="$OUT/logs"
PAR=26                       # leave headroom; some entries are hours long
PER_ENTRY_TIMEOUT=21600      # 6 hours

mkdir -p "$LOGS"

echo "=== full verifier sweep ==="
date
echo "commit:  $(git rev-parse --short HEAD)"
echo "dirty:   $(git status --porcelain --untracked-files=no | wc -l) tracked files modified (0 expected)"
echo "entries: $(ls releases/v4/db/*.json | wc -l)"
echo "parallel: $PAR   timeout per entry: ${PER_ENTRY_TIMEOUT}s"
echo

verify_one() {
  E="$1"; OUT="$2"; LOGS="$3"; TMO="$4"
  B=$(basename "$E" .json)
  L="$LOGS/$B.log"
  S=$(date +%s)
  timeout "$TMO" python scripts/verify_entry.py "$E" > "$L" 2>&1
  RC=$?
  D=$(( $(date +%s) - S ))
  if   grep -q "PASS — VQE energy reproduced" "$L"; then V=PASS
  elif grep -q "FAIL — energy differs"        "$L"; then V=FAIL_ENERGY
  elif grep -q "tampered"                     "$L" && grep -q "✗" "$L"; then V=FAIL_HASH
  elif [ "$RC" -eq 124 ]; then V=TIMEOUT
  else V=ERROR
  fi
  DIFF=$(grep -oE "differs by [0-9.e+-]+" "$L" | head -1 | sed "s/differs by //")
  python - "$E" "$V" "$D" "${DIFF:-}" "$RC" "$OUT" <<'PY'
import json, os, sys
entry, verdict, secs, diff, rc, out = sys.argv[1:7]
d = json.load(open(entry))
rec = {
    "entry_id": d.get("entry_id"),
    "file": os.path.basename(entry),
    "molecule": (d.get("problem") or {}).get("name"),
    "mapping": (d.get("encoding") or {}).get("mapping"),
    "ansatz_type": (d.get("encoding") or {}).get("ansatz_type"),
    "optimizer": (d.get("run_config") or {}).get("optimizer"),
    "trust": (d.get("trust") or {}).get("level") if isinstance(d.get("trust"), dict) else d.get("trust"),
    "stored_gap_ha": (d.get("results", {}).get("quality") or {}).get("abs_vqe_exact_gap"),
    "verdict": verdict,
    "energy_diff_ha": float(diff) if diff else None,
    "seconds": int(secs),
    "returncode": int(rc),
}
os.makedirs(out, exist_ok=True)
json.dump(rec, open(os.path.join(out, rec["file"]), "w"), indent=1)
print("  %-8s %-52s %6ds %s" % (verdict, rec["file"][:52], int(secs),
                                ("Δ=" + diff) if diff else ""))
PY
}
export -f verify_one

ls releases/v4/db/*.json | xargs -P "$PAR" -I{} bash -c 'verify_one "$@"' _ {} "$OUT" "$LOGS" "$PER_ENTRY_TIMEOUT"

echo
echo "=== done ==="
date
echo "records: $(ls "$OUT"/*.json 2>/dev/null | wc -l)"
