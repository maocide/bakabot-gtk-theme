#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

snapshot() {
  find \
    "$ROOT/gtk-2.0" \
    "$ROOT/gtk-3.0" \
    "$ROOT/gtk-3.20" \
    "$ROOT/gtk-4.0" \
    "$ROOT/assets" \
    "$ROOT/gnome-shell" \
    "$ROOT/cinnamon" \
    "$ROOT/xfwm4" \
    -type f -print0 |
    sort -z |
    xargs -0 sha256sum
}

echo "==> Building twice and comparing generated files"
"$ROOT/tools/build.sh"
snapshot >"$TMP/first.sha"
"$ROOT/tools/build.sh"
snapshot >"$TMP/second.sha"

if ! diff -u "$TMP/first.sha" "$TMP/second.sha"; then
  echo "ERROR: build is not deterministic; generated files changed." >&2
  exit 1
fi

echo "==> Checking git whitespace"
git -C "$ROOT" diff --check

echo "==> Parsing GTK3 CSS"
if ! "$PYTHON" - <<'PY' 2>"$TMP/gtk3.err"
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

for path in ("gtk-3.0/gtk.css", "gtk-3.20/gtk.css", "gtk-3.20/gtk-dark.css"):
    provider = Gtk.CssProvider()
    try:
        provider.load_from_path(path)
    except GLib.Error as error:
        print(f"FAIL {path}: {error.message}")
        raise SystemExit(1)
    print(f"OK {path}")
PY
then
  cat "$TMP/gtk3.err" >&2
  exit 1
fi

echo "==> Parsing GTK4 CSS"
if ! "$PYTHON" - <<'PY' 2>"$TMP/gtk4.err"
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

for path in ("gtk-4.0/gtk.css", "gtk-4.0/gtk-dark.css"):
    provider = Gtk.CssProvider()
    try:
        provider.load_from_path(path)
    except GLib.Error as error:
        print(f"FAIL {path}: {error.message}")
        raise SystemExit(1)
    print(f"OK {path}")
PY
then
  cat "$TMP/gtk4.err" >&2
  exit 1
fi

echo "==> Verification passed"
