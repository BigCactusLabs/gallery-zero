#!/usr/bin/env python3
"""Build the Gallery Zero website (GitHub Pages) from the theme specs and READMEs.

Reads themes/*.json for colors and placards, each collection README for the
wall text, and writes a static site: index.html, the .terminal profiles, a zip
of every profile, a zip per collection, the share image, and the gilt frame
around the hero terminal (tools/assets/frame-circuit.webp, a generated image).

    python3 tools/build_site.py --out _site
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import struct
import zipfile
import zlib
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://bigcactuslabs.github.io/gallery-zero/"
REPO_URL = "https://github.com/BigCactusLabs/gallery-zero"
ZIP_NAME = "gallery-zero.zip"
OG_NAME = "og.png"

# The hero's frame: an original image, generated for the gallery. A Louis XV swept frame whose
# acanthus runs on as gold circuit traces over a black lattice. "size" is the cut-out in
# tools/assets; "sight" is its opening, plus a few px tucked under the frame's lip. List more
# than one frame and they take turns as the palettes rotate.
FRAMES = [
    {"file": "frame-circuit.webp", "size": (1600, 1197), "sight": (206, 214, 1392, 980)},
]

# Hanging order on the site, matching the top-level README.
COLLECTIONS = ("rothko", "de-amaral", "condo", "monet", "tanaka", "riley", "pelton", "demuth")

ANSI = (
    "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "bright_black", "bright_red", "bright_green", "bright_yellow",
    "bright_blue", "bright_magenta", "bright_cyan", "bright_white",
)
EXTRA = ("background", "foreground", "bold", "cursor", "cursor_text", "selection")


def inline_md(text: str) -> str:
    """Escape text and render the inline Markdown the READMEs use."""
    out = html.escape(text, quote=False)
    out = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", out)
    out = re.sub(r"\x60([^\x60]+)\x60", r"<code>\1</code>", out)
    out = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", out)
    return out


def parse_readme(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    head, _, rest = text.partition("\n---\n")
    paras = [p.strip() for p in head.split("\n\n") if p.strip() and not p.startswith("#")]
    works: dict[str, str] = {}
    order: list[str] = []
    for block in re.split(r"^### ", rest, flags=re.M)[1:]:
        title, _, body = block.partition("\n")
        body = body.split("\n---", 1)[0]
        prose = [p.strip() for p in body.split("\n\n") if p.strip() and not p.strip().startswith("<img")]
        works[title.strip()] = " ".join(prose)
        order.append(title.strip())
    return {"lede": paras[0], "intro": paras[1:], "works": works, "order": order}


def profile_path(collection: str, name: str) -> Path:
    matches = [p for p in (ROOT / collection).glob("*.terminal") if p.stem.split(" — ", 1)[-1] == name]
    if len(matches) != 1:
        raise SystemExit(f"expected one profile for {collection}/{name}, found {len(matches)}")
    return matches[0]


def load() -> list[dict]:
    collections = []
    for slug in COLLECTIONS:
        spec = json.loads((ROOT / "themes" / f"{slug}.json").read_text(encoding="utf-8"))
        wall = parse_readme(ROOT / slug / "README.md")
        by_name = {t["name"]: t for t in spec["themes"]}
        if set(by_name) != set(wall["order"]):
            raise SystemExit(f"{slug}: README works {sorted(wall['order'])} != themes {sorted(by_name)}")
        works = []
        for name in wall["order"]:
            theme = by_name[name]
            path = profile_path(slug, name)
            works.append({
                "name": name,
                "slug": theme["slug"],
                "colors": theme["colors"],
                "placard": theme["depth"].get("window_title", name),
                "alpha": theme["depth"].get("background_alpha", 1.0),
                "text": wall["works"][name],
                "file": f"{slug}/{path.name}",
            })
        collections.append({"slug": slug, "artist": spec["artist"], "lede": wall["lede"],
                            "intro": wall["intro"], "works": works})
    return collections


def href(rel: str) -> str:
    return "/".join(quote(part) for part in rel.split("/"))


def style_vars(colors: dict) -> str:
    keys = ANSI + EXTRA
    return ";".join(f"--{k.replace('_', '-')}:{colors[k]}" for k in keys)


def session(collection: str) -> str:
    """A short shell session that uses every slot of the palette."""
    c = collection
    span = lambda cls, text: f'<span class="{cls}">{text}</span>'
    swatch = lambda keys: "".join(f'<i data-k="{k}" style="background:var(--{k.replace("_", "-")})"></i>' for k in keys)
    chips = [span("chips", swatch(ANSI[:8])), span("chips", swatch(ANSI[8:]))]
    files = [span("c-bright-blue b", "studies/"), span("c-bright-green b", "hang.sh*"),
             span("c-cyan", "notes.md"), span("c-yellow", "palette.json")]
    diff = [f' canvas.txt | 6 {span("c-green", "+++")}{span("c-red", "---")}',
            f' {span("c-bright-yellow", "frame.toml")} | 2 {span("c-bright-green", "+")}{span("c-bright-red", "-")}']
    glyphs = (f'{span("b", "phosphor on glass")} {span("c-bright-magenta", "✦")} {span("c-bright-cyan", "◐")} '
              f'{span("c-white", "░")}{span("c-bright-white", "▓")}')
    cursor = span("cursor", " ")
    prompt = f'{span("c-blue dir", f"~/{c}")} {span("c-magenta", "main")} {span("c-bright-black", "❯")} '
    return "\n".join([
        f'{prompt}ls -F',
        "  ".join(files),
        f'{prompt}git diff --stat',
        *diff,
        f'{prompt}echo "{span("sel", "phosphor on glass")}"',
        glyphs,
        *chips,
        f'{prompt}{cursor}',
    ])


def hang(frames: list[dict]) -> dict:
    """Lay the frames over one easel, scaled so their openings share a top edge and a width.

    Returns the template's easel values: the easel's proportions, the opening's place on it,
    and each frame's box and opening height as CSS and markup.
    """
    boxes = []
    for f in frames:
        (w, h), (left, top, right, bottom) = f["size"], f["sight"]
        k = 1 / (right - left)   # scale: the opening is 1 wide
        boxes.append((-left * k, -top * k, w * k, h * k, (bottom - top) * k))
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    ew = max(b[0] + b[2] for b in boxes) - x0
    eh = max(b[1] + b[3] for b in boxes) - y0
    pct = lambda part, whole: f"{100 * part / whole:.3f}%"
    css, imgs = [], []
    for i, (f, (x, y, w, h, sight_h)) in enumerate(zip(frames, boxes)):
        css.append(
            f'.gilt .f{i} {{ left: {pct(x - x0, ew)}; top: {pct(y - y0, eh)}; width: {pct(w, ew)}; height: {pct(h, eh)}; }}\n'
            f'.gilt[data-frame="{i}"] .f{i} {{ opacity: 1; }}\n'
            f'.gilt[data-frame="{i}"] .hero-term {{ height: {pct(sight_h, eh)}; }}'
        )
        imgs.append(f'<img class="frame f{i}" src="{f["file"]}" width="{f["size"][0]}" height="{f["size"][1]}" alt="">')
    return {
        "easel_w": f"{ew:.4f}", "easel_h": f"{eh:.4f}", "sight_left": pct(-x0, ew), "sight_top": pct(-y0, eh),
        "sight_w": pct(1, ew), "frames_css": "\n".join(css), "frames_html": "".join(imgs), "first_frame": frames[0]["file"],
    }


def window(work: dict, collection: str, extra_class: str = "") -> str:
    return (
        f'<div class="term {extra_class}" style="{style_vars(work["colors"])}">'
        f'<div class="bar"><span class="lights"><i></i><i></i><i></i></span>'
        f'<span class="placard">{html.escape(work["placard"])}</span></div>'
        f'<pre aria-hidden="true">{session(collection)}</pre></div>'
    )


def featured_works(collections: list[dict]) -> list[dict]:
    """The work the top-level README highlights for each collection."""
    picks = re.findall(r"^### (.+)$", (ROOT / "README.md").read_text(encoding="utf-8"), flags=re.M)
    return [next(w for w in c["works"] if w["name"] == pick) for c, pick in zip(collections, picks, strict=True)]


def room_zip(slug: str) -> str:
    return f"gallery-zero-{slug}.zip"


def png(width: int, height: int, rows: list[bytes]) -> bytes:
    """Encode 8-bit RGB rows as a PNG, so the share image needs only the stdlib."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    raw = b"".join(b"\x00" + row for row in rows)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


