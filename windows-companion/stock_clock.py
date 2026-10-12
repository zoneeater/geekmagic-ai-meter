"""One image upload using factory APIs only. No firmware or Wi-Fi operations."""

import argparse
import ipaddress
import json
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Clock:
    def __init__(self, address):
        parsed = urllib.parse.urlsplit(
            address if "://" in address else "http://" + address
        )
        ip = ipaddress.ip_address(parsed.hostname or "")
        if (
            not ip.is_private
            or ip.is_loopback
            or ip.is_unspecified
            or parsed.scheme != "http"
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise ValueError(
                "Use the clock's private LAN IP address, without a page path."
            )
        self.base = "http://" + parsed.netloc
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect()
        )

    def allowed_path(self, path):
        return path in (
            "/v.json",
            "/app.json",
            "/album.json",
            "/theme_list.json",
        ) or path.startswith(("/set?", "/doUpload?dir=", "/image/"))

    def request(self, path, data=None, headers=None):
        if not self.allowed_path(path):
            raise ValueError("Unsupported stock-display endpoint")
        request = urllib.request.Request(
            self.base + path, data=data, headers=headers or {}
        )
        with self.opener.open(request, timeout=10) as response:
            result = response.read(65537)
            if len(result) > 65536:
                raise ValueError("Unexpected response size")
            return result

    def read(self, path):
        return json.loads(self.request(path))

    def set(self, **values):
        self.request("/set?" + urllib.parse.urlencode(values))


def test_clock(clock, image, hold=15):
    version = clock.read("/v.json")
    if version.get("m") != "SmallTV-Ultra" or not str(version.get("v", "")).startswith(
        "Ultra-V"
    ):
        raise ValueError("Clock is not identified as factory SmallTV-Ultra firmware")
    app, album, rotation = (
        clock.read(path) for path in ("/app.json", "/album.json", "/theme_list.json")
    )
    # Fail before changes unless we can restore exactly the settings we alter.
    theme = app.get("theme")
    autoplay, interval = album.get("autoplay"), album.get("i_i")
    if not isinstance(theme, int) or theme == 3:
        raise ValueError(
            "Select the factory Weather or Clock theme first; original photo selection cannot yet be restored"
        )
    if autoplay not in (0, 1) or not isinstance(interval, int) or interval < 1:
        raise ValueError("Unrecognized album settings; no changes made")
    if (
        rotation.get("sw_en") not in (0, 1)
        or not isinstance(rotation.get("sw_i"), int)
        or not isinstance(rotation.get("list"), str)
    ):
        raise ValueError("Unrecognized theme rotation settings; no changes made")
    state = {
        "theme": theme,
        "autoplay": autoplay,
        "interval": interval,
        "rotation": {key: rotation[key] for key in ("sw_en", "sw_i", "list")},
    }
    backup = Path(__file__).with_name("restore.local.json")
    backup.write_text(json.dumps(state, indent=2), encoding="utf8")
    filename = "meter-test-" + uuid.uuid4().hex[:8] + ".jpg"
    boundary = "----smalltv" + uuid.uuid4().hex
    data = image.read_bytes()
    if len(data) > 50000 or not data.startswith(b"\xff\xd8"):
        raise ValueError("Expected the small generated JPEG")
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: image/jpeg\r\n\r\n'.encode()
        + data
        + f"\r\n--{boundary}--\r\n".encode()
    )
    clock.request(
        "/doUpload?dir=%2Fimage%2F",
        body,
        {"Content-Type": "multipart/form-data; boundary=" + boundary},
    )
    try:
        clock.set(sw_en=0, sw_i=rotation["sw_i"], theme_list=rotation["list"])
        clock.set(i_i=interval, autoplay=0)
        clock.set(theme=3)
        clock.set(img="/image/" + filename)
        print(
            "Test image selected for 15 seconds. Check the clock screen. Demo values only.",
            flush=True,
        )
        time.sleep(hold)
    finally:
        restore(clock, state)
        print(
            "Original theme, slideshow and rotation restored. Test JPEG retained in album."
        )


def restore(clock, state):
    # Try every restoration step even if one request fails.
    errors = []
    rotation = state["rotation"]
    for values in (
        {"i_i": state["interval"], "autoplay": state["autoplay"]},
        {"theme": state["theme"]},
        {
            "sw_en": rotation["sw_en"],
            "sw_i": rotation["sw_i"],
            "theme_list": rotation["list"],
        },
    ):
        try:
            clock.set(**values)
        except Exception:
            errors.append(True)
    if errors:
        raise RuntimeError(
            "Restoration incomplete. Run --restore when the clock is reachable, or restore settings on its page."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("address")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--test", action="store_true")
    mode.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    try:
        clock = Clock(args.address)
        if args.restore:
            restore(
                clock,
                json.loads(
                    Path(__file__)
                    .with_name("restore.local.json")
                    .read_text(encoding="utf8")
                ),
            )
        elif args.test:
            test_clock(clock, Path(__file__).with_name("stock-test.jpg"))
        else:
            value = clock.read("/v.json")
            print(json.dumps({key: value.get(key) for key in ("m", "v")}))
    except Exception as error:
        print("Clock test stopped:", type(error).__name__, str(error))
        raise SystemExit(1)
