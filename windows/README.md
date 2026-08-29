# DeepSeek Harness Desktop — Windows Package

This directory contains the Electron-based Windows application package for
DeepSeek Harness. It wraps the `dsh web` command in a native Windows window
with system tray support, proper icon integration, and automatic configuration
import from `~/.dsh`.

## Quick Start

After cloning this repo and installing dependencies:

```powershell
cd desktop-linux/windows
npm install
npx electron-builder --win --x64
```

This produces `dist/DeepSeek-Harness-Setup.exe` — a proper Windows installer
with Start Menu and Desktop shortcuts.

## Without Electron (Fallback)

If you cannot install Electron in your environment, use the Node.js launcher:

```powershell
# Ensure dsh is installed
npm i -g @deepseek-ai/dsh

# Run directly
node launcher.js

# Or create shortcuts manually
powershell -ExecutionPolicy Bypass -File install-windows.ps1
```

## Files

| File | Description |
|------|-------------|
| `launcher.js` | Main Node.js entry point — finds dsh, launches sidecar, waits for UI |
| `DeepSeek-Harness-Desktop.bat` | Batch wrapper for direct double-click launching |
| `install-windows.ps1` | Creates Start Menu / Desktop shortcuts |
| `create-shortcut.ps1` | Standalone shortcut creation utility |
| `package.json` | Electron + electron-builder configuration |
| `electron-builder.yml` | Build targets (NSIS installer for Windows) |
| `src/main.js` | Electron main process (window management, sidecar lifecycle) |
| `src/preload.js` | Electron preload script (IPC bridge) |
| `share/icons/windows/` | Windows ICO icon files |
| `bin/` | Python launcher binary (copied from desktop-linux/bin/) |

## Build Output

Running `npx electron-builder --win --x64` produces:

```
dist/
├── DeepSeek-Harness-Setup.exe    # NSIS installer (~50-100 MB)
├── DeepSeek-Harness-0.2.0-win-x64.exe  # Portable executable
└── builder-effective-config.yaml
```

The installer creates:
- Desktop shortcut: `DeepSeek Harness.lnk`
- Start Menu folder: `DeepSeek Harness\`
- Uninstaller via Add/Remove Programs

## Configuration

The app automatically imports configuration from `~/.dsh` on first launch:
- `settings.yaml` — provider/model/API key settings
- `.credentials.yaml` — OAuth/session credentials
- `profiles/web/` — full web profile including node_modules (plugins)
- `.anonymous-user-id` — session identity

To force a fresh install (no import):
```powershell
$env:DSH_FRESH=1; node launcher.js
```

## Troubleshooting

**"dsh not found" error:**
```powershell
npm i -g @deepseek-ai/dsh
```

**Sidecar fails to start:**
Check the log file at:
```
%APPDATA%\DeepSeekHarnessDesktop\home\logs\
```

**Plugins not loading:**
Ensure `profiles/web/cordis.patch.yml` contains the plugin entries:
```yaml
- id: auto-compact
  name: billion-context-dsh
- id: compaction-instant
  name: dsh-compaction-instant
- id: openwolf
  name: '@volcengine/dsh-memory-plugin'
```
