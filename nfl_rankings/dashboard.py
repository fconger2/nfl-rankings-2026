"""Write the exact CSVs the dashboard reads (data/dashboard/*.csv)."""
import pandas as pd

from .config import DASH


def _r(s, n):
    return s.round(n)


def _pc(s):
    return (s * 100).round(1)


QB_WEIGHT_LABELS = {
    "adj_epa": ("Opponent-adjusted EPA/play", "Points added per play vs. what that defense usually allows"),
    "success": ("Success rate", "Share of dropbacks that gain positive EPA"),
    "off_epa": ("Offense EPA/play", "How efficient his whole offense (every pass and run) has been in his games"),
    "cpoe": ("CPOE", "Completion % above what the throw difficulty predicts"),
    "sack_rate": ("Sack rate (lower is better)", "Sacks per dropback"),
    "rush_epa_g": ("Rushing EPA per game", "Points added on scrambles and designed runs"),
    "to_rate": ("Turnover rate (lower is better)", "INTs + lost fumbles per play"),
}
POS_WEIGHT_LABELS = {
    "adj_rush_epa": ("RB", "Opponent-adjusted rush EPA/carry", "Points added per carry vs. what that defense usually allows on runs"),
    "rush_success": ("RB", "Rush success rate", "Share of carries that gain positive EPA"),
    "ryoe_att": ("RB", "Rush yards over expected/carry", "Next Gen Stats: yards beyond what blocking and defenders' positions predicted"),
    "explosive_rate": ("RB", "Explosive run rate", "Share of carries going 10+ yards"),
    "rec_epa_g": ("RB", "Receiving EPA per game", "Points added on targets"),
    "touches_g": ("RB", "Touches per game", "Carries plus catches: his role in the offense"),
    "adj_epa_tgt": ("WR", "Opponent-adjusted EPA/target", "Points added per target vs. what that pass defense usually allows"),
    "yds_team_att": ("WR", "Yards per team pass attempt", "Receiving yards divided by his team's pass attempts in his games (a stand-in for yards per route run)"),
    "tgt_share": ("WR", "Target share", "Share of team targets in his games"),
    "air_share": ("WR", "Air yards share", "Share of team air yards in his games"),
    "croe": ("WR", "Catch rate over expected", "Catch rate above what throw difficulty predicts"),
    "yacoe": ("WR", "YAC over expected", "Yards after catch beyond the expected amount, per catch"),
    "tgt_success": ("WR", "Success rate per target", "Share of targets that gain positive EPA"),
    "adj_epa_allowed": ("DEF", "Opponent-adjusted EPA/play allowed", "Points allowed per play vs. what those offenses usually manage (lower is better)"),
    "success_allowed": ("DEF", "Success rate allowed", "Share of opponent plays that gain positive EPA (lower is better)"),
    "pass_epa_allowed": ("DEF", "Pass EPA/dropback allowed", "Lower is better"),
    "rush_epa_allowed": ("DEF", "Rush EPA/carry allowed", "Lower is better"),
    "pressure_rate": ("DEF", "Pressure rate", "Sacks plus QB hits per dropback"),
    "takeaway_rate": ("DEF", "Takeaway rate", "Interceptions plus fumble recoveries per play"),
    "explosive_allowed": ("DEF", "Explosive plays allowed", "Share of plays gaining 20+ through the air or 10+ on the ground (lower is better)"),
}


