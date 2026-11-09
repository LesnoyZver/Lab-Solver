#!/usr/bin/env python3
"""Render real program output as a PNG screenshot: black monospace text on white.

Usage:
    python3 scripts/make_screenshot.py out.png --text "program output"
    python3 scripts/make_screenshot.py out.png --text-file output.txt

The public helper is render(text, out_path, size=SIZE, pad=PAD, wrap=WRAP).
Long lines are wrapped so the picture stays readable after page scaling.
Exits with code 3 and a message when Pillow or a monospace font is unavailable.
"""

import argparse
import re
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
WRAP = 110
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _load_font(size=SIZE):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return None


def _wrap_line(line, width):
    if width <= 0 or len(line) <= width:
        return [line]
    out = []
    rest = line
    while len(rest) > width:
        cut = rest.rfind(" ", 0, width + 1)
        if cut <= 0:
            cut = width
        out.append(rest[:cut].rstrip())
        rest = rest[cut:].lstrip()
    out.append(rest)
    return out


def render(text, out_path, size=SIZE, pad=PAD, wrap=WRAP):
    if Image is None:
        raise RuntimeError("Pillow is not available")
    font = _load_font(size)
    if font is None:
        raise RuntimeError("no monospace font with Cyrillic found")

    text = ANSI.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.replace("\t", "    ").rstrip("\n").split("\n"):
        lines.extend(_wrap_line(line, wrap))

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
    parser.add_argument("--size", type=int, default=SIZE)
    parser.add_argument("--wrap", type=int, default=WRAP)
    args = parser.parse_args(argv)

    if Image is None:
        print("Pillow is not available", file=sys.stderr)
        return 3

    text = args.text
    if args.text_file:
        with open(args.text_file, encoding="utf-8") as fh:
            text = fh.read()
    try:
        render(text, args.out, size=args.size, wrap=args.wrap)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    print("saved: " + args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
