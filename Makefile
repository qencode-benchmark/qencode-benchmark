# qencode-db Makefile
# - "verify/check" is READ-ONLY (should not modify repo)
# - "regen" re-generates outputs (will modify repo)

PY ?= python3
GAP ?= 0.01

V1_DIR ?= releases/v1/db
V2_DIR ?= releases/v2/db
TRUSTED_DIR ?= releases/v2/trusted

SCHEMA_V2 ?= schema/schema_v2.json
MANIFEST ?= $(V2_DIR)/manifest.json
ENTRY_HASHES ?= $(V2_DIR)/entry_content_hashes.json

.PHONY: help check verify regen \
        v1-verify v2-verify supplychain-verify trusted-verify \
        clean-trusted

help:
	@echo "Targets:"
	@echo "  make verify        Read-only verification (no writes)"
	@echo "  make check         Alias for verify"
	@echo "  make regen         Regenerate derived outputs (writes files)"
	@echo "  make v1-verify      Validate+audit v1 (read-only)"
	@echo "  make v2-verify      Validate+audit v2 (read-only)"
	@echo "  make supplychain-verify  Verify manifest + entry hashes (read-only)"
	@echo "  make trusted-verify Check trusted outputs exist (read-only)"
	@echo "  make clean-trusted  Delete trusted output dir"
	@echo ""
	@echo "Vars you can override:"
	@echo "  GAP=0.01 V1_DIR=... V2_DIR=... TRUSTED_DIR=... PY=python3"

# Read-only checks (should not modify files)
verify: v1-verify v2-verify supplychain-verify trusted-verify
check: verify

v1-verify:
	$(PY) scripts/validate_schema.py --db-dir $(V1_DIR)
	$(PY) scripts/audit_db.py --db-dir $(V1_DIR) --gap-threshold $(GAP)

v2-verify:
	$(PY) scripts/validate_schema_v2.py --db-dir $(V2_DIR) --schema $(SCHEMA_V2)
	$(PY) scripts/audit_db_v2.py --db-dir $(V2_DIR) --gap-threshold $(GAP)

supplychain-verify:
	@test -f "$(MANIFEST)" || (echo "Missing: $(MANIFEST). Run: make regen"; exit 1)
	@test -f "$(ENTRY_HASHES)" || (echo "Missing: $(ENTRY_HASHES). Run: make regen"; exit 1)
	$(PY) scripts/verify_manifest.py --root $(V2_DIR) --manifest $(MANIFEST)
	$(PY) scripts/verify_entry_hashes_v2.py --db-dir $(V2_DIR)

trusted-verify:
	@test -f "$(TRUSTED_DIR)/trusted_index.json" || (echo "Missing trusted_index.json. Run: make regen"; exit 1)
	@test -f "$(TRUSTED_DIR)/trusted_benchmarks.csv" || (echo "Missing trusted_benchmarks.csv. Run: make regen"; exit 1)

# Regenerate everything (this WILL modify files)
regen:
	$(PY) scripts/check_all.py --gap-threshold $(GAP) \
	  --stamp-env \
	  --export-trusted --trusted-out-dir $(TRUSTED_DIR) \
	  --trusted-require-gap-check --trusted-clean-out-dir \
	  --supply-chain --manifest-only-json-entries --verify-entry-hashes

clean-trusted:
	rm -rf "$(TRUSTED_DIR)"

