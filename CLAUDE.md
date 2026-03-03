# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

Gallery Zero is a curated collection of macOS Terminal color themes inspired by famous painters. Each theme maps a painter's color relationships to the 16 ANSI color values that define a terminal session. This is an art/design project, not a software project — there is no build system, package manager, test suite, or CI pipeline.

Currently ships the **Rothko Collection**: seven themes after Mark Rothko.

## Repository Structure

- `rothko/` — Terminal profile files (`.terminal` plist XML with base64-encoded NSColor data)
- `.github/swatches/` — SVG color palette visualizations (360x200px, 16 colors in two rows)
- `README.md` — Gallery catalog with theme descriptions and installation instructions

## File Formats

**`.terminal` files** are XML plists containing NSKeyedArchiver-encoded NSColor objects for all 16 ANSI colors plus background, foreground, cursor, and selection colors. macOS Terminal imports these directly.

**Swatch SVGs** show the 16-color palette: a foreground band across the top, then 8 normal colors and 8 bright variants in a grid. Background color fills the SVG canvas.

## Conventions

- Theme files: `Artist — Theme Name.terminal` (em dash, not hyphen)
- Swatch files: `kebab-case.svg` matching the theme name
- Each artist collection lives in its own subdirectory (e.g., `rothko/`)
- README descriptions use poetic, literary language — match this tone
- Themes are named after specific artworks or artistic concepts, not generic color descriptions

## Adding a New Theme

1. Select an artwork with strong color relationships
2. Extract 16 colors mapped to ANSI roles (8 normal + 8 bright) plus background/foreground/cursor/selection
3. Create the `.terminal` plist with NSKeyedArchiver-encoded NSColor data for each color key
4. Create matching SVG swatch in `.github/swatches/`
5. Add theme entry to README.md with artwork reference and one-line poetic description
