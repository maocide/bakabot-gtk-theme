#!/usr/bin/env python3
"""Apply structural BakaBot fixes to the vendored Dracula base CSS.

These are not palette substitutions. They repair upstream behavior that GTK
3.20/4.0 needs for this theme, and must run before apply_palette.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"base fix not found: {label}")
    return text.replace(old, new, 1)


def fix_panel_buttons(text: str) -> str:
    old_tasklist = """#tasklist-button {
  color: rgba(255, 255, 255, 0.8);
  border-radius: 0;
  border: none;
  background-color: #1e1f29; }"""
    new_tasklist = """#tasklist-button {
  color: rgba(255, 255, 255, 0.8);
  border-radius: 0;
  border: none;
  background-color: transparent; }"""
    text = replace_once(text, old_tasklist, new_tasklist, "xfce tasklist background")

    old_button = """.xfce4-panel.background button.flat {
  color: white;
  border-radius: 0;
  border: none;
  background-color: #1e1f29;
  font-weight: normal; }"""
    new_button = """.xfce4-panel.background button.flat {
  color: white;
  border-radius: 0;
  border: none;
  background-color: transparent;
  font-weight: normal; }"""
    text = replace_once(text, old_button, new_button, "xfce panel button background")
    return text


def fix_titlebuttons_320(text: str) -> str:
    old = """  button.titlebutton.close:backdrop, button.titlebutton.minimize:backdrop, button.titlebutton.maximize:backdrop {
    background-image: -gtk-scaled(url("../assets/close_unfocused.png"), url("../assets/close_unfocused@2.png")); }"""
    new = """  button.titlebutton.close:backdrop {
    background-image: -gtk-scaled(url("../assets/close_unfocused.png"), url("../assets/close_unfocused@2.png")); }
  button.titlebutton.minimize:backdrop {
    background-image: -gtk-scaled(url("../assets/min_unfocused.png"), url("../assets/min_unfocused@2.png")); }
  button.titlebutton.maximize:backdrop {
    background-image: -gtk-scaled(url("../assets/maximize_unfocused.png"), url("../assets/maximize_unfocused@2.png")); }"""
    return replace_once(text, old, new, "gtk3 titlebutton backdrop")


def fix_titlebuttons_40(text: str) -> str:
    old = """windowcontrols button:backdrop {
  -gtk-icon-shadow: none;
  background-image: -gtk-scaled(url("../assets/close_unfocused.png"), url("../assets/close_unfocused@2.png")); }"""
    new = """windowcontrols button.close:backdrop {
  background-image: -gtk-scaled(url("../assets/close_unfocused.png"), url("../assets/close_unfocused@2.png")); }
windowcontrols button.minimize:backdrop {
  background-image: -gtk-scaled(url("../assets/min_unfocused.png"), url("../assets/min_unfocused@2.png")); }
windowcontrols button.maximize:backdrop {
  background-image: -gtk-scaled(url("../assets/maximize_unfocused.png"), url("../assets/maximize_unfocused@2.png")); }
windowcontrols button:backdrop {
  -gtk-icon-shadow: none; }"""
    return replace_once(text, old, new, "gtk4 titlebutton backdrop")


def fix_gtk4_height(text: str) -> str:
    old = """.nautilus-window .path-buttons-box, .nautilus-window #NautilusPathBar {
  background: transparent;
  height: 20px;
  margin-top: 7px;
  margin-bottom: 7px; }"""
    new = """.nautilus-window .path-buttons-box, .nautilus-window #NautilusPathBar {
  background: transparent;
  min-height: 20px;
  margin-top: 7px;
  margin-bottom: 7px; }"""
    return replace_once(text, old, new, "gtk4 nautilus height")


def process(path: Path, fixes: list) -> None:
    text = path.read_text()
    for fix in fixes:
        text = fix(text)
    path.write_text(text)


def main() -> int:
    for name in ("gtk.css", "gtk-dark.css"):
        process(ROOT / "gtk-3.20" / name, [fix_panel_buttons, fix_titlebuttons_320])
        process(ROOT / "gtk-4.0" / name, [fix_titlebuttons_40, fix_gtk4_height])
    print("Applied structural base fixes to gtk-3.20 and gtk-4.0 CSS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
