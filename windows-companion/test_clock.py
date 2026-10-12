import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import stock_clock


class FakeClock:
    def __init__(self, model="SmallTV-Ultra", fail=False):
        self.model = model
        self.calls = []
        self.fail = fail

    def read(self, path):
        return {
            "/v.json": {"m": self.model, "v": "Ultra-V9.0.51"},
            "/app.json": {"theme": 1},
            "/album.json": {"autoplay": 1, "i_i": 10},
            "/theme_list.json": {"sw_en": 1, "sw_i": 30, "list": "1,0,1"},
        }[path]

    def request(self, path, *args):
        self.calls.append(path)

    def set(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail and "img" in kwargs:
            raise RuntimeError("Synthetic display failure")


class StockTests(unittest.TestCase):
    def test_model_mismatch_has_no_writes(self):
        clock = FakeClock("SmallTV-PRO")
        with self.assertRaises(ValueError):
            stock_clock.test_clock(clock, Path("unused"))
        self.assertEqual(clock.calls, [])

    def test_display_failure_restores_every_changed_setting(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "test.jpg"
            image.write_bytes(b"\xff\xd8demo")
            clock = FakeClock(fail=True)
            with patch.object(
                stock_clock, "__file__", str(Path(folder) / "stock_clock.py")
            ):
                with self.assertRaises(RuntimeError):
                    stock_clock.test_clock(clock, image, hold=0)
            self.assertEqual(
                clock.calls[-3:],
                [
                    {"i_i": 10, "autoplay": 1},
                    {"theme": 1},
                    {"sw_en": 1, "sw_i": 30, "theme_list": "1,0,1"},
                ],
            )

    def test_addresses_and_firmware_endpoint_rejected(self):
        for address in (
            "https://192.168.4.1",
            "127.0.0.1",
            "8.8.8.8",
            "http://192.168.4.1/update",
        ):
            with self.assertRaises(ValueError):
                stock_clock.Clock(address)
        with self.assertRaises(ValueError):
            stock_clock.Clock("192.168.4.1").request("/update")


if __name__ == "__main__":
    unittest.main()
