# De Amaral Collection — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create seven macOS Terminal color themes tracing Olga de Amaral's career arc from raw fiber to gold to late-career color.

**Architecture:** A Python generator script converts hex color definitions into `.terminal` (NSKeyedArchiver plist) and `.svg` (swatch visualization) files. Each theme is defined as a dictionary of hex colors, generated, visually verified, then committed.

**Tech Stack:** Python 3 (stdlib only: base64, xml), macOS Terminal .terminal plist format, SVG 1.1

---

### Task 1: Write the Theme Generator Script

**Files:**
- Create: `tools/generate_theme.py`

**Step 1: Create the tools directory and generator script**

```python
#!/usr/bin/env python3
"""Generate .terminal and .svg files from hex color definitions."""

import base64
import os
import sys
import json

# --- NSColor blob encoding ---
# The .terminal format uses NSKeyedArchiver binary plists for color values.
# The structure is fixed — only the RGB float string (26 chars) changes.
# Extracted from existing Rothko themes.

_BLOB_PREFIX = base64.b64decode(
    "YnBsaXN0MDDUAQIDBAUGFRhZJGFyY2hpdmVyWCRvYmplY3RzVCR0b3BYJHZlcnNp"
    "b25fEA9OU0tleWVkQXJjaGl2ZXKjBwgPVSRudWxs0wkKCwwNDlYkY2xhc3NcTlND"
    "b2xvclNwYWNlVU5TUkdCgAIQAU8QGg=="
)
_BLOB_SUFFIX = base64.b64decode(
    "0hAREhNYJGNsYXNzZXNaJGNsYXNzbmFtZaITFFdOU0NvbG9yWE5TT2JqZWN00RYX"
    "VHJvb3SAARIAAYagCBEbJCkyREhOVVxpb3FzkJWeqay0vcDFxwAAAAAAAAEBAAAAAAAA"
    "ABkAAAAAAAAAAAAAAAAAAADM"
)


def hex_to_blob(hex_color):
    """Convert #RRGGBB to base64-encoded NSKeyedArchiver NSColor blob."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    rgb = f"{r:.6f} {g:.6f} {b:.6f}"
    assert len(rgb) == 26, f"RGB string wrong length: {len(rgb)}"
    raw = _BLOB_PREFIX + rgb.encode("ascii") + _BLOB_SUFFIX
    return base64.b64encode(raw).decode()


def generate_terminal(name, colors, output_path):
    """Generate a .terminal plist file from a color dictionary.

    colors dict must have keys:
      black, red, green, yellow, blue, magenta, cyan, white,
      bright_black, bright_red, bright_green, bright_yellow,
      bright_blue, bright_magenta, bright_cyan, bright_white,
      background, foreground, bold, cursor, cursor_text, selection
    """
    def blob(key):
        b = hex_to_blob(colors[key])
        # Indent and wrap at ~76 chars to match Apple's format
        lines = [b[i:i+64] for i in range(0, len(b), 64)]
        return "\n\t".join([""] + lines + [""])

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>ANSIBlackColor</key>
\t<data>{blob("black")}</data>
\t<key>ANSIBlueColor</key>
\t<data>{blob("blue")}</data>
\t<key>ANSIBrightBlackColor</key>
\t<data>{blob("bright_black")}</data>
\t<key>ANSIBrightBlueColor</key>
\t<data>{blob("bright_blue")}</data>
\t<key>ANSIBrightCyanColor</key>
\t<data>{blob("bright_cyan")}</data>
\t<key>ANSIBrightGreenColor</key>
\t<data>{blob("bright_green")}</data>
\t<key>ANSIBrightMagentaColor</key>
\t<data>{blob("bright_magenta")}</data>
\t<key>ANSIBrightRedColor</key>
\t<data>{blob("bright_red")}</data>
\t<key>ANSIBrightWhiteColor</key>
\t<data>{blob("bright_white")}</data>
\t<key>ANSIBrightYellowColor</key>
\t<data>{blob("bright_yellow")}</data>
\t<key>ANSICyanColor</key>
\t<data>{blob("cyan")}</data>
\t<key>ANSIGreenColor</key>
\t<data>{blob("green")}</data>
\t<key>ANSIMagentaColor</key>
\t<data>{blob("magenta")}</data>
\t<key>ANSIRedColor</key>
\t<data>{blob("red")}</data>
\t<key>ANSIWhiteColor</key>
\t<data>{blob("white")}</data>
\t<key>ANSIYellowColor</key>
\t<data>{blob("yellow")}</data>
\t<key>BackgroundAlphaInactive</key>
\t<real>1.0</real>
\t<key>BackgroundBlur</key>
\t<real>0.0</real>
\t<key>BackgroundColor</key>
\t<data>{blob("background")}</data>
\t<key>CursorBlink</key>
\t<false/>
\t<key>CursorColor</key>
\t<data>{blob("cursor")}</data>
\t<key>CursorTextColor</key>
\t<data>{blob("cursor_text")}</data>
\t<key>CursorType</key>
\t<integer>0</integer>
\t<key>DisableANSIColor</key>
\t<false/>
\t<key>FontAntialias</key>
\t<true/>
\t<key>FontWidthSpacing</key>
\t<real>1.0</real>
\t<key>ProfileCurrentVersion</key>
\t<real>2.07</real>
\t<key>ScrollbackLines</key>
\t<integer>0</integer>
\t<key>SelectionColor</key>
\t<data>{blob("selection")}</data>
\t<key>ShouldLimitScrollback</key>
\t<integer>0</integer>
\t<key>ShowActiveProcessArgumentsInTitle</key>
\t<false/>
\t<key>ShowActiveProcessInTitle</key>
\t<true/>
\t<key>ShowCommandKeyInTitle</key>
\t<false/>
\t<key>ShowDimensionsInTitle</key>
\t<false/>
\t<key>ShowRepresentedURLInTitle</key>
\t<true/>
\t<key>ShowRepresentedURLPathInTitle</key>
\t<true/>
\t<key>ShowShellCommandInTitle</key>
\t<false/>
\t<key>ShowTTYNameInTitle</key>
\t<false/>
\t<key>ShowWindowSettingsNameInTitle</key>
\t<false/>
\t<key>TextBoldColor</key>
\t<data>{blob("bold")}</data>
\t<key>TextColor</key>
\t<data>{blob("foreground")}</data>
\t<key>UseBoldFonts</key>
\t<true/>
\t<key>UseBrightBold</key>
\t<true/>
\t<key>columnCount</key>
\t<integer>120</integer>
\t<key>name</key>
\t<string>{name}</string>
\t<key>rowCount</key>
\t<integer>36</integer>
\t<key>type</key>
\t<string>Window Settings</string>
</dict>
</plist>
"""
    with open(output_path, "w") as f:
        f.write(xml)


def generate_swatch(colors, output_path):
    """Generate a 360x200 SVG swatch visualization."""
    bg = colors["background"]
    fg = colors["foreground"]

    # ANSI color order: black, red, green, yellow, blue, magenta, cyan, white
    normal = [colors[k] for k in ("black", "red", "green", "yellow",
                                   "blue", "magenta", "cyan", "white")]
    bright = [colors[k] for k in ("bright_black", "bright_red", "bright_green",
                                   "bright_yellow", "bright_blue", "bright_magenta",
                                   "bright_cyan", "bright_white")]

    rects = []
    for i, c in enumerate(normal):
        x = 16.0 + i * 41.75
        rects.append(f'  <rect x="{x:.1f}" y="56" width="35.8" height="40" rx="3" fill="{c}"/>')
    for i, c in enumerate(bright):
        x = 16.0 + i * 41.75
        rects.append(f'  <rect x="{x:.1f}" y="102" width="35.8" height="40" rx="3" fill="{c}"/>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="360" height="200" viewBox="0 0 360 200">
  <rect width="360" height="200" rx="8" fill="{bg}"/>

  <!-- foreground band -->
  <rect x="16" y="16" width="328" height="28" rx="4" fill="{fg}" opacity="0.9"/>
{chr(10).join(rects)}
</svg>"""

    with open(output_path, "w") as f:
        f.write(svg)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 generate_theme.py <theme.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        theme = json.load(f)

    name = theme["name"]
    terminal_path = theme["terminal_path"]
    swatch_path = theme["swatch_path"]
    colors = theme["colors"]

    os.makedirs(os.path.dirname(terminal_path), exist_ok=True)
    os.makedirs(os.path.dirname(swatch_path), exist_ok=True)

    generate_terminal(name, colors, terminal_path)
    generate_swatch(colors, swatch_path)
    print(f"Generated: {terminal_path}")
    print(f"Generated: {swatch_path}")
```

