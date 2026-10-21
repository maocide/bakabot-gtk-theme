#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SASS_BIN="${SASS:-}"
if [ -z "$SASS_BIN" ]; then
  if command -v sass >/dev/null 2>&1; then
    SASS_BIN="sass"
  elif [ -x "$ROOT/tools/.dart-sass/sass" ]; then
    SASS_BIN="$ROOT/tools/.dart-sass/sass"
  else
    cat >&2 <<'EOF'
Dart Sass was not found.

Install it with:
  sudo pacman -S dart-sass

Or download it into tools/.dart-sass/ and run this script again.
You can also point SASS at a specific binary:
  SASS=/path/to/sass ./tools/build.sh
EOF
    exit 1
  fi
fi

"$SASS_BIN" --no-source-map --style=expanded \
  "$ROOT/gtk-3.20/bakabot.scss" "$ROOT/gtk-3.20/bakabot.css"

"$SASS_BIN" --no-source-map --style=expanded \
  "$ROOT/gtk-4.0/bakabot.scss" "$ROOT/gtk-4.0/bakabot.css"

# The base CSS files load the compiled custom layer last. Re-add the import
# if an upstream update replaced the generated files.
for file in \
  "$ROOT/gtk-3.20/gtk.css" \
  "$ROOT/gtk-3.20/gtk-dark.css" \
  "$ROOT/gtk-4.0/gtk.css" \
  "$ROOT/gtk-4.0/gtk-dark.css"
do
  if ! grep -q '@import url("bakabot.css");' "$file"; then
    printf '\n/* BakaBot custom layer */\n@import url("bakabot.css");\n' >>"$file"
  fi
done

echo "Built gtk-3.20/bakabot.css and gtk-4.0/bakabot.css."
