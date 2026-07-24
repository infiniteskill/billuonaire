"""ab_tradebook.py — offline A/B of a candidate FILTER vs the frozen +8R baseline, on the
persisted tradebook (Z1). Seconds, no re-derive. The GATE from the edge-preserve rethink:
a pure filter SHIPS only if, per stop-mode, the surviving hi-tier (grade>=5) NET-R >= baseline
AND all 4 holdout quadrants NET-R >= baseline AND the g1->g7 ladder stays monotone — NET-R,
never win%. Else REJECT. This is the mechanical guard on every future config change.

Usage: python3 tools/ab_tradebook.py <tradebook.csv> <filter> [arg]
  filter: none | no_blind | bhit_gt0 | bhit_ge <x> | dir <LONG|SHORT> | regime <RANGE|UPTREND|DOWNTREND>
          | drop_am | nest_ge <n> | strength_ge <x>
b_hit / regime are JOINED on demand (b_hit via merge_asof to the study parquet by sym,ts;
regime via dev/plan/47-40STOCK/_REGIME.md).
"""
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path("/home/doom/Public/PROJECT/2026/trader")
PARQUET = ROOT / "runs/validate/study40_2026/evidence.parquet"
REGIME_MD = ROOT / "dev/plan/47-40STOCK/_REGIME.md"


def load_regime():
    reg = {}
    for line in REGIME_MD.read_text().splitlines():
        m = re.match(r"\|\s*([A-Z][A-Z0-9&-]+)\s*\|.*\*\*(RANGE|UPTREND|DOWNTREND)\*\*", line)
        if m:
            reg[m.group(1)] = m.group(2)
    return reg


def join_bhit(tb):
    """b_hit from the study firing parquet, matched on sym+detector+event nearest-ts
    (the trade's zone member IS a firing -> ~100% match); falls back to sym-only for the rest."""
    ev = pd.read_parquet(PARQUET)[["symbol", "ts", "detector", "event", "b_hit"]] \
        .rename(columns={"symbol": "sym", "detector": "member_det", "event": "member_event"})
    ev["ts"] = pd.to_datetime(ev["ts"], utc=True)
    tb = tb.copy(); tb["_ts"] = pd.to_datetime(tb["ts"], utc=True)
    tb["member_event"] = tb["member_event"].fillna("")
    ev = ev.sort_values("ts"); tb = tb.sort_values("_ts")
    out = pd.merge_asof(tb, ev, left_on="_ts", right_on="ts",
                        by=["sym", "member_det", "member_event"], direction="nearest",
                        tolerance=pd.Timedelta("90min"), suffixes=("", "_ev")).drop(columns=["ts_ev"], errors="ignore")
    miss = out["b_hit"].isna()
    if miss.any():   # fallback: sym-only nearest for unmatched
        ev2 = ev[["sym", "ts", "b_hit"]].sort_values("ts")
        fb = pd.merge_asof(out[miss].sort_values("_ts"), ev2, left_on="_ts", right_on="ts",
                           by="sym", direction="nearest", tolerance=pd.Timedelta("120min"), suffixes=("", "_fb"))
        out.loc[miss, "b_hit"] = fb["b_hit_fb"].values if "b_hit_fb" in fb else fb["b_hit"].values
    return out.drop(columns=["_ts"], errors="ignore")


def apply_filter(tb, name, arg):
    if name in ("none", "no_blind"):        # no_blind = no-op (grade already excludes strength/width)
        return tb
    if name == "bhit_gt0":
        return tb[tb["b_hit"] > 0]
    if name == "bhit_ge":
        return tb[tb["b_hit"] >= float(arg)]
    if name == "dir":
        return tb[tb["dir"] == arg]
    if name == "regime":
        return tb[tb["regime"] == arg]
    if name == "drop_am":                   # drop 09:15-11:00 entries
        h = pd.to_datetime(tb["ts"]).dt.hour * 60 + pd.to_datetime(tb["ts"]).dt.minute
        return tb[h >= 11 * 60]
    if name == "nest_ge":
        return tb[tb["nest_depth"] >= int(arg)]
    if name == "strength_ge":
        return tb[tb["strength"] >= float(arg)]
    raise SystemExit(f"unknown filter {name}")


def tier_stats(df):
    """net-R per trade for the key cells."""
    def m(sub):
        return (len(sub), round(sub["net"].mean(), 3) if len(sub) else None,
                100 * (sub["R"] > 0).mean() if len(sub) else None)
    out = {"ALL": m(df), "hi>=4": m(df[df.grade >= 4]), "hi>=5": m(df[df.grade >= 5])}
    for g in range(1, 8):
        out[f"g{g}"] = m(df[df.grade == g])
    for q in sorted(df["quad"].dropna().unique()):
        out[f"quad:{q}"] = m(df[df["quad"] == q])
    return out


def show(mode, base, filt):
    print(f"\n=== STOP_MODE={mode} ===")
    print(f"{'cell':12} {'BASE n/netR/win':>26}   {'FILT n/netR/win':>26}   verdict")
    ladder_ok = True; quad_ok = True; hi_ok = True
    prev = None
    for k in list(base):
        bn, bnet, bw = base[k]; fn, fnet, fw = filt.get(k, (0, None, None))
        v = ""
        if k == "hi>=5" and bnet is not None and fnet is not None:
            hi_ok = fnet >= bnet; v = "HI-TIER " + ("HOLD/UP ✅" if hi_ok else "DROP ❌")
        if k.startswith("quad:") and bnet is not None:
            ok = (fnet is not None) and (fnet >= bnet); quad_ok &= ok; v = "✅" if ok else "❌"
        if re.match(r"g[1-7]$", k) and fnet is not None:
            if prev is not None and fnet < prev - 0.01:
                ladder_ok = False
            prev = fnet
        bs = f"{bn:5}/{'' if bnet is None else format(bnet,'+.2f')}/{'' if bw is None else format(bw,'.0f')}"
        fs = f"{fn:5}/{'' if fnet is None else format(fnet,'+.2f')}/{'' if fw is None else format(fw,'.0f')}"
        print(f"{k:12} {bs:>26}   {fs:>26}   {v}")
    ship = hi_ok and quad_ok and ladder_ok
    print(f"  GATE[{mode}]: hi-tier {'✅' if hi_ok else '❌'} | all-quads {'✅' if quad_ok else '❌'} | "
          f"ladder-monotone {'✅' if ladder_ok else '❌'}  ->  {'SHIP-CANDIDATE' if ship else 'REJECT'}")
    return ship


def main():
    tbfile = Path(sys.argv[1])
    name = sys.argv[2] if len(sys.argv) > 2 else "none"
    arg = sys.argv[3] if len(sys.argv) > 3 else None
    tb = pd.read_csv(tbfile)
    if "b_hit" in name or name == "bhit_gt0":
        tb = join_bhit(tb)
        print(f"joined b_hit: {tb['b_hit'].notna().sum()}/{len(tb)} matched")
    if name == "regime":
        tb["regime"] = tb["sym"].map(load_regime())
    print(f"tradebook={tbfile.name}  filter={name} {arg or ''}  total-records={len(tb)}")
    allship = True
    for mode in ["intrabar", "m5_close", "eod"]:
        b = tb[tb["mode"] == mode]; f = apply_filter(b, name, arg)
        allship &= show(mode, tier_stats(b), tier_stats(f))
    print(f"\n>>> OVERALL: {'SHIP-CANDIDATE (all modes pass gate)' if allship else 'REJECT (a mode fails the gate)'} <<<")


if __name__ == "__main__":
    main()