**Step 2: Verify the generator reproduces a known Rothko theme**

Run:
```bash
python3 -c "
import sys; sys.path.insert(0, 'tools')
from generate_theme import hex_to_blob
import base64, re

# Round-trip test: known hex → blob → decode → same hex
test_colors = ['#13110f', '#a84828', '#c87028', '#d8b887', '#ffffff', '#000000']
for h in test_colors:
    blob = hex_to_blob(h)
    raw = base64.b64decode(blob)
    m = re.search(r'([\d.]+ [\d.]+ [\d.]+)', raw.decode('latin-1'))
    parts = m.group(1).split()
    back = '#{:02x}{:02x}{:02x}'.format(*[round(float(x)*255) for x in parts])
    status = 'PASS' if h == back else 'FAIL'
    print(f'{status}: {h} → {back}')
"
```

Expected: All PASS.

**Step 3: Commit**

```bash
git add tools/generate_theme.py
git commit -m "Add theme generator script for .terminal and .svg files"
```

---

### Task 2: Define and Generate — Muro Tejido

The most austere theme. Raw wool, horsehair, undyed linen. 1970s woven walls.

**Files:**
- Create: `themes/muro-tejido.json`
- Create: `de-amaral/De Amaral — Muro Tejido.terminal`
- Create: `.github/swatches/muro-tejido.svg`

