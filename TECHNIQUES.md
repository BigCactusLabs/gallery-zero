# Techniques

A short tour of every terminal trick in the gallery. Terminal.app has no documented theming API — just a plist format, some AppKit archaeology, and a handful of escape codes. This is what we found in the walls.

## The frame: `.terminal` files

A Terminal profile is an XML plist of `"type" => "Window Settings"`. Double-click imports it. Everything below lives inside that one file — no plugins, no daemons, nothing running.

## The pigment: NSKeyedArchiver color blobs

Every color key (`ANSIRedColor`, `BackgroundColour`, …) is a `Data` blob: an **NSKeyedArchiver**-serialized `NSColor`, complete with an embedded 3KB sRGB ICC profile. The color itself is stored twice, as ASCII float strings — `NSRGB` (sRGB components) and `NSComponents` (the custom-space components). Legacy profiles used the older NSArchiver format; we normalized all of them to keyed archives in sRGB so every canvas renders in the same color space it was mixed in.

Fun consequence: you can retint a profile with a text substitution on bytes inside a binary blob inside an XML file.

## The glass: alpha baked into the paint

Terminal has no `BackgroundAlpha` key. Window transparency *is* the alpha component of the archived background `NSColor` — the fourth float in those component strings. Pair it with `BackgroundBlur` (0–1, frosted glass over whatever's behind) and the window becomes a pane instead of a poster. `BackgroundAlphaInactive` / `BackgroundBlurInactive` control the unfocused state. The gallery follows Apple's own translucent profiles (Clear Light 0.93, Clear Dark 0.95, blur 0.5): an unfocused window keeps its alpha and drops its blur to zero, so the pane goes sharp rather than dim. The earlier **veil** — thinner glass when unfocused — lifted dark panes to mid-grey over a bright desktop and was retired.

We tune these per painting within a fixed band: alpha 0.93–0.98, blur 0–0.5. Dense late-Rothko glazes sit at the top of the band; acrylic-on-paper sits at the bottom, still the thinnest pane in the building. Because transparency mixes the profile background with whatever is behind the window, the specs are audited against black, mid-grey, and white backing colors. Foreground text must keep a contrast ratio of at least 4.5:1 in active and inactive windows, and the audit enforces the band itself.

## The light: sixteen ANSI values

The palette is the painting reduced to `black`→`bright_white`, plus background, foreground, bold, cursor, and selection. Every Gallery Zero profile enables `DynamicANSIForegroundColors`, which lets Terminal adjust ANSI foreground use when a specified color would be difficult to read. The source palette stays unchanged in `themes/*.json`.

## The placard: window titles

`WindowTitle` holds a museum label ("Seagram Murals — Rothko, 1958–59"). The catch: Terminal appends process names, dimensions, tty paths, and more unless you switch off every `Show…InTitle` bit individually. Eight booleans to get a clean placard.

## The proportions: type and rhythm

- `columnCount` / `rowCount` — window geometry. We tried matching each canvas's aspect ratio; wonky in practice, so all frames are now a uniform 110×30.
- `FontHeightSpacing` — line spacing as mood: tight (1.05) for dense surfaces, airy (1.16) for meditative ones.
- `CursorBlink` — the one animated pixel. A blinking ember for the fiery paintings, a still cursor for the serene ones.

## Live repainting: OSC escape codes

`OSC 11` (`printf '\e]11;#1a1c14\a'`) recolors the background of a *running* terminal; `OSC 111`/`110` reset it. Verified working on Tahoe by pixel-sampling the window. This is the door to live palette shifts — sunrise-to-dusk Monet, anyone?

## Truecolor painting: the half-block

The character `▀` with an independent 24-bit foreground (`\e[38;2;r;g;bm`) and background (`\e[48;2;r;g;bm`) gives two pixels per cell — doubling vertical resolution. Enough to paint a legible Rothko in a terminal window. (The mural painter is currently resting in storage.)

## The trap door: `RunCommandAsShell`

On Tahoe, if a file-opened profile contains `RunCommandAsShell` at all, Terminal word-splits `CommandString` and execs it raw — broken. Omit the key entirely and the command feeds into the interactive login shell, which persists afterward. The rare case where the fix is deleting the setting.

## The studio: spec-driven generation

`themes/*.json` is the source of truth — palette plus a `depth`/`veil` block per theme. The checked-in SVG swatches and `.terminal` files show that source in different forms. The profile tool keeps the depth settings synchronized and verifies every palette and depth value:

```sh
python3 tools/profiles.py sync-depth
python3 tools/profiles.py verify
python3 tools/profiles.py audit-contrast
```

---

*The profile-file details are AppKit archaeology. All of them survive an import dialog.*
