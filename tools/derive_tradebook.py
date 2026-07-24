"""derive_tradebook.py — DERIVE the tradebook (winners+losers) from the tools and
measure the HONEST edge verdict (iteration 5).

Runs the wired taught profile over 1m data; each decide()-take is a trade; simulates
forward on the finest (1m) candles gap-aware; applies HONEST per-trade rupee costs
(bps*price / tiny-risk = the dominant toll on a tight stop, RETHINK/doc-34); reports
net-R by GRADE, the high-grade tier, and a 4-way holdout (time-half x crc32(sym)%2).
The point: does the nest_depth-discriminated high-grade tier survive honest fill-through?

Usage: python3 tools/derive_tradebook.py <SYM,SYM,...> [min_grade]
"""
import json
import sys
import zlib
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, "/home/doom/Public/PROJECT/2026/trader/app")
from trader.config import check_detector_deps, load_settings
from trader.engine.decision import _ZONE_DETS, _ZONE_EVENTS, decide
from trader.engine.pipeline import Orchestrator
from trader.feed.file import FileFeed
from trader.models.candle import Timeframe

ROOT = Path("/home/doom/Public/PROJECT/2026/trader")
PROFILE = ROOT / "runs/validate/taught_profile/config.json"
CFG = json.loads(PROFILE.read_text())
import os
DATA = Path(os.environ.get("DERIVE_DATA", str(ROOT / "data/wide")))
TAUGHT = ["extremes", "swings", "liquidity", "sweep", "structure", "wyckoff",
          "orderblock", "fvg", "compression", "ob_taught", "fvg_n", "propulsion2",
          "premium_discount", "htf_nest"]


def cost_R(entry, risk):
    """Honest round-trip cost as a fraction of R. bps*price dominates when the
    stop is tiny; fixed brokerage amortised over the risk-budget qty."""
    f, c = CFG["fills"], CFG["fills"]["costs"]
    bps = (f["slippage_bps"] + f["half_spread_bps"]) / 1e4
    e, r = float(entry), float(risk)
    per_share = e * (2 * bps + c["stt_pct"] / 100 + 2 * c["exchange_pct"] / 100)
    risk_budget = CFG["capital"] * CFG["risk"]["per_trade_pct"] / 100
    return per_share / r + 2 * c["brokerage_flat"] / risk_budget


def _tap(pipe, trades, min_grade, gate_bars=20, min_rr=0.0):
    orig = pipe.registry.run_all

    def run_all(ctx):
        evs = orig(ctx)
        if any(e.detector in _ZONE_DETS and e.meta.get("event") in _ZONE_EVENTS for e in evs):
            w = ctx.candles.last(gate_bars, Timeframe("5m"))
            cutoff = w[0].ts if w else ctx.now
            window = list(evs) + [e for e in ctx.evidence_history if e.ts >= cutoff]
            d = decide(ctx, window, min_grade, min_rr)
            if d.take:
                rs = d.reasons
                nd = next((int(x.split(":")[1]) for x in rs if x.startswith("nest:")), 0)
                mat = next((float(x.split(":")[1]) for x in rs if x.startswith("maturity:")), 0.0)
                mem = d.members[0] if d.members else ("", "", 0.0)
                trades.append({"sym": pipe.symbol, "ts": ctx.now, "dir": d.direction.name,
                               "entry": d.entry, "sl": d.sl, "target": d.target, "grade": d.grade,
                               # ADDITIVE feature capture (Z1) — for offline A/B on the graded frame:
                               "bos": "bos" in rs, "sweep": "sweep" in rs, "ote": "ote" in rs,
                               "phase": "phase" in rs, "nest_depth": nd, "maturity": mat,
                               "zone_lo": d.zone[0] if d.zone else None,
                               "zone_hi": d.zone[1] if d.zone else None,
                               "member_det": mem[0], "member_event": mem[1], "strength": mem[2]})
        return evs
    pipe.registry.run_all = run_all


def _sim(t, m1, m5, stop_mode="intrabar", hold=3000):
    """Forward fill sim. stop_mode:
      'intrabar' (research/strict) = 1m path, stop on intrabar TOUCH of sl (-1R).
      'm5_close' (PRODUCTION, F9)   = 5m path, stop only when an M5 bar CLOSES beyond
        sl and fills at that close (loss CAN exceed 1R); target is a limit (touch).
    Both gap-aware (open beyond sl -> stop at open). Raw R; costs applied separately."""
    e, sl, tgt = t["entry"], t["sl"], t["target"]
    long = t["dir"] == "LONG"
    d = 1 if long else -1
    risk = abs(e - sl)
    if not risk:
        return None, None
    if stop_mode == "m5_close":
        for b in [c for c in m5 if c.ts >= t["ts"]][:hold]:
            if (long and b.open <= sl) or (not long and b.open >= sl):
                return "gap", float((b.open - e) / risk) * d
            if (b.high >= tgt) if long else (b.low <= tgt):      # limit target = touch
                return "target", round(float(abs(tgt - e) / risk), 2)
            if (b.close <= sl) if long else (b.close >= sl):     # M5-close stop -> fill at close
                return "stop", round(float((b.close - e) / risk) * d, 2)
        return "timeout", None
    eod = stop_mode == "eod"     # PRODUCTION intraday: force-close at 15:10 same session
    for b in [c for c in m1 if c.ts >= t["ts"]][:hold]:
        if eod and (b.ts.hour * 60 + b.ts.minute) >= 15 * 60 + 10:
            return "eod", round(float((b.close - e) / risk) * d, 2)  # squareoff at close
        if (long and b.open <= sl) or (not long and b.open >= sl):
            return "gap", float((b.open - e) / risk) * d
        if (b.low <= sl) if long else (b.high >= sl):
            return "stop", -1.0
        if (b.high >= tgt) if long else (b.low <= tgt):
            return "target", round(float(abs(tgt - e) / risk), 2)
    return "timeout", None


