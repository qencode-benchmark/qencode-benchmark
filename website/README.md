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

