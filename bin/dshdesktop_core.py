"""Core of DeepSeek Harness Desktop: platform paths, dsh resolution, sidecar
supervision, and one-time local-configuration import. Shared by the GTK entry
(Linux) and the pywebview/tk entry (Windows)."""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

APP_ID = 'deepseek-harness-desktop'
APP_NAME = 'DeepSeek Harness'
APP_VERSION = '0.2.0'

BOOT_TIMEOUT_SECONDS = 90.0
ATTACH_TIMEOUT_SECONDS = 10.0
SHUTDOWN_TIMEOUT_SECONDS = 5.0
SIDECAR_LOGS_KEPT = 10
URL_LINE_PATTERN = re.compile(r'dsh web:\s*(\S+)')

# Files copied from an existing local harness home so the user configures
# nothing twice: user settings, credentials (mode 600), anonymous identity,
# and the web profile's user patch layer (plugin registrations live there).
IMPORT_FILES = ('settings.yaml', '.credentials.yaml', '.anonymous-user-id')
IMPORT_PROFILE_FILES = ('profiles/web/cordis.patch.yml',)
IMPORT_MARKER = '.dsh-desktop-import.json'


def is_windows() -> bool:
    return os.name == 'nt'


def data_dir() -> Path:
    """Per-user data directory owned by the desktop app."""
    if is_windows():
        base = os.environ.get('APPDATA') or str(Path.home() / 'AppData' / 'Roaming')
        return Path(base) / 'DeepSeekHarnessDesktop'
    base = os.environ.get('XDG_DATA_HOME') or str(Path.home() / '.local' / 'share')
    return Path(base) / APP_ID


def app_root() -> Path:
    """Directory containing this app's bin/, share/, and windows/ trees."""
    return Path(__file__).resolve().parent.parent


def default_home() -> Path:
    return data_dir() / 'home'


def local_dsh_home() -> Path | None:
    """An existing local harness home to import configuration from, if any."""
    env_home = os.environ.get('DSH_HOME')
    if env_home:
        candidate = Path(env_home).expanduser()
        return candidate if candidate != default_home() else None
    candidate = Path.home() / '.dsh'
    return candidate if candidate.is_dir() else None


def find_repo_root() -> Path | None:
    """A deepseek-harness checkout usable for source mode and the hub catalog."""
    env_repo = os.environ.get('DSH_REPO')
    if env_repo:
        candidate = Path(env_repo).expanduser()
        if (candidate / 'apps' / 'cli' / 'src' / 'bin.ts').exists():
            return candidate
        return None
    for parent in [app_root(), *app_root().parents]:
        if (parent / 'apps' / 'cli' / 'src' / 'bin.ts').exists():
            return parent
    return None


def version_key(text: str) -> tuple[int, ...]:
    """Sortable tuple from a version-like directory name; junk sorts lowest."""
    return tuple(int(part) for part in re.findall(r'\d+', text)) or (0,)


def resolve_dsh(explicit: str | None) -> tuple[str, list[str], Path | None]:
    """Resolve how to launch `dsh web` on this machine.

    Returns (mode, command_prefix, working_directory). Precedence: explicit
    --dsh/DSH_BIN, a harness checkout with dependencies installed (runs the
    source entry through tsx), then the installed `dsh` (PATH, npm, nvm).
    """
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.exists():
            raise SystemExit(f'dsh binary not found: {path}')
        return 'bin', _shim_prefix(path), None

    repo = find_repo_root()
    if repo is not None:
        source_entry = repo / 'apps' / 'cli' / 'src' / 'bin.ts'
        if (repo / 'node_modules' / 'tsx').exists() and source_entry.exists():
            node = shutil.which('node')
            if node is None:
                raise SystemExit('repo source mode needs node on PATH')
            return 'repo-source', [node, '--import', 'tsx/esm', str(source_entry)], repo
        bundled = repo / 'node_modules' / '.bin' / 'dsh'
        if bundled.exists():
            return 'bin', _shim_prefix(bundled), None

    on_path = shutil.which('dsh')
    if on_path:
        return 'bin', _shim_prefix(Path(on_path)), None

    nvm_candidates = sorted(
        Path.home().glob('.nvm/versions/node/*/bin/dsh'),
        key=lambda path: version_key(path.parts[-4]),
        reverse=True,
    )
    if nvm_candidates:
        return 'bin', _shim_prefix(nvm_candidates[0]), None

    npm_shim = Path(os.environ.get('APPDATA', '')) / 'npm' / 'dsh.cmd'
    if npm_shim.is_file():
        return 'bin', _shim_prefix(npm_shim), None

    raise SystemExit(
        'dsh executable not found. Install DeepSeek Harness (npm i -g '
        '@deepseek-ai/dsh), or point --dsh / DSH_BIN at it.'
    )


def _shim_prefix(path: Path) -> list[str]:
    """Command prefix for a dsh entry point, wrapping .cmd/.bat shims in cmd."""
    if is_windows() and path.suffix.lower() in ('.cmd', '.bat'):
        return ['cmd', '/c', str(path)]
    return [str(path)]


def sidecar_env(home: Path, command_prefix: list[str]) -> dict[str, str]:
    """Environment for the sidecar: its own DSH_HOME and a PATH that reaches node."""
    env = os.environ.copy()
    env['DSH_HOME'] = str(home)
    launcher = command_prefix[-1] if command_prefix[0] == 'cmd' else command_prefix[0]
    env['PATH'] = f"{Path(launcher).parent}{os.pathsep}{env.get('PATH', '')}"
    return env


