"""Deterministic no-card backend for state-machine tests."""

from __future__ import annotations

from .base import SimBackend
from .models import AkaResult, AkaStatus, CardStatus


class MockSimBackend(SimBackend):
    def __init__(self, result: AkaResult | None = None):
        self._result = result or AkaResult(AkaStatus.UNSUPPORTED, detail="mock")
        self.last_request_lengths: tuple[int, int] | None = None

    def card_status(self) -> CardStatus:
        return CardStatus(present=True, ready=True, applications=("usim",))

    def authenticate_aka(self, rand: bytes, autn: bytes) -> AkaResult:
        self.validate_challenge(rand, autn)
        self.last_request_lengths = (len(rand), len(autn))
        return self._result