**Step 1: Create the theme definition**

```json
{
  "name": "De Amaral — Muro Tejido",
  "terminal_path": "de-amaral/De Amaral — Muro Tejido.terminal",
  "swatch_path": ".github/swatches/muro-tejido.svg",
  "colors": {
    "black":          "#0d0b08",
    "red":            "#8b5e3c",
    "green":          "#5a6040",
    "yellow":         "#967838",
    "blue":           "#3a3540",
    "magenta":        "#6b4a48",
    "cyan":           "#3e4a45",
    "white":          "#a89880",
    "bright_black":   "#2c2419",
    "bright_red":     "#b06a42",
    "bright_green":   "#707a4a",
    "bright_yellow":  "#b89858",
    "bright_blue":    "#585268",
    "bright_magenta": "#8a6058",
    "bright_cyan":    "#587068",
    "bright_white":   "#d4c8b0",
    "background":     "#1a1510",
    "foreground":     "#c4b498",
    "bold":           "#d4c8b0",
    "cursor":         "#967838",
    "cursor_text":    "#1a1510",
    "selection":      "#2c2419"
  }
}
```

**Step 2: Generate the theme files**

Run: `python3 tools/generate_theme.py themes/muro-tejido.json`

Expected:
```
Generated: de-amaral/De Amaral — Muro Tejido.terminal
Generated: .github/swatches/muro-tejido.svg
```

**Step 3: Visually verify the swatch SVG**

Open `.github/swatches/muro-tejido.svg` in a browser. Verify:
- Dark background, warm tones throughout
- Yellow/gold slots are muted ochre (not bright)
- Blues are barely blue — dark shadows
- Overall impression: raw, austere, earthy

**Step 4: Commit**

```bash
git add themes/muro-tejido.json "de-amaral/De Amaral — Muro Tejido.terminal" .github/swatches/muro-tejido.svg
git commit -m "Add De Amaral — Muro Tejido theme

Raw wool and horsehair. After the woven wall works, 1970s."
```

---

### Task 3: Define and Generate — Hojarasca

Autumn leaf litter. Warm mid-tone background. Decomposing greens and burnt sienna.

