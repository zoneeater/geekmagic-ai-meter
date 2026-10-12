"""SD PRO image adapter, matching upstream profiles.SdProProfile."""

import hashlib
import json
import time
import urllib.parse
import uuid
from pathlib import Path

from stock_clock import Clock


class SdClock(Clock):
    def allowed_path(self, path):
        parsed = urllib.parse.urlsplit(path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path in ("/config", "/theme/list", "/photo/list", "/photo/upload"):
            return not parsed.query
        if parsed.path == "/api/set":
            return (
                set(query) == {"key", "value"}
                and query["key"] == ["theme"]
                and len(query["value"]) == 1
                and query["value"][0] in [str(i) for i in range(7)]
            )
        if parsed.path in ("/photo/toggle", "/theme/toggle"):
            field = "name" if parsed.path == "/photo/toggle" else "id"
            return (
                set(query) == {field, "state"}
                and len(query[field]) == 1
                and query["state"] in (["0"], ["1"])
            )
        if parsed.path in ("/photo/interval", "/theme/interval"):
            return (
                set(query) == {"val"}
                and len(query["val"]) == 1
                and query["val"][0].isdigit()
            )
        return False

    def change(self, path, **values):
        response = self.request(path + "?" + urllib.parse.urlencode(values))
        if response.strip().upper() == b"FAIL":
            raise RuntimeError("Clock rejected a display setting")

    def capture(self):
        # /config can contain credentials; retain only the display mode.
        theme = self.read("/config").get("theme")
        themes = self.read("/theme/list")
        photos = self.read("/photo/list")
        if type(theme) is not int or theme not in range(7):
            raise ValueError("Unrecognized SD PRO current mode")
        if (
            type(themes.get("interval")) is not int
            or themes["interval"] < 0
            or type(photos.get("interval")) is not int
            or photos["interval"] < 1
        ):
            raise ValueError("Unrecognized slideshow intervals")
        items = themes.get("themes")
        files = photos.get("files")
        if (
            not isinstance(items, list)
            or len(items) != 7
            or {t.get("id") for t in items} != set(range(7))
            or any(type(t.get("enabled")) is not bool for t in items)
        ):
            raise ValueError("Unrecognized SD PRO theme list")
        if not isinstance(files, list) or any(
            not isinstance(f.get("name"), str) or type(f.get("enabled")) is not bool
            for f in files
        ):
            raise ValueError("Unrecognized SD PRO photo list")
        state = {
            "profile": "sd-pro",
            "theme": theme,
            "themeInterval": themes["interval"],
            "photoInterval": photos["interval"],
            "themes": [{"id": t["id"], "enabled": t["enabled"]} for t in items],
            "photos": [{"name": f["name"], "enabled": f["enabled"]} for f in files],
        }
        Path(__file__).with_name("sd-restore.local.json").write_text(
            json.dumps(state), encoding="utf8"
        )
        return state

    def upload(self, data, filename):
        if not data.startswith(b"\xff\xd8") or len(data) > 50000:
            raise ValueError("Expected a small JPEG")
        boundary = "----sdmeter" + uuid.uuid4().hex
        body = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: image/jpeg\r\n\r\n'.encode()
            + data
            + f"\r\n--{boundary}--\r\n".encode()
        )
        response = self.request(
            "/photo/upload",
            body,
            {"Content-Type": "multipart/form-data; boundary=" + boundary},
        )
        if response.strip().upper() == b"FAIL":
            raise RuntimeError("Image upload rejected")

    def show(self, filename):
        photos = self.read("/photo/list")["files"]
        if not any(f.get("name") == filename for f in photos):
            raise RuntimeError("Uploaded image is not in photo list")
        self.change("/photo/toggle", name=filename, state=1)
        for photo in photos:
            if photo["name"] != filename:
                self.change("/photo/toggle", name=photo["name"], state=0)
        # This firmware rejects disabling the last active theme.
        self.change("/theme/toggle", id=2, state=1)
        for theme in range(7):
            if theme != 2:
                self.change("/theme/toggle", id=theme, state=0)
        self.change("/photo/interval", val=1)
        self.change("/api/set", key="theme", value=2)

    def restore(self, state):
        actions = [
            ("/photo/toggle", {"name": p["name"], "state": int(p["enabled"])})
            for p in state["photos"]
        ]
        if state.get("managed"):
            actions.append(("/photo/toggle", {"name": state["managed"], "state": 0}))
        actions += [
            ("/theme/toggle", {"id": t["id"], "state": int(t["enabled"])})
            for t in sorted(state["themes"], key=lambda t: not t["enabled"])
        ]
        actions += [
            ("/photo/interval", {"val": state["photoInterval"]}),
            ("/theme/interval", {"val": state["themeInterval"]}),
            ("/api/set", {"key": "theme", "value": state["theme"]}),
        ]
        failures = 0
        for path, values in actions:
            try:
                self.change(path, **values)
            except Exception:
                failures += 1
        if failures:
            raise RuntimeError(
                "Display restoration incomplete; use --profile sd-pro --restore when reachable"
            )


def run(clock, data_reader, continuous=False):
    state = clock.capture()
    state["managed"] = "ai-meter-" + uuid.uuid4().hex[:12] + ".jpg"
    Path(__file__).with_name("sd-restore.local.json").write_text(
        json.dumps(state), encoding="utf8"
    )
    digest = None
    uploaded = False
    try:
        while True:
            data = data_reader()
            current = hashlib.sha256(data).hexdigest()
            if current != digest:
                clock.upload(data, state["managed"])
                uploaded = True
                digest = current
            clock.show(state["managed"])
            print("SD PRO image selected.", flush=True)
            time.sleep(120 if continuous else 15)
            if not continuous:
                break
    finally:
        if not uploaded:
            state.pop("managed", None)
        clock.restore(state)
        print("Original SD PRO display settings restored.", flush=True)
