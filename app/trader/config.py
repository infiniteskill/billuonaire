import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from trader.models.market import MarketSpec, _minutes


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def check_detector_deps(enabled: list[str]) -> None:
    """propulsion_block reads OB_BULL/OB_BEAR Levels written by orderblock/
    ob_lux; without one enabled BEFORE it (run_all executes config order) it
    silently produces nothing. Shared by Settings validation and tools that
    mutate ``detectors.enabled`` post-validation (study --only)."""
    if "propulsion_block" in enabled:
        i = enabled.index("propulsion_block")
        if not any(p in enabled[:i] for p in ("orderblock", "ob_lux")):
            raise ValueError(
                "propulsion_block requires orderblock or ob_lux enabled "
                "before it in detectors.enabled")


class RiskCfg(StrictModel):
    per_trade_pct: float = Field(gt=0)
    daily_loss_pct: float = Field(gt=0)
    max_trades_day: int = Field(gt=0)
    max_per_stock: int = Field(gt=0)
    consecutive_loss_stop: int = Field(gt=0)
    expiry_size_mult: float = Field(gt=0)
    daily_profit_lock_R: float = Field(default=2.0, gt=0)
    day_after_trend_mult: float = Field(default=0.75, gt=0)  # axiom 16
    portfolio_heat_pct: float = Field(default=1.0, gt=0)     # B8 open-risk cap
    max_correlated_positions: int = Field(default=2, gt=0)   # same-direction cap
    min_minutes_between_trades: int = Field(default=15, ge=0)  # B11 cooldown
    range_pin_size_mult: float = Field(default=0.5, gt=0)    # fade edges half-size
    leverage: float = Field(default=5.0, gt=0)               # NSE MIS notional cap
    max_cost_reward_ratio: float = Field(default=0.15, gt=0)  # rt costs vs T1 reward


class TimeCfg(StrictModel):
    # NB: no observe_until knob -- the observation window is observe_min ONLY
    # (a second clock-time value could silently disagree with it)
    no_entry_after: str
    squareoff: str
    observe_min: int = Field(default=105, ge=0)  # entry window opens open+observe_min
    # audit 5: entries before the template lock (135m) trade an unlocked read;
    # True opens the window at max(observe_min, lock) -- False = old behavior
    entry_after_lock: bool = False

    @field_validator("no_entry_after", "squareoff")
    @classmethod
    def _check_hhmm(cls, v: str) -> str:
        _minutes(v)  # raises on malformed HH:MM
        return v

    @model_validator(mode="after")
    def _entry_window_before_squareoff(self) -> "TimeCfg":
        if _minutes(self.no_entry_after) >= _minutes(self.squareoff):
            raise ValueError(f"time.no_entry_after {self.no_entry_after} must be "
                             f"before squareoff {self.squareoff}")
        return self


class StopsCfg(StrictModel):
    # NB: no wick tolerance knob -- stealth stops are close-confirmed ONLY
    # (wicks through the stop never exit, however many in a row)
    atr_buffer: float = Field(gt=0)
    round_offset_ticks: int = Field(gt=0)
    min_stop_atr: float = Field(default=1.0, gt=0)  # cost floor: widen tighter stops


class EntryCfg(StrictModel):
    arm_proximity_atr: float = Field(default=1.0, gt=0)  # 06 §4: arm only near
    chase_tolerance_atr: float = Field(default=0.1, gt=0)
    max_stop_atr: float = Field(default=2.0, gt=0)
    arm_ttl_candles: int = Field(default=12, gt=0)
    fill_ttl_candles: int = Field(default=6, gt=0)  # M5 lifetime of entry limit


class EventsCfg(StrictModel):
    big_candle_atr: float = Field(default=3.0, gt=0)
    cooldown_candles: int = Field(default=6, gt=0)


class LadderCfg(StrictModel):
    # Elimination-ladder gate (research runs/long60/FACTS.md): emit only
    # signals whose zone earns >= min_rung (1 prior-session first touch,
    # 2 +H1 nested, 3 +sweep-aligned). Absent section = disabled =
    # pre-ladder behavior exactly; the shipped template opts in at 3.
    enabled: bool = False
    min_rung: int = Field(default=3, ge=0, le=3)