**Files:**
- Create: `themes/hojarasca.json`
- Create: `de-amaral/De Amaral — Hojarasca.terminal`
- Create: `.github/swatches/hojarasca.svg`

**Step 1: Create the theme definition**

```json
{
  "name": "De Amaral — Hojarasca",
  "terminal_path": "de-amaral/De Amaral — Hojarasca.terminal",
  "swatch_path": ".github/swatches/hojarasca.svg",
  "colors": {
    "black":          "#1a1408",
    "red":            "#a85830",
    "green":          "#607040",
    "yellow":         "#b89038",
    "blue":           "#404858",
    "magenta":        "#7a4840",
    "cyan":           "#486050",
    "white":          "#b8a878",
    "bright_black":   "#524028",
    "bright_red":     "#c86838",
    "bright_green":   "#809858",
    "bright_yellow":  "#d8b050",
    "bright_blue":    "#586878",
    "bright_magenta": "#985858",
    "bright_cyan":    "#688868",
    "bright_white":   "#e8d8a8",
    "background":     "#3a2e20",
    "foreground":     "#d4b878",
    "bold":           "#e8d8a8",
    "cursor":         "#d8b050",
    "cursor_text":    "#3a2e20",
    "selection":      "#524028"
  }
}
```

**Step 2: Generate the theme files**

Run: `python3 tools/generate_theme.py themes/hojarasca.json`

**Step 3: Visually verify the swatch SVG**

Open `.github/swatches/hojarasca.svg` in a browser. Verify:
- Warm mid-brown background (noticeably lighter than Muro Tejido)
- Autumn palette — burnt sienna, olive, dried gold
- Bright yellow is golden-leaf colored
- Blues are muted twilight — present but subdued

**Step 4: Commit**

```bash
git add themes/hojarasca.json "de-amaral/De Amaral — Hojarasca.terminal" .github/swatches/hojarasca.svg
git commit -m "Add De Amaral — Hojarasca theme

Leaf litter and autumn decay. After the Hojarasca series, late 1970s."
```

---

### Task 4: Define and Generate — Alquimia

The signature theme. Deep brown background. Gold dominant. Saffron linen and gold leaf.

**Files:**
- Create: `themes/alquimia.json`
- Create: `de-amaral/De Amaral — Alquimia.terminal`
- Create: `.github/swatches/alquimia.svg`

**Step 1: Create the theme definition**

```json
{
  "name": "De Amaral — Alquimia",
  "terminal_path": "de-amaral/De Amaral — Alquimia.terminal",
  "swatch_path": ".github/swatches/alquimia.svg",
  "colors": {
    "black":          "#0e0a04",
    "red":            "#a04020",
    "green":          "#506838",
    "yellow":         "#c89830",
    "blue":           "#384058",
    "magenta":        "#784038",
    "cyan":           "#3a5848",
    "white":          "#b8a070",
    "bright_black":   "#382810",
    "bright_red":     "#c85828",
    "bright_green":   "#689848",
    "bright_yellow":  "#e8b840",
    "bright_blue":    "#4a5878",
    "bright_magenta": "#985048",
    "bright_cyan":    "#508868",
    "bright_white":   "#e8d090",
    "background":     "#1c1408",
    "foreground":     "#d4a850",
    "bold":           "#e8d090",
    "cursor":         "#e8b840",
    "cursor_text":    "#1c1408",
    "selection":      "#382810"
  }
}
```

**Step 2: Generate the theme files**

Run: `python3 tools/generate_theme.py themes/alquimia.json`

**Step 3: Visually verify the swatch SVG**

Open `.github/swatches/alquimia.svg` in a browser. Verify:
- Deep brown background
- Yellow slots are the stars — bright gold dominates
- Foreground band reads as gold/saffron
- Blues are shadow-on-gold, not sky-blue
- Cyans are verdigris (green-blue patina)
- Magentas are wine/cochineal, not pink

**Step 4: Commit**

```bash
git add themes/alquimia.json "de-amaral/De Amaral — Alquimia.terminal" .github/swatches/alquimia.svg
git commit -m "Add De Amaral — Alquimia theme

Gold leaf on fiber. After the Alquimia series, 1984."
```

