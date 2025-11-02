# -*- coding: utf-8 -*-
"""generate_images.py

Auto-generates PNG images from manifest.csv and set1/*.txt.
Adjusts font, size, and color based on tags.

Required library: Pillow (pip install pillow)
"""
from __future__ import annotations

import csv
import os
import sys
import pathlib
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

JP_FONT_FAMILIES = ["Yu Gothic UI", "Yu Gothic", "Meiryo", "MS Gothic", "MS Mincho"]
JP_FONT_FILES = [
    "YuGothR.ttc",
    "YuGothM.ttc",
    "YuGothB.ttc",
    "msgothic.ttc",
    "msmincho.ttc",
    "meiryo.ttc",
]
JP_MONO_FAMILIES = ["MS Gothic", "MS Mincho"]
JP_MONO_FILES = ["msgothic.ttc", "msmincho.ttc"]
EN_MONO_FAMILIES = ["Consolas", "Courier New"]
EN_MONO_FILES = ["consola.ttf", "cour.ttf", "lucon.ttf"]

DEFAULT_FONT = ImageFont.load_default()


def _load_font(candidate: str, size: int) -> ImageFont.ImageFont | None:
    try:
        # Try loading without index first (for .ttf files)
        return ImageFont.truetype(candidate, size)
    except OSError:
        pass
    
    # Try with index=0 for .ttc files
    try:
        return ImageFont.truetype(candidate, size, index=0)
    except (OSError, AttributeError):
        return None


def pick_font(families, size: int, fallback_files) -> ImageFont.ImageFont:
    # Direct file path approach - skip font name resolution
    # NOTE: Windows-specific paths. For Linux/macOS, add font paths manually:
    #   Linux: /usr/share/fonts/truetype/...
    #   macOS: /System/Library/Fonts/... or ~/Library/Fonts/...
    windows_dir = pathlib.Path(os.environ.get("WINDIR", "C:\\Windows"))
    font_paths = [
        windows_dir / "Fonts" / filename
        for filename in fallback_files
    ]

    for path in font_paths:
        if path.exists():
            font = _load_font(str(path), size)
            if font:
                return font

    print(f"[WARN] Font fallback: {fallback_files} -> default font", file=sys.stderr)
    return DEFAULT_FONT


def resolve_font(lang: str, tags: str, size: int) -> ImageFont.ImageFont:
    tag_list = tags.split("-")
    if "mono" in tag_list and "code" in tag_list:
        if lang == "EN":
            return pick_font(EN_MONO_FAMILIES, size, EN_MONO_FILES)
        return pick_font(JP_MONO_FAMILIES, size, JP_MONO_FILES)
    return pick_font(JP_FONT_FAMILIES, size, JP_FONT_FILES)


def calc_style(lang: str, tags: str) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], int, float, bool, float]:
    bg = (255, 255, 255)
    fg = (0, 0, 0)
    font_size = 14
    line_spacing = 1.4
    invert = "invert" in tags
    
    # Extract tilt angle from tags (e.g., tilt2, tilt5, tilt10)
    import re
    tilt_match = re.search(r"tilt(\d+)", tags)
    tilt_angle = float(tilt_match.group(1)) if tilt_match else 0.0

    if "small" in tags:
        font_size = 11
    if "large" in tags:
        font_size = 18
    if "dense" in tags:
        line_spacing = 1.1
    if "lowcontrast" in tags:
        fg = (153, 153, 153)
    if invert:
        bg, fg = (51, 51, 51), (255, 255, 255)

    return bg, fg, font_size, line_spacing, invert, tilt_angle


def render_text(text: str, font: ImageFont.ImageFont, max_width: int, line_spacing: float):
    # NOTE: Full-width/half-width mixed text may cause slight width errors.
    #       For future: Consider EastAsianWidth module for precise CJK handling.
    lines = []
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    
    for paragraph in text.split("\n"):
        buf = ""
        for ch in paragraph:
            bbox = draw.textbbox((0, 0), buf + ch, font=font)
            width = bbox[2] - bbox[0]
            if width <= max_width:
                buf += ch
            else:
                lines.append(buf)
                buf = ch
        lines.append(buf)
    
    bbox_height = draw.textbbox((0, 0), "Hg", font=font)
    line_height = int((bbox_height[3] - bbox_height[1]) * line_spacing)
    return lines, line_height


def draw_image(text: str, lang: str, tags: str, out_path: pathlib.Path) -> None:
    bg, fg, font_size, line_spacing, invert, tilt_angle = calc_style(lang, tags)
    font = resolve_font(lang, tags, font_size)
    
    # Warn if using default font (potential garbled text)
    if font == DEFAULT_FONT:
        print(f"[WARN] Using default font for {out_path.name} - Japanese text may be garbled", file=sys.stderr)

    # NOTE: For high-DPI testing (120dpi/200dpi), scale width/padding proportionally.
    #       Current: 96dpi baseline (1200px @ padding=40)
    width = 1200
    padding = 40
    max_width = width - padding * 2

    lines, line_height = render_text(text, font, max_width, line_spacing)
    height = padding * 2 + max(line_height, line_height * len(lines))

    # NOTE: RGB mode (no alpha). For future transparency needs, use "RGBA".
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    y = padding
    for ln in lines:
        draw.text((padding, y), ln, font=font, fill=fg)
        y += line_height

    if tilt_angle != 0:
        img = img.rotate(tilt_angle, expand=True, fillcolor=bg)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    print(f"[IMAGE] Generated: {out_path}")


def main(manifest="test_images/set1/manifest.csv", root="test_images/set1") -> None:
    root_path = pathlib.Path(root)
    manifest_path = pathlib.Path(manifest)

    with manifest_path.open(encoding="utf-8") as fp:
        rows = list(csv.DictReader(fp))

    for row in rows:
        txt_path = root_path / row["file"].replace(".png", ".txt")
        if not txt_path.exists():
            print(f"[WARN] TXT not found: {txt_path}", file=sys.stderr)
            continue
        text = txt_path.read_text(encoding="utf-8")
        draw_image(text, row["lang"], row["tags"], root_path / row["file"])


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        main(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        main()
