"""STEP 3 (long60) -- COMBINATION grid. All CAUSAL (backward-looking only):

a. tool x tool CO-FIRE pairs: A-signal with a same-direction B-signal at or
   BEFORE A (0..3 bars back, zone-mid distance <= 0.5 x A.atr). Entry stays on
   A (next bar) -- B is already known at entry time => causal.
b. tool x filter matrix at each tool's best base config (regime/release/
   wyckoff-align/M15-align/premium-discount/vol-regime).
c. stacked configs: tool + per-family better-side filter subsets (<=3) x full
   exit grid -> holdout-stable top list (ranked by robust = worst holdout cell).
d. SEQUENCE chains: A fires 1..6 bars BEFORE B (same symbol+direction, no zone
   constraint); entry on B at B's best config => causal chain.

Consumes sigmeta60/res60/cfgmeta60/solo_grid_hold parquets (l60_solo.py).
Writes pair_table.csv, pair_matrix.csv, filter_table.csv, stack_table.csv,
seq_table.csv to the scratchpad.
"""
from __future__ import annotations

import itertools
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

SP = Path("/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/"
          "a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad")

DETS = ["ob_lux", "fvg_cb", "compression_fade", "inducement", "bpr",
        "mitigation", "turtle_soup"]
TRAP = {"TREND", "DOUBLE_TRAP", "TRAP_REVERSAL"}
MIN_FULL, MIN_CELL = 300, 75
MIN_COMBO, MIN_COMBO_CELL = 60, 15      # pairs/chains are rarer events
BAR = 300                                # native 5m bars

df = pd.read_parquet(SP / "sigmeta60.parquet")
res = pd.read_parquet(SP / "res60.parquet")
cfgmeta = pd.read_parquet(SP / "cfgmeta60.parquet")
gh = pd.read_parquet(SP / "solo_grid_hold.parquet")

N = len(df)
df["mid"] = (df["zone_lo"] + df["zone_hi"]) / 2
df["epoch"] = pd.DatetimeIndex(pd.to_datetime(df["ts"])).as_unit("s").asi8
half = df["half"].values
crc = df["crc"].values

# net_R lookup: cfg -> float array indexed by sig_id (NaN = unsizable)
NCFG = len(cfgmeta)
netR = np.full((NCFG, N), np.nan, dtype=np.float64)
netR[res["cfg"].values, res["sig_id"].values] = res["net_R"].values

BEST = {}                                # det -> (cfg_id, full exp)
for det in DETS:
    g = gh[(gh.detector == det) & (gh.n >= MIN_FULL)].sort_values(
        "exp", ascending=False)
    if g.empty:                              # tiny dev subsets only
        g = gh[gh.detector == det].sort_values("exp", ascending=False)
    b = g.iloc[0]
    cid = int(cfgmeta[(cfgmeta.k == b.k) & (cfgmeta.scheme == b.scheme)]
              .cfg.iloc[0])
    BEST[det] = (cid, float(b.exp))
    print(f"best cfg {det:17} k={b.k} {b.scheme:10} exp={b.exp:+.3f} n={int(b.n)}")


def cells(mask: np.ndarray, cfg: int, min_full=MIN_FULL, min_cell=MIN_CELL):
    """(n, exp, win, t1, t2, c0, c1, robust, all_pos) of net_R[cfg] over mask."""
    v = netR[cfg]
    ok = mask & ~np.isnan(v)
    out = []
    for m in (ok, ok & (half == "T1"), ok & (half == "T2"),
              ok & (crc == 0), ok & (crc == 1)):
        x = v[m]
        out.append((len(x), float(x.mean()) if len(x) else float("nan"),
                    float((x > 0).mean()) if len(x) else float("nan")))
    (n, e, w), cs = out[0], out[1:]
    all_pos = (n >= min_full and e == e and e > 0
               and all(cn >= min_cell and ce == ce and ce > 0 for cn, ce, _ in cs))
    rb = min(ce for cn, ce, _ in cs) if all(ce == ce for _, ce, _ in cs) \
        else float("nan")
    return dict(n=n, exp=e, win=w, t1=cs[0][1], t2=cs[1][1], c0=cs[2][1],
                c1=cs[3][1], robust=rb, all_pos=all_pos)


def hit_stats(mask: np.ndarray):
    d = df[mask]
    d = d[(d["hit"] != "na") & d["b_hit"].notna()]
    if not len(d):
        return float("nan"), float("nan"), float("nan"), 0
    hit = float((d["hit"] == "hit").mean())
    base = float(d["b_hit"].mean())
    return hit, base, hit - base, len(d)


DMASK = {det: (df["detector"] == det).values for det in DETS}