---

### Task 5: Define and Generate — Alquimia Plata

Nocturnal counterpart. Cool dark background. Silver metallics, blue-greys, lavender.

**Files:**
- Create: `themes/alquimia-plata.json`
- Create: `de-amaral/De Amaral — Alquimia Plata.terminal`
- Create: `.github/swatches/alquimia-plata.svg`

**Step 1: Create the theme definition**

```json
{
  "name": "De Amaral — Alquimia Plata",
  "terminal_path": "de-amaral/De Amaral — Alquimia Plata.terminal",
  "swatch_path": ".github/swatches/alquimia-plata.svg",
  "colors": {
    "black":          "#0a0a10",
    "red":            "#885048",
    "green":          "#506858",
    "yellow":         "#988868",
    "blue":           "#3a4868",
    "magenta":        "#685078",
    "cyan":           "#3a5868",
    "white":          "#a0a0b0",
    "bright_black":   "#303038",
    "bright_red":     "#a86858",
    "bright_green":   "#688878",
    "bright_yellow":  "#b8a878",
    "bright_blue":    "#5868a8",
    "bright_magenta": "#886898",
    "bright_cyan":    "#588898",
    "bright_white":   "#d0d0e0",
    "background":     "#18181e",
    "foreground":     "#b8b8c8",
    "bold":           "#d0d0e0",
    "cursor":         "#b8b8c8",
    "cursor_text":    "#18181e",
    "selection":      "#303038"
  }
}
```

**Step 2: Generate the theme files**

Run: `python3 tools/generate_theme.py themes/alquimia-plata.json`

**Step 3: Visually verify the swatch SVG**

Open `.github/swatches/alquimia-plata.svg` in a browser. Verify:
- Cool charcoal background — clearly different from the warm themes
- Blues and cyans are more prominent than other themes
- Yellows shifted toward tarnished silver, not gold
- Magentas are lavender/plum — cooler than the cochineal of warm themes
- Overall impression: moonlit, metallic

**Step 4: Commit**

```bash
git add themes/alquimia-plata.json "de-amaral/De Amaral — Alquimia Plata.terminal" .github/swatches/alquimia-plata.svg
git commit -m "Add De Amaral — Alquimia Plata theme

Silver leaf in shadow. After the silver alchemy works, 1980s–90s."
```

---

### Task 6: Define and Generate — Strata

Geological layers. Dark background. Ochre, terracotta, clay, sand. Compressed earth.

**Files:**
- Create: `themes/strata.json`
- Create: `de-amaral/De Amaral — Strata.terminal`
- Create: `.github/swatches/strata.svg`

**Step 1: Create the theme definition**

```json
{
  "name": "De Amaral — Strata",
  "terminal_path": "de-amaral/De Amaral — Strata.terminal",
  "swatch_path": ".github/swatches/strata.svg",
  "colors": {
    "black":          "#0c0a08",
    "red":            "#a85838",
    "green":          "#587048",
    "yellow":         "#b08830",
    "blue":           "#384058",
    "magenta":        "#784840",
    "cyan":           "#405850",
    "white":          "#a89878",
    "bright_black":   "#302818",
    "bright_red":     "#c86848",
    "bright_green":   "#70884a",
    "bright_yellow":  "#d0a848",
    "bright_blue":    "#506878",
    "bright_magenta": "#986058",
    "bright_cyan":    "#587868",
    "bright_white":   "#d8c8a0",
    "background":     "#181210",
    "foreground":     "#c8a878",
    "bold":           "#d8c8a0",
    "cursor":         "#d0a848",
    "cursor_text":    "#181210",
    "selection":      "#302818"
  }
}
```

**Step 2: Generate the theme files**

Run: `python3 tools/generate_theme.py themes/strata.json`

**Step 3: Visually verify the swatch SVG**

Open `.github/swatches/strata.svg` in a browser. Verify:
- Very dark earthy background
- Warm terracotta reds, ochre yellows
- Greens are mineral/copper ore tones
- Blues are deep mineral — slate and stone
- Similar warmth to Muro Tejido but richer, more saturated

