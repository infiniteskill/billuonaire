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
DATA = ROOT / "data/wide"
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


def _tap(pipe, trades, min_grade, gate_bars=20):
    orig = pipe.registry.run_all

    def run_all(ctx):
        evs = orig(ctx)
        if any(e.detector in _ZONE_DETS and e.meta.get("event") in _ZONE_EVENTS for e in evs):
            w = ctx.candles.last(gate_bars, Timeframe("5m"))
            cutoff = w[0].ts if w else ctx.now
            window = list(evs) + [e for e in ctx.evidence_history if e.ts >= cutoff]
            d = decide(ctx, window, min_grade)
            if d.take:
                trades.append({"sym": pipe.symbol, "ts": ctx.now, "dir": d.direction.name,
                               "entry": d.entry, "sl": d.sl, "target": d.target, "grade": d.grade})
        return evs
    pipe.registry.run_all = run_all


def _sim(t, m1, hold=3000):
    """Gap-aware forward sim on the finest (1m) candles = honest fill-through.
    Raw R (costs applied separately). intrabar stop-before-target (conservative)."""
    e, sl, tgt = t["entry"], t["sl"], t["target"]
    long = t["dir"] == "LONG"
    risk = abs(e - sl)
    if not risk:
        return None, None
    path = [c for c in m1 if c.ts >= t["ts"]][:hold]
    for b in path:
        if (long and b.open <= sl) or (not long and b.open >= sl):
            return "gap", float((b.open - e) / risk) * (1 if long else -1)
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
    orch = Orchestrator(s, FileFeed(DATA, s.market_spec()), syms, index_symbol=None,
                        max_qty=1, journal_dir=ROOT / "runs/validate/derive_work")
    trades = []
    for pipe in orch.pipelines.values():
        _tap(pipe, trades, min_grade)
    orch.run()
    m1s = {sym: orch.store._data.get(sym, {}).get(Timeframe.M1, []) for sym in syms}

    rows = []
    for t in trades:
        o, r = _sim(t, m1s[t["sym"]])
        if r is None:
            continue
        net = r - cost_R(t["entry"], abs(t["entry"] - t["sl"]))
        rows.append((t, o, r, net))
    if not rows:
        print("no closed trades"); return
    split = sorted(t["ts"] for t, *_ in rows)[len(rows) // 2]

    def stat(sub, label):
        if not sub:
            return
        net = [n for *_, n in sub]
        wins = sum(1 for _, o, r, n in sub if r > 0)
        print(f"  {label:14} n={len(sub):4} win%={100*wins//len(sub):3} "
              f"gross/t={sum(r for _,o,r,n in sub)/len(sub):+.2f}R "
              f"NET/t={sum(net)/len(net):+.3f}R")

    print(f"=== HONEST DERIVED TRADEBOOK  syms={syms} min_grade={min_grade} ===")
    print(f"closed={len(rows)}  (1m fill-through, rupee costs, holdout)")
    from collections import Counter
    print("outcomes:", dict(Counter(o for _, o, r, n in rows)))
    stat(rows, "ALL")
    print("by grade:")
    bg = defaultdict(list)
    for row in rows:
        bg[row[0]["grade"]].append(row)
    for g in sorted(bg):
        stat(bg[g], f"grade {g}")
    print("HIGH-GRADE tier (>=4):")
    hi = [r for r in rows if r[0]["grade"] >= 4]
    stat(hi, "hi ALL")
    print("  holdout quadrants (hi tier):")
    hq = defaultdict(list)
    for row in hi:
        hq[_quad(row[0], split)].append(row)
    for q in sorted(hq):
        stat(hq[q], "  " + q)


if __name__ == "__main__":
    main()