def _quad(t, split_ts):
    return ("late" if t["ts"] >= split_ts else "early") + "/" + \
           ("A" if zlib.crc32(t["sym"].encode()) % 2 == 0 else "B")


def main():
    syms = sys.argv[1].split(",")
    min_grade = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    s = load_settings(PROFILE)
    s.detectors.enabled = list(TAUGHT)
    check_detector_deps(s.detectors.enabled)
    jdir = Path(os.environ.get("DERIVE_JOURNAL", str(ROOT / "runs/validate/derive_work")))  # env override -> parallel shards
    orch = Orchestrator(s, FileFeed(DATA, s.market_spec()), syms, index_symbol=None,
                        max_qty=1, journal_dir=jdir)
    min_rr = float(os.environ.get("DERIVE_MIN_RR", 0))   # proven cross-regime gate; 0=off (frozen)
    trades = []
    for pipe in orch.pipelines.values():
        _tap(pipe, trades, min_grade, min_rr=min_rr)
    orch.run()
    m1s = {sym: orch.store._data.get(sym, {}).get(Timeframe.M1, []) for sym in syms}
    m5s = {sym: orch.store._data.get(sym, {}).get(Timeframe.M5, []) for sym in syms}
    from collections import Counter
    tb = []   # ADDITIVE (Z1): persist every closed trade-record for offline graded-frame A/B

    def stat(sub, label):
        if not sub:
            return
        net = [n for *_, n in sub]
        wins = sum(1 for _, o, r, n in sub if r > 0)
        print(f"  {label:14} n={len(sub):4} win%={100*wins//len(sub):3} "
              f"gross/t={sum(r for _,o,r,n in sub)/len(sub):+.2f}R "
              f"NET/t={sum(net)/len(net):+.3f}R")

    def report(mode):
        rows = []
        for t in trades:
            o, r = _sim(t, m1s[t["sym"]], m5s[t["sym"]], mode)
            if r is None:
                continue
            net = r - cost_R(t["entry"], abs(t["entry"] - t["sl"]))
            rows.append((t, o, r, net))
        if not rows:
            print("no closed trades"); return
        split = sorted(t["ts"] for t, *_ in rows)[len(rows) // 2]
        print(f"\n=== STOP_MODE={mode}  syms={len(syms)}  min_grade={min_grade} ===")
        print(f"closed={len(rows)}  outcomes: {dict(Counter(o for _,o,r,n in rows))}")
        stat(rows, "ALL")
        print("by grade:")
        bg = defaultdict(list)
        for row in rows:
            bg[row[0]["grade"]].append(row)
        for g in sorted(bg):
            stat(bg[g], f"grade {g}")
        hi = [r for r in rows if r[0]["grade"] >= 4]
        print("HIGH-GRADE tier (>=4):"); stat(hi, "hi ALL")
        print("  holdout quadrants (hi tier):")
        hq = defaultdict(list)
        for row in hi:
            hq[_quad(row[0], split)].append(row)
        for q in sorted(hq):
            stat(hq[q], "  " + q)
        for t, o, r, net in rows:      # ADDITIVE: one record per trade per mode
            tb.append({"mode": mode, "outcome": o, "R": r, "net": round(float(net), 4),
                       "quad": _quad(t, split),
                       **{k: (float(v) if isinstance(v, Decimal)
                              else (v.isoformat() if hasattr(v, "isoformat") else v))
                          for k, v in t.items()}})

    report("intrabar")     # research/strict (the +6.13R baseline, multi-day holds)
    report("m5_close")     # PRODUCTION F9 — does the edge survive M5-close stops?
    report("eod")          # PRODUCTION intraday — does it survive 15:10 same-day squareoff?

    import csv             # ADDITIVE (Z1): dump the tradebook — enables seconds-long A/B vs the +8R tier
    out = Path(os.environ.get("DERIVE_TB_OUT", str(ROOT / "runs/validate/derive_tradebook.csv")))
    if tb:
        keys = sorted({k for row in tb for k in row})
        with out.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(tb)
        print(f"\nwrote {len(tb)} trade-records -> {out}")


if __name__ == "__main__":
    main()
