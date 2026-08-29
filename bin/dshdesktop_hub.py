"""Built-in dsh plugin hub: catalog, registration, install/remove operations,
and a small window UI (GTK on Linux, Tkinter on Windows).

A dsh plugin is an npm package installed into the web profile plus one
`insert` entry in the profile's `cordis.patch.yml` user patch layer. The hub
manages both halves with the same commands the CLI uses (`dsh plugin --profile
web add/remove`, i.e. pnpm under the hood) and edits the patch layer the
documented way, preserving its header comments and non-insert entries."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import yaml

from dshdesktop_core import find_repo_root, sidecar_env


class HubContext:
    """Everything hub operations need: the app's DSH_HOME and dsh launcher."""

    def __init__(self, home: Path, command_prefix: list[str], workdir: Path | None) -> None:
        self.home = home
        self.command_prefix = command_prefix
        self.workdir = workdir

    @property
    def profile_dir(self) -> Path:
        return self.home / 'profiles' / 'web'

    @property
    def patch_path(self) -> Path:
        return self.profile_dir / 'cordis.patch.yml'


def _patch_header(text: str) -> str:
    """Leading comment lines of the patch file, kept across rewrites."""
    header_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith('#'):
            header_lines.append(line)
        elif line.strip():
            break
    return ('\n'.join(header_lines) + '\n') if header_lines else ''


def read_entries(ctx: HubContext) -> list:
    """The patch file's top-level YAML array (empty list when absent/blank)."""
    try:
        text = ctx.patch_path.read_text(encoding='utf-8')
    except OSError:
        return []
    loaded = yaml.safe_load(text)
    return [entry for entry in loaded if isinstance(entry, dict)] if isinstance(loaded, list) else []


def write_entries(ctx: HubContext, entries: list) -> None:
    ctx.patch_path.parent.mkdir(parents=True, exist_ok=True)
    original = ctx.patch_path.read_text(encoding='utf-8') if ctx.patch_path.exists() else ''
    body = yaml.safe_dump(entries, sort_keys=False, allow_unicode=True) if entries else '[]\n'
    ctx.patch_path.write_text(_patch_header(original) + body, encoding='utf-8')


def registrations(ctx: HubContext) -> list[dict]:
    """All {id, name} plugin registrations across the patch layer's insert lists."""
    found: list[dict] = []
    for entry in read_entries(ctx):
        inserted = entry.get('insert')
        if isinstance(inserted, list):
            found.extend(item for item in inserted if isinstance(item, dict))
    return found


def register(ctx: HubContext, plugin_id: str, package: str) -> None:
    """Add one {id, name} registration, merging into an existing insert entry."""
    entries = read_entries(ctx)
    for entry in entries:
        inserted = entry.get('insert')
        if isinstance(inserted, list):
            if any(isinstance(item, dict) and item.get('id') == plugin_id for item in inserted):
                return  # Already registered; registering is idempotent.
            inserted.append({'id': plugin_id, 'name': package})
            write_entries(ctx, entries)
            return
    entries.append({'insert': [{'id': plugin_id, 'name': package}]})
    write_entries(ctx, entries)


def unregister(ctx: HubContext, plugin_id: str, package: str | None = None) -> None:
    """Drop every registration matching the id (or the package name)."""
    entries = read_entries(ctx)
    changed = False
    for entry in entries:
        inserted = entry.get('insert')
        if not isinstance(inserted, list):
            continue
        kept = [item for item in inserted
                if not (isinstance(item, dict)
                        and (item.get('id') == plugin_id
                             or (package is not None and item.get('name') == package)))]
        if len(kept) != len(inserted):
            entry['insert'] = kept
            changed = True
    if changed:
        write_entries(ctx, entries)


