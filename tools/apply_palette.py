#!/usr/bin/env python3
"""Apply the BakaBot palette to Dracula's generated CSS and raster assets.

The upstream v4.0.0 build pipeline (node-sass 4 / Gulp) is obsolete, so the
generated CSS files are treated as the runtime source of truth. The SCSS
variables are kept in sync manually for documentation and for a future,
modernized build.
"""

from __future__ import annotations

import colorsys
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import palette as baka_palette  # noqa: E402

TOKENS = baka_palette.tokens()
PINK_HEX = TOKENS["primary"]
PINK_DARK_HEX = TOKENS["primary_dark"]
PINK_LIGHT_HEX = TOKENS["primary_light"]
CYAN_HEX = TOKENS["secondary"]
CYAN_HOVER_HEX = TOKENS["secondary_hover"]
CYAN_LIGHT_HEX = TOKENS["secondary_light"]

PINK_RGB = baka_palette.get_rgb("primary")
PINK_DARK_RGB = baka_palette.get_rgb("primary_dark")
PINK_LIGHT_RGB = baka_palette.get_rgb("primary_light")
CYAN_RGB = baka_palette.get_rgb("secondary")
CYAN_HOVER_RGB = baka_palette.get_rgb("secondary_hover")
CYAN_LIGHT_RGB = baka_palette.get_rgb("secondary_light")

PINK_HSV = baka_palette.get_hsv("primary")
CYAN_HSV = baka_palette.get_hsv("secondary")
PINK_HUE = PINK_HSV[0] * 360
PINK_HUE_ASSET = round(PINK_HUE)

# Literal accent colors used by the generated CSS and assets.
# Sources include both pristine upstream Dracula colors and current BakaBot
# colors, so the pass works on vendored base CSS and legacy outputs.
HEX_MAP = {
    # Upstream Dracula accents
    "#bd93f9": PINK_HEX,  # purple -> primary
    "#ff79c6": PINK_HEX,  # old pink -> primary
    "#ff69b4": PINK_HEX,  # hot pink -> primary
    "#50fa7a": CYAN_HEX,  # green -> secondary
    "#50fa7b": CYAN_HEX,
    "#72bfd0": CYAN_HEX,  # muted cyan -> secondary
    "#13b1d5": CYAN_HEX,  # link blue -> secondary
    "#8be9fd": CYAN_HEX,  # legacy cyan -> secondary
    "#4caec3": CYAN_HEX,  # success cyan -> secondary
    "#5fb6ca": CYAN_HEX,
    "#a1ce4b": CYAN_HEX,  # drop target green -> secondary
    "#13a0bf": CYAN_HEX,
    "#2fc9ec": CYAN_HOVER_HEX,  # link hover
    "#82fba0": CYAN_LIGHT_HEX,  # info backdrop
    "#98d0dd": CYAN_LIGHT_HEX,  # question backdrop
    "#6e5991": PINK_HEX,  # GTK2 purple selection -> primary

    # Current BakaBot outputs (idempotence and legacy files)
    "#ff85b3": PINK_HEX,
    "#ff85b4": PINK_HEX,
    "#ff5293": PINK_DARK_HEX,
    "#ffb8d3": PINK_LIGHT_HEX,
    "#00e0e0": CYAN_HEX,
    "#14ffff": CYAN_HOVER_HEX,
    "#33f0f0": CYAN_HOVER_HEX,
    "#66ecec": CYAN_LIGHT_HEX,
    "#66f0f0": CYAN_LIGHT_HEX,
}

