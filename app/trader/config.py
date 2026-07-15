import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _validate_hhmm(value: str) -> str:
    if not _HHMM.match(value):
        raise ValueError(f"expected HH:MM time string, got {value!r}")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RiskCfg(StrictModel):
    per_trade_pct: float = Field(gt=0)
    daily_loss_pct: float = Field(gt=0)
    max_trades_day: int = Field(gt=0)
    max_per_stock: int = Field(gt=0)
    consecutive_loss_stop: int = Field(gt=0)
    expiry_size_mult: float = Field(gt=0)


class TimeCfg(StrictModel):
    observe_until: str
    no_entry_after: str
    squareoff: str

    @field_validator("observe_until", "no_entry_after", "squareoff")
    @classmethod
    def _check_hhmm(cls, v: str) -> str:
        return _validate_hhmm(v)


class StopsCfg(StrictModel):
    atr_buffer: float = Field(gt=0)
    wick_tolerance_candles: int = Field(gt=0)
    round_offset_ticks: int = Field(gt=0)


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


class Settings(StrictModel):
    capital: float = Field(gt=0)
    risk: RiskCfg
    time: TimeCfg
    stops: StopsCfg
    confluence: ConfluenceCfg
    detectors: DetectorsCfg
    fills: FillsCfg

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
