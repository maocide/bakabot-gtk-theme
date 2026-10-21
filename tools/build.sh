#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"

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

# 1. Generate SCSS tokens and legacy color values from the palette source.
"$PYTHON" "$ROOT/tools/palette.py"

# 2. Restore the pristine upstream base CSS, then apply BakaBot fixes/palette.
for name in gtk.css gtk-dark.css; do
  cp "$ROOT/vendor/dracula-v4.0.0/gtk-3.20/$name" "$ROOT/gtk-3.20/$name"
  cp "$ROOT/vendor/dracula-v4.0.0/gtk-4.0/$name" "$ROOT/gtk-4.0/$name"
done

"$PYTHON" "$ROOT/tools/apply_base_fixes.py"
"$PYTHON" "$ROOT/tools/apply_palette.py"

# 3. Custom SCSS layer and generated window buttons.
"$SASS_BIN" --no-source-map --style=expanded \
  "$ROOT/gtk-3.20/bakabot.scss" "$ROOT/gtk-3.20/bakabot.css"

"$SASS_BIN" --no-source-map --style=expanded \
  "$ROOT/gtk-4.0/bakabot.scss" "$ROOT/gtk-4.0/bakabot.css"

"$PYTHON" "$ROOT/tools/generate_window_buttons.py"

# 4. The base CSS files load the compiled custom layer last.
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

echo "Built BakaBot base CSS, custom layer, assets, and window buttons."
