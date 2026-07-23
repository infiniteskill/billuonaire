"""derive_tradebook.py — the user's idea: DERIVE the tradebook (winners AND
losers) from the tools, not from a hand-supplied log.

Runs the wired taught profile over 1m data; on every bar where a fresh decisional
zone retests, calls decision.decide() over a recent evidence window; each `take`
becomes a trade. Then simulates every trade forward on the real M5 candles
(gap-aware, intrabar stop-before-target) -> win/lose -> R. Winners and losers are
BOTH in the output (the losers = the setups the tools took that failed), so net-R
is the DERIVED profitability. Costs applied as a flat R toll.

Honest scope: recognition-accurate tools only approximate the user's SELECTION, so
this measures the TOOLS' edge (== the user's edge only insofar as the gates encode
the selection). Data = whatever 1m history exists (data/wide ~17d).
Usage: python3 tools/derive_tradebook.py <SYM,SYM> [min_grade] [toll_R]
"""
import sys
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
DATA = ROOT / "data/wide"
TAUGHT = ["extremes", "swings", "liquidity", "sweep", "structure", "wyckoff",
          "orderblock", "fvg", "compression", "ob_taught", "fvg_n", "propulsion2",
          "premium_discount", "htf_nest"]


def _tap(pipe, trades, min_grade, gate_bars=20):
    orig = pipe.registry.run_all

    def run_all(ctx):
        evs = orig(ctx)
        if any(e.detector in _ZONE_DETS and e.meta.get("event") in _ZONE_EVENTS for e in evs):
            tf = Timeframe("5m")
            w = ctx.candles.last(gate_bars, tf)
            cutoff = w[0].ts if w else ctx.now
            window = list(evs) + [e for e in ctx.evidence_history if e.ts >= cutoff]
            d = decide(ctx, window, min_grade)
            if d.take:
                trades.append({"sym": pipe.symbol, "ts": ctx.now, "dir": d.direction.name,
                               "entry": d.entry, "sl": d.sl, "target": d.target,
                               "grade": d.grade})
        return evs
    pipe.registry.run_all = run_all


def _sim(t, m5, slip=Decimal("0.10"), hold=600):
    """Gap-aware forward sim on M5 with realistic SLIPPAGE on every fill (entry,
    stop, target each ~2 ticks worse). On a tiny structural stop the slippage
    dominates R -- this is the fill-through/toll RETHINK/doc-34 calls the whole
    game. Returns (outcome, R) with R on the EFFECTIVE (slipped) risk."""
    e, sl, tgt = t["entry"], t["sl"], t["target"]
    long = t["dir"] == "LONG"
    d = 1 if long else -1
    e_eff = e + slip * d                                 # entry filled worse
    sl_eff = sl - slip * d                               # stop filled worse
    tgt_eff = tgt - slip * d                             # target filled worse
    risk = abs(e_eff - sl_eff)
    if not risk:
        return "no_risk", None
    path = [c for c in m5 if c.ts >= t["ts"]][:hold]
    for b in path:
        if (long and b.open <= sl) or (not long and b.open >= sl):     # gap-through
            return "gap", round(float((b.open - slip * d - e_eff) / risk) * d, 2)
        hit_sl = (b.low <= sl) if long else (b.high >= sl)
        hit_tg = (b.high >= tgt) if long else (b.low <= tgt)
        if hit_sl:
            return "stop", round(float((sl_eff - e_eff) / risk) * d, 2)
        if hit_tg:
            return "target", round(float((tgt_eff - e_eff) / risk) * d, 2)
    return "timeout", None


def main():
    syms = sys.argv[1].split(",")
    min_grade = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    toll = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
    s = load_settings(PROFILE)
    s.detectors.enabled = list(TAUGHT)
    check_detector_deps(s.detectors.enabled)
    feed = FileFeed(DATA, s.market_spec())
    orch = Orchestrator(s, feed, syms, index_symbol=None, max_qty=1,
                        journal_dir=ROOT / "runs/validate/derive_work")
    trades = []
    for pipe in orch.pipelines.values():
        _tap(pipe, trades, min_grade)
    orch.run()
    m5s = {sym: orch.store._data.get(sym, {}).get(Timeframe.M5, []) for sym in syms}

    rows = [(t, *_sim(t, m5s[t["sym"]])) for t in trades]
    closed = [(t, o, r) for t, o, r in rows if r is not None]
    wins = [r for _, o, r in closed if r > 0]
    losses = [r for _, o, r in closed if r <= 0]
    gross = sum(r for _, _, r in closed)
    net = gross - toll * len(closed)                       # flat R toll per trade
    from collections import Counter
    print(f"=== DERIVED TRADEBOOK  syms={syms} min_grade={min_grade} toll={toll}R ===")
    print(f"takes={len(trades)}  closed={len(closed)}  (timeouts/no-risk={len(trades)-len(closed)})")
    if closed:
        print(f"win%={100*len(wins)//len(closed)}  ({len(wins)}W/{len(losses)}L)")
        print(f"outcomes={dict(Counter(o for _, o, _ in closed))}")
        print(f"gross_R={gross:.1f}  net_R(after {toll}R toll)={net:.1f}  "
              f"per_trade={net/len(closed):+.3f}R")
        print(f"avg_win={sum(wins)/len(wins):.1f}R  avg_loss={sum(losses)/len(losses):.2f}R" if wins and losses else "")
        bg = {}
        for t, o, r in closed:
            bg.setdefault(t["grade"], []).append(r)
        print("by grade (n, net/trade after toll):")
        for g in sorted(bg):
            v = bg[g]
            print(f"  grade {g}: n={len(v)}  net/trade={sum(v)/len(v)-toll:+.3f}R")


if __name__ == "__main__":
    main()
