#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-$HOME/.themes/BakaBot}"

if [ "${SKIP_BUILD:-0}" != "1" ]; then
  "$ROOT/tools/build.sh"
fi

mkdir -p "$DEST"

rsync -a --delete \
  --exclude '.git/' \
  --exclude '.github/' \
  --exclude 'Art/' \
  --exclude 'node_modules/' \
  --exclude 'src/' \
  --exclude 'tools/' \
  --exclude 'vendor/' \
  --exclude '*.scss' \
  --exclude '*.css.map' \
  --exclude 'Gulpfile.js' \
  --exclude 'package.json' \
  --exclude 'package-lock.json' \
  --exclude 'screenshot.png' \
  "$ROOT"/ "$DEST"/

# rsync --delete does not remove excluded paths; keep source-only material out.
rm -rf "$DEST/vendor" "$DEST/tools" "$DEST/src"

echo "Installed BakaBot GTK theme to: $DEST"
