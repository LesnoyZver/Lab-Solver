#!/usr/bin/env python3
"""Render real program output as a PNG screenshot: black monospace text on white.

Usage:
    python3 scripts/make_screenshot.py out.png --text "program output"
    python3 scripts/make_screenshot.py out.png --text-file output.txt

The public helper is render(text, out_path). Exits with code 3 and a message
when Pillow is unavailable or no monospace font with Cyrillic is installed.
"""

import argparse
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None

FONT_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/cour.ttf",
]
SIZE = 22
PAD = 24


def _load_font(size=SIZE):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return None


def render(text, out_path, size=SIZE, pad=PAD):
    if Image is None:
        raise RuntimeError("Pillow is not available")
    font = _load_font(size)
    if font is None:
        raise RuntimeError("no monospace font with Cyrillic found")

    lines = text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n").split("\n")
    try:
        width = max(int(font.getlength(line)) for line in lines) + 2 * pad
    except AttributeError:
        width = max(font.getsize(line)[0] for line in lines) + 2 * pad
    step = int(size * 1.35)
    height = step * len(lines) + 2 * pad

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    y = pad
    for line in lines:
        draw.text((pad, y), line, font=font, fill="black")
        y += step
    image.save(str(out_path))
    return out_path


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--text", default="")
    parser.add_argument("--text-file")
    args = parser.parse_args(argv)

    if Image is None:
        print("Pillow is not available", file=sys.stderr)
        return 3

    text = args.text
    if args.text_file:
        with open(args.text_file, encoding="utf-8") as fh:
            text = fh.read()
    try:
        render(text, args.out)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    print("saved: " + args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
