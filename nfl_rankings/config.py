"""Paths and settings shared by every model."""
from pathlib import Path

SEASON = 2026
SEASON_GAMES = 17

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"            # downloaded nflverse files (not committed)
MODEL = ROOT / "data" / "model"        # full model output, one CSV per group (committed)
DASH = ROOT / "data" / "dashboard"     # the exact CSVs the dashboard reads (committed)
ODDS = ROOT / "odds"                   # award odds inputs and history (committed)

NFLVERSE = "https://github.com/nflverse/nflverse-data/releases/download"
FILES = {
    f"pbp_{SEASON}.csv.gz": f"{NFLVERSE}/pbp/play_by_play_{SEASON}.csv.gz",
    f"roster_{SEASON}.csv": f"{NFLVERSE}/rosters/roster_{SEASON}.csv",
    "ngs_rushing.csv.gz": f"{NFLVERSE}/nextgen_stats/ngs_rushing.csv.gz",
    "games.csv": f"{NFLVERSE}/schedules/games.csv",
}

# ---- QB model
QB_MIN_SNAP_SHARE = 0.66   # share of team dropbacks
GARBAGE_WP = (0.10, 0.90)  # garbage time = offense win prob outside this band

# ---- RB / WR models
RB_MIN_CARRIES = 50
WR_MIN_TARGETS = 30
USAGE_CAP = 0.30           # usage stats can't exceed this share of a score, combined

# ---- projections
PRIOR_GAMES = 4            # games of group-average production blended into per-game rates
