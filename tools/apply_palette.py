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

# Literal accent colors used by the generated CSS and assets.
HEX_MAP = {
    "#bd93f9": "#ff85b3",  # Dracula purple -> BakaBot pink
    "#ff79c6": "#ff85b3",  # old Dracula pink -> BakaBot pink
    "#ff69b4": "#ff85b3",  # hot pink leftovers -> BakaBot pink
    "#50fa7a": "#00e0e0",  # Dracula green -> BakaBot cyan
    "#50fa7b": "#00e0e0",
    "#72bfd0": "#00e0e0",  # muted cyan -> BakaBot cyan
    "#13b1d5": "#00e0e0",  # link blue -> cyan
    "#8be9fd": "#00e0e0",  # legacy cyan -> cyan
    "#4caec3": "#00e0e0",  # success cyan -> cyan
    "#5fb6ca": "#00e0e0",
    "#a1ce4b": "#00e0e0",  # drop target green -> cyan
    "#13a0bf": "#00e0e0",
    "#2fc9ec": "#33f0f0",  # link hover
    "#82fba0": "#66f0f0",  # info backdrop
    "#98d0dd": "#66f0f0",  # question backdrop
    "#6e5991": "#ff85b3",  # GTK2 purple selection -> pink
}

# RGBA colors need their own map so the alpha value is preserved.
RGBA_MAP = {
    (189, 147, 249): (255, 133, 179),  # purple selection -> pink
    (159, 99, 246): (255, 82, 147),  # darken(selected_bg, 10%) -> pink
    (174, 123, 248): (255, 184, 211),  # lighten(selected_bg, 10%) -> pink
    (255, 105, 180): (255, 133, 179),
    (80, 250, 122): (0, 224, 224),  # green -> cyan
    (80, 250, 123): (0, 224, 224),
    (114, 191, 208): (0, 224, 224),  # muted cyan -> cyan
    (19, 177, 213): (0, 224, 224),  # links -> cyan
    (76, 174, 195): (0, 224, 224),
    (95, 182, 202): (0, 224, 224),
    (19, 160, 191): (0, 224, 224),
    (161, 206, 75): (0, 224, 224),
    (47, 201, 236): (51, 240, 240),
    (130, 251, 160): (102, 240, 240),
    (152, 208, 221): (102, 240, 240),
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
        chunk = re.sub(r"#72bfd0\b", "#ff85b3", chunk, flags=re.IGNORECASE)
        chunk = re.sub(
            r"rgba\(\s*114\s*,\s*191\s*,\s*208\s*,\s*([0-9.]+)\s*\)",
            r"rgba(255, 133, 179, \1)",
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
            "rgba(255, 133, 179, 0.5)", "rgba(0, 224, 224, 0.5)"
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

    nr, ng, nb = colorsys.hsv_to_rgb(337.4 / 360, s, v)
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


def recolor_rgba(px: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    r, g, b, a = px
    if a < 8:
        return px

    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    h *= 360

    # Neutral/dark UI surfaces must stay Dracula neutrals.
    if s < 0.25 or v < 0.30:
        return px

    # Green and existing cyan accents -> BakaBot cyan. Preserve value to keep
    # anti-aliasing; the brightest pixels become exactly #00e0e0.
    if 75 <= h <= 225:
        nh, ns, nv = 180.0, 1.0, min(v, 0.878)
    # Purple/pink accents -> BakaBot pink. The saturation threshold keeps
    # neutral dark surfaces such as #44475d untouched.
    elif 225 < h <= 345 and s >= 0.34:
        nh, ns, nv = 337.0, 0.48, 1.0
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
