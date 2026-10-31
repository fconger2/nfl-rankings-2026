# nfl-rankings-2026

QB, RB, WR and team-defense rankings for the 2026 NFL season, built from advanced stats, plus award-odds ladders from sportsbooks and Kalshi.

**Website: https://fconger2.github.io/nfl-rankings-2026/**  
Claude dashboard version: https://claude.ai/artifact/2axP89esYs8A2ZwcBjgtwi

## How the rankings work

Every group is scored the same way:

1. **Compute the stats** from [nflverse](https://github.com/nflverse/nflverse-data) play-by-play (plus Next Gen Stats rush yards over expected for RBs). Efficiency stats are **opponent-adjusted**: each play's EPA has the opposing unit's average subtracted.
2. **Standardize** each stat into a z-score within the group.
3. **Weight each stat by how consistent it is this season**: the correlation between a player's odd-week and even-week numbers. Stats that hold steady reflect skill; noisy ones get little say. The main efficiency stat always keeps a meaningful weight, and usage stats (touches, target share, air yards share) are capped at 30% combined.
4. **Scale** the weighted sum so 50 = group average and 10 = one standard deviation.

| Group | Qualifier | Stats in the score |
|---|---|---|
| QB | 66%+ of team dropbacks | Adj EPA/play, success rate, offense EPA/play, CPOE, sack rate, rushing EPA/game, turnover rate |
| RB | 50+ carries | Adj rush EPA/carry, success rate, rush yards over expected/carry, 10+ yard run rate, receiving EPA/game, touches/game |
| WR | 30+ targets | Adj EPA/target, yards per team pass attempt, target share, air yards share, catch rate over expected, YAC over expected, success rate |
| Defense | All 32 | Adj EPA/play allowed, success rate allowed, pass EPA allowed, rush EPA allowed, pressure rate, takeaway rate, explosive plays allowed |

Garbage time is kept in every score; the QB board shows how much each QB gains from it separately.

**Projections**: per-game rates blended with four games of the group average, times the team's remaining games. QBs: each team's current starter. RBs/WRs: players who played in their team's latest game.

**Award ladders**: book odds are converted to implied probabilities and divided by their sum to strip the vig. Books only list the top of each market, so leaders' chances run slightly high. Kalshi prices are shown alongside for the names Kalshi displays publicly.

## Running it

```bash
pip install -r requirements.txt
python run.py              # downloads data, uses the latest completed week
python run.py --week 8     # pick a week
```

Outputs:

- `data/model/` — full model output for every group, plus `meta.json` with weights and consistency numbers
- `data/dashboard/` — the exact CSVs the dashboard reads
- `index.html` — the GitHub Pages site, rebuilt by `run.py` from `dashboard/index.html` + `site/shell.html`; it reads `data/dashboard/*.csv`
- `odds/input.json` — current award odds (edit this to update ladders); each run saves a copy to `odds/history/`

Settings (qualifiers, usage cap, projection prior) live in `nfl_rankings/config.py`.

## Weekly updates

A scheduled task runs every Tuesday morning: it refreshes the odds, runs `run.py`, commits the results here and updates the dashboard. Steps are in `CLAUDE.md`.