OG_SIZE = (1200, 630)


def og_image(featured: list[dict]) -> bytes:
    """The share card: one panel per collection, its featured palette laid out like a swatch."""
    width, height = OG_SIZE
    panel = width // len(featured)
    chip_w, chip_h, gap = 42, 50, 16
    left = (panel - 2 * chip_w) // 2
    top = (height - (chip_h + gap + 8 * chip_h)) // 2
    grid = top + chip_h + gap
    rgb = lambda value: bytes.fromhex(value.lstrip("#")[:6])
    rows = []
    for y in range(height):
        if top <= y < top + chip_h:
            pair = ("foreground", "foreground")
        elif 0 <= (y - grid) // chip_h < 8:
            slot = (y - grid) // chip_h
            pair = (ANSI[slot], ANSI[slot + 8])
        else:
            pair = ()
        row = bytearray()
        for w in featured:
            cells = bytearray(rgb(w["colors"]["background"]) * panel)
            for i, key in enumerate(pair):
                x = left + i * chip_w
                cells[x * 3:(x + chip_w) * 3] = rgb(w["colors"][key]) * chip_w
            row += cells
        row += row[-3:] * (width - len(row) // 3)
        rows.append(bytes(row))
    return png(width, height, rows)


def render(collections: list[dict]) -> str:
    total = sum(len(c["works"]) for c in collections)
    featured = featured_works(collections)
    hero_data = json.dumps([
        {"vars": {f"--{k.replace('_', '-')}": w["colors"][k] for k in ANSI + EXTRA},
         "placard": w["placard"], "file": href(w["file"]), "name": w["name"], "dir": "~/" + c}
        for w, c in zip(featured, COLLECTIONS)
    ], ensure_ascii=False)
    nav = "".join(f'<a href="#{c["slug"]}">{html.escape(c["artist"])}</a>' for c in collections)
    rooms = []
    for c, pick in zip(collections, featured, strict=True):
        # The featured work hangs first, full width; the rest keep README order.
        cards = []
        for w in [pick] + [w for w in c["works"] if w is not pick]:
            wid = f'{c["slug"]}-{w["slug"]}'
            name = html.escape(w["name"])
            cards.append(
                f'<article class="work{" feature" if w is pick else ""}" id="{wid}">'
                f'{window(w, c["slug"])}'
                f'<div class="caption"><div class="label"><h3><a href="#{wid}">{name}</a></h3>'
                f'<a class="dl" href="{href(w["file"])}" download>Download<span class="vh"> {name}</span></a></div>'
                f'<p>{inline_md(w["text"])}</p></div></article>'
            )
        intro = "".join(f"<p>{inline_md(p)}</p>" for p in c["intro"])
        artist = html.escape(c["artist"])
        rooms.append(
            f'<section class="room" id="{c["slug"]}" aria-labelledby="{c["slug"]}-h">'
            f'<header class="wall"><h2 id="{c["slug"]}-h">{artist}</h2>'
            f'<p class="lede">{inline_md(c["lede"])}</p>{intro}'
            f'<p class="links"><a class="dl" href="{room_zip(c["slug"])}" download>Download all {len(c["works"])}'
            f'<span class="vh"> {artist} themes</span></a>'
            f'<a class="src" href="{REPO_URL}/tree/main/{c["slug"]}">Collection notes on GitHub</a></p></header>'
            f'<div class="works">{"".join(cards)}</div></section>'
        )
    first = featured[0]
    easel = hang(FRAMES)
    description = (f"{total} color themes for macOS Terminal, after paintings by Mark Rothko, Olga de Amaral, "
                   "George Condo, Claude Monet, Atsuko Tanaka, Bridget Riley, Agnes Pelton and Charles Demuth.")
    return TEMPLATE.format(
        description=html.escape(description), site=SITE_URL, repo=REPO_URL, zip=ZIP_NAME, total=total,
        nav=nav, rooms="".join(rooms), hero=window(first, COLLECTIONS[0], "hero-term"),
        hero_name=html.escape(first["placard"]), hero_file=href(first["file"]), hero_data=hero_data,
        favicon=FAVICON, og=OG_NAME, og_w=OG_SIZE[0], og_h=OG_SIZE[1],
        frame_count=len(FRAMES), **easel,
    )


FAVICON = quote(
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
    "<rect width='32' height='32' rx='7' fill='#34120f'/>"
    "<rect x='6' y='6' width='20' height='6' rx='1.5' fill='#e15a50'/>"
    "<rect x='6' y='14' width='20' height='5' rx='1.5' fill='#240b08'/>"
    "<rect x='6' y='21' width='20' height='5' rx='1.5' fill='#a77971'/></svg>"
)

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gallery Zero · Color themes for macOS Terminal, after eight painters</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{site}">
<meta property="og:type" content="website">
<meta property="og:title" content="Gallery Zero">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{site}">
<meta property="og:image" content="{site}{og}">
<meta property="og:image:width" content="{og_w}">
<meta property="og:image:height" content="{og_h}">
<meta property="og:image:alt" content="The palettes of eight Gallery Zero themes, one for each painter.">
<meta name="twitter:card" content="summary_large_image">
<meta name="color-scheme" content="light dark">
<link rel="icon" href="data:image/svg+xml,{favicon}">
<link rel="preload" as="image" href="{first_frame}">
<style>
:root {{
  --wall: #f3f3f2; --ink: #17171a; --muted: #5f5f66; --rule: #dcdcdc; --card: #ffffff;
  --serif: ui-serif, "New York", "Iowan Old Style", Georgia, serif;
  --sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  --shadow: 0 1px 1px rgb(0 0 0 / .06), 0 8px 18px -6px rgb(0 0 0 / .18), 0 30px 60px -20px rgb(0 0 0 / .28);
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --wall: #141416; --ink: #ececee; --muted: #9a9aa3; --rule: #2a2a2e; --card: #1c1c1f;
          --shadow: 0 0 0 1px rgb(255 255 255 / .06), 0 20px 50px -18px rgb(0 0 0 / .8); }}
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; scroll-padding-top: 64px; }}
@media (prefers-reduced-motion: reduce) {{ html {{ scroll-behavior: auto; }} }}
body {{ margin: 0; background: var(--wall); color: var(--ink); font: 16px/1.55 var(--sans);
       -webkit-font-smoothing: antialiased; }}
