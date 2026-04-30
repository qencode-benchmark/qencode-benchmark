#!/usr/bin/env python3
"""
job_poller.py
=============
Runs continuously on Ubuntu. Every 60 seconds it asks the QEncode API
for the next pending certification job, runs the benchmark, publishes
the updated leaderboard, then marks the job complete.

Usage:
    cd ~/work/qencode-db
    conda activate qencode
    python scripts/job_poller.py

Stop with Ctrl-C.

Required env vars (add to ~/.bashrc):
    LEADERBOARD_PUBLISH_SECRET   — shared secret (already set)

Optional:
    QENCODE_API_URL              — defaults to https://www.qencode-benchmark.org
    POLL_INTERVAL_SECONDS        — defaults to 60
"""

import os
import sys
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    sys.exit("requests not installed. Run: pip install requests")

# ── Config ────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent
SCRIPTS   = REPO_ROOT / "scripts"

API_URL = os.environ.get("QENCODE_API_URL", "https://www.qencode-benchmark.org").rstrip("/")
SECRET  = os.environ.get("LEADERBOARD_PUBLISH_SECRET", "")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", "60"))

SUITE_YAML    = str(REPO_ROOT / "benchmarks" / "standard" / "suite_v2.yaml")
OUT_DIR       = str(REPO_ROOT / "releases" / "v2" / "db")
PYTHON        = sys.executable  # use the active conda python

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("poller")

AUTH = {"Authorization": f"Bearer {SECRET}"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def run(cmd: list[str], label: str) -> tuple[bool, str]:
    """Run a subprocess, stream output, return (success, combined_output)."""
    log.info(f"  → {label}")
    log.info(f"    {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=False,   # stream to terminal so you can watch progress
        text=True,
    )
    ok = result.returncode == 0
    if not ok:
        log.error(f"  ✗ {label} exited with code {result.returncode}")
    else:
        log.info(f"  ✓ {label} done")
    return ok, f"exit_code={result.returncode}"


def claim_job() -> dict | None:
    """Ask the API to claim the next pending job. Returns job dict or None."""
    try:
        r = requests.post(
            f"{API_URL}/api/admin/jobs",
            params={"action": "claim"},
            headers=AUTH,
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("job")   # None if queue is empty
    except Exception as e:
        log.warning(f"claim_job error: {e}")
        return None


def finish_job(job_id: int, success: bool, error_message: str = "", notes: str = "") -> dict | None:
    """Mark the job as completed or failed in the API. Returns response data including certification_token."""
    try:
        r = requests.post(
            f"{API_URL}/api/admin/jobs/{job_id}",
            json={"success": success, "error_message": error_message, "notes": notes},
            headers=AUTH,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        cert_token = data.get("certification_token")
        log.info(f"Job #{job_id} marked {'completed' if success else 'failed'}")
        if cert_token:
            log.info(f"  Certification token : {cert_token}")
            log.info(f"  Verify URL          : {data.get('verify_url', '')}")
        return data
    except Exception as e:
        log.error(f"finish_job error: {e}")
        return None


def extract_molecule(product_label: str) -> str | None:
    """
    Try to extract a molecule name from the product label.
    Single-molecule orders should include the molecule name in the label
    once we add a post-payment form (Phase 5). Until then, returns None.
    """
    known = ["H2", "LiH", "HF", "N2", "BeH2"]
    for mol in known:
        if mol.lower() in product_label.lower():
            return mol
    return None


def run_job(job: dict) -> tuple[bool, str]:
    """
    Execute the benchmark for a given job.
    Returns (success, notes).
    """
    product_type  = job.get("product_type", "unknown")
    product_label = job.get("product_label", "")
    customer_email = job.get("customer_email", "")
    job_id        = job["id"]

    log.info(f"━━━ Starting job #{job_id} ━━━")
    log.info(f"  Product : {product_label}")
    log.info(f"  Customer: {customer_email}")

    steps_ok = True
    notes    = []

    # ── Step 1: Run benchmark ─────────────────────────────────────────────────
    if product_type == "full_suite":
        cmd = [
            PYTHON, str(SCRIPTS / "run_standard_suite.py"),
            "--suite", SUITE_YAML,
            "--out-dir", OUT_DIR,
            "--resume",
            "--workers", "4",
        ]
        ok, out = run(cmd, "Full Suite v2 benchmark run")

    elif product_type == "single_molecule":
        molecule = extract_molecule(product_label)
        if molecule:
            cmd = [
                PYTHON, str(SCRIPTS / "run_standard_suite.py"),
                "--suite", SUITE_YAML,
                "--out-dir", OUT_DIR,
                "--molecule", molecule,
                "--resume",
                "--workers", "4",
            ]
            ok, out = run(cmd, f"Single-molecule benchmark run ({molecule})")
        else:
            # Molecule not yet known — log and skip execution until Phase 5
            log.warning(
                f"  ⚠  Single-molecule job #{job_id}: molecule not specified in product label.\n"
                f"     Reply to {customer_email} to ask which molecule, then re-queue manually."
            )
            return False, "molecule_not_specified: contact customer to confirm target molecule"

    else:
        log.warning(f"  ⚠  Unknown product type '{product_type}' — skipping execution")
        return False, f"unknown_product_type: {product_type}"

    if not ok:
        return False, f"benchmark_failed: {out}"
    notes.append(f"benchmark_ok")

    # ── Step 2: Regenerate leaderboard CSVs ───────────────────────────────────
    ok, out = run(
        [PYTHON, str(SCRIPTS / "generate_leaderboard.py")],
        "Generate leaderboard CSVs",
    )
    if not ok:
        log.warning("  Leaderboard generation failed — will still try to publish")
    else:
        notes.append("leaderboard_generated")

    # ── Step 3: Publish live leaderboard to website ───────────────────────────
    ok, out = run(
        [PYTHON, str(SCRIPTS / "publish_leaderboard_live.py")],
        "Publish leaderboard to live website",
    )
    if ok:
        notes.append("leaderboard_published")
    else:
        log.warning("  Leaderboard publish failed — website not yet updated")

    return True, " | ".join(notes)


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    if not SECRET:
        sys.exit(
            "ERROR: LEADERBOARD_PUBLISH_SECRET is not set.\n"
            "Run: source ~/.bashrc  (or open a new terminal)"
        )

    log.info(f"QEncode job poller started — polling every {POLL_INTERVAL}s")
    log.info(f"API: {API_URL}")

    while True:
        try:
            job = claim_job()

            if job:
                log.info(f"Found job #{job['id']} — starting ...")
                success, notes = run_job(job)
                result = finish_job(job["id"], success=success, notes=notes)

                if success:
                    log.info(f"✓ Job #{job['id']} complete. Notes: {notes}")
                    if result and result.get("verify_url"):
                        log.info(f"━━━ CERTIFICATION ISSUED ━━━━━━━━━━━━━━━━━━━━━━━━━")
                        log.info(f"  Verify : {result['verify_url']}")
                        log.info(f"  Badge  : {API_URL}/api/badge/{result['certification_token']}")
                        log.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                else:
                    log.error(f"✗ Job #{job['id']} failed. Notes: {notes}")

                # Don't sleep after a job — check immediately for another
                continue

            else:
                log.debug("No pending jobs.")

        except KeyboardInterrupt:
            log.info("Poller stopped by user.")
            break
        except Exception as e:
            log.error(f"Unexpected error in poll loop: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