def write(qb, qb_proj, qb_meta, pos, pos_meta, mvp, awards, through_week):
    DASH.mkdir(parents=True, exist_ok=True)
    q = qb
    pd.DataFrame({
        "qb_id": q.qb_id, "rank": q["rank"], "qb": q.name, "team": q.team, "games": q.games, "dropbacks": q.dropbacks,
        "snap_share": _pc(q.snap_share), "score": _r(q.score, 1), "adj_epa": _r(q.adj_epa, 3), "epa_play": _r(q.epa_play, 3),
        "total_epa": _r(q.total_epa, 1), "cpoe": _r(q.cpoe, 1), "success": _pc(q.success), "sack_rate": _pc(q.sack_rate),
        "to_rate": _pc(q.to_rate), "adot": _r(q.adot, 1), "rush_epa_g": _r(q.rush_epa_g, 2), "off_epa": _r(q.off_epa, 3),
        "off_success": _pc(q.off_success), "run_game_epa": _r(q.run_game_epa, 3), "comp": q.comp, "att": q.att,
        "comp_pct": _pc(q.comp_pct), "pass_yds": q.pass_yds, "pass_td": q.pass_td, "ints": q.ints, "ypa": _r(q.ypa, 1),
        "anya": _r(q.anya, 1), "sacks": q.sacks, "rush_att": q.rush_att, "rush_yds": q.rush_yds, "rush_td": q.rush_td,
        "gt_plays": q.gt_plays, "gt_share": _pc(q.gt_share), "gt_epa_play": _r(q.gt_epa_play, 3),
        "gt_epa_total": _r(q.gt_epa_total, 1), "gt_boost": _r(q.gt_boost, 3), "gt_rank": q.gt_rank,
    }).to_csv(DASH / "qbs.csv", index=False)

    s = qb_proj
    proj = pd.DataFrame({"qb_id": s.qb_id, "qb": s.name, "team": s.team, "games_left": s.games_left.astype(int)})
    for k in ["pass_yds", "pass_td", "ints", "rush_yds", "rush_td"]:
        proj[f"{k}_ros"] = s[f"{k}_ros"].round().astype(int)
        proj[f"{k}_final"] = s[f"{k}_final"].round().astype(int)
    proj.sort_values("pass_yds_final", ascending=False).to_csv(DASH / "proj.csv", index=False)

    pd.DataFrame([{"feature": f, "stat": a, "meaning": b, "weight": round(qb_meta["weights"][f] * 100, 1),
                   "consistency": round(qb_meta["reliability"][f], 2)} for f, (a, b) in QB_WEIGHT_LABELS.items()]
                 ).sort_values("weight", ascending=False).to_csv(DASH / "weights.csv", index=False)
    pd.DataFrame([{"through_week": through_week, "n_qbs": len(q), "min_snap_share": int(qb_meta["min_snap_share"] * 100),
                   "n_starters": len(proj)}]).to_csv(DASH / "meta.csv", index=False)

    rb, wr, de = pos["rb"], pos["wr"], pos["def"]
    pd.DataFrame({
        "player_id": rb.player_id, "rank": rb["rank"], "player": rb.name, "team": rb.team, "games": rb.games,
        "score": _r(rb.score, 1), "adj_rush_epa": _r(rb.adj_rush_epa, 3), "rush_epa": _r(rb.rush_epa, 3),
        "rush_success": _pc(rb.rush_success), "ryoe_att": _r(rb.ryoe_att, 2), "explosive_rate": _pc(rb.explosive_rate),
        "rec_epa_g": _r(rb.rec_epa_g, 2), "touches_g": _r(rb.touches_g, 1), "carries": rb.carries, "rush_yds": rb.rush_yds,
        "ypc": _r(rb.ypc, 1), "rush_td": rb.rush_td, "targets": rb.targets, "rec": rb.rec, "rec_yds": rb.rec_yds,
        "rec_td": rb.rec_td, "scrim_yds": rb.scrim_yds, "fum_lost": rb.fum_lost,
    }).to_csv(DASH / "rbs.csv", index=False)
    pd.DataFrame({
        "player_id": wr.player_id, "rank": wr["rank"], "player": wr.name, "team": wr.team, "games": wr.games,
        "score": _r(wr.score, 1), "adj_epa_tgt": _r(wr.adj_epa_tgt, 3), "epa_tgt": _r(wr.epa_tgt, 3),
        "yds_team_att": _r(wr.yds_team_att, 2), "tgt_share": _pc(wr.tgt_share), "air_share": _pc(wr.air_share),
        "croe": _pc(wr.croe), "yacoe": _r(wr.yacoe, 2), "tgt_success": _pc(wr.tgt_success), "targets": wr.targets,
        "rec": wr.rec, "rec_yds": wr.rec_yds, "rec_td": wr.rec_td, "catch_pct": _pc(wr.catch_pct), "ypr": _r(wr.ypr, 1),
        "adot": _r(wr.adot, 1), "air_yds": wr.air_yds, "yac": wr.yac,
    }).to_csv(DASH / "wrs.csv", index=False)
    pd.DataFrame({
        "team": de.team, "rank": de["rank"], "games": de.games, "score": _r(de.score, 1),
        "adj_epa_allowed": _r(de.adj_epa_allowed, 3), "epa_allowed": _r(de.epa_allowed, 3),
        "success_allowed": _pc(de.success_allowed), "pass_epa_allowed": _r(de.pass_epa_allowed, 3),
        "rush_epa_allowed": _r(de.rush_epa_allowed, 3), "pressure_rate": _pc(de.pressure_rate),
        "takeaway_rate": _pc(de.takeaway_rate), "explosive_allowed": _pc(de.explosive_allowed),
        "ppg_allowed": _r(de.ppg_allowed, 1), "ypp_allowed": _r(de.ypp_allowed, 2), "sacks": de.sacks,
        "sack_rate": _pc(de.sack_rate), "takeaways": de.takeaways, "third_conv": _pc(de.third_conv), "rz_td_rate": _pc(de.rz_td_rate),
    }).to_csv(DASH / "defense.csv", index=False)

    rows = []
    for p, src, stats in (("RB", rb, ("carries", "rush_yds", "rush_td", "rec", "rec_yds", "rec_td")),
                          ("WR", wr, ("targets", "rec", "rec_yds", "rec_td"))):
        for x in src[src.active].itertuples():
            row = dict(key=f"{p}:{x.player_id}", pos=p, player=x.name, team=x.team, games_left=int(x.games_left))
            for st in stats:
                row[f"{st}_ros"] = int(round(getattr(x, f"{st}_ros")))
                row[f"{st}_final"] = int(round(getattr(x, f"{st}_final")))
            rows.append(row)
    pd.DataFrame(rows).to_csv(DASH / "pos_proj.csv", index=False)

    grp = {"RB": "rb", "WR": "wr", "DEF": "def"}
    pd.DataFrame([{"feature": f, "group": g, "stat": a, "meaning": b,
                   "weight": round(pos_meta[grp[g]]["weights"][f] * 100, 1),
                   "consistency": round(pos_meta[grp[g]]["reliability"][f], 2)} for f, (g, a, b) in POS_WEIGHT_LABELS.items()]
                 ).sort_values(["group", "weight"], ascending=[True, False]).to_csv(DASH / "pos_weights.csv", index=False)
    pd.DataFrame([{"min_carries": pos_meta["rb"]["min"], "min_targets": pos_meta["wr"]["min"]}]).to_csv(DASH / "pos_meta.csv", index=False)

    mvp.to_csv(DASH / "mvp.csv", index=False)
    awards.to_csv(DASH / "awards.csv", index=False)
