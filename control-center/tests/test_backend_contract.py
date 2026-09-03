import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_SOURCE = (ROOT / "backend" / "openstick-sms-web.py").read_text(
    encoding="utf-8"
)


class BackendContractTests(unittest.TestCase):
    def test_core_get_endpoints_remain_available(self):
        for endpoint in (
            "/api/health",
            "/api/build",
            "/api/diagnostic-download",
            "/api/uplink",
            "/api/wifi",
            "/api/messages",
            "/api/contacts",
        ):
            self.assertIn(endpoint, BACKEND_SOURCE)

    def test_build_information_is_in_health_and_diagnostics(self):
        self.assertGreaterEqual(BACKEND_SOURCE.count("'build': build_details()"), 2)

    def test_esim_writes_require_admin_authentication(self):
        protected_section = BACKEND_SOURCE.split("protected = self.path in (", 1)[1].split(")", 1)[0]
        self.assertIn("'/api/esim-action'", protected_section)
        self.assertIn("'/api/esim-download'", protected_section)

    def test_esim_download_rejects_cellular_uplink(self):
        self.assertIn("if not network['safe_for_download']:", BACKEND_SOURCE)
        self.assertIn("当前互联网出口是蜂窝网络", BACKEND_SOURCE)

    def test_esim_usb_download_requires_verified_proxy(self):
        self.assertIn("proxy_url = esim_usb_proxy_url() if interface == 'usb0' else ''", BACKEND_SOURCE)
        self.assertIn("safe_for_download = bool(proxy_url)", BACKEND_SOURCE)
        self.assertIn("'HTTPS_PROXY': proxy_url", BACKEND_SOURCE)


if __name__ == "__main__":
    unittest.main()