# RGBA colors need their own map so the alpha value is preserved.
RGBA_MAP = {
    # Upstream Dracula accents
    (189, 147, 249): PINK_RGB,  # purple selection -> primary
    (159, 99, 246): PINK_DARK_RGB,  # darken(selected_bg, 10%)
    (174, 123, 248): PINK_LIGHT_RGB,  # lighten(selected_bg, 10%)
    (255, 105, 180): PINK_RGB,
    (80, 250, 122): CYAN_RGB,  # green -> secondary
    (80, 250, 123): CYAN_RGB,
    (114, 191, 208): CYAN_RGB,  # muted cyan -> secondary
    (19, 177, 213): CYAN_RGB,  # links -> secondary
    (76, 174, 195): CYAN_RGB,
    (95, 182, 202): CYAN_RGB,
    (19, 160, 191): CYAN_RGB,
    (161, 206, 75): CYAN_RGB,
    (47, 201, 236): CYAN_HOVER_RGB,
    (130, 251, 160): CYAN_LIGHT_RGB,
    (152, 208, 221): CYAN_LIGHT_RGB,

    # Current BakaBot outputs (idempotence and legacy files)
    (255, 133, 179): PINK_RGB,
    (255, 82, 147): PINK_DARK_RGB,
    (255, 184, 211): PINK_LIGHT_RGB,
    (0, 224, 224): CYAN_RGB,
    (51, 240, 240): CYAN_HOVER_RGB,
    (102, 240, 240): CYAN_LIGHT_RGB,
    (102, 236, 236): CYAN_LIGHT_RGB,
}

CSS_FILES = [
    "gtk-3.20/gtk.css",
    "gtk-3.20/gtk-dark.css",
    "gtk-4.0/gtk.css",
    "gtk-4.0/gtk-dark.css",
    "gtk-3.0/gtk.css",
    "gnome-shell/gnome-shell.css",
    "gnome-shell/v40/gnome-shell.css",
    "cinnamon/cinnamon.css",
    "cinnamon/cinnamon-dark.css",
]

SVG_DIRS = [
    "assets",
    "gtk-2.0/assets",
    "gnome-shell/assets",
    "cinnamon/common-assets",
    "cinnamon/dark-assets",
]
SVG_FILES = ["gtk-2.0/assets.svg"]
PNG_DIRS = ["assets", "gtk-2.0/assets"]
TEXT_FILES = ["gtk-2.0/gtkrc"]


