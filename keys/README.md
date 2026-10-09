# Project signing key

`qencode_ed25519_public.pem` is the public half of the key QEncode signs entries with.

| | |
|---|---|
| algorithm | Ed25519 (RFC 8032) |
| key id | `ed25519:85d603a74774d0ac` — the first 16 hex digits of the SHA-256 of the raw 32-byte public key |
| created | 2026-10-09 |
| signs | every entry in `releases/v4/db/` |

Each entry's `trust.signature_b64` is a signature over the message

    qencode/entry-sha256/v1:<provenance.entry_hash_sha256>

and `trust.signing_key_id` names this key. To check one entry, or all of them, with nothing
installed beyond Python:

```bash
python scripts/verify_entry.py releases/v4/db/<entry>.json --hash-only --require-signature
```

A valid signature shows that the holder of the private key signed exactly this content. It
does not show that the computation was right; re-running the entry
(`python scripts/verify_entry.py <entry>.json`) checks that. See
[docs/VERIFY.md](../docs/VERIFY.md).

The private key is not in this repository and never will be. If it is ever replaced, the
new public key will be added here alongside this one, with the date, and every entry
re-signed; a signature by a key not listed here is not a QEncode signature.
