"""Failure-model package — PLAN-A §5 / ADR-006."""

from engine.failure_models.base import FailureModel
from engine.failure_models.coffin_manson import CoffinManson
from engine.failure_models.exponential import ExponentialDecay
from engine.failure_models.weibull import WeibullDecay

__all__ = [
    "FailureModel",
    "ExponentialDecay",
    "WeibullDecay",
    "CoffinManson",
]
