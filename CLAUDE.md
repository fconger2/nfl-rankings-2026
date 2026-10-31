# Weekly update procedure

This repo powers the dashboard at https://claude.ai/artifact/2axP89esYs8A2ZwcBjgtwi (a Dashboard-type artifact).
Each Tuesday's update does the steps below, in order. Work on `main`.

## 1. Refresh award odds (`odds/input.json`)

Search the web for the current boards and rewrite `odds/input.json`, keeping its structure exactly:

- `as_of`: date of the MVP book board (YYYY-MM-DD).
- `mvp.odds`: DraftKings MVP odds, `[full name, team, position, "+odds"]`. Good sources: The Big Lead "NFL MVP odds entering Week N", Sports Illustrated betting, ESPN's awards betting tracker.
- `awards.{opoy,dpoy,oroy,droy,coy}`: DraftKings boards (ESPN's "NFL awards tracker: odds for MVP, Rookie of the Year and more" lists all of them). `cpoy`: the SportsBettingDime comeback consensus if DraftKings isn't shown.
- `kalshi.<award>.chance`: percent chance for each name Kalshi's market page shows (kalshi.com/markets/kxnflmvp/..., kxnflopoty-27, kxnfldpoty-27, kxnfloroty-27, kxnfldroty-27, kxnflcoty-27). Comeback: CryptoStruct's Kalshi KXNFLCPOTY page (last trades). Add a `teams` map for any Kalshi-only name.
- Update every `source` string with the outlet and date.

Only use numbers you actually found on a page dated this week. If a board can't be found, leave that award's previous entry as it is and say so in the commit message.
Don't change `odds/history/` by hand; `run.py` copies `input.json` there.

## 2. Run the models

```bash
pip install -r requirements.txt   # pandas, numpy
python run.py
```

It downloads nflverse data and uses the latest week whose games have all finished. Check the printout:
- `through week` should be one higher than last week's `data/dashboard/meta.csv` (if it isn't, the data hasn't posted yet: stop and report).
- Top-5 lists should look sensible (no blank names, no team listed twice in DEF).

`run.py` also rebuilds `index.html` (the GitHub Pages site at https://fconger2.github.io/nfl-rankings-2026/), so committing publishes the site.

## 3. Commit and push

```bash
git add -A
git commit -m "Week N update"
git push origin main
```

## 4. Update the dashboard

Artifact URL: `https://claude.ai/artifact/2axP89esYs8A2ZwcBjgtwi`

For every file in `data/dashboard/`, the dataset id is the file name without `.csv`:
`qbs, proj, weights, meta, rbs, wrs, defense, pos_proj, pos_weights, pos_meta, mvp, awards`.

1. Upload each CSV to the artifact's asset store (Artifact tool, `action: publish`, `url`, `asset: true`, `file_path`). Each upload returns a `/_blob/<id>` url.
2. Read each `datasets/<id>` document (ArtifactData `get`) for its version, then in one ArtifactData `batch` `update` each with
   `source: {kind: "file", url: "<new /_blob url>", name: "<file>.csv"}`, `updated: {at: <now ISO>, by: "Claude"}`,
   and change "through Week N" in its `description` where it appears. Pin each entry with `if_version`.
3. If `dashboard/index.html` changed in this commit, also `set` `files/index.html` to `{text: <file contents>}` in the same batch.
4. Read `data/users/me` doc `check` until it isn't `checking` (5 reads max); fix anything it reports as failed.
5. List the artifact's assets (`action: list`, `scope: assets`) and delete any blob no dataset references anymore.

## 5. Report

Send a short summary: the week now covered, the No. 1 in each group, the biggest movers in each top 10 versus last week (compare with the previous commit's `data/dashboard/*.csv`), and any odds board that couldn't be refreshed.