a {{ color: inherit; }}
.vh {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }}
.shell {{ max-width: 1240px; margin: 0 auto; padding: 0 clamp(20px, 4vw, 48px); }}

/* Lobby */
.lobby > *, .works > * {{ min-width: 0; }}
.lobby {{ display: grid; grid-template-columns: minmax(0, 5fr) minmax(0, 7fr); gap: clamp(32px, 5vw, 72px);
          align-items: center; padding: clamp(48px, 9vw, 120px) 0 clamp(40px, 5vw, 72px); }}
h1 {{ font: 500 clamp(44px, 6.4vw, 84px)/0.98 var(--serif); letter-spacing: -0.025em; margin: 0 0 24px; }}
.lobby p {{ font-size: clamp(17px, 1.5vw, 19px); color: var(--muted); max-width: 34ch; margin: 0 0 32px; }}
.actions {{ display: flex; flex-wrap: wrap; gap: 12px; }}
.btn {{ display: inline-flex; align-items: center; gap: 8px; height: 44px; padding: 0 20px; border-radius: 999px;
        font-weight: 600; font-size: 15px; text-decoration: none; transition: transform .15s, background-color .15s; }}
.btn:active {{ transform: scale(.98); }}
.btn.primary {{ background: var(--ink); color: var(--wall); }}
.btn.ghost {{ box-shadow: inset 0 0 0 1px var(--rule); }}
.btn.ghost:hover {{ background: var(--card); }}
.lobby .install {{ margin: 24px 0 0; font-size: 14px; }}
.install code {{ font: 13px var(--mono); }}
.easel {{ margin: 0; justify-self: center; width: min(100%, 700px); }}
.easel figcaption {{ display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-top: 18px; font-size: 14px; color: var(--muted); }}
.easel figcaption a {{ color: var(--ink); font-weight: 600; text-decoration: none; }}
.easel figcaption a:hover {{ text-decoration: underline; }}
.controls {{ display: flex; align-items: center; gap: 4px; margin-right: -6px; }}
.dots {{ display: flex; align-items: center; }}
.toggle {{ width: 28px; height: 28px; padding: 0; border: 0; border-radius: 50%; background: none; color: var(--muted);
           cursor: pointer; display: grid; place-items: center; transition: color .15s, background-color .15s; }}
