#!/usr/bin/env python3
"""Generate BakaBot's monochrome window buttons.

Outputs:
  * xfwm4 titlebar buttons (28x32 PNG + SVG source)
  * GTK CSD titlebutton assets (16x16 / 32x32 PNG + SVG source)

The design is intentionally classic: minimize is an underscore, maximize is a
square, close is an X, and maximized windows use a restore glyph.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent

BG = (30, 31, 41)  # #1e1f29, titlebar background
HOVER_BG = (52, 53, 70)  # #343546
PRESS_BG = (40, 42, 54)  # #282a36
ACTIVE_GLYPH = (200, 204, 214)  # #c8ccd6
INACTIVE_GLYPH = (111, 116, 131)  # #6f7483
HOVER_GLYPH = (248, 248, 242)  # #f8f8f2
PRESS_GLYPH = (255, 255, 255)
CLOSE_HOVER = (255, 85, 85)  # #ff5555

SCALE = 4


def rgba(color: tuple[int, int, int], alpha: int = 255) -> tuple[int, int, int, int]:
    return (*color, alpha)


def draw_glyph(
    draw: ImageDraw.ImageDraw,
    action: str,
    color: tuple[int, int, int],
    box: tuple[float, float, float, float],
    width: float,
    fill_bg: tuple[int, int, int] | None = None,
) -> None:
    """Draw a glyph inside box=(left, top, right, bottom)."""
    left, top, right, bottom = box
    cx = (left + right) / 2
    cy = (top + bottom) / 2
    stroke = rgba(color)

    if action == "close":
        draw.line((left, top, right, bottom), fill=stroke, width=round(width))
        draw.line((right, top, left, bottom), fill=stroke, width=round(width))
    elif action == "hide":
        y = bottom - width / 2
        draw.line((left, y, right, y), fill=stroke, width=round(width))
    elif action == "maximize":
        draw.rectangle((left, top, right, bottom), outline=stroke, width=round(width))
    elif action == "maximize-toggled":
        back = (left - 1, top - 2, right - 3, bottom - 4)
        front = (left + 2, top + 2, right, bottom)
        draw.rectangle(back, outline=stroke, width=round(width))
        if fill_bg is not None:
            draw.rectangle(front, fill=rgba(fill_bg), outline=rgba(fill_bg))
        draw.rectangle(front, outline=stroke, width=round(width))
    elif action == "menu":
        for y in (top, cy, bottom):
            draw.line((left, y, right, y), fill=stroke, width=round(width))
    elif action == "shade":
        mid = (left + right) / 2
        draw.line((left, top, mid, bottom), fill=stroke, width=round(width))
        draw.line((mid, bottom, right, top), fill=stroke, width=round(width))
    elif action == "stick":
        r = (right - left) / 4
        draw.ellipse((cx - r, top, cx + r, top + 2 * r), outline=stroke, width=round(width))
        draw.line((cx, top + 2 * r, cx, bottom), fill=stroke, width=round(width))
        draw.line((cx - r * 1.6, bottom, cx + r * 1.6, bottom), fill=stroke, width=round(width))
    else:
        raise ValueError(f"unknown action: {action}")


def render_png(
    path: Path,
    size: tuple[int, int],
    action: str,
    glyph_color: tuple[int, int, int],
    background: tuple[int, int, int] | None,
    glyph_box: tuple[float, float, float, float],
    line_width: float,
) -> None:
    width, height = size
    im = Image.new("RGBA", (width * SCALE, height * SCALE), rgba(background or (0, 0, 0), 0))
    draw = ImageDraw.Draw(im)

    if background is not None:
        draw.rectangle((0, 0, width * SCALE, height * SCALE), fill=rgba(background))

    box = tuple(v * SCALE for v in glyph_box)
    draw_glyph(
        draw,
        action,
        glyph_color,
        box,
        line_width * SCALE,
        fill_bg=background,
    )
    im = im.resize((width, height), Image.Resampling.LANCZOS)
    if background is None:
        im.save(path, optimize=True)
    else:
        im.convert("RGB").save(path, optimize=True)


def svg_glyph(
    action: str,
    color: str,
    box: tuple[float, float, float, float],
    width: float,
    fill_bg: str | None = None,
) -> str:
    left, top, right, bottom = box
    cx = (left + right) / 2
    cy = (top + bottom) / 2
    common = f'fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"'

    if action == "close":
        return (
            f'<line x1="{left}" y1="{top}" x2="{right}" y2="{bottom}" {common}/>'
            f'<line x1="{right}" y1="{top}" x2="{left}" y2="{bottom}" {common}/>'
        )
    if action == "hide":
        y = bottom - width / 2
        return f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" {common}/>'
    if action == "maximize":
        return f'<rect x="{left}" y="{top}" width="{right-left}" height="{bottom-top}" {common}/>'
    if action == "maximize-toggled":
        back = (left - 1, top - 2, right - 3, bottom - 4)
        front = (left + 2, top + 2, right, bottom)
        fill = f'<rect x="{front[0]}" y="{front[1]}" width="{front[2]-front[0]}" height="{front[3]-front[1]}" fill="{fill_bg}"/>' if fill_bg else ""
        return (
            f'<rect x="{back[0]}" y="{back[1]}" width="{back[2]-back[0]}" height="{back[3]-back[1]}" {common}/>'
            f"{fill}"
            f'<rect x="{front[0]}" y="{front[1]}" width="{front[2]-front[0]}" height="{front[3]-front[1]}" {common}/>'
        )
    if action == "menu":
        return "".join(
            f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" {common}/>'
            for y in (top, cy, bottom)
        )
    if action == "shade":
        mid = (left + right) / 2
        return (
            f'<polyline points="{left},{top} {mid},{bottom} {right},{top}" {common}/>'
        )
    if action == "stick":
        r = (right - left) / 4
        return (
            f'<circle cx="{cx}" cy="{top + r}" r="{r}" {common}/>'
            f'<line x1="{cx}" y1="{top + 2*r}" x2="{cx}" y2="{bottom}" {common}/>'
            f'<line x1="{cx - r*1.6}" y1="{bottom}" x2="{cx + r*1.6}" y2="{bottom}" {common}/>'
        )
    raise ValueError(action)


def svg_document(width: int, height: int, body: str, background: str | None) -> str:
    bg = f'  <rect width="{width}" height="{height}" fill="{background}"/>\n' if background else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n{bg}  {body}\n</svg>\n'
    )


def hex_color(color: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % color


def main() -> None:
    xfwm4_dir = ROOT / "xfwm4"
    xfwm4_assets = xfwm4_dir / "assets"
    xfwm4_assets.mkdir(parents=True, exist_ok=True)

    actions = ["close", "hide", "maximize", "maximize-toggled", "menu", "shade", "stick"]
    states = {
        "active": (BG, ACTIVE_GLYPH),
        "inactive": (BG, INACTIVE_GLYPH),
        "prelight": (HOVER_BG, HOVER_GLYPH),
        "pressed": (PRESS_BG, PRESS_GLYPH),
    }

    for action in actions:
        for state, (bg, glyph) in states.items():
            state_glyph = CLOSE_HOVER if action == "close" and state in ("prelight", "pressed") else glyph
            box = (9.0, 11.0, 19.0, 21.0)
            png_path = xfwm4_dir / f"{action}-{state}.png"
            render_png(png_path, (28, 32), action, state_glyph, bg, box, 1.6)

            svg_path = xfwm4_assets / f"{action}-{state}.svg"
            body = svg_glyph(action, hex_color(state_glyph), box, 1.6, hex_color(bg))
            svg_path.write_text(svg_document(28, 32, body, hex_color(bg)))

    # GTK CSD titlebutton assets. These are transparent glyph-only images.
    csd = {
        "close": ("close", ACTIVE_GLYPH),
        "close_prelight": ("close", CLOSE_HOVER),
        "close_unfocused": ("close", INACTIVE_GLYPH),
        "maximize": ("maximize", ACTIVE_GLYPH),
        "maximize_prelight": ("maximize", HOVER_GLYPH),
        "maximize_unfocused": ("maximize", INACTIVE_GLYPH),
        "min": ("hide", ACTIVE_GLYPH),
        "min_prelight": ("hide", HOVER_GLYPH),
        "min_unfocused": ("hide", INACTIVE_GLYPH),
    }

    assets_dir = ROOT / "assets"
    for name, (action, glyph) in csd.items():
        box = (4.0, 4.0, 12.0, 12.0)
        render_png(assets_dir / f"{name}.png", (16, 16), action, glyph, None, box, 1.4)
        render_png(assets_dir / f"{name}@2.png", (32, 32), action, glyph, None, (8.0, 8.0, 24.0, 24.0), 2.8)
        svg_path = assets_dir / f"{name}.svg"
        svg_path.write_text(svg_document(16, 16, svg_glyph(action, hex_color(glyph), box, 1.4), None))

    # Pressed SVGs are referenced by the legacy GTK3 stylesheet.
    pressed = {
        "close_pressed": ("close", CLOSE_HOVER),
        "maximize_pressed": ("maximize", HOVER_GLYPH),
        "min_pressed": ("hide", HOVER_GLYPH),
    }
    for name, (action, glyph) in pressed.items():
        box = (4.0, 4.0, 12.0, 12.0)
        (assets_dir / f"{name}.svg").write_text(
            svg_document(16, 16, svg_glyph(action, hex_color(glyph), box, 1.4), None)
        )

    print("Generated xfwm4 buttons and GTK CSD titlebutton assets.")


if __name__ == "__main__":
    main()
