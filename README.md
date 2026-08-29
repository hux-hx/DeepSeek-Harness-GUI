# DeepSeek Harness Desktop (Linux + Windows)

A native desktop GUI for DeepSeek Harness: the harness `dsh web` UI in a native window, with `dsh web` supervised as a sidecar. Ships a built-in **dsh Plugin Hub**, reuses an existing local harness configuration (no second setup), and packages as a double-click app on both Linux and Windows.

GitHub: <https://github.com/hux-hx/DeepSeek-Harness-GUI>

## Why this exists

Web research (August 2026) found no official Linux desktop build of DeepSeek Harness:

| Channel | Status |
| --- | --- |
| Official (`github.com/deepseek-ai/deepseek-harness`) | Local Web UI via `dsh web` (`http://127.0.0.1:3080`); no signed desktop installer on any platform |
| Community macOS ([fendouai/deepseek-harness-desktop](https://github.com/fendouai/deepseek-harness-desktop) v0.1.0-rc.5) | Apple Silicon DMG only: bundled Node.js runtime + supervised `dsh` sidecar + the existing Web UI |
| Community Windows (Microsoft Store, "DeepSeek-Harness-Setup") | Windows installer packaging the Web UI |
| Linux | Nothing published — this app fills that gap, and adds a Windows adaptation |

This app follows the same architecture as the community macOS/Windows wrappers, with zero bundled runtime: it drives the dsh already on the machine and adds the desktop shell (icon, menu entry, native window, sidecar lifecycle, plugin hub).

## Features

- **Supervised sidecar** — boots `dsh web` with its own `DSH_HOME` and an OS-picked port; closing the window (or SIGTERM/SIGINT) terminates the whole process tree (SIGTERM, 5 s grace, SIGKILL).
- **No second configuration** — on first run the app copies an existing local harness home's `settings.yaml`, `.credentials.yaml`, `.anonymous-user-id`, and the web profile's `cordis.patch.yml` into its own home (mode bits preserved). Providers, models, and API keys carry over; sessions are not touched. `--fresh` skips the import.
- **Built-in Plugin Hub** — a window that manages dsh plugins for the web profile: scans the harness checkout for `@deepseek-ai` packages as a catalog, shows what is installed/registered, installs npm packages into the profile (`dsh plugin --profile web add`), registers/unregisters them in `cordis.patch.yml` (header comments and non-insert entries preserved), and streams the command output. Open it from the "Plugin Hub" button in the window toolbar, or `--plugins`.
- **Native window shell** — `Ctrl+R` reload, `Ctrl+Shift+R` bypass-cache reload, `Ctrl+=`/`Ctrl+-`/`Ctrl+0` zoom, `F11` fullscreen, `Ctrl+Q` quit; window size and zoom are remembered; links leaving the app origin open in the system browser (Linux).

## Layout

```
DeepSeek-Harness-GUI/            (this repo)
├── bin/deepseek-harness-desktop    entry: CLI + GTK window (Linux) / pywebview (Windows)
├── bin/dshdesktop_core.py          paths, dsh resolution, sidecar, config import
├── bin/dshdesktop_hub.py           plugin hub logic + GTK/Tk UIs
├── share/applications/*.desktop.in MATE/GNOME menu entry template
├── share/icons/…                   SVG, PNG (48/128/256), Windows .ico
├── windows/                        double-click .cmd launchers + install-windows.ps1
├── install.sh / uninstall.sh       per-user install (Linux, ~/.local)
└── README.md / README.zh.md / LICENSE
```

## Install (Linux)

```sh
cd DeepSeek-Harness-GUI
./install.sh          # per-user, prefix ~/.local
```

Installs `~/.local/bin/deepseek-harness-desktop`, icons, a MATE/GNOME menu entry (Development), and a double-clickable `~/Desktop/DeepSeek-Harness-Desktop.desktop`. Requirements: Python 3, GTK 3, WebKit2GTK 4.1 (`gir1.2-webkit2-4.1`), and a working `dsh` (`npm i -g @deepseek-ai/dsh`).

## Install (Windows)

1. Install Python 3 (python.org, tick "Add to PATH" + tcl/tk) and `py -3 -m pip install pywebview` (uses the WebView2 runtime built into Windows 10/11).
2. Install the harness: `npm i -g @deepseek-ai/dsh`.
3. Double-click `windows/install-windows.ps1` (or run it with `powershell -ExecutionPolicy Bypass -File install-windows.ps1`) — it checks the prerequisites and creates Start Menu + Desktop shortcuts for the app and the Plugin Hub.
4. Double-click **DeepSeek Harness Desktop**.

## Usage

```sh
deepseek-harness-desktop                         # boot a sidecar, open the window
deepseek-harness-desktop --attach http://127.0.0.1:3080   # wrap an already-running dsh web
deepseek-harness-desktop --plugins               # open the Plugin Hub
deepseek-harness-desktop --port 4200             # fixed sidecar port
deepseek-harness-desktop --home ~/.dsh           # share the main DSH home (see note)
deepseek-harness-desktop --dsh /path/to/dsh      # explicit dsh executable
deepseek-harness-desktop --repo /path/to/deepseek-harness   # source mode + hub catalog
deepseek-harness-desktop --fresh                 # skip local-config import
deepseek-harness-desktop --geometry 1440x900     # initial window size
deepseek-harness-desktop --check                 # headless boot/readiness/shutdown test
```

First launch imports the local harness configuration automatically, so the UI starts with your providers, models, and API key already configured. If no local harness exists, the Web UI's own onboarding asks once.

> Note: sharing `--home ~/.dsh` while another `dsh web` runs makes two processes write one profile; prefer the default isolated home, or `--attach` for the running instance.

## How dsh is resolved

`--dsh`/`DSH_BIN` → a harness checkout with `node_modules` installed next to the app or via `--repo`/`DSH_REPO` (runs `apps/cli/src/bin.ts` through tsx, i.e. the project source) → `dsh` on `PATH` → nvm (Linux: `~/.nvm/versions/node/*/bin/dsh`) or npm global (`%APPDATA%\npm\dsh.cmd`) on Windows.

## Data layout

```
Linux:  ~/.local/share/deepseek-harness-desktop/
Windows: %APPDATA%\DeepSeekHarnessDesktop\
├── home/                  # DSH_HOME of the sidecar (profiles, storages, logs/, imported config)
├── hub-packages.json      # plugin hub memory
└── window-state.json      # last window size/maximized/zoom (Linux)
```

Sidecar logs: `home/logs/sidecar-<timestamp>.log` (10 newest kept) — the first place to look on boot failures.

## Troubleshooting

- **"dsh executable not found"** — set `DSH_BIN`/`--dsh`. Menu launches often lack nvm's `PATH`; the launcher also checks the nvm/npm shim locations automatically.
- **Slow first boot** — the web profile installs its plugin dependencies into the fresh `DSH_HOME` on first run; later launches start in seconds.
- **Rendering glitches on old GPUs** — run with `WEBKIT_DISABLE_COMPOSITING_MODE=1` (Linux) for software rendering.
- **Plugin installed but not visible** — the hub registers it in `cordis.patch.yml`; reload the Web UI afterwards.

## Security

The window shows exactly the official `dsh web` UI served on loopback; no bundled or modified harness binaries are involved. The sidecar holds the same privileges as any local `dsh` run (filesystem, shell, model key), so keep approvals on and scope the API key as you would for `dsh web`. Credential files are copied with their original `0600` mode.

## License

MIT — see [LICENSE](LICENSE).