.toggle[hidden] {{ display: none; }}
.toggle:hover {{ color: var(--ink); background: var(--card); }}
.toggle svg {{ width: 12px; height: 12px; fill: currentColor; }}
.toggle .play, .toggle[data-state="paused"] .pause {{ display: none; }}
.toggle[data-state="paused"] .play {{ display: block; }}
.dots button {{ width: 20px; height: 20px; padding: 0; border: 0; background: none; cursor: pointer; display: grid; place-items: center; }}
.dots button::after {{ content: ""; width: 7px; height: 7px; border-radius: 50%; background: color-mix(in srgb, var(--muted) 55%, var(--wall)); transition: background-color .3s, transform .3s; }}
.dots button:hover::after {{ background: var(--muted); }}
.dots button[aria-current="true"]::after {{ background: var(--ink); transform: scale(1.3); }}

/* Index */
.index {{ position: sticky; top: 0; z-index: 5; background: color-mix(in srgb, var(--wall) 82%, transparent);
          backdrop-filter: saturate(1.6) blur(16px); -webkit-backdrop-filter: saturate(1.6) blur(16px);
          border-bottom: 1px solid var(--rule); }}
.index .shell {{ display: flex; gap: 4px; overflow-x: auto; scrollbar-width: none; height: 52px; align-items: center; }}
.index a {{ flex: none; padding: 6px 14px; border-radius: 999px; font-size: 14px; font-weight: 500; text-decoration: none;
            color: var(--muted); transition: color .2s, background-color .2s; }}
