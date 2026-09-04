#!/usr/bin/env python3
"""
QEncode — Publish leaderboard CSVs to production database
==========================================================
Reads the 4 CSV files from website/public/data/ and POSTs them to
the /api/admin/publish-leaderboard endpoint, replacing whatever is
currently in the Neon Postgres database.

Usage:
    python scripts/publish_leaderboard.py \
        --secret YOUR_LEADERBOARD_PUBLISH_SECRET \
        [--url https://qencode-benchmark.org]

Or set env var:
    export LEADERBOARD_PUBLISH_SECRET=your_secret
    python scripts/publish_leaderboard.py

If the deployment sits behind Vercel deployment protection, supply the bypass token
through the environment as well. It is a credential and must not be committed:

    export VERCEL_PROTECTION_BYPASS=...

The POST carries the publish secret in an Authorization header, so TLS certificate
verification is always on and the header is never forwarded across a redirect to a
different origin. `--insecure` exists for a local test server and warns loudly.
"""

import argparse
import csv
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parent.parent
DATA_DIR   = REPO_ROOT / "website" / "public" / "data"
DEFAULT_URL = "https://www.qencode-benchmark.org"

# ── CSV parsing ───────────────────────────────────────────────────────────────
def num(v):
    if v in (None, "", "None", "null"): return None
    try:   return float(v)
    except: return None

def bool_val(v):
    return str(v).strip().lower() in ("true", "1", "yes")

def intval(v):
    """Whole-number variant of num(), for the BIGINT resource columns."""
    f = num(v)
    return None if f is None else int(f)

def optbool(v):
    """Nullable boolean: absent/empty stays None rather than collapsing to False."""
    if v in (None, "", "None", "null"):
        return None
    return bool_val(v)

def _base_row(r):
    """Common fields for all leaderboard rows (v3 + v4)."""
    return {
        "rank":               int(r["rank"]),
        "entry_id":           r.get("entry_id", ""),
        "molecule":           r["molecule"],
        "basis":              r.get("basis") or None,       # v4 new field
        "orbital_opt":        r.get("orbital_opt") or None, # v4 new field
        "mapping":            r["mapping"],
        "ansatz":             r["ansatz"],
        "gap":                num(r["gap"]),
        "depth":              num(r.get("depth")),
        "two_q_gates":        num(r.get("2q_gates")),
        "baseline":           bool_val(r.get("baseline", False)),
        "beats_classical":    bool_val(r.get("beats_classical", False)) if r.get("beats_classical") not in (None, "", "None", "null") else None,
        "ccsd_t_correlation": num(r.get("ccsd_t_correlation")),
        "vqe_energy":         num(r.get("vqe_energy")),
        "casci_energy":       num(r.get("casci_energy")),
        "hf_energy":          num(r.get("hf_energy")),
        # Fault-tolerant resource proxies. Absent from v3 CSVs, so .get() rather
        # than indexing — an older CSV publishes with these as null, not an error.
        "t_gate_estimate":    intval(r.get("t_gate_estimate")),
        "non_clifford_gates": intval(r.get("non_clifford_gates")),
        # Certification margin and fragility, added 2026-09-04. Same .get() treatment:
        # an older CSV publishes with these null rather than failing.
        "optimizer":          r.get("optimizer") or None,
        "optimiser_family":   r.get("optimiser_family") or None,
        "amplifies":          optbool(r.get("amplifies")),
        "margin":             num(r.get("margin")),
        "chem_accurate":      optbool(r.get("chem_accurate")),
        "robustness":         r.get("robustness") or None,
        "at_risk":            optbool(r.get("at_risk")),
    }

