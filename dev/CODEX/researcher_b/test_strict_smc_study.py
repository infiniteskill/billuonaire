from __future__ import annotations

import pandas as pd
import numpy as np

import strict_smc_study as s


def frame(rows):
    d = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    d["ts"] = pd.date_range("2026-07-01 09:15", periods=len(d), freq="5min", tz="Asia/Kolkata")
    d["session"] = "2026-07-01"
    d["minute"] = d.ts.dt.hour * 60 + d.ts.dt.minute
    d["atr"] = 1.0
    d["prev_mid"] = 10.0
    return d


def test_swing_has_separate_pivot_and_availability_time():
    d = frame([
        (9, 10, 8, 9), (9, 11, 8, 9), (9, 15, 8, 9),
        (9, 11, 8, 9), (9, 10, 8, 9),
    ])
    [x] = [x for x in s.candidate_swings("X", d) if x.kind == "SWING_H"]
    assert x.pivot_idx == 2
    assert x.available_idx == 4
    assert x.pivot_ts != x.available_ts


def test_newly_confirmed_swing_cannot_be_swept_retroactively_same_bar():
    d = frame([
        (9, 10, 8, 9), (9, 11, 8, 9), (9, 15, 8, 9),
        (9, 11, 8, 9), (9, 10, 8, 9),  # confirmation bar completes pivot
        (9, 16, 8, 9),                 # only this later bar may sweep it
    ])
    events = []
    _, sweeps, _ = s.build_states("X", d, events)
    high = [x for x in sweeps if x["parent"].kind == "SWING_H"]
    assert len(high) == 1
    assert high[0]["idx"] == 5
    assert high[0]["parent"].available_idx == 4


def test_displacement_shape_is_directional_and_close_confirmed():
    d = frame([(10, 10.2, 9.8, 10)] * 5 + [(10, 11.2, 9.9, 11.1)])
    assert s.displacement_direction(5, d) == 1
    mirror = frame([(10, 10.2, 9.8, 10)] * 5 + [(10, 10.1, 8.8, 8.9)])
    assert s.displacement_direction(5, mirror) == -1


def test_ordered_parent_lineage_and_one_use_sweep():
    d = frame([
        (10, 10.2, 9.8, 10), (10, 10.2, 9.8, 10),
        (10, 10.2, 9.8, 10), (10, 10.2, 9.8, 10),
        (10, 10.0, 9.8, 9.9),            # c1
        (9.9, 11.2, 9.8, 11.1),          # c2 displacement
        (11.0, 11.3, 10.4, 11.0),        # c3: bull FVG 10.0..10.4
    ])
    swept = s.Swing("X:SWING_L:1", "X", "SWING_L", 1, 3, 9.8,
                    d.ts.iloc[1].isoformat(), s.known_at(d.ts.iloc[3]))
    mss = s.Swing("X:SWING_H:2", "X", "SWING_H", 2, 4, 10.5,
                  d.ts.iloc[2].isoformat(), s.known_at(d.ts.iloc[4]))
    parent = {"event_id": "X:SWEEP:P:5", "symbol": "X", "idx": 5,
              "session": "2026-07-01", "direction": 1, "parent": swept,
              "extreme": 9.8, "mss_parent": mss}
    events = []
    lineages = s.form_lineages("X", d, [parent], events)
    assert len(lineages) == 1
    x = lineages[0]
    assert x["sweep_idx"] <= x["disp_idx"] < x["fvg_idx"]
    assert x["mss"] is True
    assert len({z["sweep_event_id"] for z in lineages}) == len(lineages)


def test_shallow_first_touch_consumes_freshness_no_later_ce_cherry_pick():
    d = frame([(10, 10.5, 9.5, 10)] * 10)
    d.loc[6, ["low", "high"]] = [10.30, 10.50]  # touches zone 10..10.4, not CE 10.2
    d.loc[7, ["low", "high"]] = [10.10, 10.50]  # later reaches CE but is ineligible
    lin = {"lineage_id": "L", "symbol": "X", "direction": 1,
           "fvg_idx": 5, "zone_lo": 10.0, "zone_hi": 10.4,
           "fvg_event_id": "F", "atr": 1.0, "sweep_extreme": 9.0,
           "mss": False, "session": "2026-07-01"}
    events = []
    assert s.make_trade(d, [], lin, events) == []
    touches = [e for e in events if e["event_type"] == "FVG_FIRST_TOUCH"]
    assert len(touches) == 1
    assert touches[0]["bar_idx"] == 6
    assert touches[0]["ce_reached"] is False


def test_same_bar_stop_target_ambiguity_is_stop_first():
    d = frame([(10, 12, 8, 10)] * 3)
    result = s.simulate_path(d, 0, 1, entry=10, stop=9, target=11.5, qty=10)
    assert result["exit_kind"] == "stop"
    assert result["exit_idx"] == 0
