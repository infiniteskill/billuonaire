"""Decision gates: ordered pre-trade vetoes run just before an entry.

GateChain.check returns the FIRST failing Verdict (or a pass); the caller
journals every returned Verdict. EventCooldownGate keeps instance memory of
its trigger timestamp, so keep one GateChain per symbol per session."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from trader.config import Settings
from trader.models.candle import Timeframe
from trader.models.evidence import Direction
from trader.models.market import _minutes


@dataclass(frozen=True)
class Verdict:
    allow: bool
    gate: str
    reason: str


@dataclass
class RiskState:
    """Mutable per-day risk ledger; reset_day() at each session open.
    Memory-only by design, like Position -- replay-safe (state rebuilds by
    re-running the feed from day start); crash-recovery is a live-phase concern."""

    settings: Settings
    trades_today: int = 0
    per_symbol: dict[str, int] = field(default_factory=dict)
    consecutive_losses: int = 0
    daily_pnl_R: float = 0.0
    locked: bool = False
    open_risk: Decimal = Decimal(0)          # sum of open risk_pts x qty (B8)
    open_dirs: dict[str, Direction] = field(default_factory=dict)
    _amts: dict[str, Decimal] = field(default_factory=dict)  # release ledger

    def record_open(self, symbol: str, risk_amt: Decimal = Decimal(0),
                    direction: Direction | None = None) -> None:
        self.trades_today += 1
        self.per_symbol[symbol] = self.per_symbol.get(symbol, 0) + 1
        self.open_risk += risk_amt
        self._amts[symbol] = risk_amt
        if direction is not None:
            self.open_dirs[symbol] = direction

    def record_close(self, r_multiple: float, symbol: str | None = None) -> None:
        self.open_risk -= self._amts.pop(symbol, Decimal(0))
        self.open_dirs.pop(symbol, None)
        r = self.settings.risk
        self.daily_pnl_R += r_multiple
        self.consecutive_losses = self.consecutive_losses + 1 if r_multiple < 0 else 0
        if (self.consecutive_losses >= r.consecutive_loss_stop
                or self.daily_pnl_R * r.per_trade_pct <= -r.daily_loss_pct
                or self.daily_pnl_R >= r.daily_profit_lock_R):
            self.locked = True

    def reset_day(self) -> None:
        self.trades_today, self.consecutive_losses, self.daily_pnl_R = 0, 0, 0.0
        self.per_symbol, self.locked = {}, False
        self.open_risk, self.open_dirs, self._amts = Decimal(0), {}, {}


class Gate(ABC):
    name = "gate"

    @abstractmethod
    def check(self, ctx, direction, plan_zone, htf_phase, risk) -> Verdict: ...

    def _ok(self) -> Verdict: return Verdict(True, self.name, "ok")
    def _no(self, reason: str) -> Verdict: return Verdict(False, self.name, reason)


class TimeWindowGate(Gate):
    name = "time_window"

    def __init__(self, settings: Settings):
        self.observe_min, self.until = settings.time.observe_min, settings.time.no_entry_after

    def check(self, ctx, direction, plan_zone, htf_phase, risk) -> Verdict:
        start = ctx.spec.session_open_dt(ctx.now) + timedelta(minutes=self.observe_min)
        if ctx.now < start:
            return self._no(f"observing until {start:%H:%M}")
        if ctx.now >= ctx.now.replace(hour=_minutes(self.until) // 60,
                                      minute=_minutes(self.until) % 60,
                                      second=0, microsecond=0):
            return self._no(f"no entries after {self.until}")
        return self._ok()


class TemplateGate(Gate):
    name = "template"

    def check(self, ctx, direction, plan_zone, htf_phase, risk) -> Verdict:
        if ctx.day.template == "UNCLASSIFIED":
            return self._no("day template unclassified")
        return self._ok()


class RegimeVetoGate(Gate):
    name = "regime_veto"

    def check(self, ctx, direction, plan_zone, htf_phase, risk) -> Verdict:
        if htf_phase == "MARKDOWN" and direction is Direction.LONG:
            return self._no("htf MARKDOWN vetoes LONG")
        if htf_phase == "MARKUP" and direction is Direction.SHORT:
            return self._no("htf MARKUP vetoes SHORT")
        return self._ok()


class EventCooldownGate(Gate):
    """Big M5 candle (> big_candle_atr x ATR) or session-open gap (> 1 x ATR
    vs prev day close) blocks entries for the next cooldown_candles candles."""

    name = "event_cooldown"

    def __init__(self, settings: Settings):
        self.big = Decimal(str(settings.events.big_candle_atr))
        self.cooldown = settings.events.cooldown_candles
        self._trigger_ts = None

    def check(self, ctx, direction, plan_zone, htf_phase, risk) -> Verdict:
        atr, last = ctx.atr(Timeframe.M5), ctx.candles.last(1, Timeframe.M5)
        if atr is None or not last:
            return self._ok()
        c = last[-1]
        today, prev = ctx.candles.today(Timeframe.M5), ctx.candles.prev_day(Timeframe.M5)
        if c.range > self.big * atr:
            self._trigger_ts = c.ts
        elif today and prev and abs(today[0].open - prev[-1].close) > atr:
            self._trigger_ts = max(self._trigger_ts or today[0].ts, today[0].ts)
        if self._trigger_ts is not None:
            elapsed = (c.ts - self._trigger_ts) // timedelta(minutes=Timeframe.M5.minutes)
            if elapsed <= self.cooldown:
                return self._no(f"event cooldown, candle {elapsed}/{self.cooldown}")
        return self._ok()


class ChaseGate(Gate):
    name = "chase"

    def __init__(self, settings: Settings):
        self.tol = Decimal(str(settings.entry.chase_tolerance_atr))

    def check(self, ctx, direction, plan_zone, htf_phase, risk) -> Verdict:
        atr, last = ctx.atr(Timeframe.M5), ctx.candles.last(1, Timeframe.M5)
        if plan_zone is None or atr is None or not last:
            return self._ok()
        lo, hi = min(plan_zone), max(plan_zone)
        close, tol = last[-1].close, self.tol * atr
        if direction is Direction.LONG and close > hi + tol:
            return self._no(f"close {close} chases above zone edge {hi}")
        if direction is Direction.SHORT and close < lo - tol:
            return self._no(f"close {close} chases below zone edge {lo}")
        return self._ok()


class RiskBudgetGate(Gate):
    name = "risk_budget"

    def __init__(self, settings: Settings):
        self.r, self.capital = settings.risk, Decimal(str(settings.capital))

    def check(self, ctx, direction, plan_zone, htf_phase, risk) -> Verdict:
        if risk.locked:
            return self._no("risk locked for the day")
        if risk.trades_today >= self.r.max_trades_day:
            return self._no(f"max {self.r.max_trades_day} trades/day reached")
        if risk.per_symbol.get(ctx.symbol, 0) >= self.r.max_per_stock:
            return self._no(f"max {self.r.max_per_stock} trade(s) in {ctx.symbol} reached")
        # B8 portfolio heat: open risk + this plan's budget vs heat% of capital
        new = self.capital * Decimal(str(self.r.per_trade_pct)) / 100
        cap = self.capital * Decimal(str(self.r.portfolio_heat_pct)) / 100
        if risk.open_risk + new > cap:
            return self._no(f"portfolio heat {risk.open_risk + new} > cap {cap}")
        same = sum(1 for d in risk.open_dirs.values() if d is direction)
        if same >= self.r.max_correlated_positions:
            return self._no(f"{same} open position(s) already {direction.name}")
        return self._ok()


class GateChain:
    """Fixed-order chain; cheap/static gates first, stateful budget last."""

    def __init__(self, settings: Settings):
        self.gates = [TimeWindowGate(settings), TemplateGate(), RegimeVetoGate(),
                      EventCooldownGate(settings), ChaseGate(settings),
                      RiskBudgetGate(settings)]

    def check(self, ctx, direction, plan_zone, htf_phase, risk_state) -> Verdict:
        for gate in self.gates:
            verdict = gate.check(ctx, direction, plan_zone, htf_phase, risk_state)
            if not verdict.allow:
                return verdict
        return Verdict(True, "chain", "all gates passed")
