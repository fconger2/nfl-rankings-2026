"""Award ladders: sportsbook odds -> no-vig chances, plus Kalshi prices and the QB model join."""
import json
import shutil

import pandas as pd

from .config import ODDS


def american(o):
    o = int(str(o).replace("+", ""))
    return o


def implied(o):
    return 100 / (o + 100) if o > 0 else -o / (-o + 100)


def fmt(o):
    return f"+{o}" if o > 0 else str(o)


def board(rows):
    """rows: list of (player, team, ..., odds). Returns df with implied and no-vig chance in percent."""
    df = pd.DataFrame([dict(player=r[0], team=r[1], am=american(r[-1]), pos=(r[2] if len(r) == 4 else "")) for r in rows])
    df["implied_p"] = df.am.map(implied)
    df["novig_p"] = df.implied_p / df.implied_p.sum()
    df = df.sort_values("novig_p", ascending=False).reset_index(drop=True)
    df["ladder"] = df.index + 1
    df["odds"] = df.am.map(fmt)
    df["implied"] = (df.implied_p * 100).round(1)
    df["novig"] = (df.novig_p * 100).round(1)
    return df


def previous_board(as_of):
    """Most recent saved MVP board dated before as_of."""
    hist = sorted(p for p in (ODDS / "history").glob("*.json") if p.stem < as_of)
    return json.loads(hist[-1].read_text()) if hist else None


def model_lookup(qbs, roster):
    by_name = roster.dropna(subset=["gsis_id"]).drop_duplicates("full_name").set_index("full_name").gsis_id
    q = qbs.set_index("qb_id")

    def find(player, team):
        gid = by_name.get(player)
        if gid in q.index:
            return q.loc[gid]
        last = player.split()[-1]
        hit = qbs[(qbs.team == team) & qbs.name.str.endswith(last)]
        return hit.iloc[0] if len(hit) == 1 else None
    return find


def build(qbs, roster):
    inp = json.loads((ODDS / "input.json").read_text())
    as_of = inp["as_of"]
    shutil.copy(ODDS / "input.json", ODDS / "history" / f"{as_of}.json")

    # ---- MVP
    m = board(inp["mvp"]["odds"])
    prev = previous_board(as_of)
    if prev:
        pb = board(prev["mvp"]["odds"]).set_index("player")
        m["odds_prev"] = m.player.map(pb.odds)
        m["novig_prev"] = m.player.map(pb.novig)
        m["change"] = (m.novig - m.novig_prev).round(1)
        m["prev_as_of"] = prev["as_of"]
    else:
        m["odds_prev"] = m["novig_prev"] = m["change"] = m["prev_as_of"] = None
    find = model_lookup(qbs, roster)
    hits = [find(r.player, r.team) if r.pos == "QB" else None for r in m.itertuples()]
    m["model_rank"] = [int(h["rank"]) if h is not None else None for h in hits]
    m["model_score"] = [float(h["score"]) if h is not None else None for h in hits]
    km = inp["kalshi"].get("mvp", {})
    m["kalshi"] = m.player.map(km.get("chance", {}))
    m["gap"] = (m.novig - m.kalshi).round(1)
    m["as_of"] = as_of
    m["source"] = inp["mvp"]["source"]
    m["kalshi_source"] = km.get("source", "")
    mvp = m[["ladder", "player", "team", "pos", "odds", "implied", "novig", "odds_prev", "novig_prev", "change",
             "model_rank", "model_score", "kalshi", "gap", "as_of", "prev_as_of", "source", "kalshi_source"]]
    mvp = mvp.astype({"model_rank": "Int64"})

    # ---- other awards
    rows = []
    for slug, a in inp["awards"].items():
        b = board(a["odds"])
        k = inp["kalshi"].get(slug, {})
        chance = k.get("chance", {})
        for r in b.itertuples():
            rows.append(dict(key=f"{slug}:{r.player}", award=slug, award_name=a["name"], source=a["source"], ladder=r.ladder,
                             player=r.player, team=r.team, odds=r.odds, implied=r.implied, novig=r.novig,
                             kalshi=chance.get(r.player), kalshi_source=k.get("source", "")))
        for player, v in chance.items():  # names Kalshi lists that the book board doesn't
            if player not in set(b.player):
                rows.append(dict(key=f"{slug}:{player}", award=slug, award_name=a["name"], source=a["source"], ladder=None,
                                 player=player, team=k.get("teams", {}).get(player, ""), odds="", implied=None, novig=None,
                                 kalshi=v, kalshi_source=k.get("source", "")))
    aw = pd.DataFrame(rows)
    aw["gap"] = (aw.novig - aw.kalshi).round(1)
    aw["ladder"] = aw.ladder.astype("Int64")
    return mvp, aw, inp
