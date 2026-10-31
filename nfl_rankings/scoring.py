"""Shared scoring: reliability weights, z-score composites, projections."""
import numpy as np
import pandas as pd

from .config import PRIOR_GAMES, SEASON_GAMES, USAGE_CAP


def split_reliability(build, feats, halves, key, qualifies):
    """Correlation of each stat between odd-week and even-week samples of the same players/teams."""
    a, b = (build(h) for h in halves)
    a, b = a[qualifies(a)], b[qualifies(b)]
    m = a.merge(b, on=key, suffixes=("_a", "_b"))
    rel = {}
    for f, _, _ in feats:
        r = m[[f + "_a", f + "_b"]].dropna().corr().iloc[0, 1]
        rel[f] = float(max(r, 0.0)) if pd.notna(r) else 0.0
    return rel, len(m)


def weights_from(rel, feats, usage_cap=USAGE_CAP):
    """Weight = reliability (floor 0.05); the anchor stat gets a floor of 0.5; usage stats capped together."""
    raw = {}
    for f, _, kind in feats:
        w = max(rel[f], 0.05)
        if kind == "anchor":
            w = max(w, 0.5)
        raw[f] = w
    tot = sum(raw.values())
    w = {f: v / tot for f, v in raw.items()}
    usage = [f for f, _, k in feats if k == "usage"]
    u = sum(w[f] for f in usage)
    if usage and u > usage_cap:
        su, so = usage_cap / u, (1 - usage_cap) / (1 - u)
        w = {f: v * (su if f in usage else so) for f, v in w.items()}
    return {f: round(v, 4) for f, v in w.items()}


def composite(df, feats, weights):
    """50 = group average, 10 = one standard deviation of the weighted z-score sum."""
    z = pd.DataFrame({f: (df[f] - df[f].mean()) / df[f].std() * (1 if hi else -1) for f, hi, _ in feats}).fillna(0)
    s = sum(z[f] * weights[f] for f, _, _ in feats)
    df = df.copy()
    df["score"] = (50 + 10 * s / s.std()).round(1)
    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    return df


def project(df, team_games, stats, id_col, active_ids, baseline=None):
    """Per-game rates blended with PRIOR_GAMES of the group average, times the team's remaining games."""
    base = df if baseline is None else baseline
    lg = {s: (base[s] / base.games).mean() for s in stats}
    df = df.copy()
    df["active"] = df[id_col].isin(active_ids)
    df["games_left"] = np.where(df.active, (SEASON_GAMES - df.team.map(team_games)).clip(lower=0), 0)
    for s in stats:
        pg = (df[s] + PRIOR_GAMES * lg[s]) / (df.games + PRIOR_GAMES)
        df[f"{s}_ros"] = pg * df.games_left
        df[f"{s}_final"] = df[s] + df[f"{s}_ros"]
    return df
