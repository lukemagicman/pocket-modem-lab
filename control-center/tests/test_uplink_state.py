import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend" / "openstick-sms-web.py"
SPEC = importlib.util.spec_from_file_location("openstick_backend", BACKEND)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class UplinkStateTests(unittest.TestCase):
    def test_online_usb_transition_updates_all_levels(self):
        usb_interface = {
            "interface": "usb0",
            "state": "limited",
            "internet": None,
            "connectivity_check": "not_run",
        }
        uplinks = {
            "usb": {
                "state": "limited",
                "internet": None,
                "connectivity_check": "not_run",
                "role": "candidate",
                "reverse_ready": False,
                "interfaces": [usb_interface],
            }
        }
        transition = {
            "status": "online",
            "active": "usb",
            "checks": {"internet": True, "dns_available": True},
        }
        internet, check = MODULE.apply_transition_status(
            "usb", "usb0", uplinks, transition
        )
        self.assertIs(internet, True)
        self.assertEqual(check, "passed")
        self.assertEqual(uplinks["usb"]["state"], "online")
        self.assertEqual(uplinks["usb"]["role"], "uplink")
        self.assertTrue(uplinks["usb"]["reverse_ready"])
        self.assertEqual(usb_interface["state"], "online")

    def test_stale_transition_is_not_applied(self):
        uplinks = {"usb": {"state": "limited", "internet": None}}
        transition = {
            "status": "online",
            "active": "wifi",
            "checks": {"internet": True},
        }
        internet, check = MODULE.apply_transition_status(
            "usb", "usb0", uplinks, transition
        )
        self.assertIsNone(internet)
        self.assertEqual(check, "not_run")
        self.assertEqual(uplinks["usb"]["state"], "limited")

    def test_checking_transition_reports_running(self):
        uplinks = {"usb": {"state": "limited", "connectivity_check": "not_run"}}
        internet, check = MODULE.apply_transition_status(
            "usb", "usb0", uplinks, {"status": "checking", "active": "usb"}
        )
        self.assertIsNone(internet)
        self.assertEqual(check, "running")
        self.assertEqual(uplinks["usb"]["state"], "connecting")


if __name__ == "__main__":
    unittest.main()

