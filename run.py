"""Weekly pipeline: download data, run every model, write model output and dashboard CSVs.

    python run.py                 # latest completed week
    python run.py --week 7        # a specific week
    python run.py --skip-download # reuse files already in data/raw
"""
import argparse
import json

from nfl_rankings import data, dashboard, odds, positions, qb
from nfl_rankings.config import MODEL, SEASON


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int, help="last week to include (default: latest completed week)")
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args()

    if not args.skip_download:
        data.download()
    week = args.week or data.completed_week()
    print(f"season {SEASON}, through week {week}")
    d = data.load_pbp(week)

    qb_ranked, qb_proj, qb_meta = qb.run(d)
    pos, pos_meta = positions.run(d, week)
    mvp, awards, odds_in = odds.build(qb_ranked, data.roster())

    MODEL.mkdir(parents=True, exist_ok=True)
    qb_ranked.to_csv(MODEL / "qb.csv", index=False)
    qb_proj.to_csv(MODEL / "qb_projections.csv", index=False)
    for k, v in pos.items():
        v.to_csv(MODEL / f"{k}.csv", index=False)
    (MODEL / "meta.json").write_text(json.dumps(
        {"season": SEASON, "through_week": week, "odds_as_of": odds_in["as_of"], "qb": qb_meta, **pos_meta}, indent=1, default=float))

    dashboard.write(qb_ranked, qb_proj, qb_meta, pos, pos_meta, mvp, awards, week)

    print("\nTop 5 each:")
    print("QB ", ", ".join(qb_ranked.name.head(5)))
    print("RB ", ", ".join(pos["rb"].name.head(5)))
    print("WR ", ", ".join(pos["wr"].name.head(5)))
    print("DEF", ", ".join(pos["def"].team.head(5)))
    print("MVP", ", ".join(f"{r.player} {r.novig}%" for r in mvp.head(3).itertuples()))


if __name__ == "__main__":
    main()