.index a:hover {{ color: var(--ink); }}
.index a[aria-current="true"] {{ color: var(--ink); background: var(--card); box-shadow: 0 0 0 1px var(--rule); }}

/* Rooms */
.room {{ padding: clamp(56px, 8vw, 104px) 0 0; }}
.wall {{ max-width: 68ch; margin-bottom: clamp(32px, 4vw, 52px); }}
h2 {{ font: 500 clamp(36px, 4.4vw, 56px)/1 var(--serif); letter-spacing: -0.02em; margin: 0 0 16px; }}
.wall .lede {{ font-size: 19px; color: var(--ink); margin: 0 0 12px; }}
.wall p {{ color: var(--muted); margin: 0 0 12px; }}
.wall .links {{ display: flex; flex-wrap: wrap; align-items: center; gap: 10px 18px; margin: 22px 0 0; }}
.src {{ font-size: 14px; color: var(--muted); }}
.works {{ display: grid; grid-template-columns: minmax(0, 1fr); gap: 52px 32px; }}
.work .label {{ display: flex; justify-content: space-between; align-items: baseline; gap: 12px; margin: 20px 0 6px; }}
h3 {{ font: 500 22px/1.2 var(--serif); margin: 0; letter-spacing: -0.01em; }}
h3 a {{ text-decoration: none; }}
h3 a::after {{ content: "#"; margin-left: .35em; color: var(--muted); opacity: 0; transition: opacity .15s; }}
h3 a:hover::after, h3 a:focus-visible::after {{ opacity: 1; }}
.work p {{ margin: 0; font-size: 14.5px; color: var(--muted); }}
.dl {{ flex: none; color: var(--ink); font-size: 14px; font-weight: 600; text-decoration: none; padding: 4px 12px; border-radius: 999px;
       box-shadow: inset 0 0 0 1px var(--rule); transition: background-color .15s; }}
