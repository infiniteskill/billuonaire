"""Time-of-day danger detector ("timestats"): blends a cold-start prior
table with learned per-bucket sweep-danger; Evidence strength inverts the
danger of the current session-relative time bucket.

Bucket index = minutes-since-session_open // bucket_min; count =
spec.session_minutes // bucket_min. NSE-shaped sessions (session_minutes
== 375) use the empirical intraday danger table; any other session (e.g.
24h crypto) gets a flat 0.5 prior until learned.

Learning (wired by a later phase): record(bucket, swept) accumulates
(sweeps, total) per bucket; danger(bucket) blends prior with observed
counts Laplace-style: (prior*prior_weight + sweeps) / (prior_weight +
total). save()/load() persist counts as JSON at
"{path}/timestats-{symbol}.json" when params.path is set; path=None ->
in-memory only, no disk IO.

detect() emits one NEUTRAL Evidence per new closed M5 candle: strength =
1 - danger(bucket of ctx.now), zone = candle's (low, high) ([] if none),
ttl 1, meta {"bucket", "danger"}."""

from __future__ import annotations

import json
from pathlib import Path

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.market import MarketSpec

_DEFAULTS = {"bucket_min": 5, "prior_weight": 20, "path": None}

# (minutes-from-open upper bound exclusive, danger); last entry is the tail.
_NSE_TABLE = [(75, 0.8), (105, 0.5), (225, 0.3), (285, 0.6), (None, 0.8)]


def nse_prior(minutes: float) -> float:
    return next(d for hi, d in _NSE_TABLE if hi is None or minutes < hi)


def bucket_count(spec: MarketSpec, bucket_min: int) -> int:
    return spec.session_minutes // bucket_min


def bucket_index(now, spec: MarketSpec, bucket_min: int) -> int:
    elapsed = (now - spec.session_open_dt(now)).total_seconds() / 60
    return int(elapsed // bucket_min)


@register
class TimestatsDetector(Detector):
    name = "timestats"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._counts: dict[int, tuple[int, int]] = {}  # bucket -> (sweeps, total)
        self._seen: set = set()

    def prior(self, bucket: int, spec: MarketSpec) -> float:
        if spec.session_minutes != 375:
            return 0.5
        return nse_prior(bucket * self.params["bucket_min"])

    def record(self, bucket: int, swept: bool) -> None:
        sweeps, total = self._counts.get(bucket, (0, 0))
        self._counts[bucket] = (sweeps + int(swept), total + 1)

    def danger(self, bucket: int, spec: MarketSpec) -> float:
        sweeps, total = self._counts.get(bucket, (0, 0))
        w = self.params["prior_weight"]
        return (self.prior(bucket, spec) * w + sweeps) / (w + total)

    def _path_for(self, symbol: str) -> Path | None:
        path = self.params["path"]
        return Path(path) / f"timestats-{symbol}.json" if path else None

    def save(self, symbol: str) -> None:
        p = self._path_for(symbol)
        if p is None:
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({str(k): list(v) for k, v in self._counts.items()}))

    def load(self, symbol: str) -> None:
        p = self._path_for(symbol)
        if p is None or not p.exists():
            return
        self._counts = {int(k): tuple(v) for k, v in json.loads(p.read_text()).items()}

    def detect(self, ctx: StockContext) -> list[Evidence]:
        window = ctx.candles.last(1, Timeframe.M5)
        zone = (window[-1].low, window[-1].high) if window else []
        key = window[-1].ts if window else ctx.now
        if key in self._seen:
            return []
        self._seen.add(key)
        bucket = bucket_index(ctx.now, ctx.spec, self.params["bucket_min"])
        danger = self.danger(bucket, ctx.spec)
        return [Evidence(
            detector=self.name, direction=Direction.NEUTRAL, strength=1 - danger,
            zone=zone, ts=ctx.now, ttl_candles=1,
            meta={"bucket": bucket, "danger": danger},
        )]
