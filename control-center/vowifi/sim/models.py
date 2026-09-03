"""Safe data models for SIM AKA operations.

Authentication material is deliberately excluded from repr output.  Callers
must keep result objects in memory and must not serialize them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AkaStatus(str, Enum):
    SUCCESS = "success"
    SYNC_FAILURE = "sync_failure"
    MAC_FAILURE = "mac_failure"
    SIM_ERROR = "sim_error"
    UNSUPPORTED = "unsupported"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class CardStatus:
    present: bool
    ready: bool = False
    applications: tuple[str, ...] = ()
    pin1_enabled: bool | None = None
    detail: str | None = None


@dataclass(frozen=True)
class AkaResult:
    status: AkaStatus
    res: bytes | None = field(default=None, repr=False)
    ck: bytes | None = field(default=None, repr=False)
    ik: bytes | None = field(default=None, repr=False)
    auts: bytes | None = field(default=None, repr=False)
    detail: str | None = None

    def __repr__(self) -> str:
        lengths = {
            name: len(value)
            for name in ("res", "ck", "ik", "auts")
            if (value := getattr(self, name)) is not None
        }
        return (
            f"AkaResult(status={self.status.value!r}, "
            f"secret_lengths={lengths!r}, detail={self.detail!r})"
        )

    def public_summary(self) -> dict[str, object]:
        """Return a JSON-safe summary without authentication material."""
        return {
            "status": self.status.value,
            "lengths": {
                name: len(value)
                for name in ("res", "ck", "ik", "auts")
                if (value := getattr(self, name)) is not None
            },
            "detail": self.detail,
        }


def _read_lv(data: bytes, offset: int, name: str) -> tuple[bytes, int]:
    if offset >= len(data):
        raise ValueError(f"missing {name} length")
    length = data[offset]
    start = offset + 1
    end = start + length
    if end > len(data):
        raise ValueError(f"truncated {name}")
    return data[start:end], end


def parse_usim_auth_response(
    payload: bytes,
    sw1: int = 0x90,
    sw2: int = 0x00,
) -> AkaResult:
    """Parse a 3G USIM AUTHENTICATE response without logging secrets.

    Successful responses use tag DB followed by LV-encoded RES, CK and IK.
    Synchronization failures use tag DC followed by LV-encoded AUTS.
    """
    if not 0 <= sw1 <= 0xFF or not 0 <= sw2 <= 0xFF:
        return AkaResult(AkaStatus.SIM_ERROR, detail="invalid status word")
    if (sw1, sw2) in {(0x98, 0x62), (0x98, 0x64)}:
        return AkaResult(AkaStatus.MAC_FAILURE, detail=f"sw={sw1:02x}{sw2:02x}")
    if (sw1, sw2) != (0x90, 0x00):
        return AkaResult(AkaStatus.SIM_ERROR, detail=f"sw={sw1:02x}{sw2:02x}")
    if not payload:
        return AkaResult(AkaStatus.SIM_ERROR, detail="empty response")

    try:
        tag = payload[0]
        if tag == 0xDB:
            res, offset = _read_lv(payload, 1, "RES")
            ck, offset = _read_lv(payload, offset, "CK")
            ik, _ = _read_lv(payload, offset, "IK")
            if not res or not ck or not ik:
                raise ValueError("empty success field")
            return AkaResult(AkaStatus.SUCCESS, res=res, ck=ck, ik=ik)
        if tag == 0xDC:
            auts, _ = _read_lv(payload, 1, "AUTS")
            if not auts:
                raise ValueError("empty AUTS")
            return AkaResult(AkaStatus.SYNC_FAILURE, auts=auts)
        return AkaResult(AkaStatus.UNSUPPORTED, detail=f"response tag=0x{tag:02x}")
    except ValueError as exc:
        return AkaResult(AkaStatus.SIM_ERROR, detail=str(exc))