.dl:hover {{ background: var(--card); }}
@media (min-width: 800px) {{
  .works {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .feature {{ grid-column: 1 / -1; display: grid; grid-template-columns: minmax(0, 7fr) minmax(0, 5fr);
              gap: clamp(32px, 4vw, 56px); align-items: center; }}
  .feature .label {{ margin-top: 0; }}
  .feature h3 {{ font-size: 30px; }}
  .feature p {{ font-size: 16px; margin-top: 10px; }}
  .feature .term pre {{ font-size: min(clamp(12px, 1.15vw, 14.5px), calc((100cqi - 44px) / 26.4)); padding: 20px 22px 24px; }}
  .feature .bar {{ height: 34px; }}
}}
@media (min-width: 1200px) {{ .works {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }} }}
code {{ font-family: var(--mono); font-size: .9em; }}

/* Terminal window */
.term {{ container-type: inline-size; border-radius: 12px; overflow: hidden; background: var(--background); color: var(--foreground);
         box-shadow: var(--shadow); transition: transform .35s cubic-bezier(.2,.7,.2,1), box-shadow .35s; }}
.works .term:hover {{ transform: translateY(-3px); }}
.term, .term * {{ transition-property: background-color, color, transform; transition-duration: .7s; }}
.bar {{ position: relative; display: flex; align-items: center; justify-content: center; height: 30px; padding: 0 74px;
        background: color-mix(in srgb, var(--background) 86%, var(--foreground)); }}
