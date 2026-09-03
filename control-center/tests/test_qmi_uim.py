import subprocess
import unittest

from vowifi.sim.mock import MockSimBackend
from vowifi.sim.models import AkaResult, AkaStatus
from vowifi.sim.qmi_uim import QmiUimBackend


class FakeRunner:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode
        self.calls = []

    def __call__(self, args, timeout):
        self.calls.append((list(args), timeout))
        return subprocess.CompletedProcess(args, self.returncode, self.stdout, "")


class QmiUimTests(unittest.TestCase):
    def test_card_status_is_read_only_and_parameterized(self):
        runner = FakeRunner(
            "Card state: 'present'\nApplication type:  'usim (2)'\n"
            "Application state: 'ready'\nPIN1 state: 'disabled'\n"
        )
        backend = QmiUimBackend(runner=runner)
        status = backend.card_status()
        self.assertTrue(status.present)
        self.assertTrue(status.ready)
        self.assertEqual(status.applications, ("usim",))
        self.assertFalse(status.pin1_enabled)
        self.assertEqual(runner.calls[0][0][-1], "--uim-get-card-status")

    def test_card_io_is_denied_by_default(self):
        backend = QmiUimBackend(runner=FakeRunner())
        with self.assertRaises(PermissionError):
            backend.open_logical_channel("A0000000871002")
        with self.assertRaises(PermissionError):
            backend.authenticate_aka(bytes(16), bytes(16))

    def test_mock_stores_lengths_not_challenge(self):
        expected = AkaResult(AkaStatus.MAC_FAILURE)
        backend = MockSimBackend(expected)
        result = backend.authenticate_aka(bytes(range(16)), bytes(range(16, 32)))
        self.assertIs(result, expected)
        self.assertEqual(backend.last_request_lengths, (16, 16))
        self.assertFalse(hasattr(backend, "last_rand"))

    def test_challenge_length_is_validated(self):
        backend = MockSimBackend()
        with self.assertRaises(ValueError):
            backend.authenticate_aka(b"short", bytes(16))


if __name__ == "__main__":
    unittest.main()