# ---------------- causal filters ----------------
COND = {
    "regime_trap": df["template"].isin(TRAP).values,
    "regime_range": ~df["template"].isin(TRAP).values,
    "release": ((df["minute"] >= 660) & (df["minute"] <= 885)).values,
    "outside": ~((df["minute"] >= 660) & (df["minute"] <= 885)).values,
    "wyck_aligned": (df["wyck"] == "aligned").values,
    "wyck_counter": (df["wyck"] == "counter").values,
    "htf_align": (df["htf"] == "align").values,
    "htf_counter": (df["htf"] == "counter").values,
    "pd_fav": (df["pd_cls"] == "favorable").values,
    "pd_unf": (df["pd_cls"] == "unfavorable").values,
    "vol_exp": (df["vol"] == "expansion").values,
    "vol_con": (df["vol"] == "contraction").values,
}
FAM_VALUES = {"regime": ["regime_trap", "regime_range"],
              "time": ["release", "outside"],
              "wyck": ["wyck_aligned", "wyck_counter"],
              "htf": ["htf_align", "htf_counter"],
              "pd": ["pd_fav", "pd_unf"],
              "vol": ["vol_exp", "vol_con"]}


# ---------------- (a) causal co-fire pairs ----------------
def prior_fire_mask(det_a: str, det_b: str, lo_bars: int, hi_bars: int,
                    zone_atr: float | None) -> np.ndarray:
    """Mask over ALL signals: A-signals with a same-symbol same-direction B
    signal ts in [tsA - hi_bars*BAR, tsA - lo_bars*BAR] (and zone-mid within
    zone_atr * A.atr if given)."""
    out = np.zeros(N, dtype=bool)
    A = df[DMASK[det_a]]
    B = df[DMASK[det_b]]
    for (sym, d), ga in A.groupby(["symbol", "direction"]):
        gb = B[(B["symbol"] == sym) & (B["direction"] == d)]
        if gb.empty:
            continue
        bt = np.sort(gb["epoch"].values)
        order = np.argsort(gb["epoch"].values)
        bmid = gb["mid"].values[order]
        at = ga["epoch"].values
        j0 = np.searchsorted(bt, at - hi_bars * BAR, side="left")
        j1 = np.searchsorted(bt, at - lo_bars * BAR, side="right")
        if zone_atr is None:
            hitv = j1 > j0
        else:
            amid = ga["mid"].values; aatr = ga["atr"].values
            hitv = np.array([np.any(np.abs(bmid[a:b] - m) <= zone_atr * v)
                             if b > a else False
                             for a, b, m, v in zip(j0, j1, amid, aatr)])
        out[ga.index.values[hitv]] = True
    return out


