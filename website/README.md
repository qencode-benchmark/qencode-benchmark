# QEncode Leaderboard Website (Vercel Stack)

This folder contains a public-facing Next.js website for the QEncode leaderboard.

## Local development

```bash
cd website
npm install
npm run dev
```

Open http://localhost:3000.

## Data source

In production the leaderboard is served from Neon Postgres. The CSVs in
`website/public/data/` are the local-development fallback, used automatically when
`POSTGRES_URL` is unset:

- `leaderboard_accuracy.csv`, `leaderboard_hardware_cost.csv`,
  `leaderboard_balanced.csv`, `leaderboard_research.csv`
- `leaderboard_metadata.json`
- `references_v4.json` — the reference energies behind `/score`, a byte-for-byte copy of
  the table shipped in the Python package. `tests/test_website_references.py` fails if
  the two ever differ.

To regenerate the CSVs from the entry database and publish them:

```bash
python scripts/export_leaderboard_v4.py            # entry JSONs -> CSVs
python scripts/publish_leaderboard.py              # CSVs -> live Postgres
```

Use `--dry-run` on either to see what would happen without writing anything.

> Until 2026-09-04 this section told you to run `scripts/sync_website_leaderboard_data.py`,
> a script that has never existed in this repository.

## Design (Phase 2)

The UI was upgraded to a more polished "Lovable-style" look (hero, gradient cards, improved tables) while keeping the dataset-driven leaderboard logic unchanged.

## Deploy to Vercel

1. Push this repo to GitHub.
2. In Vercel: **Add New Project** -> import repo.
3. Set **Root Directory** to `website`.
4. Build command: `npm run build`
5. Output: default Next.js output.

After deploy, attach your custom domain in Vercel settings.


## Local build

`npm run build` works from a clean checkout **with no environment variables**: every
route reads its secrets at request time, and the mail client is constructed on first
send rather than at import (an import-time client made the whole site unbuildable on any
machine without the production Resend key, until 2026-09-04).

- Node **20 or newer**. `@neondatabase/serverless` requires >= 19 and the Ubuntu 24.04
  apt package is 18. A user-level install from the official nodejs.org tarball is enough;
  no sudo needed.
- If a build fails with `Cannot find module .../loaders/next-app-loader.js`, delete
  `.next/` and rebuild. That path comes from a persisted webpack cache written by an
  older Next where the loader was a file; Next 15 ships it as a directory. The cache
  survives `npm ci`.
- Vercel builds with its own Node and a clean cache, which is why a build can pass there
  and fail locally without any code difference.
