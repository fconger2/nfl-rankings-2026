"""RB, WR and team-defense models."""
import numpy as np
import pandas as pd

from . import data
from .config import RB_MIN_CARRIES, WR_MIN_TARGETS
from .scoring import composite, project, split_reliability, weights_from

RB_FEATURES = [("adj_rush_epa", True, "anchor"), ("rush_success", True, ""), ("ryoe_att", True, ""),
               ("explosive_rate", True, ""), ("rec_epa_g", True, ""), ("touches_g", True, "usage")]
WR_FEATURES = [("adj_epa_tgt", True, "anchor"), ("yds_team_att", True, ""), ("tgt_share", True, "usage"),
               ("air_share", True, "usage"), ("croe", True, ""), ("yacoe", True, ""), ("tgt_success", True, "")]
DEF_FEATURES = [("adj_epa_allowed", False, "anchor"), ("success_allowed", False, ""), ("pass_epa_allowed", False, ""),
                ("rush_epa_allowed", False, ""), ("pressure_rate", True, ""), ("takeaway_rate", True, ""),
                ("explosive_allowed", False, "")]


def plays(d):
    return d[((d["pass"] == 1) | (d.rush == 1)) & d.epa.notna() & d.defteam.notna()].copy()


def rb_table(d, rb_ids, ngs):
    p = plays(d)
    all_runs = p[(p.rush == 1) & (p.qb_scramble != 1)]
    adj = all_runs.groupby("defteam").epa.mean() - all_runs.epa.mean()
    runs = all_runs[all_runs.rusher_player_id.isin(rb_ids)]
    runs = runs.assign(adj_epa=runs.epa - runs.defteam.map(adj).fillna(0))
    targets = p[(p.pass_attempt == 1) & (p.sack != 1) & p.receiver_player_id.isin(rb_ids)]
    rows = []
    for pid, g in runs.groupby("rusher_player_id"):
        t = targets[targets.receiver_player_id == pid]
        games = pd.concat([g.game_id, t.game_id]).nunique()
        rec = t[t.complete_pass == 1]
        n = ngs.get(pid, {})
        rows.append(dict(
            player_id=pid, name=g.rusher_player_name.mode().iat[0], team=g.posteam.mode().iat[0], games=games,
            carries=len(g), rush_yds=int(g.rushing_yards.fillna(0).sum()), rush_td=int(g.rush_touchdown.sum()),
            ypc=g.rushing_yards.fillna(0).sum() / len(g),
            targets=len(t), rec=len(rec), rec_yds=int(rec.receiving_yards.fillna(0).sum()), rec_td=int(t.pass_touchdown.sum()),
            fum_lost=int(((p.fumble_lost == 1) & (p.fumbled_1_player_id == pid)).sum()),
            adj_rush_epa=g.adj_epa.mean(), rush_epa=g.epa.mean(), rush_success=g.success.mean(),
            explosive_rate=(g.rushing_yards >= 10).mean(),
            ryoe_att=(n["ryoe"] / n["att"]) if n.get("att") else np.nan,
            rec_epa_g=t.epa.sum() / games, touches_g=(len(g) + len(rec)) / games, total_epa=g.epa.sum() + t.epa.sum(),
        ))
    out = pd.DataFrame(rows)
    out["scrim_yds"] = out.rush_yds + out.rec_yds
    return out


def wr_table(d, wr_ids):
    p = plays(d)
    passes = p[(p.pass_attempt == 1) & (p.sack != 1)]
    adj = passes.groupby("defteam").epa.mean() - passes.epa.mean()
    t_all = passes[passes.receiver_player_id.notna()].copy()
    t_all["adj_epa"] = t_all.epa - t_all.defteam.map(adj).fillna(0)
    team_att = passes.groupby(["posteam", "game_id"]).size()
    team_air = passes.groupby(["posteam", "game_id"]).air_yards.apply(lambda s: s.clip(lower=0).sum())
    rows = []
    for pid, g in t_all[t_all.receiver_player_id.isin(wr_ids)].groupby("receiver_player_id"):
        team = g.posteam.mode().iat[0]
        gids = g.game_id.unique()
        att = team_att.loc[team].reindex(gids).sum()
        air = team_air.loc[team].reindex(gids).sum()
        rec = g[g.complete_pass == 1]
        rows.append(dict(
            player_id=pid, name=g.receiver_player_name.mode().iat[0], team=team, games=len(gids),
            targets=len(g), rec=len(rec), rec_yds=int(rec.receiving_yards.fillna(0).sum()), rec_td=int(g.pass_touchdown.sum()),
            air_yds=int(g.air_yards.fillna(0).sum()), yac=int(rec.yards_after_catch.fillna(0).sum()),
            catch_pct=len(rec) / len(g), ypr=rec.receiving_yards.fillna(0).sum() / max(len(rec), 1), adot=g.air_yards.mean(),
            adj_epa_tgt=g.adj_epa.mean(), epa_tgt=g.epa.mean(), tgt_success=g.success.mean(),
            yds_team_att=rec.receiving_yards.fillna(0).sum() / att, tgt_share=len(g) / att,
            air_share=g.air_yards.fillna(0).clip(lower=0).sum() / air,
            croe=(g.complete_pass - g.cp).mean(), yacoe=(rec.yards_after_catch - rec.xyac_mean_yardage).mean(),
            total_epa=g.epa.sum(),
        ))
    return pd.DataFrame(rows)


