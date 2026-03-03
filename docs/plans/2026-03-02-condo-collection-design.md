# Condo Collection — Design

Terminal color themes after George Condo (b. 1957). Seven profiles organized as psychological states — each theme a different mental register from his "Psychological Cubism."

## Theme Lineup

The arc is emotional, not chronological: jazzy warmth → synthetic uncanny → clash → instability → darkness → fragmentation → chromatic liberation.

| # | Title | After | Palette Character |
|---|-------|-------|-------------------|
| 1 | Dancing to Miles | *Dancing to Miles*, 1985 | Jazzy warmth, neo-expressionist. Warm yellows, pinks, blacks on cream/ochre. The gateway theme — most livable. |
| 2 | Artificial Realism | His coined term, 1980s+ | Uncanny synthetic. Colors 10% off from what you'd expect — synthetic pinks, chemical greens, plastic blues. The uncanny valley. |
| 3 | Antipodal | Antipodal portrait series, 2000s | Maximum clash. True primaries forced together against stark black/white. Colors that shouldn't touch. |
| 4 | Mental States | *Mental States* series, 2011 | Acid tones. Green-yellows, hot pinks, cold blues in the same space. Warm/cool collision. Unstable, vibrating. |
| 5 | Dreams and Nightmares | *Dreams and Nightmares of the Queen*, 2006 | Old Master darkness. Burgundy/brown ground, tarnished gold, deep greens, candlelit warmth corrupted by sickly accents. Goya by way of Condo. |
| 6 | People Are Strange | Exhibition, 2023 | Fragmented, layered. Turquoise, metallic gold, dusty pink, charcoal. The most sophisticated — colors argue but they're well-dressed. |
| 7 | Diagonal | Diagonal series, 2023–24 | Cascading color planes against pastoral ground. The brightest, most geometric palette. Pure chromatic energy. |

## ANSI Color Mapping Strategy

### Core Principles (Anti-de-Amaral)

- **No material coherence** — colors can be arbitrary, synthetic, wrong. No justification needed.
- **Contrast is the medium** — every theme has at least one ANSI pair that visually clashes.
- **The "Condo yellow"** — his signature. The yellow slot is always vivid, often uncomfortably so.
- **Flesh tones as corruption** — reds and magentas lean toward skin tones gone wrong: too pink, too bruised, too flushed.
- **Black is expressive** — heavy and gestural, not empty neutral.

### Per-Theme Color Logic

- **Dancing to Miles**: Warmest. Jazz-club yellows, smoky pinks, deep blacks. Cream/ochre background.
- **Artificial Realism**: Every color slightly off. Pinks too synthetic, greens too chemical, blues too plastic. Medium-dark background.
- **Antipodal**: True primaries at full saturation. Red, blue, yellow fight each other. Black/white background provides no relief.
- **Mental States**: Acid palette. Chartreuse, hot pink, icy blue, dirty yellow. Colors that induce anxiety. Dark background.
- **Dreams and Nightmares**: Darkest theme. Deep burgundy ground. Tarnished gold, bottle green, candlelight orange, bruise purple.
- **People Are Strange**: Most refined. Turquoise/teal anchors, metallic gold accents, dusty rose, warm charcoal background.
- **Diagonal**: Brightest. Vivid pure-hue planes — each ANSI color a bold, clean statement. Light or vivid background.

## File Structure

```
condo/
  Condo — Dancing to Miles.terminal
  Condo — Artificial Realism.terminal
  Condo — Antipodal.terminal
  Condo — Mental States.terminal
  Condo — Dreams and Nightmares.terminal
  Condo — People Are Strange.terminal
  Condo — Diagonal.terminal

.github/swatches/
  dancing-to-miles.svg
  artificial-realism.svg
  antipodal.svg
  mental-states.svg
  dreams-and-nightmares.svg
  people-are-strange.svg
  diagonal.svg
```

## README

New section after the De Amaral Collection:

```markdown
## The Condo Collection

Seven profiles after George Condo (b. 1957). Psychological Cubism,
reconsidered as phosphor on glass.
```

Descriptions should be sharper and more irreverent than Rothko/de Amaral — matching Condo's confrontational energy.

## Naming Conventions

- Terminal files: `Condo — Theme Name.terminal` (em dash)
- Swatch files: `kebab-case.svg`
- Directory: `condo/`

## Future: v2 Clash Edition

User expressed interest in a future version that pushes the clashing harder. Current v1 prioritizes daily-drivable palettes while maintaining Condo's energy.

## References

- [George Condo — TheArtStory](https://www.theartstory.org/artist/condo-george/)
- [People Are Strange — Hauser & Wirth](https://www.hauserwirth.com/hauser-wirth-exhibitions/48647-george-condo-people-are-strange/)
- [Mental States — Tate](https://www.tate.org.uk/art/artworks/condo-mental-states-t14734)
- [George Condo retrospective — Musée d'Art Moderne de Paris](https://www.mam.paris.fr/en/expositions/exhibitions-george-condo)
- [George Condo — Sprüth Magers](https://spruethmagers.com/artists/george-condo/)
