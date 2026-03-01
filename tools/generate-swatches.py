#!/usr/bin/env python3
"""Extract colors from .terminal files and generate Rothko-style SVG swatches."""

import glob
import os
import plistlib
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
SWATCH_DIR = os.path.join(ROOT_DIR, ".github", "swatches")

COLOR_KEYS = [
    "ANSIBlackColor", "ANSIRedColor", "ANSIGreenColor", "ANSIYellowColor",
    "ANSIBlueColor", "ANSIMagentaColor", "ANSICyanColor", "ANSIWhiteColor",
    "ANSIBrightBlackColor", "ANSIBrightRedColor", "ANSIBrightGreenColor",
    "ANSIBrightYellowColor", "ANSIBrightBlueColor", "ANSIBrightMagentaColor",
    "ANSIBrightCyanColor", "ANSIBrightWhiteColor",
]


def extract_rgb(data: bytes) -> str:
    """Decode NSKeyedArchiver color data to hex color string."""
    inner = plistlib.loads(data)
    rgb_bytes = inner["$objects"][1]["NSRGB"]
    floats = [float(x) for x in rgb_bytes.decode("ascii").split()]
    return "#{:02x}{:02x}{:02x}".format(*(int(f * 255) for f in floats))


def slug(name: str) -> str:
    """Convert theme name to a filename slug."""
    # Strip "Rothko — " prefix, lowercase, replace spaces with hyphens
    short = re.sub(r"^Rothko\s*[—–-]\s*", "", name)
    return re.sub(r"[^a-z0-9]+", "-", short.lower()).strip("-")


def generate_svg(name: str, bg: str, fg: str, colors: list[str]) -> str:
    """Generate a Rothko-style SVG swatch.

    Layout: stacked horizontal bands on the background color.
    Top band = foreground/text color.
    Middle rows = 8 standard ANSI colors, then 8 bright variants.
    """
    w, h = 360, 200
    pad = 16
    gap = 6
    inner_w = w - pad * 2

    # Two rows of 8 color blocks each (standard + bright)
    block_w = (inner_w - 7 * gap) / 8
    row_h = 40
    fg_band_h = 28

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f'  <rect width="{w}" height="{h}" rx="8" fill="{bg}"/>',
        "",
        f'  <!-- foreground band -->',
        f'  <rect x="{pad}" y="{pad}" width="{inner_w}" height="{fg_band_h}" rx="4" fill="{fg}" opacity="0.9"/>',
    ]

    # Standard ANSI colors (first 8)
    y1 = pad + fg_band_h + gap * 2
    for i, c in enumerate(colors[:8]):
        x = pad + i * (block_w + gap)
        lines.append(f'  <rect x="{x:.1f}" y="{y1}" width="{block_w:.1f}" height="{row_h}" rx="3" fill="{c}"/>')

    # Bright ANSI colors (last 8)
    y2 = y1 + row_h + gap
    for i, c in enumerate(colors[8:16]):
        x = pad + i * (block_w + gap)
        lines.append(f'  <rect x="{x:.1f}" y="{y2}" width="{block_w:.1f}" height="{row_h}" rx="3" fill="{c}"/>')

    lines.append("</svg>")
    return "\n".join(lines)


def main():
    os.makedirs(SWATCH_DIR, exist_ok=True)
    terminal_files = sorted(glob.glob(os.path.join(ROOT_DIR, "*.terminal")))

    for path in terminal_files:
        with open(path, "rb") as f:
            plist = plistlib.load(f)

        name = plist["name"]
        bg = extract_rgb(plist["BackgroundColor"])
        fg = extract_rgb(plist["TextColor"])
        colors = [extract_rgb(plist[k]) for k in COLOR_KEYS]

        svg = generate_svg(name, bg, fg, colors)
        out_path = os.path.join(SWATCH_DIR, f"{slug(name)}.svg")
        with open(out_path, "w") as f:
            f.write(svg)
        print(f"  {slug(name)}.svg")

    print(f"\nGenerated {len(terminal_files)} swatches in .github/swatches/")


if __name__ == "__main__":
    main()
