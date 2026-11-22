#!/usr/bin/env python3
"""Build the Gallery Zero website (GitHub Pages) from the theme specs and READMEs.

Reads themes/*.json for colors and placards, each collection README for the
wall text, and writes a static site: index.html, the .terminal profiles, and a
zip of every profile.

    python3 tools/build_site.py --out _site
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import zipfile
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://bigcactuslabs.github.io/gallery-zero/"
REPO_URL = "https://github.com/BigCactusLabs/gallery-zero"
ZIP_NAME = "gallery-zero.zip"

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
    swatch = lambda keys: "".join(f'<i style="background:var(--{k.replace("_", "-")})"></i>' for k in keys)
    prompt = (f'<span class="c-green">gallery</span> <span class="c-blue dir">~/{c}</span> '
              f'<span class="c-magenta">main</span> <span class="c-bright-black">❯</span> ')
    return "\n".join([
        f'{prompt}ls -F',
        '<span class="c-bright-blue b">studies/</span>  <span class="c-bright-green b">hang.sh*</span>  '
        '<span class="c-cyan">notes.md</span>  <span class="c-yellow">palette.json</span>',
        f'{prompt}git diff --stat',
        ' canvas.txt | 6 <span class="c-green">+++</span><span class="c-red">---</span>',
        ' <span class="c-bright-yellow">frame.toml</span> | 2 <span class="c-bright-green">+</span><span class="c-bright-red">-</span>',
        f'{prompt}echo "<span class="sel">phosphor on glass</span>"',
        '<span class="b">phosphor on glass</span> <span class="c-bright-magenta">✦</span> <span class="c-bright-cyan">◐</span> <span class="c-white">░</span><span class="c-bright-white">▓</span>',
        f'<span class="chips">{swatch(ANSI[:8])}</span>',
        f'<span class="chips">{swatch(ANSI[8:])}</span>',
        f'{prompt}<span class="cursor"> </span>',
    ])


def window(work: dict, collection: str, extra_class: str = "") -> str:
    return (
        f'<div class="term {extra_class}" style="{style_vars(work["colors"])}">'
        f'<div class="bar"><span class="lights"><i></i><i></i><i></i></span>'
        f'<span class="placard">{html.escape(work["placard"])}</span></div>'
        f'<pre aria-hidden="true">{session(collection)}</pre></div>'
    )


def render(collections: list[dict]) -> str:
    total = sum(len(c["works"]) for c in collections)
    picks = re.findall(r"^### (.+)$", (ROOT / "README.md").read_text(encoding="utf-8"), flags=re.M)
    featured = [next(w for w in c["works"] if w["name"] == pick) for c, pick in zip(collections, picks, strict=True)]
    hero_data = json.dumps([
        {"vars": {f"--{k.replace('_', '-')}": w["colors"][k] for k in ANSI + EXTRA},
         "placard": w["placard"], "file": href(w["file"]), "name": w["name"], "dir": "~/" + c}
        for w, c in zip(featured, COLLECTIONS)
    ], ensure_ascii=False)
    nav = "".join(f'<a href="#{c["slug"]}">{html.escape(c["artist"])}</a>' for c in collections)
    rooms = []
    for c in collections:
        cards = []
        for w in c["works"]:
            cards.append(
                f'<article class="work" id="{c["slug"]}-{w["slug"]}">'
                f'{window(w, c["slug"])}'
                f'<div class="label"><h3>{html.escape(w["name"])}</h3>'
                f'<a class="dl" href="{href(w["file"])}" download>Download<span class="vh"> {html.escape(w["name"])}</span></a></div>'
                f'<p>{inline_md(w["text"])}</p></article>'
            )
        intro = "".join(f"<p>{inline_md(p)}</p>" for p in c["intro"])
        rooms.append(
            f'<section class="room" id="{c["slug"]}" aria-labelledby="{c["slug"]}-h">'
            f'<header class="wall"><h2 id="{c["slug"]}-h">{html.escape(c["artist"])}</h2>'
            f'<p class="lede">{inline_md(c["lede"])}</p>{intro}'
            f'<a class="src" href="{REPO_URL}/tree/main/{c["slug"]}">Collection notes on GitHub</a></header>'
            f'<div class="works">{"".join(cards)}</div></section>'
        )
    first = featured[0]
    description = (f"{total} color themes for macOS Terminal, after paintings by Mark Rothko, Olga de Amaral, "
                   "George Condo, Claude Monet, Atsuko Tanaka, Bridget Riley, Agnes Pelton and Charles Demuth.")
    return TEMPLATE.format(
        description=html.escape(description), site=SITE_URL, repo=REPO_URL, zip=ZIP_NAME, total=total,
        nav=nav, rooms="".join(rooms), hero=window(first, COLLECTIONS[0], "hero-term"),
        hero_name=html.escape(first["placard"]), hero_file=href(first["file"]), hero_data=hero_data,
        favicon=FAVICON,
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
<meta name="twitter:card" content="summary">
<meta name="color-scheme" content="light dark">
<link rel="icon" href="data:image/svg+xml,{favicon}">
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
.easel {{ margin: 0; }}
.easel figcaption {{ display: flex; justify-content: space-between; gap: 16px; margin-top: 18px; font-size: 14px; color: var(--muted); }}
.easel figcaption a {{ color: var(--ink); font-weight: 600; text-decoration: none; }}
.easel figcaption a:hover {{ text-decoration: underline; }}
.dots {{ display: flex; align-items: center; margin-right: -6px; }}
.dots button {{ width: 20px; height: 20px; padding: 0; border: 0; background: none; cursor: pointer; display: grid; place-items: center; }}
.dots button::after {{ content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--rule); transition: background-color .3s, transform .3s; }}
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
.src {{ font-size: 14px; color: var(--muted); }}
.works {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 360px), 1fr)); gap: 56px 36px; }}
.work .label {{ display: flex; justify-content: space-between; align-items: baseline; gap: 12px; margin: 20px 0 6px; }}
h3 {{ font: 500 22px/1.2 var(--serif); margin: 0; letter-spacing: -0.01em; }}
.work p {{ margin: 0; font-size: 14.5px; color: var(--muted); }}
.dl {{ flex: none; font-size: 14px; font-weight: 600; text-decoration: none; padding: 4px 12px; border-radius: 999px;
       box-shadow: inset 0 0 0 1px var(--rule); transition: background-color .15s; }}
.dl:hover {{ background: var(--card); }}
code {{ font-family: var(--mono); font-size: .9em; }}

/* Terminal window */
.term {{ border-radius: 12px; overflow: hidden; background: var(--background); color: var(--foreground);
         box-shadow: var(--shadow); transition: transform .35s cubic-bezier(.2,.7,.2,1), box-shadow .35s; }}
.works .term:hover {{ transform: translateY(-3px); }}
.term, .term * {{ transition-property: background-color, color, transform; transition-duration: .7s; }}
.bar {{ position: relative; display: flex; align-items: center; justify-content: center; height: 30px; padding: 0 74px;
        background: color-mix(in srgb, var(--background) 86%, var(--foreground)); }}
.lights {{ position: absolute; left: 12px; display: flex; gap: 8px; }}
.lights i {{ width: 12px; height: 12px; border-radius: 50%; background: #ff5f57; }}
.lights i:nth-child(2) {{ background: #febc2e; }} .lights i:nth-child(3) {{ background: #28c840; }}
.placard {{ font: 600 12px var(--sans); opacity: .62; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.term pre {{ margin: 0; padding: 14px 16px 16px; font: 12.5px/1.5 var(--mono); white-space: pre; overflow: hidden; }}
.hero-term pre {{ font-size: clamp(12px, 1.15vw, 14.5px); padding: 20px 22px 24px; }}
.hero-term .bar {{ height: 34px; }}
.b {{ color: var(--bold); font-weight: 700; }}
.sel {{ background: var(--selection); }}
.cursor {{ background: var(--cursor); color: var(--cursor-text); animation: blink 1.1s steps(1) infinite; }}
@keyframes blink {{ 50% {{ background: transparent; }} }}
@media (prefers-reduced-motion: reduce) {{ .cursor {{ animation: none; }} .term, .term * {{ transition: none; }} }}
.chips {{ display: inline-flex; gap: 0; vertical-align: middle; }}
.chips i {{ display: inline-block; width: 3ch; height: 1.2em; }}
{ansi_css}

footer {{ margin-top: clamp(80px, 10vw, 140px); border-top: 1px solid var(--rule); padding: 40px 0 56px; font-size: 14px; color: var(--muted); }}
footer .shell {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: 16px; }}

@media (max-width: 860px) {{
  .lobby {{ grid-template-columns: 1fr; }}
  .lobby p {{ max-width: 46ch; }}
}}
@media (max-width: 520px) {{ .hero-term pre, .term pre {{ font-size: 11px; padding: 12px 14px 14px; }} }}
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
      <p class="install">Double-click a <code>.terminal</code> file to add it to Terminal &rsaquo; Settings &rsaquo; Profiles.</p>
    </div>
    <figure class="easel" id="easel">
      {hero}
      <figcaption><a id="easel-file" href="{hero_file}" download>{hero_name}</a><span class="dots" id="easel-dots"></span></figcaption>
    </figure>
  </section>
</div>
<nav class="index" aria-label="Collections"><div class="shell">{nav}</div></nav>
<div class="shell">{rooms}</div>
</main>
<footer><div class="shell"><span>Gallery Zero. Palettes sampled from images of each painting. Themes licensed <a href="{repo}/blob/main/LICENSE">CC BY 4.0</a>.</span>
<span><a href="{repo}/blob/main/TECHNIQUES.md">How the profiles are built</a> · <a href="{repo}">Source</a></span></div></footer>
<script>
const works = {hero_data};
const term = document.querySelector('.hero-term');
const link = document.getElementById('easel-file');
const dots = document.getElementById('easel-dots');
const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
let at = 0, timer;
function show(i) {{
  at = (i + works.length) % works.length;
  const w = works[at];
  for (const [k, v] of Object.entries(w.vars)) term.style.setProperty(k, v);
  term.querySelector('.placard').textContent = w.placard;
  term.querySelectorAll('.dir').forEach(d => d.textContent = w.dir);
  link.textContent = w.placard; link.href = w.file;
  dots.querySelectorAll('button').forEach((b, j) => b.setAttribute('aria-current', j === at));
}}
works.forEach((w, i) => {{
  const b = document.createElement('button');
  b.type = 'button'; b.setAttribute('aria-label', w.name);
  b.onclick = () => {{ show(i); restart(); }};
  dots.append(b);
}});
function restart() {{ clearInterval(timer); if (!still) timer = setInterval(() => show(at + 1), 4200); }}
const easel = document.getElementById('easel');
easel.addEventListener('mouseenter', () => clearInterval(timer));
easel.addEventListener('mouseleave', restart);
show(0); restart();

const links = [...document.querySelectorAll('.index a')];
const io = new IntersectionObserver(entries => {{
  for (const e of entries) if (e.isIntersecting)
    links.forEach(a => a.setAttribute('aria-current', a.hash === '#' + e.target.id));
}}, {{ rootMargin: '-45% 0px -50% 0px' }});
document.querySelectorAll('.room').forEach(r => io.observe(r));
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
    with zipfile.ZipFile(out / ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zf:
        for c in collections:
            for w in c["works"]:
                src = ROOT / w["file"]
                dest = out / w["file"]
                dest.parent.mkdir(exist_ok=True)
                shutil.copy2(src, dest)
                zf.write(src, f"gallery-zero/{w['file']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Gallery Zero website.")
    parser.add_argument("--out", type=Path, default=ROOT / "_site")
    build(parser.parse_args().out)


if __name__ == "__main__":
    main()
