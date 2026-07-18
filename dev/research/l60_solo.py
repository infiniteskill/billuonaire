"""STEP 2 (long60) -- PER-TOOL SOLO battery over signals60.parquet.

Realistic-fill grid (task spec): SL k in {0.5, 0.75, 1.0, 1.5} x ATR, target in
{1, 1.5, 2, 3} R, fixed + breakeven-at-1R management (be1r only for tgt>1).
Fills replicate app/trader/execution/paper.py economics via step2_engine.simulate
(UNMODIFIED reuse): entry = next-bar OPEN + half-spread; stop = level-or-gap-open
+ half-spread+slippage; target = limit + half-spread; EOD = last close +
half+slippage; intrabar stop-before-target. NOTE: bars are NATIVE 5m -- "next
bar" granularity is 5 minutes (coarser than the old M1 runs; gap-through-stop
fills are correspondingly more pessimistic, target fills more conservative).

Outputs (scratchpad): res60.parquet (sig_id x cfg -> net_R), cfgmeta60.parquet,
sigmeta60.parquet (augmented signal metadata incl. EOD-path MFE/MAE),
solo_grid_hold.parquet (per det x cfg with holdout cells), solo_table.csv
(Table 1 rows). Prints the solo sniper table.
"""
from __future__ import annotations

import os
import sys
import time
import zlib
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

SP = Path("/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/"
          "a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad")
sys.path.insert(0, str(SP))
from step2_engine import simulate, path_excursions      # noqa: E402  (unmodified reuse)

KS = (0.5, 0.75, 1.0, 1.5)
SCHEMES = ([(f"fixed_t{m:g}", "fixed", m) for m in (1, 1.5, 2, 3)]
           + [(f"be1r_t{m:g}", "be1r", m) for m in (1.5, 2, 3)])
DETS = ["ob_lux", "fvg_cb", "compression_fade", "inducement", "bpr",
        "mitigation", "turtle_soup"]
MIN_FULL, MIN_CELL = 300, 75


