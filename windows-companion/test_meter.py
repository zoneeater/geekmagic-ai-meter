import unittest
from datetime import datetime, timezone
from PIL import Image
import io
from meter import reading, render


class MeterTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2030, 1, 1, tzinfo=timezone.utc).timestamp()
        self.value = {
            "version": 1,
            "source": "codex",
            "updatedAt": "2030-01-01T00:00:00Z",
            "primary": {"remainingPercent": 0},
            "secondary": {"remainingPercent": 100},
        }

    def test_zero_is_valid_and_missing_not_full(self):
        result = reading(self.value, "codex", self.now)
        self.assertEqual((result["primary"], result["secondary"]), (0, 100))
        self.assertIsNone(reading(None, "claude", self.now)["primary"])

    def test_stale_wrong_provider_and_bad_values(self):
        self.assertEqual(
            reading(self.value, "codex", self.now + 301)["status"], "Stale"
        )
        self.assertIsNone(reading(self.value, "gemini", self.now)["primary"])
        for bad in (True, float("nan"), 101, -1, "50"):
            self.value["primary"]["remainingPercent"] = bad
            self.assertIsNone(reading(self.value, "codex", self.now)["primary"])

    def test_jpeg_is_small_stable_and_240_square(self):
        values = {
            key: reading(None, key, self.now) for key in ("codex", "claude", "gemini")
        }
        data = render(values)
        self.assertEqual(Image.open(io.BytesIO(data)).size, (240, 240))
        self.assertLess(len(data), 50000)
        self.assertEqual(data, render(values))


if __name__ == "__main__":
    unittest.main()