def repo_catalog() -> list[dict]:
    """{name, description} for @deepseek-ai packages in a harness checkout."""
    repo = find_repo_root()
    if repo is None:
        return []
    catalog: list[dict] = []
    for manifest in sorted(repo.glob('packages/*/*/package.json')):
        try:
            data = json.loads(manifest.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        name = data.get('name', '')
        if name.startswith('@deepseek-ai/'):
            catalog.append({'name': name, 'description': data.get('description', '')})
    return catalog


def profile_state(ctx: HubContext) -> tuple[list[str], dict[str, str]]:
    """The web profile's declared bundles and installed dependency packages."""
    manifest = ctx.profile_dir / 'package.json'
    try:
        data = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return [], {}
    profile = data.get('dsh', {}).get('profile', {})
    bundles = [str(item) for item in profile.get('bundles', [])]
    dependencies = {str(k): str(v) for k, v in data.get('dependencies', {}).items()}
    return bundles, dependencies


def installed_nodes(ctx: HubContext) -> set[str]:
    """Package names physically present under the profile's node_modules."""
    root = ctx.profile_dir / 'node_modules'
    found: set[str] = set()
    if not root.is_dir():
        return found
    for child in root.iterdir():
        if child.name.startswith('@') and child.is_dir():
            found.update(f"{child.name}/{pkg.name}" for pkg in child.iterdir() if pkg.is_dir())
        elif child.is_dir():
            found.add(child.name)
    return found


def run_plugin_command(ctx: HubContext, args: list[str], on_output) -> int:
    """Run `dsh plugin --profile web <args>`, streaming merged output lines."""
    argv = [*ctx.command_prefix, 'plugin', '--profile', 'web', *args]
    kwargs: dict = {
        'cwd': ctx.workdir,
        'env': sidecar_env(ctx.home, ctx.command_prefix),
        'stdout': subprocess.PIPE,
        'stderr': subprocess.STDOUT,
        'text': True,
        'errors': 'replace',
        'bufsize': 1,
    }
    if os.name != 'nt':
        kwargs['start_new_session'] = True
    try:
        proc = subprocess.Popen(argv, **kwargs)
    except OSError as error:
        on_output(f'failed to launch dsh plugin: {error}')
        return 1
    assert proc.stdout is not None
    for line in proc.stdout:
        on_output(line.rstrip('\n'))
    return proc.wait()


def install_and_register(ctx: HubContext, plugin_id: str, package: str, on_output) -> bool:
    """Install the npm package into the profile, then register the plugin id."""
    on_output(f'$ dsh plugin --profile web add {package}')
    if run_plugin_command(ctx, ['add', package], on_output) != 0:
        on_output('! install failed; nothing registered')
        return False
    register(ctx, plugin_id, package)
    on_output(f"registered '{plugin_id}' ({package}) in cordis.patch.yml — reload the Web UI")
    return True


def unregister_and_remove(ctx: HubContext, plugin_id: str, package: str, on_output) -> bool:
    """Unregister the plugin id, then remove the npm package from the profile."""
    unregister(ctx, plugin_id, package)
    on_output(f'$ dsh plugin --profile web remove {package}')
    ok = run_plugin_command(ctx, ['remove', package], on_output) == 0
    on_output(f"unregistered '{plugin_id}'" + ('' if ok else ' (package remove reported an error)'))
    return ok


def load_saved_hub_state() -> list[dict]:
    """Manually added hub packages remembered across runs."""
    path = _state_path()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _state_path() -> Path:
    from dshdesktop_core import data_dir

    return data_dir() / 'hub-packages.json'


def save_hub_state(items: list[dict]) -> None:
    path = _state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(items, indent=2) + '\n', encoding='utf-8')
    except OSError:
        pass  # Losing the manual-package memory is cosmetic.


def default_plugin_id(package: str) -> str:
    """A reasonable patch id derived from a package name."""
    tail = package.split('/')[-1]
    tail = tail.split('@')[0] or tail
    return tail.replace('@deepseek-ai/', '').replace('dsh-', '').strip() or 'plugin'


# --- UIs -----------------------------------------------------------------


