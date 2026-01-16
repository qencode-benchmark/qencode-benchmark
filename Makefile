SHELL := /bin/bash

PY ?= python3
GAP ?= 0.01

V1_DIR ?= releases/v1/db
V2_DIR ?= releases/v2/db
TRUSTED_DIR ?= releases/v2/trusted

SCHEMA_V1 ?= schema_v1.json
SCHEMA_V2 ?= schema/schema_v2.json

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

check:
	$(PY) scripts/check_all.py --gap-threshold $(GAP) \
	  --stamp-env \
	  --export-trusted --trusted-out-dir $(TRUSTED_DIR) \
	  --trusted-require-gap-check --trusted-clean-out-dir \
	  --supply-chain --manifest-only-json-entries --verify-entry-hashes

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

supplychain:
	$(PY) scripts/build_manifest.py --root $(V2_DIR) --out $(V2_DIR)/manifest.json --only-json-entries
	$(PY) scripts/verify_manifest.py --root $(V2_DIR) --manifest $(V2_DIR)/manifest.json
	$(PY) scripts/entry_content_hashes_v2.py --db-dir $(V2_DIR) --out-dir $(V2_DIR)
	$(PY) scripts/verify_entry_hashes_v2.py --db-dir $(V2_DIR)

clean-trusted:
	rm -rf $(TRUSTED_DIR)

