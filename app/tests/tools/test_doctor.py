"""trader doctor: synthetic good/bad fixtures for every check."""

from datetime import datetime, timedelta

import pandas as pd

from trader.tools.doctor import check_file, run_dir, splices

HEADER = "ts,open,high,low,close,volume"


def _rows(day="2026-07-15", n=375, step=1, px="100.00,101.00,99.00,100.50",
          vol="10", start="09:15"):
    base = datetime.fromisoformat(f"{day}T{start}:00+05:30")
    return [f"{(base + timedelta(minutes=step * i)).isoformat()},{px},{vol}"
            for i in range(n)]


def _write(tmp_path, rows, name="X.csv", header=HEADER):
    p = tmp_path / name
    p.write_text("\n".join([header, *rows]) + "\n")
    return p


def _codes(rep, sev=None):
    return {i.code for i in rep.issues if sev is None or i.sev == sev}


# ------------------------------------------------------------- clean fixtures

def test_clean_m1_file(tmp_path):
    rep = check_file(_write(tmp_path, _rows("2026-07-15") + _rows("2026-07-16")))
    assert rep.issues == [] and rep.cadence == 1 and rep.rows == 750
    assert rep.sessions == {datetime(2026, 7, 15).date(): 375,
                            datetime(2026, 7, 16).date(): 375}


def test_clean_5m_file_cadence_detected(tmp_path):
    rep = check_file(_write(tmp_path, _rows(n=75, step=5)))
    assert rep.issues == [] and rep.cadence == 5


# ------------------------------------------------------------------ criticals

def test_bad_header_is_critical(tmp_path):
    p = _write(tmp_path, ["2026-07-15T09:15:00+05:30,1,1,1,1,1"],
               header="date,o,h,l,c,v")
    rep = check_file(p)
    assert _codes(rep, "CRITICAL") == {"schema"}


def test_duplicate_and_unsorted_ts(tmp_path):
    r = _rows(n=3)
    rep = check_file(_write(tmp_path, [r[0], r[2], r[2], r[1]]))
    assert {"ts_dup", "ts_order"} <= _codes(rep, "CRITICAL")


def test_naive_and_wrong_offset_ts(tmp_path):
    rep = check_file(_write(tmp_path, [
        "2026-07-15T09:15:00,100.00,101.00,99.00,100.50,10",        # naive
        "2026-07-15T09:16:00+00:00,100.00,101.00,99.00,100.50,10",  # not IST
    ]))
    assert {"ts_naive", "ts_tz"} <= _codes(rep, "CRITICAL")


def test_unparseable_ts(tmp_path):
    rep = check_file(_write(tmp_path, ["nonsense,1.00,1.00,1.00,1.00,1"]))
    assert _codes(rep, "CRITICAL") == {"ts_parse"}


def test_out_of_session_rows(tmp_path):
    rep = check_file(_write(tmp_path, _rows(start="09:14", n=1)
                            + _rows(start="15:30", n=1)))
    assert "session" in _codes(rep, "CRITICAL")


def test_ohlc_violations(tmp_path):
    rep = check_file(_write(tmp_path, [
        "2026-07-15T09:15:00+05:30,100.00,99.00,99.00,100.00,10",   # high < open
        "2026-07-15T09:16:00+05:30,-1.00,1.00,-2.00,0.50,10",       # non-positive
        "2026-07-15T09:17:00+05:30,NaN,101.00,99.00,100.00,10",     # NaN
        "2026-07-15T09:18:00+05:30,junk,101.00,99.00,100.00,10",    # unparseable
    ]))
    assert {"ohlc", "price"} <= _codes(rep, "CRITICAL")


def test_off_grid_tick_is_warning_not_critical(tmp_path):
    rep = check_file(_write(tmp_path, ["2026-07-15T09:15:00+05:30,"
                                       "100.02,101.00,99.00,100.00,10"]))
    assert _codes(rep, "WARNING") == {"tick"} and rep.n_crit == 0


def test_bad_volume(tmp_path):
    rep = check_file(_write(tmp_path, _rows(n=1, vol="-5")
                            + _rows(n=1, vol="1.5", start="09:16")))
    assert "volume" in _codes(rep, "CRITICAL")


# -------------------------------------------------------------- discontinuity

def test_splice_flagged_across_sessions(tmp_path):
    p = _write(tmp_path, _rows("2026-07-15", n=3)
               + _rows("2026-07-16", n=3, px="130.00,131.00,129.00,130.50"))
    rep = check_file(p)
    crit = [i for i in rep.issues if i.code == "splice"]
    assert len(crit) == 1 and "29.4%" in crit[0].msg
    assert check_file(p, jump_pct=40).n_crit == 0     # threshold respected


def test_no_splice_below_threshold(tmp_path):
    p = _write(tmp_path, _rows("2026-07-15", n=3)
               + _rows("2026-07-16", n=3, px="110.00,111.00,109.00,110.50"))
    assert "splice" not in _codes(check_file(p))      # ~9.5% move: normal gap


def test_splices_helper_positional():
    df = pd.DataFrame({"ts": ["a", "b"], "open": ["100", "200"],
                       "high": ["210", "210"], "low": ["90", "90"],
                       "close": ["100", "205"], "volume": ["1", "1"]})
    assert splices(df) == [("b", 100.0)] and splices(df, jump_pct=150) == []


# -------------------------------------------------------- cadence + sessions

def test_cadence_mixed_1m_row_in_5m_file(tmp_path):
    stray = _rows(n=1, start="09:16")                 # off the 5m grid
    rep = check_file(_write(tmp_path, _rows(n=75, step=5)[:1] + stray
                            + _rows(n=74, step=5)[1:]))
    assert "cadence" in _codes(rep, "CRITICAL")


def test_thin_session_warning(tmp_path):
    rep = check_file(_write(tmp_path, _rows(n=5)))    # 5/375 M1 rows
    assert _codes(rep, "WARNING") == {"thin_session"} and rep.n_crit == 0


def test_gap_session_is_info(tmp_path):
    rep = check_file(_write(tmp_path, _rows(n=370)))  # 370/375: minor gap
    assert _codes(rep, "INFO") == {"gap_session"} and rep.n_crit == 0


def test_issue_cap_suppresses_detail(tmp_path):
    rep = check_file(_write(tmp_path, _rows(n=10, vol="-1")))
    vol = [i for i in rep.issues if i.code == "volume"]
    assert len(vol) == 4 and vol[-1].msg == "... +7 more"


def test_empty_file_is_warning(tmp_path):
    rep = check_file(_write(tmp_path, []))
    assert _codes(rep, "WARNING") == {"empty"} and rep.n_crit == 0


# ------------------------------------------------------------------ cross-file

def test_run_dir_flags_stale_file(tmp_path):
    _write(tmp_path, _rows("2026-07-15") + _rows("2026-07-16"), name="A.csv")
    _write(tmp_path, _rows("2026-07-15"), name="B.csv")
    reps = {r.name: r for r in run_dir(tmp_path)}
    assert [i.code for i in reps["B.csv"].issues] == ["stale"]
    assert reps["A.csv"].issues == []
