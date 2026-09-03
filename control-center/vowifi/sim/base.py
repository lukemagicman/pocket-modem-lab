"""Abstract SIM interface used by the future SWu layer."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import AkaResult, CardStatus


class SimBackend(ABC):
    @abstractmethod
    def card_status(self) -> CardStatus:
        """Return non-sensitive card readiness information."""

    @abstractmethod
    def authenticate_aka(self, rand: bytes, autn: bytes) -> AkaResult:
        """Ask the SIM to process a network-provided AKA challenge."""

    @staticmethod
    def validate_challenge(rand: bytes, autn: bytes) -> None:
        if not isinstance(rand, bytes) or not isinstance(autn, bytes):
            raise TypeError("RAND and AUTN must be bytes")
        if len(rand) != 16 or len(autn) != 16:
            raise ValueError("RAND and AUTN must each be 16 bytes")