def load() -> pd.DataFrame:
    df = pd.read_parquet(SP / "signals60.parquet").reset_index(drop=True)
    df["sig_id"] = np.arange(len(df))
    df["minute"] = df["ts"].map(
        lambda s: (lambda t: t.hour * 60 + t.minute)(datetime.fromisoformat(s)))
    df["crc"] = df["symbol"].map(lambda s: zlib.crc32(s.encode()) % 2)
    sess = np.sort(df["session"].unique())
    cut = sess[len(sess) // 2]
    df["half"] = np.where(df["session"].values < cut, "T1", "T2")
    df.attrs["cut"] = cut
    print(f"signals={len(df)}  sessions={len(sess)} ({sess[0]}..{sess[-1]})  "
          f"temporal cut={cut}", flush=True)
    return df


def run_grid(df: pd.DataFrame):
    cfg_list = [(k, name, mgmt, tgt) for k in KS for name, mgmt, tgt in SCHEMES]
    cfgmeta = pd.DataFrame(cfg_list, columns=["k", "scheme", "mgmt", "tgt"])
    cfgmeta["cfg"] = np.arange(len(cfgmeta))
    sig_id = []; cfg = []; netR = []; kind_a = []
    mfe = np.full(len(df), np.nan); mae = np.full(len(df), np.nan)
    kmap = {"stop": 0, "tgt": 1, "eod": 2}
    t0 = time.time()
    for r in df.itertuples(index=False):
        if r.sig_id % 20000 == 0:
            print(f"  grid {r.sig_id}/{len(df)}  t={time.time()-t0:.0f}s",
                  flush=True)
        o = np.asarray(r.po, float); h = np.asarray(r.ph, float)
        l = np.asarray(r.pl, float); c = np.asarray(r.pc, float)
        d = int(r.direction); atr = float(r.atr)
        mfe[r.sig_id], mae[r.sig_id] = path_excursions(o, h, l, c, d, atr)
        for ci, (k, _name, mgmt, tgt) in enumerate(cfg_list):
            res = simulate(o, h, l, c, d, atr, k, mgmt, tgt)
            if res is None:
                continue
            nr, kd = res
            sig_id.append(r.sig_id); cfg.append(ci)
            netR.append(nr); kind_a.append(kmap[kd])
    res = pd.DataFrame(dict(sig_id=np.asarray(sig_id, np.int32),
                            cfg=np.asarray(cfg, np.int16),
                            net_R=np.asarray(netR, np.float32),
                            kind=np.asarray(kind_a, np.uint8)))
    df["mfe_atr"] = mfe; df["mae_atr"] = mae
    print(f"grid rows={len(res)}  t={time.time()-t0:.0f}s", flush=True)
    return res, cfgmeta


def cell_stats(x: pd.Series):
    return len(x), (float(x.mean()) if len(x) else float("nan")), \
        (float((x > 0).mean()) if len(x) else float("nan"))


def grid_holdout(res, sigmeta, cfgmeta, group_cols=("detector",)) -> pd.DataFrame:
    m = res.merge(sigmeta[["sig_id", "detector", "event", "session", "crc",
                           "half"]], on="sig_id").merge(cfgmeta, on="cfg")
    rows = []
    for key, g in m.groupby([*group_cols, "k", "scheme"], observed=True):
        n, exp, win = cell_stats(g["net_R"])
        t1 = g[g.half == "T1"]["net_R"]; t2 = g[g.half == "T2"]["net_R"]
        c0 = g[g.crc == 0]["net_R"]; c1 = g[g.crc == 1]["net_R"]
        cells = [cell_stats(x) for x in (t1, t2, c0, c1)]
        all_pos = (n >= MIN_FULL and exp > 0
                   and all(cn >= MIN_CELL and ce == ce and ce > 0
                           for cn, ce, _ in cells))
        robust = min(ce for _, ce, _ in cells) if all(
            ce == ce for _, ce, _ in cells) else float("nan")
        rows.append(dict(zip([*group_cols, "k", "scheme"], key)) | dict(
            n=n, exp=exp, win=win,
            t1=cells[0][1], t2=cells[1][1], c0=cells[2][1], c1=cells[3][1],
            n_t1=cells[0][0], n_t2=cells[1][0], n_c0=cells[2][0], n_c1=cells[3][0],
            robust=robust, all_pos=all_pos))
    return pd.DataFrame(rows)


def hit_stats(g: pd.DataFrame) -> tuple[float, float, float, int]:
    d = g[g["hit"] != "na"]
    d = d[d["b_hit"].notna()]
    if not len(d):
        return (float("nan"),) * 3 + (0,)
    hit = float((d["hit"] == "hit").mean())
    base = float(d["b_hit"].mean())
    return hit, base, hit - base, len(d)


def main():
    df = load()
    res, cfgmeta = run_grid(df)
    res.to_parquet(SP / "res60.parquet", index=False)
    cfgmeta.to_parquet(SP / "cfgmeta60.parquet", index=False)
    sigmeta = df.drop(columns=["po", "ph", "pl", "pc"])
    sigmeta.to_parquet(SP / "sigmeta60.parquet", index=False)

    gh = grid_holdout(res, sigmeta, cfgmeta)
    gh.to_parquet(SP / "solo_grid_hold.parquet", index=False)
    ghe = grid_holdout(res, sigmeta, cfgmeta, group_cols=("detector", "event"))
    ghe.to_parquet(SP / "solo_grid_hold_ev.parquet", index=False)

    # -------- Table 1: per (detector, event) + per-detector pooled --------
    rows = []
    for det in DETS:
        sub_all = sigmeta[sigmeta.detector == det]
        gdet = gh[gh.detector == det]
        for ev, sub in [("(all)", sub_all),
                        *sorted(sub_all.groupby("event"), key=lambda x: -len(x[1]))]:
            hit, base, edge, nd = hit_stats(sub)
            mfe_m = float(sub["mfe_atr"].mean()); mae_m = float(sub["mae_atr"].mean())
            row = dict(detector=det, event=ev, n=len(sub), n_hit=nd,
                       hit=hit, base=base, edge=edge,
                       mfe=mfe_m, mae=mae_m,
                       ratio=mfe_m / mae_m if mae_m else float("nan"))
            if ev == "(all)":
                g = gdet[gdet.n >= MIN_FULL].sort_values("exp", ascending=False)
                if len(g):
                    b = g.iloc[0]
                    row |= dict(best_k=b.k, best_scheme=b.scheme, best_n=int(b.n),
                                best_exp=b.exp, best_win=b.win, best_t1=b.t1,
                                best_t2=b.t2, best_c0=b.c0, best_c1=b.c1,
                                best_robust=b.robust, best_all_pos=bool(b.all_pos))
            rows.append(row)
    tbl = pd.DataFrame(rows)
    tbl.to_csv(SP / "solo_table.csv", index=False)

    pd.set_option("display.width", 250)
    print("\n===== TABLE 1 (per-detector pooled) =====")
    print(tbl[tbl.event == "(all)"].to_string(index=False))
    print("\n===== best 3 configs / detector =====")
    for det in DETS:
        g = gh[(gh.detector == det) & (gh.n >= MIN_FULL)] \
            .sort_values("exp", ascending=False).head(3)
        print(g.to_string(index=False))
    w = gh[gh.all_pos]
    print(f"\nconfigs positive on full + all 4 holdout cells: {len(w)}")
    if len(w):
        print(w.sort_values("exp", ascending=False).to_string(index=False))
    # old-window overlap split (old 30d data = sessions >= 2026-06-19)
    print("\n===== old-window overlap check (>= 2026-06-19 vs before) =====")
    old = sigmeta[sigmeta.session >= "2026-06-19"]
    new = sigmeta[sigmeta.session < "2026-06-19"]
    for name, s in (("overlap(old-window)", old), ("new-OOS(earlier)", new)):
        for det in DETS:
            sub = s[s.detector == det]
            hit, base, edge, nd = hit_stats(sub)
            print(f"  {name:20} {det:17} n={len(sub):6} hit={hit:.3f} "
                  f"base={base:.3f} edge={edge:+.3f}")


if __name__ == "__main__":
    main()
