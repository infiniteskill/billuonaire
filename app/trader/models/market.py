"""MarketSpec: every market-specific constant (timezone, session bounds, tick
size). Core code takes a spec (default NSE), so switching markets is config only."""

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo


def _minutes(hhmm: str, allow_24: bool = False) -> int:
    """Minutes since midnight for "HH:MM"; "24:00" (=1440) only if allow_24."""
    m = re.fullmatch(r"([0-2]\d):([0-5]\d)", hhmm or "")
    if not m or (int(m[1]) > 23 and not (allow_24 and hhmm == "24:00")):
        raise ValueError(f"invalid HH:MM time {hhmm!r}")
    return int(m[1]) * 60 + int(m[2])


@dataclass(frozen=True)
class MarketSpec:
    """A market's trading calendar + price grid. Defaults are NSE equity."""

    tz: str = "Asia/Kolkata"
    session_open: str = "09:15"    # "00:00" for 24h markets
    session_close: str = "15:30"   # exclusive; "24:00" allowed for 24h
    tick_size: Decimal = Decimal("0.05")
    expiry_weekday: int | None = 1  # weekly derivatives expiry; None = none.
    # Tuesday: NSE moved index/stock derivative expiries Thu -> Tue (SEBI
    # expiry-day rationalisation, effective late 2025 / Sep 1 2025 onward).

    def __post_init__(self):
        object.__setattr__(self, "tick_size", Decimal(str(self.tick_size)))
        if self.tick_size <= 0:
            raise ValueError(f"tick_size must be > 0, got {self.tick_size}")
        if self.expiry_weekday is not None and not 0 <= self.expiry_weekday <= 6:
            raise ValueError(f"expiry_weekday must be 0-6 or None, got {self.expiry_weekday}")
        if self.session_minutes <= 0:
            raise ValueError(f"session_close {self.session_close!r} must be "
                             f"after session_open {self.session_open!r}")

    @property
    def tzinfo(self) -> ZoneInfo: return ZoneInfo(self.tz)
    @property
    def open_t(self) -> time: return time(*divmod(_minutes(self.session_open), 60))
    @property
    def close_t(self) -> time:  # "24:00" wraps to midnight
        return time(*divmod(_minutes(self.session_close, True) % 1440, 60))
    @property
    def session_minutes(self) -> int:  # 375 for NSE; 1440 for 24h
        return _minutes(self.session_close, True) - _minutes(self.session_open)

    def quantize(self, value) -> Decimal:
        """Snap value onto the market's tick grid (round half up)."""
        d = Decimal(str(value))
        return (d / self.tick_size).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * self.tick_size

    def session_open_dt(self, ts: datetime) -> datetime:
        """Session open of ts's day, on ts's own wall clock."""
        return ts.replace(hour=self.open_t.hour, minute=self.open_t.minute,
                          second=0, microsecond=0)


def is_expiry(d: date, spec: "MarketSpec") -> bool:
    """Derivatives expiry day: the LAST spec.expiry_weekday of d's month (None
    => never), not every occurrence -- NSE stock/index derivatives expire
    monthly on the last Tuesday, shifted to the previous trading day on a
    holiday. That holiday shift is NOT modeled here (no holiday calendar
    available): this treats the raw weekday-matched last occurrence as
    expiry even when it happens to be a holiday."""
    return (spec.expiry_weekday is not None and d.weekday() == spec.expiry_weekday
            and (d + timedelta(days=7)).month != d.month)


NSE = MarketSpec()
