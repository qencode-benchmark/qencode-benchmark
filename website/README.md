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

The site serves leaderboard data from:

- `website/public/data/leaderboard_accuracy.csv`
- `website/public/data/leaderboard_hardware_cost.csv`
- `website/public/data/leaderboard_balanced.csv`
- `website/public/data/leaderboard_metadata.json`

To refresh from the latest benchmark release:

```bash
python scripts/sync_website_leaderboard_data.py
```

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
