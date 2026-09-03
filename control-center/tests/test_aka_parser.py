import unittest

from vowifi.sim.models import AkaStatus, parse_usim_auth_response


class AkaParserTests(unittest.TestCase):
    def test_success_response_is_parsed_and_redacted(self):
        res = bytes.fromhex("0102030405060708")
        ck = bytes(range(16))
        ik = bytes(range(16, 32))
        payload = bytes((0xDB, len(res))) + res + bytes((len(ck),)) + ck + bytes((len(ik),)) + ik
        result = parse_usim_auth_response(payload)
        self.assertEqual(result.status, AkaStatus.SUCCESS)
        self.assertEqual(result.res, res)
        self.assertEqual(result.ck, ck)
        self.assertEqual(result.ik, ik)
        rendered = repr(result)
        self.assertNotIn(res.hex(), rendered)
        self.assertNotIn(ck.hex(), rendered)
        self.assertEqual(result.public_summary()["lengths"], {"res": 8, "ck": 16, "ik": 16})

    def test_sync_failure(self):
        auts = bytes(range(14))
        result = parse_usim_auth_response(bytes((0xDC, len(auts))) + auts)
        self.assertEqual(result.status, AkaStatus.SYNC_FAILURE)
        self.assertEqual(result.auts, auts)
        self.assertNotIn(auts.hex(), repr(result))

    def test_mac_failure_status_word(self):
        result = parse_usim_auth_response(b"", 0x98, 0x62)
        self.assertEqual(result.status, AkaStatus.MAC_FAILURE)

    def test_truncated_success_is_sim_error(self):
        result = parse_usim_auth_response(bytes.fromhex("DB08AABB"))
        self.assertEqual(result.status, AkaStatus.SIM_ERROR)
        self.assertIn("truncated", result.detail)

    def test_unknown_tag_is_unsupported(self):
        result = parse_usim_auth_response(bytes.fromhex("AA00"))
        self.assertEqual(result.status, AkaStatus.UNSUPPORTED)


if __name__ == "__main__":
    unittest.main()
