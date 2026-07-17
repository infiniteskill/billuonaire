"""Study harness: exact outcome math, seeded baseline determinism, and a
judas-day integration smoke (sweep evidence must show positive LONG edge)."""

from datetime import date, datetime, timedelta
from decimal import Decimal

from tests.harness import scenario_settings
from trader.feed.mock import ScenarioFeed, judas_reversal
from trader.models.candle import Candle, Timeframe
from trader.models.market import NSE
from trader.tools.study import atr_series, baseline, outcome, run_study

D = Decimal
DAY = date(2026, 6, 24)  # Wednesday


def bar(i: int, o, h, l, c, day: date = DAY) -> Candle:  # noqa: E741
    ts = datetime.combine(day, NSE.open_t, tzinfo=NSE.tzinfo) \
        + timedelta(minutes=5 * i)
    return Candle("T", Timeframe.M5, ts, D(str(o)), D(str(h)), D(str(l)),
                  D(str(c)), 100)


def flat(i: int, px=100, day: date = DAY) -> Candle:
    return bar(i, px, px, px, px, day)


def test_outcome_long_hit_and_fwd():
    m5 = [bar(0, 100, 100, 100, 100),            # signal bar, ref close 100
          bar(1, 100, 100.9, 99.5, 100),         # fav .9, adv .5: no decision
          bar(2, 100, 101.2, 99.9, 101)]         # fav 1.2 >= atr first -> hit
    m5 += [flat(i, 101) for i in range(3, 6)] + [bar(6, 101, 101.5, 101, 101.5)]
    m5 += [flat(i, 99) for i in range(7, 13)]    # close[12] = 99
    out = outcome(m5, 0, 1, D(1))
    assert out["hit"] == "hit"
    assert out["fwd6"] == 1.5 and out["fwd12"] == -1.0 and out["fwd24"] is None
    assert out["mfe"] == 1.5 and out["mae"] == 1.0     # 100 - min low 99


def test_outcome_same_bar_both_is_loss_and_short_mirror():
    m5 = [flat(0), bar(1, 100, 101.5, 98.9, 100)]      # both cross in one bar
    assert outcome(m5, 0, 1, D(1))["hit"] == "loss"    # conservative
    out = outcome(m5, 0, -1, D(1))                     # SHORT: fav 1.1 first?
    assert out["hit"] == "loss"                        # adv 1.5 same bar -> loss
    m5 = [flat(0), bar(1, 100, 100.5, 98.9, 99)]
    assert outcome(m5, 0, -1, D(1))["hit"] == "hit"    # fav 1.1, adv 0.5


def test_outcome_eod_truncation_and_neutral():
    m5 = [flat(0), bar(1, 100, 100.5, 99.6, 100.4),    # only 1 same-day bar
          flat(2, 105, DAY + timedelta(days=1))]       # next session: excluded
    out = outcome(m5, 0, 1, D(1))
    assert out["hit"] == "undecided" and out["fwd6"] is None
    assert out["mfe"] == 0.5 and out["mae"] == 0.4
    m5 = [flat(0), bar(1, 100, 100.2, 99, 99)] + [flat(i, 99) for i in range(2, 13)]
    out = outcome(m5, 0, 0, D(1))                      # NEUTRAL: absolute move
    assert out["hit"] == "na" and out["fwd12"] == 1.0
    assert out["mfe"] == 0.2 and out["mae"] == 1.0     # up/down excursions


def test_baseline_seeded_deterministic():
    m5 = [bar(i, b, b + 1, b - 1, b + (i % 3 - 1) * 0.5)
          for i in range(70) for b in [100 + (i * 3) % 7]]
    atrs = atr_series(m5)
    assert atrs[13] is None and atrs[14] is not None
    a = baseline(m5, atrs, 30, 1, NSE, "T|k1")
    assert a == baseline(m5, atrs, 30, 1, NSE, "T|k1")   # same seed: identical
    assert a[0] is not None and 0 <= a[0] <= 1
    assert baseline(m5, atrs, 2, 1, NSE, "x") == (None, None)  # bucket has no ATR


def test_summarize_terciles():
    import pandas as pd

    from trader.tools.study import summarize
    rows = [dict(symbol="T", session="2026-06-24", ts=f"t{i:02d}", detector="d",
                 event="E", direction="LONG", strength=i / 10, zone_lo=1.0,
                 zone_hi=2.0, price=100.0, atr=1.0, fwd6=0.1, fwd12=0.2,
                 fwd24=0.3, mfe=1.0, mae=0.5, hit="hit" if i % 2 else "loss",
                 b_hit=0.5, b_fwd12=0.1) for i in range(9)]
    sdf = summarize(pd.DataFrame(rows))
    r = sdf.iloc[0]
    assert r["n"] == 9 and abs(r["hit"] - 4 / 9) < 1e-9 and r["base"] == 0.5
    assert r["edge_by_strength"].count("/") == 2       # three tercile edges


def test_smoke_judas_sweep_positive_long_edge(tmp_path):
    feed = ScenarioFeed([judas_reversal("MOCK", DAY, 100.0)])
    df, sdf = run_study(scenario_settings(), feed, ["MOCK"], None, tmp_path)
    assert len(df) and (tmp_path / "evidence.parquet").exists()
    assert set(df.symbol) == {"MOCK"} and df.detector.nunique() > 3
    sw = df[(df.detector == "sweep") & (df.direction == "LONG") & (df.hit != "na")]
    assert len(sw) > 0
    edge = (sw.hit == "hit").mean() - sw.b_hit.mean()
    assert edge > 0                                    # sweep must beat baseline
    row = sdf[(sdf.detector == "sweep") & (sdf.event == "SWEEP")]
    scored = df[(df.detector == "sweep") & (df.event == "SWEEP") & df.atr.notna()]
    assert len(row) == 1 and row.iloc[0]["n"] == len(scored)  # n = scored only
