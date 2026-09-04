"""The publish secret must never reach an origin the server chose.

`scripts/publish_leaderboard.py` POSTs the leaderboard with the publish secret in an
Authorization header. urllib drops the body when it follows a redirect, so the script
re-issues 307/308 by hand — and the first version of that handler forwarded
`dict(req.headers)` verbatim. A redirect target is chosen by the *server*, so any
redirect, hostile or merely misconfigured, could harvest the credential that controls
the public leaderboard.

Both directions are pinned, because the obvious fix breaks the real path:

  cross-origin  the credential must be withheld
  same-origin   the credential must still be forwarded, since Vercel legitimately
                307s between www and apex and publishing must keep working

Two throwaway HTTP servers on loopback record exactly what they were sent. No network,
no real credential, nothing published.

    pytest tests/test_publish_credential_safety.py -v
"""
from __future__ import annotations

import http.server
import json
import re
import socket
import subprocess
import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "publish_leaderboard.py"
SECRET = "TEST-SECRET-NOT-A-REAL-CREDENTIAL"


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _serve(port, handler):
    srv = http.server.HTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _publish_to(url):
    """Run the real script against a local URL. Returns without publishing anything."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--secret", SECRET, "--url", url],
        cwd=str(REPO), capture_output=True, text=True, timeout=180,
    )


def _recorder(seen, name, redirect_to=None):
    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            seen.setdefault(name, []).append(
                {k.lower(): v for k, v in self.headers.items()})
            self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
            if redirect_to:
                self.send_response(307)
                self.send_header("Location", redirect_to + self.path)
                self.end_headers()
                return
            body = json.dumps({"ok": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass
    return H


def test_secret_is_not_forwarded_across_origins():
    seen = {}
    port_a, port_b = _free_port(), _free_port()
    # localhost and 127.0.0.1 resolve to the same host but are a different origin by
    # hostname, which is exactly the comparison the script makes.
    srv_b = _serve(port_b, _recorder(seen, "B"))
    srv_a = _serve(port_a, _recorder(seen, "A", "http://localhost:%d" % port_b))
    try:
        _publish_to("http://127.0.0.1:%d" % port_a)
    finally:
        srv_a.shutdown()
        srv_b.shutdown()

    assert seen.get("A"), "the origin server was never reached"
    assert "authorization" in seen["A"][0], "the credential must reach the real endpoint"
    assert seen.get("B"), "the redirect was never followed, so nothing was proven"
    assert "authorization" not in seen["B"][0], "publish secret leaked to another origin"
    assert "x-vercel-protection-bypass" not in seen["B"][0]


def test_secret_survives_a_same_origin_redirect():
    seen = {}
    port = _free_port()
    hits = {"n": 0}

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            seen.setdefault("C", []).append(
                {k.lower(): v for k, v in self.headers.items()})
            self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
            hits["n"] += 1
            if hits["n"] == 1:
                self.send_response(307)
                self.send_header("Location", "http://127.0.0.1:%d/second" % port)
                self.end_headers()
                return
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = _serve(port, H)
    try:
        _publish_to("http://127.0.0.1:%d" % port)
    finally:
        srv.shutdown()

    assert len(seen.get("C", [])) == 2, "the same-origin redirect was not followed"
    assert "authorization" in seen["C"][1], (
        "the credential was dropped on a same-origin redirect; publishing would break")


def test_no_bypass_token_is_hardcoded():
    """The Vercel bypass token is a credential and belongs in the environment.

    Matches the header name mapped to a literal value, rather than any line mentioning
    the header — the module also names it in a list of headers to strip on redirect,
    which is the opposite of a leak.
    """
    src = SCRIPT.read_text(encoding="utf-8")
    assert "VERCEL_PROTECTION_BYPASS" in src, "the env var is how the token is supplied"
    hardcoded = re.findall(
        r"""["']x-vercel-protection-bypass["']\s*:\s*["'][A-Za-z0-9_\-]{12,}["']""",
        src, re.IGNORECASE)
    assert not hardcoded, "bypass token is hardcoded in the source: %s" % hardcoded


def test_tls_verification_is_on_by_default():
    src = SCRIPT.read_text(encoding="utf-8")
    assert "CERT_NONE" in src, "the insecure path should still exist, behind a flag"
    # every CERT_NONE assignment must sit under the --insecure branch
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if "CERT_NONE" in line and not line.strip().startswith("#"):
            window = "\n".join(lines[max(0, i - 8):i])
            assert "args.insecure" in window, (
                "TLS verification is disabled outside the --insecure branch")