.lights {{ position: absolute; left: 12px; display: flex; gap: 8px; }}
.lights i {{ width: 12px; height: 12px; border-radius: 50%; background: #ff5f57; }}
.lights i:nth-child(2) {{ background: #febc2e; }} .lights i:nth-child(3) {{ background: #28c840; }}
.placard {{ font: 600 12px var(--sans); opacity: .62; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
/* The session's longest line is 43 characters, about 26.4em wide, so the type shrinks before the window clips it. */
.term pre {{ margin: 0; padding: 14px 16px 16px; font: 12.5px/1.5 var(--mono); white-space: pre; overflow: hidden;
             font-size: min(12.5px, calc((100cqi - 32px) / 26.4)); }}
/* The easel: a terminal behind a frame. The terminal fills the frame's opening and tucks
   under its lip, and its type scales with the opening. With more than one frame they are
   laid so their openings share a top edge and a width, and they cross-fade. */
.gilt {{ position: relative; aspect-ratio: {easel_w} / {easel_h}; }}
.gilt .frame {{ position: absolute; pointer-events: none; user-select: none; opacity: 0; transition: opacity .7s;
                filter: drop-shadow(0 1px 1px rgb(0 0 0 / .45)) drop-shadow(0 14px 16px rgb(0 0 0 / .32)); }}
.hero-term {{ position: absolute; left: {sight_left}; top: {sight_top}; width: {sight_w};
              border-radius: 0; box-shadow: none; }}
.term.hero-term {{ transition-property: background-color, color, height; }}
{frames_css}
.hero-term .bar {{ display: none; }}
.hero-term pre {{ height: 100%; padding: 4.2cqi 5cqi 0; font-size: calc(88cqi / 26.4); line-height: 1.46; }}
.b {{ color: var(--bold); font-weight: 700; }}
.sel {{ background: var(--selection); }}
.cursor {{ background: var(--cursor); color: var(--cursor-text); animation: blink 1.1s steps(1) infinite; }}
@keyframes blink {{ 50% {{ background: transparent; }} }}
@media (prefers-reduced-motion: reduce) {{ .cursor {{ animation: none; }} .term, .term *, .gilt .frame {{ transition: none; }} }}
.chips {{ display: inline-flex; gap: 0; vertical-align: middle; }}
.chips i {{ display: inline-block; width: 3ch; height: 1.2em; cursor: pointer; }}
.chips i:hover {{ position: relative; box-shadow: 0 0 0 1.5px var(--foreground); }}
.tip {{ position: fixed; z-index: 10; transform: translate(-50%, calc(-100% - 8px)); padding: 5px 9px; border-radius: 6px;
        background: var(--ink); color: var(--wall); font: 500 12px var(--mono); white-space: nowrap; pointer-events: none;
        opacity: 0; transition: opacity .12s; }}
.tip.on {{ opacity: 1; }}
{ansi_css}

footer {{ margin-top: clamp(80px, 10vw, 140px); border-top: 1px solid var(--rule); padding: 40px 0 56px; font-size: 14px; color: var(--muted); }}
footer .shell {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: 16px; }}

@media (max-width: 860px) {{
  .lobby {{ grid-template-columns: 1fr; }}
  .lobby p {{ max-width: 46ch; }}
}}
@media (max-width: 520px) {{
  .works .term pre {{ padding: 12px 14px 14px; }}
  .gilt {{ margin: 0 -14px; }}
}}
</style>
</head>
<body>
<main>
<div class="shell">
  <section class="lobby">
    <div>
      <h1>Gallery Zero</h1>
      <p>{total} color themes for macOS Terminal. Each one takes the colors of a single painting and maps them onto the sixteen ANSI slots.</p>
      <div class="actions">
        <a class="btn primary" href="{zip}" download>Download all {total}</a>
        <a class="btn ghost" href="{repo}">View on GitHub</a>
      </div>
      <p class="install">Double-click a <code>.terminal</code> file to add it to Terminal &rsaquo; Settings &rsaquo; Profiles. Click any swatch to copy its hex.</p>
    </div>
    <figure class="easel" id="easel">
      <div class="gilt" id="gilt" data-frame="0">{hero}{frames_html}</div>
      <figcaption><a id="easel-file" href="{hero_file}" download>{hero_name}</a><span class="controls"><span class="dots" id="easel-dots"></span><button type="button" class="toggle" id="easel-toggle" aria-label="Pause rotation"><svg viewBox="0 0 12 12" aria-hidden="true"><path class="pause" d="M3 2h2.2v8H3zM6.8 2H9v8H6.8z"/><path class="play" d="M3.5 1.8 10 6l-6.5 4.2z"/></svg></button></span></figcaption>
    </figure>
  </section>
</div>
<nav class="index" aria-label="Collections"><div class="shell">{nav}</div></nav>
<div class="shell">{rooms}</div>
</main>
<footer><div class="shell"><span>Gallery Zero. Palettes sampled from images of each painting. Themes licensed <a href="{repo}/blob/main/LICENSE">CC BY 4.0</a>.
The frame is a generated image: Louis XV in outline, circuit traces in the carving.</span>
<span><a href="{repo}/blob/main/TECHNIQUES.md">How the profiles are built</a> · <a href="{repo}">Source</a></span></div></footer>
<script>
const works = {hero_data};
const term = document.querySelector('.hero-term');
const link = document.getElementById('easel-file');
const dots = document.getElementById('easel-dots');
const toggle = document.getElementById('easel-toggle');
const easel = document.getElementById('easel');
const gilt = document.getElementById('gilt');
const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
const holds = new Set();
let at = 0, timer, stopped = still;
function show(i) {{
  at = (i + works.length) % works.length;
  const w = works[at];
  for (const [k, v] of Object.entries(w.vars)) term.style.setProperty(k, v);
  term.querySelector('.placard').textContent = w.placard;
  term.querySelectorAll('.dir').forEach(d => d.textContent = w.dir);
  link.textContent = w.placard; link.href = w.file;
  gilt.dataset.frame = at % {frame_count};
  dots.querySelectorAll('button').forEach((b, j) => b.setAttribute('aria-current', j === at));
}}
// The rotation runs unless the visitor stopped it, or is hovering or tabbing through the easel.
function run() {{
  clearInterval(timer);
  if (!stopped && !holds.size) timer = setInterval(() => show(at + 1), 4200);
}}
function hold(why, on) {{ on ? holds.add(why) : holds.delete(why); run(); }}
works.forEach((w, i) => {{
  const b = document.createElement('button');
  b.type = 'button'; b.setAttribute('aria-label', w.name);
  b.onclick = () => {{ show(i); run(); }};
  dots.append(b);
}});
easel.addEventListener('mouseenter', () => hold('hover', true));
easel.addEventListener('mouseleave', () => hold('hover', false));
easel.addEventListener('focusin', e => hold('focus', e.target.matches(':focus-visible')));
easel.addEventListener('focusout', () => hold('focus', false));
toggle.hidden = still;
toggle.onclick = () => {{
  stopped = !stopped;
  toggle.dataset.state = stopped ? 'paused' : 'playing';
  toggle.setAttribute('aria-label', stopped ? 'Play rotation' : 'Pause rotation');
  run();
}};
show(0); run();

const strip = document.querySelector('.index .shell');
const links = [...strip.querySelectorAll('a')];
const rooms = [...document.querySelectorAll('.room')];
const inBand = new Set();
let current;
const io = new IntersectionObserver(entries => {{
  for (const e of entries) e.isIntersecting ? inBand.add(e.target.id) : inBand.delete(e.target.id);
  const id = rooms.find(r => inBand.has(r.id))?.id ?? null;
  if (id === current) return;
  current = id;
  let left = 0;
  for (const a of links) {{
    const on = a.hash === '#' + id;
    a.setAttribute('aria-current', on);
    if (on) left = a.offsetLeft - strip.offsetLeft - (strip.clientWidth - a.offsetWidth) / 2;
  }}
  strip.scrollTo({{ left, behavior: still ? 'auto' : 'smooth' }});
}}, {{ rootMargin: '-45% 0px -50% 0px' }});
rooms.forEach(r => io.observe(r));

const tip = document.createElement('div');
tip.className = 'tip'; tip.setAttribute('role', 'status');
document.body.append(tip);
let tipTimer;
const chipOf = e => e.target instanceof Element ? e.target.closest('.chips i') : null;
function hexOf(chip) {{
  const slot = '--' + chip.dataset.k.replace('_', '-');
  return getComputedStyle(chip.closest('.term')).getPropertyValue(slot).trim();
}}
function tipAt(chip, text, ms) {{
  const r = chip.getBoundingClientRect();
  tip.textContent = text;
  tip.style.left = r.left + r.width / 2 + 'px';
  tip.style.top = r.top + 'px';
  tip.classList.add('on');
  clearTimeout(tipTimer);
  if (ms) tipTimer = setTimeout(() => tip.classList.remove('on'), ms);
}}
document.addEventListener('pointerover', e => {{
  const chip = chipOf(e);
  if (chip) tipAt(chip, chip.dataset.k.replace('_', ' ') + ' ' + hexOf(chip));
}});
document.addEventListener('pointerout', e => {{
  if (chipOf(e)) tipTimer = setTimeout(() => tip.classList.remove('on'), 80);
}});
document.addEventListener('click', async e => {{
  const chip = chipOf(e);
  if (!chip) return;
  const hex = hexOf(chip);
  try {{ await navigator.clipboard.writeText(hex); tipAt(chip, 'Copied ' + hex, 1400); }}
  catch {{ tipAt(chip, hex, 1400); }}
}});
addEventListener('scroll', () => tip.classList.remove('on'), {{ passive: true }});
</script>
</body>
</html>
"""

ANSI_CSS = "\n".join(f".c-{k.replace('_', '-')} {{{{ color: var(--{k.replace('_', '-')}); }}}}" for k in ANSI)
TEMPLATE = TEMPLATE.replace("{ansi_css}", ANSI_CSS)


def build(out: Path) -> None:
    collections = load()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / "index.html").write_text(render(collections), encoding="utf-8")
    (out / ".nojekyll").write_text("")
    (out / OG_NAME).write_bytes(og_image(featured_works(collections)))
    for frame in FRAMES:
        shutil.copy2(ROOT / "tools" / "assets" / frame["file"], out / frame["file"])
    with zipfile.ZipFile(out / ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zf:
        for c in collections:
            with zipfile.ZipFile(out / room_zip(c["slug"]), "w", zipfile.ZIP_DEFLATED) as room:
                for w in c["works"]:
                    src = ROOT / w["file"]
                    dest = out / w["file"]
                    dest.parent.mkdir(exist_ok=True)
                    shutil.copy2(src, dest)
                    for archive in (zf, room):
                        archive.write(src, f"gallery-zero/{w['file']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Gallery Zero website.")
    parser.add_argument("--out", type=Path, default=ROOT / "_site")
    build(parser.parse_args().out)


if __name__ == "__main__":
    main()
