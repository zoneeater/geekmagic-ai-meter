"""Render normalized PC snapshots and display them using stock GeekMagic APIs."""

import argparse
import hashlib
import io
import json
import math
import time
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from stock_clock import Clock, restore, test_clock

PROVIDERS = ("codex", "claude", "gemini")


def window(value):
    if not isinstance(value, dict):
        return None
    percent = value.get("remainingPercent")
    if (
        isinstance(percent, bool)
        or not isinstance(percent, (int, float))
        or not math.isfinite(percent)
        or not 0 <= percent <= 100
    ):
        return None
    return round(percent)


def reset_label(value, now, weekly=False):
    reset = value.get("resetsAt") if isinstance(value, dict) else None
    if (
        isinstance(reset, bool)
        or not isinstance(reset, (int, float))
        or not math.isfinite(reset)
        or not now < reset < now + 366 * 86400
    ):
        return None
    stamp = datetime.fromtimestamp(reset)
    clock = stamp.strftime("%I:%M").lstrip("0") + stamp.strftime("%p")[0].lower()
    day = (
        stamp.strftime("%a") + " "
        if weekly or stamp.date() != datetime.fromtimestamp(now).date()
        else ""
    )
    return day + clock


def reading(value, source, now):
    unavailable = {"primary": None, "secondary": None, "status": "Unavailable"}
    if (
        not isinstance(value, dict)
        or value.get("source") != source
        or value.get("version") != 1
    ):
        return unavailable
    try:
        stamp = datetime.fromisoformat(value["updatedAt"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return unavailable
        age = now - stamp.timestamp()
    except (KeyError, ValueError, TypeError, AttributeError):
        return unavailable
    if not -60 <= age <= 300:
        return {**unavailable, "status": "Stale"}
    warning = value.get("limitWarning")
    if source == "claude" and isinstance(warning, dict):
        state = warning.get("state")
        reset = warning.get("resetsAt")
        if (
            isinstance(reset, bool)
            or not isinstance(reset, (int, float))
            or not math.isfinite(reset)
        ):
            reset = None
        expired = reset is not None and reset <= now
        label = {"limited": "LIMIT REACHED", "near-limit": "NEAR LIMIT"}.get(
            state, "NO WARNING SEEN"
        )
        detail = "USE COMPANION"
        if expired:
            label, detail = "CHECK CLAUDE", "RESET TIME PASSED"
        elif reset is not None:
            minutes = math.ceil((reset - now) / 60)
            detail = f"RESET IN {minutes // 60}h {minutes % 60}m"
        elif state == "limited":
            detail = "RESET UNKNOWN"
        return {
            **unavailable,
            "status": "Warning",
            "warningLabel": label,
            "warningDetail": detail,
            "warningReset": reset_label({"resetsAt": reset}, now),
        }
    return {
        "primary": window(value.get("primary")),
        "secondary": window(value.get("secondary")),
        "primaryReset": reset_label(value.get("primary"), now),
        "secondaryReset": reset_label(value.get("secondary"), now, weekly=True),
        "status": "Remaining",
    }


def load_readings(directory, now=None):
    now = time.time() if now is None else now
    result = {}
    for source in PROVIDERS:
        path = directory / (
            "usage.local.json" if source == "codex" else source + ".local.json"
        )
        try:
            if path.stat().st_size > 4096:
                raise ValueError("Snapshot too large")
            value = json.loads(path.read_text(encoding="utf8"))
        except (OSError, ValueError):
            value = None
        result[source] = reading(value, source, now)
    return result


def render(readings):
    image = Image.new("RGB", (240, 240), "#000000")
    draw = ImageDraw.Draw(image)
    font_path = Path("C:/Windows/Fonts/segoeuib.ttf")

    def font(size):
        return (
            ImageFont.truetype(str(font_path), size)
            if font_path.exists()
            else ImageFont.load_default(size=size)
        )

    draw.text((12, 5), "REMAINING", font=font(17), fill="#ffffff", anchor="lt")
    for source, y, color in zip(
        PROVIDERS, (29, 99, 169), ("#65e5ac", "#ffc499", "#99caff")
    ):
        value = readings[source]
        primary, secondary = value["primary"], value["secondary"]
        draw.text((12, y + 5), source.upper(), font=font(20), fill=color, anchor="lt")
        if value["status"] == "Warning":
            draw.text(
                (12, y + 29),
                value["warningLabel"],
                font=font(20),
                fill="white",
                anchor="lt",
            )
            draw.text(
                (12, y + 52),
                value["warningDetail"],
                font=font(14),
                fill="#d2d9e1",
                anchor="lt",
            )
            if value.get("warningReset"):
                draw.text(
                    (228, y + 53),
                    value["warningReset"],
                    font=font(11),
                    fill="#aebac5",
                    anchor="rt",
                )
            continue
        label = "--" if primary is None else f"{primary}%"
        draw.text((230, y), label, font=font(40), fill="white", anchor="rt")
        detail = f"WEEK {secondary}%" if secondary is not None else "WEEK --"
        draw.text((12, y + 49), detail, font=font(18), fill="#ffffff", anchor="lt")
        if primary is None:
            status = "STALE" if value["status"] == "Stale" else "NO DATA"
            draw.text((228, y + 51), status, font=font(14), fill="#d2d9e1", anchor="rt")
        else:
            for reset, offset, prefix in (
                (value.get("primaryReset"), 47, "5H "),
                (value.get("secondaryReset"), 60, "WK "),
            ):
                if reset:
                    draw.text(
                        (228, y + offset),
                        prefix + reset,
                        font=font(11),
                        fill="#aebac5",
                        anchor="rt",
                    )
        draw.rounded_rectangle((12, y + 35, 228, y + 43), radius=3, fill="#333333")
        if primary is not None and primary > 0:
            draw.rounded_rectangle(
                (12, y + 35, 12 + round(216 * primary / 100), y + 43),
                radius=3,
                fill=color,
            )
    data = io.BytesIO()
    image.save(data, "JPEG", quality=88, optimize=True)
    return data.getvalue()


def capture(clock):
    version = clock.read("/v.json")
    if version.get("m") != "SmallTV-Ultra" or not str(version.get("v", "")).startswith(
        "Ultra-V"
    ):
        raise ValueError(
            "Only verified factory SmallTV-Ultra profile is enabled; other models need an adapter"
        )
    app, album, rotation = (
        clock.read(path) for path in ("/app.json", "/album.json", "/theme_list.json")
    )
    if (
        type(app.get("theme")) is not int
        or app["theme"] == 3
        or album.get("autoplay") not in (0, 1)
        or type(album.get("i_i")) is not int
        or album["i_i"] < 1
    ):
        raise ValueError(
            "Select a stock Clock/Weather theme; unrecognized state prevents changes"
        )
    if (
        rotation.get("sw_en") not in (0, 1)
        or type(rotation.get("sw_i")) is not int
        or not isinstance(rotation.get("list"), str)
    ):
        raise ValueError("Unrecognized rotation state prevents changes")
    state = {
        "theme": app["theme"],
        "autoplay": album["autoplay"],
        "interval": album["i_i"],
        "rotation": {key: rotation[key] for key in ("sw_en", "sw_i", "list")},
    }
    Path(__file__).with_name("restore.local.json").write_text(
        json.dumps(state), encoding="utf8"
    )
    return state


def watch(clock, directory):
    state = capture(clock)
    fingerprint = None
    filename = "ai-meter-" + uuid.uuid4().hex[:12] + ".jpg"
    try:
        clock.set(
            sw_en=0,
            sw_i=state["rotation"]["sw_i"],
            theme_list=state["rotation"]["list"],
        )
        clock.set(i_i=state["interval"], autoplay=0)
        while True:
            data = render(load_readings(directory))
            digest = hashlib.sha256(data).hexdigest()
            if digest != fingerprint:
                # One unique filename per session; never overwrite or delete user images.
                boundary = "----aimeter" + uuid.uuid4().hex
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
                fingerprint = digest
                print("Meter image updated.", flush=True)
            # Reassert selection after a clock reboot without uploading unchanged pixels.
            clock.set(theme=3)
            clock.set(img="/image/" + filename)
            time.sleep(120)
    finally:
        restore(clock, state)
        print("Previous clock display settings restored.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state-dir",
        type=Path,
        required=True,
        help="Existing Windows companion meter snapshot folder",
    )
    parser.add_argument("--output", type=Path, default=Path("preview.jpg"))
    parser.add_argument("--profile", choices=("ultra", "sd-pro"), default="ultra")
    parser.add_argument(
        "--stop-on-stdin",
        action="store_true",
        help="Tray app may send stop on stdin for graceful restoration",
    )
    parser.add_argument(
        "--host", help="Clock private IP; never changes wireless settings"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--test", action="store_true", help="One 15-second display test, then restore"
    )
    mode.add_argument(
        "--watch",
        action="store_true",
        help="Upload changed readings every two minutes; Ctrl+C restores",
    )
    mode.add_argument(
        "--restore",
        action="store_true",
        help="Restore saved display settings after interrupted run",
    )
    args = parser.parse_args()
    if (args.test or args.watch or args.restore) and not args.host:
        parser.error("Device actions require --host")
    if args.profile == "sd-pro" and (args.test or args.watch or args.restore):
        from sdpro import SdClock, run

        clock = SdClock(args.host)
        if args.restore:
            clock.restore(
                json.loads(
                    Path(__file__)
                    .with_name("sd-restore.local.json")
                    .read_text(encoding="utf8")
                )
            )
        else:
            stop = None
            if args.stop_on_stdin:
                import sys
                import threading

                stop = threading.Event()

                def listen():
                    for line in sys.stdin:
                        if line.strip() == "stop":
                            break
                    stop.set()

                threading.Thread(target=listen, daemon=True).start()
            run(
                clock,
                lambda: render(load_readings(args.state_dir)),
                continuous=args.watch,
                stop=stop,
            )
        return
    if args.restore:
        restore(
            Clock(args.host),
            json.loads(
                Path(__file__)
                .with_name("restore.local.json")
                .read_text(encoding="utf8")
            ),
        )
        return
    args.output.write_bytes(render(load_readings(args.state_dir)))
    if args.test:
        test_clock(Clock(args.host), args.output)
    elif args.watch:
        watch(Clock(args.host), args.state_dir)
    else:
        print("Preview saved. No device contacted.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

