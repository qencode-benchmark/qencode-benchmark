import fs from "node:fs";
import path from "node:path";

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length === 0) return [];
  const headers = lines[0].split(",");
  return lines.slice(1).map((line) => {
    const values = line.split(",");
    const row = {};
    headers.forEach((h, i) => {
      row[h] = values[i];
    });
    return row;
  });
}

function num(v) {
  if (v === undefined || v === null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export function loadLeaderboardData() {
  const base = path.join(process.cwd(), "public", "data");
  const acc = parseCsv(fs.readFileSync(path.join(base, "leaderboard_accuracy.csv"), "utf-8")).map((r) => ({
    ...r,
    rank: num(r.rank),
    gap: num(r.gap),
    depth: num(r.depth),
    twoQ: num(r["2q_gates"]),
    baseline: String(r.baseline).toLowerCase() === "true"
  }));
  const cost = parseCsv(fs.readFileSync(path.join(base, "leaderboard_hardware_cost.csv"), "utf-8")).map((r) => ({
    ...r,
    rank: num(r.rank),
    gap: num(r.gap),
    depth: num(r.depth),
    twoQ: num(r["2q_gates"]),
    baseline: String(r.baseline).toLowerCase() === "true"
  }));
  const balanced = parseCsv(fs.readFileSync(path.join(base, "leaderboard_balanced.csv"), "utf-8")).map((r) => ({
    ...r,
    rank: num(r.rank),
    gap: num(r.gap),
    depth: num(r.depth),
    twoQ: num(r["2q_gates"]),
    balancedScore: num(r.balanced_score),
    baseline: String(r.baseline).toLowerCase() === "true"
  }));
  const metadata = JSON.parse(fs.readFileSync(path.join(base, "leaderboard_metadata.json"), "utf-8"));

  return { acc, cost, balanced, metadata };
}

