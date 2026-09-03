"""QMI UIM transport boundary.

This module is safe by default: card I/O is disabled unless a future,
explicitly approved Milestone A test constructs the backend with
``allow_card_io=True``.  Commands are always executed as argument arrays with
``shell=False``.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable, Sequence

from .base import SimBackend
from .models import AkaResult, AkaStatus, CardStatus, parse_usim_auth_response

Runner = Callable[[Sequence[str], int], subprocess.CompletedProcess[str]]


def _default_runner(args: Sequence[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        shell=False,
    )


def _hex(value: str, name: str, expected_bytes: int | None = None) -> str:
    compact = value.replace(":", "").replace(" ", "").strip()
    if not compact or len(compact) % 2 or not re.fullmatch(r"[0-9A-Fa-f]+", compact):
        raise ValueError(f"invalid {name}")
    if expected_bytes is not None and len(compact) != expected_bytes * 2:
        raise ValueError(f"invalid {name} length")
    return compact.upper()


class QmiUimBackend(SimBackend):
    def __init__(
        self,
        device: str = "/dev/wwan0qmi0",
        slot: int = 1,
        channel: int | None = None,
        *,
        allow_card_io: bool = False,
        runner: Runner = _default_runner,
    ):
        if slot not in range(1, 6):
            raise ValueError("slot must be 1-5")
        self.device = device
        self.slot = slot
        self.channel = channel
        self.allow_card_io = allow_card_io
        self._runner = runner

    def _run(self, option: str, timeout: int = 15) -> subprocess.CompletedProcess[str]:
        return self._runner(
            ["qmicli", "-d", self.device, "--device-open-proxy", option],
            timeout,
        )

    def _require_card_io(self) -> None:
        if not self.allow_card_io:
            raise PermissionError("QMI UIM card I/O is disabled")

    def card_status(self) -> CardStatus:
        result = self._run("--uim-get-card-status")
        text = f"{result.stdout}\n{result.stderr}".lower()
        if result.returncode:
            return CardStatus(present=False, detail="qmi card status failed")
        applications = tuple(
            name for name in ("usim", "isim", "sim", "csim")
            if f"application type:  '{name}" in text
        )
        return CardStatus(
            present="card state: 'present'" in text,
            ready="application state: 'ready'" in text,
            applications=applications,
            pin1_enabled=(
                False if "pin1 state: 'disabled'" in text
                else True if "pin1 state: 'enabled" in text
                else None
            ),
        )

    def open_logical_channel(self, aid: str) -> int:
        self._require_card_io()
        aid_hex = _hex(aid, "AID")
        result = self._run(f"--uim-open-logical-channel={self.slot},{aid_hex}")
        if result.returncode:
            raise RuntimeError("logical channel open failed")
        match = re.search(r"channel(?: id)?:\s*'?([0-9]+)'?", result.stdout, re.I)
        if not match:
            raise RuntimeError("logical channel ID missing")
        self.channel = int(match.group(1))
        return self.channel

    def close_logical_channel(self) -> None:
        self._require_card_io()
        if self.channel is None:
            return
        result = self._run(f"--uim-close-logical-channel={self.slot},{self.channel}")
        if result.returncode:
            raise RuntimeError("logical channel close failed")
        self.channel = None

    def send_apdu(self, apdu: bytes) -> tuple[bytes, int, int]:
        self._require_card_io()
        if self.channel is None:
            raise RuntimeError("logical channel is not open")
        if not isinstance(apdu, bytes) or not apdu:
            raise ValueError("APDU must be non-empty bytes")
        result = self._run(
            f"--uim-send-apdu={self.slot},{self.channel},{apdu.hex().upper()}"
        )
        if result.returncode:
            raise RuntimeError("APDU transport failed")
        sw1 = re.search(r"SW1:\s*'?([0-9]+)'?", result.stdout, re.I)
        sw2 = re.search(r"SW2:\s*'?([0-9]+)'?", result.stdout, re.I)
        response = re.search(r"Response:\s*'([0-9A-Fa-f: ]*)'", result.stdout, re.I)
        if not sw1 or not sw2 or not response:
            raise RuntimeError("APDU response format unsupported")
        return bytes.fromhex(_hex(response.group(1), "response")), int(sw1.group(1)), int(sw2.group(1))

    def authenticate_aka(self, rand: bytes, autn: bytes) -> AkaResult:
        self.validate_challenge(rand, autn)
        self._require_card_io()
        if self.channel is None:
            return AkaResult(AkaStatus.SIM_ERROR, detail="logical channel is not open")
        body = bytes((len(rand),)) + rand + bytes((len(autn),)) + autn
        apdu = bytes((0x00, 0x88, 0x00, 0x81, len(body))) + body
        try:
            payload, sw1, sw2 = self.send_apdu(apdu)
            return parse_usim_auth_response(payload, sw1, sw2)
        except subprocess.TimeoutExpired:
            return AkaResult(AkaStatus.TIMEOUT, detail="qmi timeout")
        except (RuntimeError, ValueError) as exc:
            return AkaResult(AkaStatus.SIM_ERROR, detail=str(exc))