class Sidecar:
    """One supervised `dsh web` process and its resolved URL."""

    def __init__(self, command_prefix: list[str], workdir: Path | None, home: Path, port: int) -> None:
        self.command_prefix = command_prefix
        self.workdir = workdir
        self.home = home
        self.port = port
        self.proc: subprocess.Popen | None = None
        self.url: str | None = None
        self.log_path: Path | None = None

    def start(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        logs_dir = self.home / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = logs_dir / f'sidecar-{time.strftime("%Y%m%d-%H%M%S")}.log'
        self._prune_logs(logs_dir)

        argv = [*self.command_prefix, 'web', '--no-open', '--port', str(self.port)]
        kwargs: dict = {
            'cwd': self.workdir,
            'env': sidecar_env(self.home, self.command_prefix),
            'stdout': subprocess.PIPE,
            'stderr': subprocess.STDOUT,
        }
        if is_windows():
            kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs['start_new_session'] = True
        self.proc = subprocess.Popen(argv, **kwargs)
        self._pump_output()

    def _pump_output(self) -> None:
        """Copy sidecar output into the log file while watching for the URL line."""
        import threading

        assert self.proc is not None and self.proc.stdout is not None

        def pump() -> None:
            with open(self.log_path, 'ab', 0) as log_file:
                for line in iter(self.proc.stdout.readline, b''):
                    log_file.write(line)
                    if self.url is None:
                        match = URL_LINE_PATTERN.search(line.decode('utf-8', 'replace'))
                        if match:
                            self.url = match.group(1)

        threading.Thread(target=pump, daemon=True).start()

    def wait_until_ready(self, timeout: float) -> str:
        """Poll the sidecar's HTTP port until the UI answers, or fail loud."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.url is not None and self._responds(self.url):
                return self.url
            if self.proc is not None and self.proc.poll() is not None:
                raise RuntimeError(
                    f'dsh web exited with code {self.proc.returncode} during startup;\n'
                    f'log: {self.log_path}'
                )
            time.sleep(0.25)
        raise RuntimeError(
            f'dsh web did not become ready within {timeout:.0f}s;\nlog: {self.log_path}'
        )

    @staticmethod
    def _responds(url: str) -> bool:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                return response.status == 200
        except (urllib.error.URLError, OSError):
            return False

    def shutdown(self) -> None:
        """Stop the sidecar tree; force-kill only after the graceful wait."""
        if self.proc is None or self.proc.poll() is not None:
            return
        if is_windows():
            self.proc.terminate()
            deadline = time.monotonic() + SHUTDOWN_TIMEOUT_SECONDS
            while time.monotonic() < deadline and self.proc.poll() is None:
                time.sleep(0.1)
            if self.proc.poll() is None:
                subprocess.run(['taskkill', '/PID', str(self.proc.pid), '/T', '/F'],
                               capture_output=True, check=False)
            return
        try:
            os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + SHUTDOWN_TIMEOUT_SECONDS
        while time.monotonic() < deadline and self.proc.poll() is None:
            time.sleep(0.1)
        if self.proc.poll() is None:
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass

    def _prune_logs(self, logs_dir: Path) -> None:
        logs = sorted(logs_dir.glob('sidecar-*.log'))
        for stale in logs[:-SIDECAR_LOGS_KEPT]:
            stale.unlink(missing_ok=True)


def import_local_config(home: Path, force: bool = False) -> list[str]:
    """Copy configuration from an existing local harness home into `home`.

    Runs once per home (marker file); returns the copied file names for
    logging. Sessions and storages are deliberately not copied: only settings,
    credentials, identity, and the profile patch layer, so the desktop app
    starts already configured without touching the running harness's state.
    """
    marker = home / IMPORT_MARKER
    if marker.exists() and not force:
        return []
    source = local_dsh_home()
    if source is None or source.resolve() == home.resolve():
        return []

    copied: list[str] = []
    home.mkdir(parents=True, exist_ok=True)
    for name in IMPORT_FILES:
        src = source / name
        if src.is_file():
            shutil.copy2(src, home / name)
            copied.append(name)
    for name in IMPORT_PROFILE_FILES:
        src = source / name
        if src.is_file():
            dest = home / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied.append(name)
    marker.write_text(json.dumps({
        'importedFrom': str(source),
        'at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'files': copied,
    }, indent=2) + '\n', encoding='utf-8')
    return copied


def is_external_uri(uri: str, app_origin: str) -> bool:
    """True for http(s) targets off the app's own origin; those leave the window."""
    from urllib.parse import urlsplit

    parts = urlsplit(uri)
    if parts.scheme not in ('http', 'https'):
        return False
    app = urlsplit(app_origin)
    return (parts.hostname, parts.port) != (app.hostname, app.port)


def load_window_state() -> dict:
    path = data_dir() / 'window-state.json'
    try:
        state = json.loads(path.read_text(encoding='utf-8'))
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def save_window_state(state: dict) -> None:
    path = data_dir() / 'window-state.json'
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    except OSError:
        pass  # A lost window size is cosmetic; never block shutdown on it.


def show_error(message: str) -> None:
    """Visible failure for menu launches where stderr is invisible."""
    if is_windows():
        try:
            import tkinter.messagebox

            tkinter.messagebox.showerror(APP_NAME, message)
            return
        except Exception:
            pass
    else:
        try:
            import gi

            gi.require_version('Gtk', '3.0')
            from gi.repository import Gtk
            dialog = Gtk.MessageDialog(
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CLOSE,
                text=f'{APP_NAME} could not start',
                secondary_text=message,
            )
            dialog.run()
            dialog.destroy()
            return
        except Exception:
            pass
    print(message, file=sys.stderr)