**Step 4: Commit**

```bash
git add themes/strata.json "de-amaral/De Amaral — Strata.terminal" .github/swatches/strata.svg
git commit -m "Add De Amaral — Strata theme

Compressed earth and mineral layers. After the Strata series, 2000s."
```

---

### Task 7: Define and Generate — Bruma

The most colorful theme. Lighter background. Vivid painted threads. Late-career liberation.

**Files:**
- Create: `themes/bruma.json`
- Create: `de-amaral/De Amaral — Bruma.terminal`
- Create: `.github/swatches/bruma.svg`

**Step 1: Create the theme definition**

```json
{
  "name": "De Amaral — Bruma",
  "terminal_path": "de-amaral/De Amaral — Bruma.terminal",
  "swatch_path": ".github/swatches/bruma.svg",
  "colors": {
    "black":          "#1a1410",
    "red":            "#c83828",
    "green":          "#388848",
    "yellow":         "#d89828",
    "blue":           "#2858a8",
    "magenta":        "#a83868",
    "cyan":           "#2888a0",
    "white":          "#685848",
    "bright_black":   "#584838",
    "bright_red":     "#e85040",
    "bright_green":   "#48a858",
    "bright_yellow":  "#e8b838",
    "bright_blue":    "#3878c8",
    "bright_magenta": "#c84878",
    "bright_cyan":    "#38a8b8",
    "bright_white":   "#484038",
    "background":     "#e8dcd0",
    "foreground":     "#3a3028",
    "bold":           "#1a1410",
    "cursor":         "#3a3028",
    "cursor_text":    "#e8dcd0",
    "selection":      "#d0c0a8"
  }
}
```

Note: This is a light-background theme. ANSI white/bright_white are dark values because "white" text should be visible against the light canvas. Bold text and foreground are dark.

**Step 2: Generate the theme files**

Run: `python3 tools/generate_theme.py themes/bruma.json`

**Step 3: Visually verify the swatch SVG**

