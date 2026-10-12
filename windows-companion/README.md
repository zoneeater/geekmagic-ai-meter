# Windows AI usage meter

Standalone mode added to the GeekMagic HACS fork. **No Home Assistant and no firmware flashing.** It follows the stock Ultra and SD PRO photo-upload/display protocols inspected in upstream `profiles.py`; the standalone transport is independent. Select `--profile sd-pro` for the Russian SD PRO-style management page. Never use the factory Ultra adapter on that interface.

Existing Windows tray companion collects Codex, Claude and Gemini snapshots. This app reads only those normalized local JSON files; it does not read account cookies, passwords or tokens. Codex is the Codex allowance, not an exact ChatGPT token balance. Website readings remain dependent on the separate companion's sign-in and validated adapters. Missing, malformed, wrong-provider or older-than-five-minute readings display `--`.

Install [uv](https://docs.astral.sh/uv/) and open PowerShell here:

```powershell
uv sync
uv run python meter.py --state-dir 'C:\path\to\smalltv-custom\meter'
```

This saves `preview.jpg` without contacting any device. For a first reversible display test, supply the actual clock address:

```powershell
uv run python meter.py --state-dir 'C:\path\to\smalltv-custom\meter' --host 192.168.1.50 --test
```

It verifies the factory Ultra profile, saves the prior Clock/Weather theme and slideshow/rotation settings in ignored `restore.local.json`, uploads one image, shows it for 15 seconds and restores the settings. No pictures are deleted. Unknown state fails before changes. Test images remain in the album. Restoration requires the clock to stay reachable.

After the visual test works, use `--watch` instead of `--test`. It uploads only changed rendered pixels, at most once every two minutes, to one unique managed filename per session. Ctrl+C restores the original display. If the process is forcibly stopped, `--restore` with the same address restores the saved settings. Start from a non-Photo theme to allow restoration. Do not run multiple display writers concurrently. Images from previous sessions remain in the album and can be removed manually. Automatic restart/reconnection is not configured.

## SD PRO interface

Use `--profile sd-pro --test` or `--profile sd-pro --watch` with the clock address. The adapter reads `/config` only for the display mode and retains no Wi-Fi credentials or API keys. It uses `/photo/upload`, enables its unique image, enables Photo theme before disabling other themes, and temporarily isolates the slideshow. Original photo enabled flags, theme flags, intervals and mode are saved to ignored `sd-restore.local.json` and restored afterward. Existing photos are never overwritten or deleted. New test images remain disabled in the album after restoration. `--profile sd-pro --restore` restores after an interrupted process.

Live API test on October 11, 2026: photo upload and selection completed and original settings were restored. An initial request failed because disabling the last enabled theme is rejected; corrected by enabling Photo first, with a regression test. Physical screen rendering still requires user confirmation. The photo-theme controls are firmware-specific; this is not a universal GeekMagic adapter.

The clock and PC must already be reachable on the same network. These scripts never change PC wireless settings, scan the LAN, flash firmware, erase partitions, or call firmware update endpoints. NMMiner is not supported. Pro support remains in the upstream HA integration and has not yet been ported to this standalone mode.

Checks: `uv run python -m unittest discover -p 'test_*.py'`. For the independent Windows project hooks, run from the repository root: `uv run --project windows-companion pre-commit run --all-files --config windows-companion/.pre-commit-config.yaml`. These cover the standalone addition; the unchanged upstream Home Assistant test suite is separate. Live clock validation remains pending until its actual address/model is supplied.
