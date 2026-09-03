import importlib.util
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend" / "openstick-sms-web.py"
SPEC = importlib.util.spec_from_file_location("openstick_backend_build", BACKEND)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BuildInfoTests(unittest.TestCase):
    def test_file_build_info_reports_real_hash(self):
        payload = b"openstick-build-test\n"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "component.bin"
            path.write_bytes(payload)
            info = MODULE.file_build_info(path, "test-version")
        self.assertTrue(info["available"])
        self.assertEqual(info["version"], "test-version")
        self.assertEqual(info["size"], len(payload))
        self.assertEqual(info["sha256"], sha256(payload).hexdigest())

    def test_missing_component_is_explicit(self):
        info = MODULE.file_build_info(ROOT / "missing-component", "missing")
        self.assertFalse(info["available"])
        self.assertEqual(info["sha256"], "")

    def test_release_version_matches_version_file(self):
        expected = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(MODULE.CONTROL_VERSION, expected)


if __name__ == "__main__":
    unittest.main()