def matching_brace(text: str, start: int) -> int:
    """Return the index just after the brace matching text[start] == '{'."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError("unbalanced braces")


def replace_in_suggested_blocks(text: str) -> str:
    """Make headerbar suggested-action buttons pink, not cyan.

    The generated CSS uses #72BFD0 for both headerbar suggested actions and
    informational widgets. Only the suggested-action blocks should become the
    pink primary accent; the rest becomes cyan in the global pass.
    """
    blocks: list[tuple[int, int]] = []
    for match in re.finditer(r"([^{}]+)\{", text):
        selector = match.group(1).split("}")[-1]
        if "button.suggested-action" in selector:
            blocks.append((match.end(), matching_brace(text, match.end() - 1)))

    # Work backwards so earlier offsets stay valid.
    for start, end in sorted(blocks, reverse=True):
        chunk = text[start:end]
        chunk = re.sub(r"#72bfd0\b", PINK_HEX, chunk, flags=re.IGNORECASE)
        chunk = re.sub(
            r"rgba\(\s*114\s*,\s*191\s*,\s*208\s*,\s*([0-9.]+)\s*\)",
            rf"rgba({PINK_RGB[0]}, {PINK_RGB[1]}, {PINK_RGB[2]}, \1)",
            chunk,
        )
        text = text[:start] + chunk + text[end:]
    return text


def fix_link_backdrop(text: str) -> str:
    """Backdrop links are dim cyan, not pink selection-colored."""
    blocks: list[tuple[int, int]] = []
    for match in re.finditer(r"([^{}]+)\{", text):
        selector = match.group(1).split("}")[-1]
        if "*:link:backdrop" in selector:
            blocks.append((match.end(), matching_brace(text, match.end() - 1)))

    for start, end in sorted(blocks, reverse=True):
        chunk = text[start:end]
        chunk = chunk.replace(
            f"rgba({PINK_RGB[0]}, {PINK_RGB[1]}, {PINK_RGB[2]}, 0.5)",
            f"rgba({CYAN_RGB[0]}, {CYAN_RGB[1]}, {CYAN_RGB[2]}, 0.5)",
        )
        text = text[:start] + chunk + text[end:]
    return text


def replace_hex(text: str) -> str:
    for src, dst in HEX_MAP.items():
        text = re.sub(re.escape(src) + r"\b", dst, text, flags=re.IGNORECASE)
    return text


def pinkify_purple(rgb: tuple[int, int, int]) -> tuple[int, int, int] | None:
    """Rotate leftover purple-derived shades to BakaBot pink.

    The generated CSS contains colors derived from the old purple via Sass
    darken()/lighten()/mix(). Their exact RGB values are not in the literal
    map above, but they are all purple-ish. Preserve saturation and value so
    borders, rubberbands, and gradients keep their original contrast.
    """
    r, g, b = rgb
    if not (b > r >= g and b - g > 12):
        return None

    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if v < 0.35 or s < 0.10:
        return None

    nr, ng, nb = colorsys.hsv_to_rgb(PINK_HUE / 360, s, v)
    return (round(nr * 255), round(ng * 255), round(nb * 255))


def replace_rgba(text: str) -> str:
    pattern = re.compile(
        r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)"
    )

    def repl(match: re.Match[str]) -> str:
        rgb = tuple(int(match.group(i)) for i in range(1, 4))
        alpha = match.group(4)
        mapped = RGBA_MAP.get(rgb)
        if mapped is None:
            mapped = pinkify_purple(rgb)
        if mapped is None:
            return match.group(0)
        return f"rgba({mapped[0]}, {mapped[1]}, {mapped[2]}, {alpha})"

    return pattern.sub(repl, text)


def process_css(path: Path) -> bool:
    original = path.read_text()
    text = replace_in_suggested_blocks(original)
    text = replace_hex(text)
    text = replace_rgba(text)
    text = fix_link_backdrop(text)
    if text == original:
        return False
    path.write_text(text)
    return True


def process_svg(path: Path) -> bool:
    original = path.read_text()
    text = replace_hex(original)
    if text == original:
        return False
    path.write_text(text)
    return True


def process_text(path: Path) -> bool:
    original = path.read_text()
    text = replace_hex(original)
    if text == original:
        return False
    path.write_text(text)
    return True


def recolor_rgba(px: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    r, g, b, a = px
    if a < 8:
        return px

    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    h *= 360

    # Neutral/dark UI surfaces must stay Dracula neutrals.
    if s < 0.25 or v < 0.30:
        return px

    # Green and existing cyan accents -> secondary. Preserve value to keep
    # anti-aliasing; the brightest pixels become the full secondary color.
    if 75 <= h <= 225:
        nh, ns, nv = (
            CYAN_HSV[0] * 360,
            round(CYAN_HSV[1], 2),
            min(v, round(CYAN_HSV[2], 3)),
        )
    # Purple/pink accents -> primary. The saturation threshold keeps
    # neutral dark surfaces such as #44475d untouched.
    elif 225 < h <= 345 and s >= 0.34:
        nh, ns, nv = PINK_HUE_ASSET, round(PINK_HSV[1], 2), 1.0
    else:
        return px

    nr, ng, nb = colorsys.hsv_to_rgb(nh / 360, ns, nv)
    return (round(nr * 255), round(ng * 255), round(nb * 255), a)


def process_png(path: Path) -> bool:
    image = Image.open(path)
    if image.mode not in ("RGBA", "RGB", "P"):
        return False
    rgba = image.convert("RGBA")
    pixels = list(rgba.getdata())
    recolored = [recolor_rgba(px) for px in pixels]
    if recolored == pixels:
        return False
    out = Image.new("RGBA", rgba.size)
    out.putdata(recolored)
    out.save(path, optimize=True)
    return True


def main() -> int:
    changed: list[str] = []

    for rel in CSS_FILES:
        path = ROOT / rel
        if path.exists() and process_css(path):
            changed.append(rel)

    for rel in TEXT_FILES:
        path = ROOT / rel
        if path.exists() and process_text(path):
            changed.append(rel)

    for rel in SVG_FILES:
        path = ROOT / rel
        if path.exists() and process_svg(path):
            changed.append(rel)

    for rel_dir in SVG_DIRS:
        for path in sorted((ROOT / rel_dir).rglob("*.svg")):
            if process_svg(path):
                changed.append(str(path.relative_to(ROOT)))

    for rel_dir in PNG_DIRS:
        for path in sorted((ROOT / rel_dir).glob("*.png")):
            if process_png(path):
                changed.append(str(path.relative_to(ROOT)))

    print(f"Updated {len(changed)} file(s).")
    for item in changed:
        print(f"  {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