def section_pairs():
    rows = []
    t0 = time.time()
    for det_a in DETS:
        cfg_a, solo_a = BEST[det_a]
        h_a = hit_stats(DMASK[det_a])
        for det_b in DETS:
            if det_b == det_a:
                continue
            m = prior_fire_mask(det_a, det_b, 0, 3, 0.5) & DMASK[det_a]
            hit, base, edge, nd = hit_stats(m)
            c = cells(m, cfg_a, MIN_COMBO, MIN_COMBO_CELL)
            solo_b = BEST[det_b][1]
            rows.append(dict(
                A=det_a, B=det_b, n_cofire=int(m.sum()), n_hit=nd,
                hit=hit, base=base, edge=edge, solo_edge_A=h_a[2],
                edge_lift=edge - h_a[2],
                exp_cofire=c["exp"], solo_exp_A=solo_a, solo_exp_B=solo_b,
                exp_lift=c["exp"] - solo_a, robust=c["robust"],
                all_pos=c["all_pos"],
                beats_both=bool(c["all_pos"] and c["robust"] == c["robust"]
                                and c["robust"] > max(solo_a, solo_b))))
        print(f"  pairs {det_a} done t={time.time()-t0:.0f}s", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(SP / "pair_table.csv", index=False)
    mat = out.pivot(index="A", columns="B", values="edge_lift")
    mat.to_csv(SP / "pair_matrix.csv")
    print(out.sort_values("exp_lift", ascending=False).head(15).to_string(index=False))
    return out


# ---------------- (b) tool x filter matrix ----------------
FILTERS_B = [("regime(TRAP)", "regime_trap"), ("release(11-14:45)", "release"),
             ("wyck_align", "wyck_aligned"), ("htf_align", "htf_align"),
             ("pd_favorable", "pd_fav"), ("vol_expansion", "vol_exp"),
             ("vol_contraction", "vol_con")]


def section_filters():
    rows = []
    for det in DETS:
        cfg, solo = BEST[det]
        dm = DMASK[det]
        base_edge = hit_stats(dm)[2]
        for label, cond in FILTERS_B:
            m = dm & COND[cond]
            c = cells(m, cfg)
            edge = hit_stats(m)[2]
            rows.append(dict(det=det, filter=label, n=c["n"], exp=c["exp"],
                             d_exp=c["exp"] - solo, d_edge=edge - base_edge,
                             robust=c["robust"], all_pos=c["all_pos"]))
    out = pd.DataFrame(rows)
    out.to_csv(SP / "filter_table.csv", index=False)
    print(out.to_string(index=False))
    return out


# ---------------- (c) stacked configs ----------------
def section_stack():
    t0 = time.time()
    cands = []
    best_any = {}                       # det -> best full-sample cand, any sign
    for det in DETS:
        dm = DMASK[det]
        cfg_best, _ = BEST[det]
        sides = []
        for fam, vals in FAM_VALUES.items():
            def side_exp(v):
                e = cells(dm & COND[v], cfg_best)["exp"]
                return e if e == e else -np.inf
            sides.append(max(vals, key=side_exp))
        for cfg in range(NCFG):
            for r in range(0, 4):
                for combo in itertools.combinations(sides, r):
                    m = dm.copy()
                    for cond in combo:
                        m &= COND[cond]
                    c = cells(m, cfg)
                    if c["all_pos"]:
                        cands.append(dict(det=det, cfg=cfg, combo=combo, **c))
                    if (c["n"] >= MIN_FULL and c["exp"] == c["exp"]
                            and (det not in best_any
                                 or c["exp"] > best_any[det]["exp"])):
                        best_any[det] = dict(det=det, cfg=cfg, combo=combo, **c)
        print(f"  stack {det} done t={time.time()-t0:.0f}s "
              f"(cands so far {len(cands)})", flush=True)
    rows_any = []
    for det, cnd in best_any.items():
        cm = cfgmeta.iloc[cnd["cfg"]]
        rows_any.append(dict(det=det, k=cm.k, scheme=cm.scheme,
                             filters="+".join(cnd["combo"]) or "(none)",
                             n=cnd["n"], win=cnd["win"], exp=cnd["exp"],
                             robust=cnd["robust"], t1=cnd["t1"], t2=cnd["t2"],
                             c0=cnd["c0"], c1=cnd["c1"]))
    pd.DataFrame(rows_any).to_csv(SP / "stack_any.csv", index=False)
    cands.sort(key=lambda x: (-round(x["robust"], 3), len(x["combo"]), -x["n"]))
    seen, top, per_det = set(), [], {}
    for cnd in cands:
        key = (cnd["det"], tuple(sorted(cnd["combo"])))
        if key in seen or per_det.get(cnd["det"], 0) >= 3:
            continue
        # redundancy: skip if a kept superset-free config subsumes at same n
        if any(t["det"] == cnd["det"] and set(t["combo"]) < set(cnd["combo"])
               and abs(t["n"] - cnd["n"]) <= 2 for t in top):
            continue
        seen.add(key)
        top.append(cnd)
        per_det[cnd["det"]] = per_det.get(cnd["det"], 0) + 1
        if len(top) >= 15:
            break
    rows = []
    for cnd in top:
        cm = cfgmeta.iloc[cnd["cfg"]]
        rows.append(dict(det=cnd["det"], k=cm.k, scheme=cm.scheme,
                         filters="+".join(cnd["combo"]) or "(none)",
                         n=cnd["n"], win=cnd["win"], exp=cnd["exp"],
                         robust=cnd["robust"], t1=cnd["t1"], t2=cnd["t2"],
                         c0=cnd["c0"], c1=cnd["c1"]))
    out = pd.DataFrame(rows)
    out.to_csv(SP / "stack_table.csv", index=False)
    print(out.to_string(index=False) if len(out) else
          "NO holdout-stable positive stacked config")
    return out


# ---------------- (d) sequence chains ----------------
def section_seq():
    rows = []
    for det_b in DETS:                    # entry tool = B
        cfg_b, solo_b = BEST[det_b]
        for det_a in DETS:
            if det_a == det_b:
                continue
            m = prior_fire_mask(det_b, det_a, 1, 6, None) & DMASK[det_b]
            c = cells(m, cfg_b, MIN_COMBO, MIN_COMBO_CELL)
            solo_a = BEST[det_a][1]
            hit, base, edge, nd = hit_stats(m)
            rows.append(dict(
                A_first=det_a, B_entry=det_b, n_chain=int(m.sum()),
                edge=edge, exp_chain=c["exp"], solo_exp_B=solo_b,
                solo_exp_A=solo_a, lift_vs_B=c["exp"] - solo_b,
                robust=c["robust"], all_pos=c["all_pos"],
                beats_both=bool(c["all_pos"] and c["robust"] == c["robust"]
                                and c["robust"] > max(solo_a, solo_b))))
    out = pd.DataFrame(rows)
    out.to_csv(SP / "seq_table.csv", index=False)
    print(out.sort_values("lift_vs_B", ascending=False).head(15)
          .to_string(index=False))
    return out


def main():
    print("\n=== (a) co-fire pairs (causal: B at/before A, <=3 bars, "
          "zone <=0.5ATR) ===", flush=True)
    section_pairs()
    print("\n=== (b) tool x filter matrix ===", flush=True)
    section_filters()
    print("\n=== (c) stacked configs (holdout-stable top) ===", flush=True)
    section_stack()
    print("\n=== (d) sequence chains (A 1..6 bars before B, entry on B) ===",
          flush=True)
    section_seq()


if __name__ == "__main__":
    main()
