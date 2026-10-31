"""Download nflverse data and load play-by-play through the latest completed week."""
import subprocess

import pandas as pd

from .config import FILES, RAW, SEASON


def download():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        dest = RAW / name
        subprocess.run(["curl", "-sSfL", "--retry", "3", "-o", str(dest), url], check=True)
        print(f"downloaded {name} ({dest.stat().st_size:,} bytes)")


def completed_week():
    """Latest regular-season week whose games have all finished."""
    g = pd.read_csv(RAW / "games.csv")
    g = g[(g.season == SEASON) & (g.game_type == "REG")]
    done = g.groupby("week").result.apply(lambda s: s.notna().all())
    done_weeks = done[done].index
    return int(done_weeks.max()) if len(done_weeks) else 0


def load_pbp(through_week):
    d = pd.read_csv(RAW / f"pbp_{SEASON}.csv.gz", low_memory=False)
    d = d[(d.season_type == "REG") & (d.week <= through_week) & d.epa.notna() & d.posteam.notna()]
    d = d[(d.qb_kneel != 1) & (d.qb_spike != 1) & (d.two_point_attempt != 1)]
    return d


def roster():
    return pd.read_csv(RAW / f"roster_{SEASON}.csv")


def ngs_rushing(weeks):
    n = pd.read_csv(RAW / "ngs_rushing.csv.gz")
    n = n[(n.season == SEASON) & n.week.isin(list(weeks))]
    g = n.groupby("player_gsis_id").agg(ryoe=("rush_yards_over_expected", "sum"), att=("rush_attempts", "sum"))
    return g.to_dict("index")
