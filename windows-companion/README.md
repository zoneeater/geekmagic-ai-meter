# Windows AI usage meter

Standalone mode added to the GeekMagic HACS fork. **No Home Assistant and no firmware flashing.** It follows the factory image-upload and display-selection protocol inspected in upstream `profiles.py`; the transport here is independent and intentionally restricted to factory SmallTV-Ultra until other profiles are tested.

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

The clock and PC must already be reachable on the same network. These scripts never change PC wireless settings, scan the LAN, flash firmware, erase partitions, or call firmware update endpoints. NMMiner is not supported. Pro and SD_PRO support remains in the upstream HA integration and has not yet been ported to this standalone mode.

Checks: `uv run python -m unittest discover -p 'test_*.py'`. For the independent Windows project hooks, run from the repository root: `uv run --project windows-companion pre-commit run --all-files --config windows-companion/.pre-commit-config.yaml`. These cover the standalone addition; the unchanged upstream Home Assistant test suite is separate. Live clock validation remains pending until its actual address/model is supplied.
