import unittest
from sdpro import SdClock


class SdTests(unittest.TestCase):
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
