# qencode-db Makefile
# Usage:
#   make help
#   make check
#   make v1
#   make v2
#   make trusted
#   make supplychain

PY ?= python3
GAP ?= 0.01

V1_DIR ?= releases/v1/db
V2_DIR ?= releases/v2/db
TRUSTED_DIR ?= releases/v2/trusted

SCHEMA_V2 ?= schema/schema_v2.json
MANIFEST ?= $(V2_DIR)/manifest.json
ENTRY_HASHES ?= $(V2_DIR)/entry_content_hashes.json

.PHONY: help check v1 v2 trusted supplychain clean-trusted

help:
	@echo "Targets:"
	@echo "  make check         Full pipeline (v1 + v2 + trusted + supply-chain)"
	@echo "  make v1            Validate v1 + build index + benchmarks + audit"
	@echo "  make v2            Migrate v1->v2 + stamp env + validate v2 + index + benchmarks + audit"
	@echo "  make trusted       Export trusted v2 set (index + csv)"
	@echo "  make supplychain   Build+verify manifest + entry hashes for v2"
	@echo "  make clean-trusted Delete trusted output dir ($(TRUSTED_DIR))"
	@echo ""
	@echo "Vars you can override:"
	@echo "  GAP=0.01 V1_DIR=... V2_DIR=... TRUSTED_DIR=... PY=python3"

check: v1 v2 trusted supplychain
	@echo "✅ make check: OK"

v1:
	$(PY) scripts/validate_schema.py --db-dir $(V1_DIR)
	$(PY) scripts/build_index.py --db-dir $(V1_DIR)
	$(PY) scripts/report_benchmarks.py --db-dir $(V1_DIR) --csv
	$(PY) scripts/audit_db.py --db-dir $(V1_DIR) --gap-threshold $(GAP)

v2:
	$(PY) scripts/migrate_v1_to_v2.py --in-dir $(V1_DIR) --out-dir $(V2_DIR) --gap-threshold $(GAP)
	$(PY) scripts/stamp_env_v2.py --db-dir $(V2_DIR) --write
	$(PY) scripts/validate_schema_v2.py --db-dir $(V2_DIR) --schema $(SCHEMA_V2)
	$(PY) scripts/build_index_v2.py --db-dir $(V2_DIR)
	$(PY) scripts/report_benchmarks_v2.py --db-dir $(V2_DIR) --csv
	$(PY) scripts/audit_db_v2.py --db-dir $(V2_DIR) --gap-threshold $(GAP)

trusted:
	$(PY) scripts/export_trusted_v2.py --db-dir $(V2_DIR) --out-dir $(TRUSTED_DIR) --gap-threshold $(GAP) --require-gap-check --clean-out-dir
	@test -f "$(TRUSTED_DIR)/trusted_index.json"
	@test -f "$(TRUSTED_DIR)/trusted_benchmarks.csv"

# IMPORTANT ORDER:
# 1) compute entry_content_hashes.json
# 2) build manifest.json (which includes that file)
# 3) verify manifest + verify entry hashes
supplychain:
	$(PY) scripts/entry_content_hashes_v2.py --db-dir $(V2_DIR) --out-dir $(V2_DIR)
	$(PY) scripts/build_manifest.py --root $(V2_DIR) --out $(MANIFEST) --only-json-entries
	$(PY) scripts/verify_manifest.py --root $(V2_DIR) --manifest $(MANIFEST)
	$(PY) scripts/verify_entry_hashes_v2.py --db-dir $(V2_DIR)

clean-trusted:
	rm -rf "$(TRUSTED_DIR)"