def parse_accuracy_csv(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(_base_row(r))
    return rows

def parse_cost_csv(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(_base_row(r))
    return rows

def parse_balanced_csv(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            row = _base_row(r)
            row["balanced_score"] = num(r.get("balanced_score"))
            rows.append(row)
    return rows

def parse_research_csv(path):
    return parse_accuracy_csv(path)  # same shape

def parse_metadata(path):
    with open(path) as f:
        return json.load(f)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Publish leaderboard CSVs to production DB")
    parser.add_argument("--secret", default=os.environ.get("LEADERBOARD_PUBLISH_SECRET",""),
                        help="LEADERBOARD_PUBLISH_SECRET value")
    parser.add_argument("--url",    default=DEFAULT_URL,
                        help=f"Base URL (default: {DEFAULT_URL})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the payload but don't send it")
    parser.add_argument("--insecure", action="store_true",
                        help="Disable TLS certificate verification. Exposes the publish "
                             "secret to anyone who can intercept the connection; for a "
                             "local test server only, never for production.")
    args = parser.parse_args()

    if not args.secret and not args.dry_run:
        print("ERROR: provide --secret or set LEADERBOARD_PUBLISH_SECRET")
        sys.exit(1)

    # ── Load files ─────────────────────────────────────────────────────────────
    acc_path      = DATA_DIR / "leaderboard_accuracy.csv"
    cost_path     = DATA_DIR / "leaderboard_hardware_cost.csv"
    balanced_path = DATA_DIR / "leaderboard_balanced.csv"
    research_path = DATA_DIR / "leaderboard_research.csv"
    meta_path     = DATA_DIR / "leaderboard_metadata.json"

    for p in [acc_path, cost_path, balanced_path, meta_path]:
        if not p.exists():
            print(f"ERROR: file not found: {p}")
            sys.exit(1)

    print("Reading CSV files...")
    accuracy  = parse_accuracy_csv(acc_path)
    cost      = parse_cost_csv(cost_path)
    balanced  = parse_balanced_csv(balanced_path)
    research  = parse_research_csv(research_path) if research_path.exists() else []
    metadata  = parse_metadata(meta_path)

    print(f"  accuracy:  {len(accuracy)} rows")
    print(f"  cost:      {len(cost)} rows")
    print(f"  balanced:  {len(balanced)} rows")
    print(f"  research:  {len(research)} rows")
    print(f"  metadata:  {metadata}")

    # ── Molecule summary ───────────────────────────────────────────────────────
    mols = sorted(set(r["molecule"] for r in accuracy))
    print(f"\nMolecules in accuracy: {mols}")

    payload = {
        "accuracy": accuracy,
        "cost":     cost,
        "balanced": balanced,
        "research": research,
        "metadata": metadata,
    }

    if args.dry_run:
        print("\n-- DRY RUN -- payload (first 2 rows each) --")
        for k in ["accuracy","cost","balanced","research"]:
            print(f"\n  {k}:")
            for row in payload[k][:2]:
                print(f"    {row}")
        print("\nNot sending (--dry-run). Remove flag to publish.")
        return

    # ── POST to API ────────────────────────────────────────────────────────────
    endpoint = args.url.rstrip("/") + "/api/admin/publish-leaderboard"
    body     = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {args.secret}",
        # Cloudflare answers the default urllib User-Agent with error 1010.
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }
    # Vercel deployment-protection bypass, read from the environment rather than
    # hardcoded. It is a credential, and committing it published it to anyone who
    # could read the repository. Unset simply means the header is not sent.
    bypass = os.environ.get("VERCEL_PROTECTION_BYPASS", "").strip()
    if bypass:
        headers["x-vercel-protection-bypass"] = bypass

    req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")

    print(f"\nPOSTing to {endpoint} ...")

    # TLS is verified. This request carries the publish secret in an Authorization
    # header, so an unverified context would hand that credential -- the one that
    # controls the public leaderboard -- to anyone able to intercept the connection,
    # with no valid certificate required. An earlier version disabled verification
    # outright to work around local certificate-chain problems. That is a trust-store
    # issue on the client; the fix is certifi, not switching verification off for
    # every user of the script.
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(cafile=certifi.where())
    except ImportError:
        pass                      # fall back to the system trust store
    if args.insecure:
        print("  WARNING: --insecure given, TLS certificate verification is DISABLED.")
        print("           The publish secret is exposed to anyone who can intercept")
        print("           this connection. Intended for a local test server only.")
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    # urllib drops the body when it follows a redirect, so 307/308 are re-issued by
    # hand. Credentials are NOT carried to a different origin: the redirect target is
    # chosen by the server, so forwarding Authorization blindly would let any redirect
    # -- hostile, compromised, or merely misconfigured -- harvest the publish secret.
    _SENSITIVE = ("authorization", "cookie", "x-vercel-protection-bypass")

    def _origin(url):
        p = urllib.parse.urlsplit(url)
        return (p.scheme, p.hostname, p.port or (443 if p.scheme == "https" else 80))

    class _PostRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if code not in (307, 308):
                return super().redirect_request(req, fp, code, msg, headers, newurl)
            fwd = dict(req.headers)
            if _origin(req.full_url) != _origin(newurl):
                dropped = sorted(k for k in fwd if k.lower() in _SENSITIVE)
                for k in dropped:
                    del fwd[k]
                if dropped:
                    print(f"  note: redirect crosses origins ({newurl}); "
                          f"not forwarding {', '.join(dropped)}")
            return urllib.request.Request(newurl, data=req.data, headers=fwd,
                                          method=req.get_method())

    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ctx),
        _PostRedirectHandler(),
    )
    try:
        with opener.open(req, timeout=60) as resp:
            data = json.loads(resp.read())
            print(f"[OK] Success: {data}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[FAIL] HTTP {e.code}: {body}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Request failed: {e}")
        sys.exit(1)

    print("\nLeaderboard updated. The website will show the new data immediately.")

if __name__ == "__main__":
    main()
