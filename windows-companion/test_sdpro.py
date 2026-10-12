import unittest
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch
import sdpro
from sdpro import SdClock


class SdTests(unittest.TestCase):
    def test_graceful_stop_restores_display_without_waiting(self):
        class FakeClock:
            def capture(self):
                return {"theme": 0}

            def upload(self, data, filename):
                self.filename = filename

            def read(self, path):
                return {"theme": 0} if path == "/config" else {"files": []}

            def show(self, filename):
                self.shown = filename

            def restore(self, state):
                self.restored = state["theme"]

        clock = FakeClock()
        stop = threading.Event()
        stop.set()
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(sdpro, "__file__", str(Path(folder) / "sdpro.py")):
                sdpro.run(clock, lambda: b"jpeg fixture", continuous=True, stop=stop)
        self.assertEqual(clock.restored, 0)
        self.assertEqual(clock.shown, clock.filename)

    def test_enable_photo_theme_before_disabling_current(self):
        clock = SdClock("192.168.0.70")
        clock.read = lambda path: {
            "files": [{"name": "old.gif"}, {"name": "meter.jpg"}]
        }
        changes = []
        clock.change = lambda path, **values: changes.append((path, values))
        clock.show("meter.jpg")
        themes = [values for path, values in changes if path == "/theme/toggle"]
        self.assertEqual(themes[0], {"id": 2, "state": 1})
        self.assertEqual(
            changes[0], ("/photo/toggle", {"name": "meter.jpg", "state": 1})
        )

    def test_only_display_endpoints_allowed(self):
        clock = SdClock("192.168.0.70")
        for path in (
            "/update",
            "/photo/delete?name=x",
            "/connect",
            "/api/set?key=ssid&value=x",
            "/api/set?key=password&value=x",
        ):
            self.assertFalse(clock.allowed_path(path))
        self.assertTrue(clock.allowed_path("/api/set?key=theme&value=2"))
        self.assertTrue(clock.allowed_path("/photo/upload"))

    def test_restore_continues_after_failure(self):
        clock = SdClock("192.168.0.70")
        calls = []

        def change(path, **values):
            calls.append((path, values))
            if path == "/photo/toggle":
                raise RuntimeError("synthetic")

        clock.change = change
        state = {
            "photos": [{"name": "old.gif", "enabled": True}],
            "themes": [{"id": 0, "enabled": True}],
            "photoInterval": 4,
            "themeInterval": 10,
            "theme": 0,
        }
        with self.assertRaises(RuntimeError):
            clock.restore(state)
        self.assertEqual(calls[-1], ("/api/set", {"key": "theme", "value": 0}))


if __name__ == "__main__":
    unittest.main()
