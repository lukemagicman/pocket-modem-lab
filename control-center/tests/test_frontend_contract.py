import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "frontend" / "index.html"


class IdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, _tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])


class FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = HTML_PATH.read_text(encoding="utf-8")
        cls.parser = IdParser()
        cls.parser.feed(cls.html)

    def test_ids_are_unique(self):
        duplicates = [name for name, count in Counter(self.parser.ids).items() if count > 1]
        self.assertEqual(duplicates, [])

    def test_build_information_elements_exist(self):
        required = {
            "diagRelease",
            "diagWebuiBuild",
            "diagBackendBuild",
            "diagUplinkBuild",
            "systemUiBuild",
            "systemBackendBuild",
            "systemUplinkBuild",
        }
        self.assertTrue(required.issubset(set(self.parser.ids)))

    def test_existing_business_endpoints_remain_referenced(self):
        for endpoint in (
            "/api/messages",
            "/api/contacts",
            "/api/health",
            "/api/diagnostic-download",
            "/api/wifi",
        ):
            self.assertIn(endpoint, self.html)

    def test_esim_writes_confirm_and_send_admin_credentials(self):
        self.assertIn("actionConfirm('下载 eSIM Profile'", self.html)
        self.assertIn("authConfirm('验证管理员身份','下载操作会写入 eUICC", self.html)
        self.assertIn("JSON.stringify({activation_code,confirmation_code,username:'admin',password})", self.html)
        self.assertIn("eSIM Profile 操作会写入 eUICC", self.html)
        self.assertIn("JSON.stringify({action,profile_id:p.profile_id,username:'admin',password})", self.html)


if __name__ == "__main__":
    unittest.main()