def def_table(d):
    p = plays(d)
    off_adj = p.groupby("posteam").epa.mean() - p.epa.mean()
    p = p.assign(adj_epa=p.epa - p.posteam.map(off_adj).fillna(0))
    db, ru = p[p.qb_dropback == 1], p[(p.rush == 1) & (p.qb_dropback != 1)]
    fin = d.sort_values("play_id").groupby("game_id").tail(1)
    pa = pd.concat([fin[["home_team", "total_away_score"]].rename(columns={"home_team": "team", "total_away_score": "pa"}),
                    fin[["away_team", "total_home_score"]].rename(columns={"away_team": "team", "total_home_score": "pa"})])
    pa = pa.groupby("team").pa.agg(["sum", "count"])
    third = p[p.down == 3]
    rz = d[(d.yardline_100 <= 20) & d.drive.notna()].drop_duplicates(["game_id", "posteam", "drive"])
    drv = d[d.drive.notna()].groupby(["game_id", "posteam", "drive"]).agg(td=("touchdown", "max"), team=("defteam", "first"))
    rz_drives = drv.loc[drv.index.isin(rz.set_index(["game_id", "posteam", "drive"]).index)]
    rows = []
    for team, g in p.groupby("defteam"):
        gd, gr = db[db.defteam == team], ru[ru.defteam == team]
        take = ((g.interception == 1) | (g.fumble_lost == 1)).sum()
        t3, rzt = third[third.defteam == team], rz_drives[rz_drives.team == team]
        rows.append(dict(
            team=team, games=g.game_id.nunique(), plays=len(g),
            adj_epa_allowed=g.adj_epa.mean(), epa_allowed=g.epa.mean(), success_allowed=g.success.mean(),
            pass_epa_allowed=gd.epa.mean(), rush_epa_allowed=gr.epa.mean(),
            pressure_rate=((gd.sack == 1) | (gd.qb_hit == 1)).mean(), sack_rate=(gd.sack == 1).mean(),
            takeaway_rate=take / len(g), takeaways=int(take), sacks=int(gd.sack.sum()),
            explosive_allowed=(((g["pass"] == 1) & (g.yards_gained >= 20)) | ((g.rush == 1) & (g.yards_gained >= 10))).mean(),
            ypp_allowed=g.yards_gained.mean(), ppg_allowed=pa.loc[team, "sum"] / pa.loc[team, "count"],
            third_conv=(t3.first_down == 1).mean() if len(t3) else np.nan, rz_td_rate=rzt.td.mean() if len(rzt) else np.nan,
        ))
    return pd.DataFrame(rows)


def run(d, through_week):
    ros = data.roster()
    rb_ids = set(ros[ros.position == "RB"].gsis_id.dropna())
    wr_ids = set(ros[ros.position == "WR"].gsis_id.dropna())
    halves = [d[d.week % 2 == 1], d[d.week % 2 == 0]]
    ngs = data.ngs_rushing(range(1, through_week + 1))
    ngs_half = [data.ngs_rushing(range(1, through_week + 1, 2)), data.ngs_rushing(range(2, through_week + 1, 2))]

    p = plays(d)
    team_games = p.groupby("posteam").game_id.nunique()
    latest = p[p.game_id == p.posteam.map(p.groupby("posteam").game_id.max())]
    active = set(latest.rusher_player_id.dropna()) | set(latest.receiver_player_id.dropna())
    out, meta = {}, {}

    rel, n = split_reliability(lambda h: rb_table(h, rb_ids, ngs_half[int(h.week.iat[0] % 2 == 0)]), RB_FEATURES, halves,
                               "player_id", lambda x: x.carries >= RB_MIN_CARRIES / 2.5)
    w = weights_from(rel, RB_FEATURES)
    rb = rb_table(d, rb_ids, ngs)
    rb = composite(rb[rb.carries >= RB_MIN_CARRIES], RB_FEATURES, w)
    rb = project(rb, team_games, ["carries", "rush_yds", "rush_td", "rec", "rec_yds", "rec_td"], "player_id", active)
    out["rb"], meta["rb"] = rb, dict(weights=w, reliability=rel, reliability_n=n, min=RB_MIN_CARRIES, n=len(rb))

    rel, n = split_reliability(lambda h: wr_table(h, wr_ids), WR_FEATURES, halves, "player_id",
                               lambda x: x.targets >= WR_MIN_TARGETS / 2.5)
    w = weights_from(rel, WR_FEATURES)
    wr = wr_table(d, wr_ids)
    wr = composite(wr[wr.targets >= WR_MIN_TARGETS], WR_FEATURES, w)
    wr = project(wr, team_games, ["targets", "rec", "rec_yds", "rec_td"], "player_id", active)
    out["wr"], meta["wr"] = wr, dict(weights=w, reliability=rel, reliability_n=n, min=WR_MIN_TARGETS, n=len(wr))

    rel, n = split_reliability(def_table, DEF_FEATURES, halves, "team", lambda x: x.plays > 0)
    w = weights_from(rel, DEF_FEATURES)
    out["def"] = composite(def_table(d), DEF_FEATURES, w)
    meta["def"] = dict(weights=w, reliability=rel, reliability_n=n, n=32)
    return out, meta