Open `.github/swatches/bruma.svg` in a browser. Verify:
- Light warm background — dramatically different from other themes
- Vivid, saturated colors across ALL slots (the collection's color explosion)
- Reds, greens, blues, magentas are all genuinely vivid — not muted
- The release valve: this is where the collection breaks free from earth tones

**Step 4: Commit**

```bash
git add themes/bruma.json "de-amaral/De Amaral — Bruma.terminal" .github/swatches/bruma.svg
git commit -m "Add De Amaral — Bruma theme

Painted threads in mist. After the Bruma series, 2010s."
```

---

### Task 8: Define and Generate — Sol

The brightest theme. Warm bright background. Radiant gold foreground on light warm field.

**Files:**
- Create: `themes/sol.json`
- Create: `de-amaral/De Amaral — Sol.terminal`
- Create: `.github/swatches/sol.svg`

**Step 1: Create the theme definition**

```json
{
  "name": "De Amaral — Sol",
  "terminal_path": "de-amaral/De Amaral — Sol.terminal",
  "swatch_path": ".github/swatches/sol.svg",
  "colors": {
    "black":          "#181008",
    "red":            "#b84820",
    "green":          "#587830",
    "yellow":         "#c88818",
    "blue":           "#405080",
    "magenta":        "#984058",
    "cyan":           "#387868",
    "white":          "#705830",
    "bright_black":   "#604818",
    "bright_red":     "#d86038",
    "bright_green":   "#78a048",
    "bright_yellow":  "#e8a828",
    "bright_blue":    "#5870a0",
    "bright_magenta": "#b85870",
    "bright_cyan":    "#489888",
    "bright_white":   "#504020",
    "background":     "#f0e0c8",
    "foreground":     "#483818",
    "bold":           "#382808",
    "cursor":         "#c88818",
    "cursor_text":    "#f0e0c8",
    "selection":      "#e0c8a0"
  }
}
```

Note: Like Bruma, this is a light-background theme. White/bright_white are dark. But unlike Bruma's cool mist, Sol's background is warm — sunlit parchment. The ANSI colors lean warm: golds, burnt oranges, olive greens.

**Step 2: Generate the theme files**

Run: `python3 tools/generate_theme.py themes/sol.json`

**Step 3: Visually verify the swatch SVG**

Open `.github/swatches/sol.svg` in a browser. Verify:
- Bright warm background — lighter and warmer than Bruma
- Gold/yellow is the star color (like Alquimia but inverted brightness)
- Reds are warm burnt orange
- Greens are olive-gold, not vivid
- Overall impression: looking at her gold leaf works in direct sunlight

**Step 4: Commit**

```bash
git add themes/sol.json "de-amaral/De Amaral — Sol.terminal" .github/swatches/sol.svg
git commit -m "Add De Amaral — Sol theme

Sunlit gold. After the radiant works spanning her career."
```

---

### Task 9: Update README

**Files:**
- Modify: `README.md:55-69` (between the Rothko section divider and Acquisitions)

**Step 1: Add the De Amaral collection section**

Insert after line 55 (`---`) and before `## Acquisitions`:

```markdown

## The De Amaral Collection

Seven profiles after Olga de Amaral (b. 1932). Gold leaf and horsehair, reconsidered as phosphor on glass.

### Muro Tejido

<img src=".github/swatches/muro-tejido.svg" width="360" alt="Muro Tejido palette" />

Raw wool and silence. After the woven walls, 1970s.

### Hojarasca

<img src=".github/swatches/hojarasca.svg" width="360" alt="Hojarasca palette" />

What the forest floor remembers. After the leaf-litter series, late 1970s.

### Alquimia

<img src=".github/swatches/alquimia.svg" width="360" alt="Alquimia palette" />

Fiber becoming gold. After the *Alquimia* series, 1984.

### Alquimia Plata

<img src=".github/swatches/alquimia-plata.svg" width="360" alt="Alquimia Plata palette" />

The same transformation, by moonlight. After the silver alchemy works, 1980s–90s.

### Strata

<img src=".github/swatches/strata.svg" width="360" alt="Strata palette" />

Earth compressed into memory. After the *Strata* series, 2000s.

### Bruma

<img src=".github/swatches/bruma.svg" width="360" alt="Bruma palette" />

Thread released from gravity. After the *Bruma* series, 2010s.

### Sol

<img src=".github/swatches/sol.svg" width="360" alt="Sol palette" />

The light the gold was always borrowing. After the radiant works spanning her career.

---

```

**Step 2: Update the Acquisitions section command example**

Change the example to show both collections:

```markdown
## Acquisitions

Double-click any `.terminal` file. It will appear in **Terminal → Preferences → Profiles**. Select it. Set it as default if you like.

Or, from the command line:

```sh
open "rothko/Rothko — Black and Orange.terminal"
open "de-amaral/De Amaral — Alquimia.terminal"
```
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "Add De Amaral collection to README

Seven themes from Muro Tejido to Sol."
```

---

### Task 10: Clean Up and Final Commit

**Step 1: Decide on generator script and theme JSON files**

The `tools/` directory and `themes/` directory contain the generator infrastructure. These are useful for future collections (Albers, Martin, etc. from brainstorm.md). Keep them in the repo.

Add `themes/` to `.gitignore` if the JSON definitions feel like build artifacts. Or keep them as source-of-truth color definitions — recommended since they're human-readable documentation of each palette.

**Step 2: Verify all files are present**

Run:
```bash
ls -la de-amaral/
ls -la .github/swatches/
```

Expected: 7 `.terminal` files in `de-amaral/`, 7 new `.svg` files in `.github/swatches/` (plus the 7 existing Rothko ones).

**Step 3: Final verification — open a .terminal file in macOS Terminal**

Run:
```bash
open "de-amaral/De Amaral — Alquimia.terminal"
```

This should import the profile into Terminal. Verify it appears in Terminal → Preferences → Profiles and that colors look correct.

**Step 4: Commit any remaining changes**

```bash
git status
# If anything unstaged:
git add -A
git commit -m "De Amaral collection: seven terminal themes complete"
```
