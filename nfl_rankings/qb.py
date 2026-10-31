"""QB model: opponent-adjusted efficiency + offense efficiency, garbage-time split, projections."""
import numpy as np
import pandas as pd

from .config import GARBAGE_WP, QB_MIN_SNAP_SHARE
from .scoring import composite, project, split_reliability, weights_from

# (stat, higher_is_better, kind) — "anchor" keeps a minimum weight
FEATURES = [("adj_epa", True, "anchor"), ("cpoe", True, ""), ("success", True, ""), ("sack_rate", False, ""),
            ("to_rate", False, ""), ("rush_epa_g", True, ""), ("off_epa", True, "")]


def qb_plays(d):
    """Dropbacks (pass, sack, scramble) + QB designed runs, tagged with the QB's id."""
    db = d[d.qb_dropback == 1].copy()
    db["qb_id"], db["qb_name"], db["kind"] = db["id"], db["name"], "dropback"
    db = db[db.qb_id.notna()]
    qbs = set(db.groupby("qb_id").size().loc[lambda s: s >= 20].index)
    run = d[(d.rush_attempt == 1) & (d.qb_scramble != 1) & (d.qb_dropback != 1) & d.rusher_player_id.isin(qbs)].copy()
    run["qb_id"], run["qb_name"], run["kind"] = run.rusher_player_id, run.rusher_player_name, "run"
    p = pd.concat([db, run], ignore_index=True)
    p = p[p.qb_id.isin(qbs)]
    p["garbage"] = (p.wp < GARBAGE_WP[0]) | (p.wp > GARBAGE_WP[1])
    for kind, mask in [("dropback", d.qb_dropback == 1), ("run", (d.rush_attempt == 1) & (d.qb_dropback != 1))]:
        sub = d[mask]
        adj = sub.groupby("defteam").epa.mean() - sub.epa.mean()
        m = p.kind == kind
        p.loc[m, "def_adj"] = p.loc[m, "defteam"].map(adj).fillna(0)
    p["adj_epa_play"] = p.qb_epa - p.def_adj
    return p


def summarize(p, d):
    rows = []
    offense = d[(d["pass"] == 1) | (d.rush == 1)]
    for qid, g in p.groupby("qb_id"):
        db = g[g.kind == "dropback"]
        att = db[(db.complete_pass == 1) | (db.incomplete_pass == 1) | (db.interception == 1)]
        sacks = db[db.sack == 1]
        rush = g[g.rusher_player_id == qid]
        comp, pyds = att.complete_pass.sum(), att.passing_yards.fillna(0).sum()
        ptd, ints = att.pass_touchdown.sum(), att.interception.sum()
        fl = ((g.fumble_lost == 1) & (g.fumbled_1_player_id == qid)).sum()
        sack_yds = -sacks.yards_gained.sum()
        games = g.game_id.nunique()
        gt, ngt = g[g.garbage], g[~g.garbage]
        team = g.posteam.mode().iat[0]
        off = offense[(offense.posteam == team) & offense.game_id.isin(g.game_id.unique())]
        nonqb_run = off[(off.rush == 1) & (off.qb_dropback != 1) & (off.rusher_player_id != qid)]
        rows.append(dict(
            qb_id=qid, name=g.qb_name.mode().iat[0], team=team, games=games, dropbacks=len(db), plays=len(g),
            epa_play=g.qb_epa.mean(), epa_db=db.qb_epa.mean(), adj_epa=g.adj_epa_play.mean(), total_epa=g.qb_epa.sum(),
            cpoe=att.cpoe.mean(), success=db.success.mean(), sack_rate=len(sacks) / max(len(db), 1),
            to_rate=(ints + fl) / max(len(g), 1), adot=att.air_yards.mean(), rush_epa_g=rush.qb_epa.sum() / games,
            comp=int(comp), att=len(att), pass_yds=int(pyds), pass_td=int(ptd), ints=int(ints), fum_lost=int(fl),
            sacks=len(sacks), comp_pct=comp / max(len(att), 1), ypa=pyds / max(len(att), 1),
            anya=(pyds + 20 * ptd - 45 * ints - sack_yds) / max(len(att) + len(sacks), 1),
            rush_att=len(rush), rush_yds=int(rush.rushing_yards.fillna(0).sum()), rush_td=int((rush.rush_touchdown == 1).sum()),
            gt_share=len(gt) / len(g), gt_plays=len(gt), gt_epa_play=gt.qb_epa.mean() if len(gt) else np.nan,
            gt_epa_total=gt.qb_epa.sum(), nongt_epa_play=ngt.qb_epa.mean(),
            off_epa=off.epa.mean(), off_success=off.success.mean(), run_game_epa=nonqb_run.epa.mean(),
        ))
    out = pd.DataFrame(rows)
    out["gt_boost"] = out.epa_play - out.nongt_epa_play
    return out


def run(d):
    halves = [d[d.week % 2 == 1], d[d.week % 2 == 0]]
    rel, n = split_reliability(lambda h: summarize(qb_plays(h), h), FEATURES, halves, "qb_id", lambda x: x.dropbacks >= 40)
    raw = {f: max(rel[f], 0.05) for f, _, _ in FEATURES}
    raw["adj_epa"] = max(raw["adj_epa"], 0.5)
    tot = sum(raw.values())
    weights = {f: round(v / tot, 4) for f, v in raw.items()}  # QBs: no usage stats, so no cap

    q = summarize(qb_plays(d), d)
    team_db = d[(d.qb_dropback == 1) & d.id.notna()].groupby("posteam").size()
    q["snap_share"] = q.dropbacks / q.team.map(team_db)

    # projections: each team's current starter (most dropbacks in its latest game), qualified or not
    db = d[(d.qb_dropback == 1) & d.id.notna()]
    latest = db[db.game_id == db.posteam.map(db.groupby("posteam").game_id.max())]
    starters = set(latest.groupby(["posteam", "id"]).size().reset_index().sort_values(0).groupby("posteam").tail(1).id)
    team_games = d.groupby("posteam").game_id.nunique()
    stats = ["pass_yds", "pass_td", "ints", "rush_yds", "rush_td", "comp", "att"]
    q = project(q, team_games, stats, "qb_id", starters, baseline=q[q.snap_share >= QB_MIN_SNAP_SHARE])
    q = q.rename(columns={"active": "starter"})
    proj = q[q.starter].copy()

    ranked = composite(q[q.snap_share >= QB_MIN_SNAP_SHARE], FEATURES, weights)
    ranked["gt_rank"] = ranked.gt_epa_total.rank(ascending=False, method="min").astype(int)
    meta = dict(weights=weights, reliability=rel, reliability_n=n, min_snap_share=QB_MIN_SNAP_SHARE, n=len(ranked))
    return ranked, proj, meta
