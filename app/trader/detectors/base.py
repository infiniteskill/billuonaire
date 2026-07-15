"""Detector plugin foundation.

Every detector subclasses ``Detector`` and registers itself with the
``@register`` decorator, which adds it to the module-level ``REGISTRY`` by
``cls.name`` (duplicate names fail loudly at import time).

``DetectorRegistry`` instantiates only the detectors named in
``settings.detectors.enabled`` (config-driven enable/disable), in config
order, passing each its ``settings.detectors.params[name]`` dict.

``run_all`` degrades gracefully:
- a detector whose ``requires`` are not satisfied by the context is skipped
  silently (e.g. options data absent);
- a detector that raises must NEVER poison the others: the exception is
  logged via ``logging.getLogger("trader.detectors")`` and the run continues.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from trader.config import Settings
from trader.engine.context import StockContext
from trader.models.evidence import Evidence

logger = logging.getLogger("trader.detectors")

REGISTRY: dict[str, type["Detector"]] = {}


def register(cls: type["Detector"]) -> type["Detector"]:
    """Class decorator: add a Detector subclass to REGISTRY by ``cls.name``.
    A duplicate name is a programming error -> ValueError at import time."""
    if cls.name in REGISTRY:
        raise ValueError(
            f"duplicate detector name {cls.name!r}: "
            f"{REGISTRY[cls.name].__qualname__} already registered"
        )
    REGISTRY[cls.name] = cls
    return cls


class Detector(ABC):
    """Base class for all detectors.

    Class attributes:
    - ``name``: unique registry key, also the ``Evidence.detector`` tag.
    - ``requires``: capability tags the context must provide, e.g.
      ``{"options_chain"}``; unmet -> the detector is skipped silently.
    """

    name: str
    requires: frozenset[str] = frozenset()

    def __init__(self, params: dict):
        self.params = params

    @abstractmethod
    def detect(self, ctx: StockContext) -> list[Evidence]:
        ...


def _requires_met(detector: Detector, ctx: StockContext) -> bool:
    """A requirement is met iff the context provides it. This phase only
    knows ``options_chain`` (met iff ctx.options is not None); an unknown
    requirement is never met, so the detector is skipped, not crashed."""
    for req in detector.requires:
        if req == "options_chain":
            if ctx.options is None:
                return False
        else:
            return False
    return True


class DetectorRegistry:
    """Holds the enabled detector instances, in config order."""

    def __init__(self, settings: Settings):
        unknown = [n for n in settings.detectors.enabled if n not in REGISTRY]
        if unknown:
            raise ValueError(
                f"unknown detector(s) in config: {unknown}; "
                f"known: {sorted(REGISTRY)}"
            )
        self.detectors: list[Detector] = [
            REGISTRY[name](settings.detectors.params.get(name, {}))
            for name in settings.detectors.enabled
        ]

    def run_all(self, ctx: StockContext) -> list[Evidence]:
        """Run every enabled detector against ctx, in config order.
        Unmet ``requires`` -> silent skip. A raising detector is logged and
        contributes nothing, but never stops the others."""
        evidence: list[Evidence] = []
        for detector in self.detectors:
            if not _requires_met(detector, ctx):
                continue
            try:
                evidence.extend(detector.detect(ctx))
            except Exception:
                logger.exception(
                    "detector %r failed on %s at %s; skipping it this tick",
                    detector.name, ctx.symbol, ctx.now,
                )
        return evidence
