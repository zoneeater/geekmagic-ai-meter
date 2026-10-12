# Windows AI usage meter

Standalone companion display for the stock GeekMagic SD PRO-style photo API. No Home Assistant is required. The working display uses three full-screen pages in **Codex → Gemini → Claude** order, with the clock's built-in slideshow advancing every **10 seconds**.

Codex and Gemini show large remaining percentages, remaining bars, weekly readings and small local reset-time labels where supplied. Codex reports its Codex allowance, not an exact ChatGPT token balance. Claude Free uses observed limit warnings instead of percentage polling: **No warning seen**, **Near limit**, or **Limit reached**, with a reset countdown/time when the warning provides one. No warning seen does not mean full allowance. Use Claude in the Windows tray companion's own Claude window; other browsers and mobile apps are not monitored.

The renderer reads normalized local snapshots from the separate Windows companion. It does not read account credentials or conversations. Missing or stale percentage readings remain unavailable. The companion checks readings every two minutes; the clock cycles its three stored JPEGs independently, avoiding uploads on each transition. Only changed images are uploaded.

## Run the SD PRO display

Install [uv](https://docs.astral.sh/uv/) and open PowerShell in `windows-companion`:

```powershell
uv sync
uv run python meter.py --state-dir 'C:\path\to\smalltv-custom\meter'
```

This creates a local combined preview without contacting the clock. Use the clock's actual private address for the live slideshow:

```powershell
uv run python meter.py --state-dir 'C:\path\to\smalltv-custom\meter' --profile sd-pro --host 192.168.0.70 --watch
```

The Windows tray app normally supervises this command. `--test` shows a short reversible slideshow test and restores afterward. `--stop-on-stdin` allows the tray to send `stop` or close stdin to request restoration. Ctrl+C also restores. For an interrupted run, use `--profile sd-pro --restore` with the same clock address once reachable. Run only one writer at a time.

Original photo flags, theme flags, intervals and display mode are saved in ignored `sd-restore.local.json`. The adapter uploads three uniquely named short JPEGs, enables Photo before disabling other themes, selects its own pages and sets the photo interval to 10 seconds. User photos are never overwritten or deleted. Managed images remain in the album, disabled after restoration. Restoration requires the clock to be reachable. The adapter reads `/config` only for display mode and retains no wireless credentials or API keys.

The legacy `ultra` adapter uses different factory endpoints and a combined image. Never use it on the SD PRO interface. NMMiner is not supported. These scripts do not change PC wireless settings or flash firmware. Upstream Home Assistant integration code is separate from this standalone project.

## Validation

The full-screen display was confirmed by the user on October 12, 2026. Live API verification confirmed three selected pages and a 10-second interval; the short test restored the previous display. Regression tests cover slideshow selection, short filenames and restoration. A real Claude limit warning has not yet been observed during live validation.

From the repository root:

```powershell
uv run --project windows-companion pre-commit run --all-files --config windows-companion/.pre-commit-config.yaml
```

These checks cover the standalone addition; the unchanged upstream Home Assistant test suite is separate. Keep local snapshots, restore files, sessions and installed dependencies off GitHub.