def run_gtk_hub(ctx: HubContext) -> None:
    """GTK3 hub window (Linux). Blocks until the window is closed."""
    import gi

    gi.require_version('Gtk', '3.0')
    from gi.repository import GLib, Gtk

    window = Gtk.Window(title=f'Plugin Hub — dsh profile web')
    window.set_default_size(860, 560)

    store = Gtk.ListStore(bool, str, str, str)  # installed, id, package, description
    tree = Gtk.TreeView(model=store, headers_visible=True)
    for position, title, width in ((0, '✓', 30), (1, 'plugin id', 170), (2, 'package', 250),
                                   (3, 'description', 360)):
        renderer = Gtk.CellRendererText(xalign=0.5 if position == 0 else 0.0)
        column = Gtk.TreeViewColumn(title, renderer, text=position)
        column.set_resizable(True)
        column.set_min_width(width if position != 0 else 30)
        tree.append_column(column)

    scroll = Gtk.ScrolledWindow()
    scroll.set_vexpand(True)
    scroll.add(tree)

    output = Gtk.TextView(editable=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
    out_scroll = Gtk.ScrolledWindow()
    out_scroll.set_size_request(-1, 130)
    out_scroll.add(output)
    out_buffer = output.get_buffer()

    id_entry = Gtk.Entry()
    id_entry.set_placeholder_text('plugin id (patch key, e.g. ui-aqua)')
    pkg_entry = Gtk.Entry()
    pkg_entry.set_placeholder_text('npm package (e.g. @deepseek-ai/dsh-web-app)')
    busy = Gtk.Label(label='')

    def log(message: str) -> None:
        GLib.idle_add(out_buffer.insert_at_cursor, message + '\n', -1)

    def refresh(_button=None) -> None:
        store.clear()
        bundles, dependencies = profile_state(ctx)
        nodes = installed_nodes(ctx)
        registered = {item.get('id'): item.get('name') for item in registrations(ctx)}
        known: dict[str, dict] = {}
        for item in repo_catalog():
            known.setdefault(item['name'], item)
        for name, version in dependencies.items():
            known.setdefault(name, {'name': name, 'description': f'installed {version}'})
        for name, version in sorted(known.items()):
            plugin_ids = [pid for pid, pkg in registered.items() if pkg == name]
            plugin_id = plugin_ids[0] if plugin_ids else ''
            installed = name in nodes or name in bundles
            description = known[name].get('description', '')
            label = f'{plugin_id} (registered)' if plugin_id else description
            store.append([installed, plugin_id or '—', name, label])

    def selected() -> tuple[str, str] | None:
        model, tree_iter = tree.get_selection().get_selected()
        if tree_iter is None:
            return None
        return model[tree_iter][1], model[tree_iter][2]

    def on_install(_button) -> None:
        plugin_id = id_entry.get_text().strip() or default_plugin_id(pkg_entry.get_text().strip())
        package = pkg_entry.get_text().strip()
        picked = selected()
        if not package and picked:
            plugin_id = plugin_id if id_entry.get_text().strip() else default_plugin_id(picked[1])
            package = picked[1]
        if not package:
            log('! enter an npm package name first')
            return
        busy.set_text(f'working: {package} …')
        thread_run(lambda: install_and_register(ctx, plugin_id, package, log), refresh, busy)

    def on_remove(_button) -> None:
        picked = selected()
        if not picked:
            log('! select a plugin row first')
            return
        plugin_id, package = picked
        if plugin_id == '—':
            plugin_id = default_plugin_id(package)
        busy.set_text(f'removing: {package} …')
        thread_run(lambda: unregister_and_remove(ctx, plugin_id, package, log), refresh, busy)

    def thread_run(work, after, busy_label) -> None:
        import threading

        def run() -> None:
            try:
                work()
            finally:
                GLib.idle_add(after)
                GLib.idle_add(busy_label.set_text, '')

        threading.Thread(target=run, daemon=True).start()

    buttons = Gtk.Box(spacing=6)
    for label, handler in (('Install / Register', on_install), ('Remove', on_remove),
                           ('Refresh', refresh)):
        button = Gtk.Button(label=label)
        button.connect('clicked', handler)
        buttons.pack_start(button, False, False, 0)
    buttons.pack_end(busy, False, False, 12)

    entry_row = Gtk.Box(spacing=6)
    entry_row.pack_start(id_entry, False, True, 170)
    entry_row.pack_start(pkg_entry, True, True, 0)

    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    outer.set_border_width(8)
    outer.pack_start(buttons, False, False, 0)
    outer.pack_start(entry_row, False, False, 0)
    outer.pack_start(scroll, True, True, 0)
    outer.pack_start(out_scroll, False, False, 0)
    window.add(outer)
    window.connect('destroy', Gtk.main_quit)
    window.show_all()
    refresh()
    log('Plugin Hub: install a package into the web profile, register it in cordis.patch.yml.')
    log('The plugin takes effect after the Web UI reloads.')
    Gtk.main()


def run_tk_hub(ctx: HubContext) -> None:
    """Tkinter hub window (Windows). Blocks until the window is closed."""
    import tkinter as tk
    from tkinter import ttk

    window = tk.Tk()
    window.title('Plugin Hub — dsh profile web')
    window.geometry('860x560')

    columns = ('installed', 'id', 'package', 'description')
    tree = ttk.Treeview(window, columns=columns, show='headings', height=14)
    for column, text, width in (('installed', '✓', 40), ('id', 'plugin id', 160),
                                ('package', 'package', 240), ('description', 'description', 360)):
        tree.heading(column, text=text)
        tree.column(column, width=width, anchor=tk.W)
    tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))

    output = tk.Text(window, height=7, state=tk.DISABLED, wrap=tk.WORD)
    output.pack(fill=tk.X, padx=8, pady=4)

    def log(message: str) -> None:
        window.after(0, lambda: (output.configure(state=tk.NORMAL),
                                  output.insert(tk.END, message + '\n'),
                                  output.see(tk.END),
                                  output.configure(state=tk.DISABLED)))

    id_entry = tk.Entry(window, width=28)
    pkg_entry = tk.Entry(window)
    busy = tk.Label(window, text='')
    busy.pack(side=tk.BOTTOM, fill=tk.X, padx=8)

    def refresh() -> None:
        tree.delete(*tree.get_children())
        bundles, dependencies = profile_state(ctx)
        nodes = installed_nodes(ctx)
        registered = {item.get('id'): item.get('name') for item in registrations(ctx)}
        known: dict[str, dict] = {}
        for item in repo_catalog():
            known.setdefault(item['name'], item)
        for name, version in dependencies.items():
            known.setdefault(name, {'name': name, 'description': f'installed {version}'})
        for name in sorted(known):
            plugin_ids = [pid for pid, pkg in registered.items() if pkg == name]
            plugin_id = plugin_ids[0] if plugin_ids else '—'
            installed = '✓' if (name in nodes or name in bundles) else ''
            tree.insert('', tk.END, values=(installed, plugin_id, name,
                                            known[name].get('description', '')))

    def on_install() -> None:
        package = pkg_entry.get().strip()
        picked = tree.selection()
        if not package and picked:
            package = tree.item(picked[0])['values'][2]
        if not package:
            log('! enter an npm package name first')
            return
        plugin_id = id_entry.get().strip() or default_plugin_id(package)
        busy.configure(text=f'working: {package} …')

        def work() -> None:
            try:
                install_and_register(ctx, plugin_id, package, log)
            finally:
                window.after(0, refresh)
                window.after(0, lambda: busy.configure(text=''))

        import threading
        threading.Thread(target=work, daemon=True).start()

    def on_remove() -> None:
        picked = tree.selection()
        if not picked:
            log('! select a plugin row first')
            return
        values = tree.item(picked[0])['values']
        plugin_id = str(values[1]) if str(values[1]) != '—' else default_plugin_id(str(values[2]))
        package = str(values[2])
        busy.configure(text=f'removing: {package} …')

        def work() -> None:
            try:
                unregister_and_remove(ctx, plugin_id, package, log)
            finally:
                window.after(0, refresh)
                window.after(0, lambda: busy.configure(text=''))

        import threading
        threading.Thread(target=work, daemon=True).start()

    row = tk.Frame(window)
    row.pack(fill=tk.X, padx=8, pady=(0, 8))
    tk.Button(row, text='Install / Register', command=on_install).pack(side=tk.LEFT, padx=(0, 6))
    tk.Button(row, text='Remove', command=on_remove).pack(side=tk.LEFT, padx=(0, 6))
    tk.Button(row, text='Refresh', command=refresh).pack(side=tk.LEFT, padx=(0, 12))
    tk.Label(row, text='id').pack(side=tk.LEFT)
    id_entry.pack(side=tk.LEFT, padx=(4, 8))
    tk.Label(row, text='package').pack(side=tk.LEFT)
    pkg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

    log('Plugin Hub: install a package into the web profile, register it in cordis.patch.yml.')
    log('The plugin takes effect after the Web UI reloads.')
    refresh()
    window.mainloop()