class ConfluenceCfg(StrictModel):
    threshold: float = Field(gt=0)
    weights: dict[str, float]

    @field_validator("weights")
    @classmethod
    def _non_negative(cls, v: dict[str, float]) -> dict[str, float]:
        if bad := {k: w for k, w in v.items() if w < 0}:
            raise ValueError(f"confluence.weights must be >= 0: {bad}")
        return v


class ExitsCfg(StrictModel):
    # Per-signal profit target R, keyed by a plan's meta["sl_source"] detector.
    # A plan whose sl_source is present takes profit (full remainder) at that R
    # instead of the default 3R/T3 ladder; absent/unmapped => default behavior.
    target_r_by_source: dict[str, float] = Field(default_factory=dict)

    @field_validator("target_r_by_source")
    @classmethod
    def _positive(cls, v: dict[str, float]) -> dict[str, float]:
        if bad := {k: r for k, r in v.items() if r <= 0}:
            raise ValueError(f"exits.target_r_by_source must be > 0: {bad}")
        return v


class DetectorsCfg(StrictModel):
    enabled: list[str]
    disabled: list[str]
    params: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _lists_clean(self) -> "DetectorsCfg":
        for name, lst in (("enabled", self.enabled), ("disabled", self.disabled)):
            if dups := sorted({d for d in lst if lst.count(d) > 1}):
                raise ValueError(f"detectors.{name} has duplicates: {dups}")
        if both := sorted(set(self.enabled) & set(self.disabled)):
            raise ValueError(f"detectors both enabled and disabled: {both}")
        return self


class CostsCfg(StrictModel):
    brokerage_flat: float = Field(gt=0)
    stt_pct: float = Field(gt=0)          # NSE intraday equity: SELL leg only
    exchange_pct: float = Field(gt=0)     # txn charges + GST + stamp duty approx, both legs


class FillsCfg(StrictModel):
    slippage_bps: float = Field(gt=0)
    half_spread_bps: float = Field(gt=0)
    costs: CostsCfg


class MarketCfg(StrictModel):
    tz: str = "Asia/Kolkata"
    session_open: str = "09:15"
    session_close: str = "15:30"
    tick_size: float | str = "0.05"
    expiry_weekday: int | None = Field(default=1, ge=0, le=6)  # Tue (NSE, late 2025)

    def to_spec(self) -> MarketSpec:
        return MarketSpec(self.tz, self.session_open, self.session_close,
                          self.tick_size, self.expiry_weekday)

    @model_validator(mode="after")
    def _valid_spec(self) -> "MarketCfg":  # MarketSpec rejects bad times / tick <= 0
        return self.to_spec() and self


class Settings(StrictModel):
    capital: float = Field(gt=0)
    index_symbol: str | None = None  # index-context source (e.g. "NIFTY50")
    index_stale_min: int = Field(default=15, gt=0)  # older IndexView = absent
    risk: RiskCfg
    time: TimeCfg
    stops: StopsCfg
    confluence: ConfluenceCfg
    detectors: DetectorsCfg
    fills: FillsCfg
    exits: ExitsCfg = Field(default_factory=ExitsCfg)
    entry: EntryCfg = Field(default_factory=EntryCfg)
    events: EventsCfg = Field(default_factory=EventsCfg)
    ladder: LadderCfg = Field(default_factory=LadderCfg)
    market: MarketCfg = Field(default_factory=MarketCfg)  # absent => NSE

    def market_spec(self) -> MarketSpec:
        return self.market.to_spec()

    @model_validator(mode="after")
    def _cross_checks(self) -> "Settings":
        check_detector_deps(self.detectors.enabled)
        if self.stops.min_stop_atr > self.entry.max_stop_atr:
            raise ValueError(  # the cost-floor widening would ALWAYS overshoot
                f"stops.min_stop_atr {self.stops.min_stop_atr} must be <= "
                f"entry.max_stop_atr {self.entry.max_stop_atr}")
        return self

    def enabled_weights(self) -> dict[str, float]:
        w = {k: v for k, v in self.confluence.weights.items()
             if k in self.detectors.enabled}
        total = sum(w.values())
        if total == 0:
            return {}
        return {k: v / total * 100 for k, v in w.items()}


def load_settings(path: Path) -> Settings:
    return Settings.model_validate_json(Path(path).read_text())


def load_stocks(path: Path) -> list[str]:
    data = json.loads(Path(path).read_text())
    return data["stocks"]
