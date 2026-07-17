import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from trader.models.market import MarketSpec, _minutes


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RiskCfg(StrictModel):
    per_trade_pct: float = Field(gt=0)
    daily_loss_pct: float = Field(gt=0)
    max_trades_day: int = Field(gt=0)
    max_per_stock: int = Field(gt=0)
    consecutive_loss_stop: int = Field(gt=0)
    expiry_size_mult: float = Field(gt=0)
    daily_profit_lock_R: float = Field(default=2.0, gt=0)
    day_after_trend_mult: float = Field(default=0.75, gt=0)  # axiom 16


class TimeCfg(StrictModel):
    observe_until: str
    no_entry_after: str
    squareoff: str
    observe_min: int = Field(default=105, ge=0)  # entry window opens open+observe_min

    @field_validator("observe_until", "no_entry_after", "squareoff")
    @classmethod
    def _check_hhmm(cls, v: str) -> str:
        _minutes(v)  # raises on malformed HH:MM
        return v


class StopsCfg(StrictModel):
    # NB: no wick tolerance knob -- stealth stops are close-confirmed ONLY
    # (wicks through the stop never exit, however many in a row)
    atr_buffer: float = Field(gt=0)
    round_offset_ticks: int = Field(gt=0)


class EntryCfg(StrictModel):
    arm_proximity_atr: float = Field(default=1.0, gt=0)  # 06 §4: arm only near
    chase_tolerance_atr: float = Field(default=0.1, gt=0)
    max_stop_atr: float = Field(default=1.2, gt=0)
    arm_ttl_candles: int = Field(default=12, gt=0)


class EventsCfg(StrictModel):
    big_candle_atr: float = Field(default=3.0, gt=0)
    cooldown_candles: int = Field(default=6, gt=0)


class ConfluenceCfg(StrictModel):
    threshold: float = Field(gt=0)
    weights: dict[str, float]


class DetectorsCfg(StrictModel):
    enabled: list[str]
    disabled: list[str]
    params: dict = Field(default_factory=dict)


class CostsCfg(StrictModel):
    brokerage_flat: float = Field(gt=0)
    stt_pct: float = Field(gt=0)
    exchange_pct: float = Field(gt=0)


class FillsCfg(StrictModel):
    slippage_bps: float = Field(gt=0)
    half_spread_bps: float = Field(gt=0)
    costs: CostsCfg


class MarketCfg(StrictModel):
    tz: str = "Asia/Kolkata"
    session_open: str = "09:15"
    session_close: str = "15:30"
    tick_size: float | str = "0.05"
    expiry_weekday: int | None = Field(default=3, ge=0, le=6)

    def to_spec(self) -> MarketSpec:
        return MarketSpec(self.tz, self.session_open, self.session_close,
                          self.tick_size, self.expiry_weekday)

    @model_validator(mode="after")
    def _valid_spec(self) -> "MarketCfg":  # MarketSpec rejects bad times / tick <= 0
        return self.to_spec() and self


class Settings(StrictModel):
    capital: float = Field(gt=0)
    index_symbol: str | None = None  # index-context source (e.g. "NIFTY50")
    risk: RiskCfg
    time: TimeCfg
    stops: StopsCfg
    confluence: ConfluenceCfg
    detectors: DetectorsCfg
    fills: FillsCfg
    entry: EntryCfg = Field(default_factory=EntryCfg)
    events: EventsCfg = Field(default_factory=EventsCfg)
    market: MarketCfg = Field(default_factory=MarketCfg)  # absent => NSE

    def market_spec(self) -> MarketSpec:
        return self.market.to_spec()

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
