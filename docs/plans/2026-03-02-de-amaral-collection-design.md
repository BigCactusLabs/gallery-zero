# De Amaral Collection — Design

Terminal color themes after Olga de Amaral (b. 1932). Seven profiles tracing her career arc from raw fiber to radiant gold to late-career color.

## Theme Lineup

The collection moves chronologically through her work, from dark/austere to luminous to vivid.

| # | Title | After | Period | Palette Character |
|---|-------|-------|--------|-------------------|
| 1 | Muro Tejido | Woven Wall works | 1970s | Dark background. Raw wool browns, undyed linen, horsehair blacks. The most austere theme. |
| 2 | Hojarasca | Leaf-litter series | Late 1970s | Warm mid-tone background. Burnt sienna, dried gold, olive, decomposing greens. |
| 3 | Alquimia | Alchemy series (gold) | 1984+ | Deep brown background. Dominant golds and saffrons. The signature piece. |
| 4 | Alquimia Plata | Silver alchemy works | 1980s–90s | Cool dark background. Silver metallics, blue-greys, muted lavenders. Nocturnal counterpart to Alquimia. |
| 5 | Strata | Strata series | 2000s | Layered earth tones on dark ground. Ochre, terracotta, clay, sand. Geological, compressed. |
| 6 | Bruma | Mist series | 2010s+ | Lighter background. The most colorful theme — vivid painted threads. Late-career color liberation. |
| 7 | Sol | Sun imagery spanning her work | Spanning | Warm bright background. Radiant gold foreground on light warm field. The light-background theme. |

## ANSI Color Mapping Strategy

### Warm Slots (Red, Yellow, White)

These carry the collection. Yellow is where her gold lives — the signature slot. Red ranges from terracotta to rust to burnt sienna. White maps to raw linen, bleached fiber, or bright gold.

### Cool Slots as Studio Materials

Cool colors are not muted compromises. Every ANSI color should feel like a material from her studio:

- **Blue / Bright Blue**: Oxidized metal, tarnished silver, shadow on gold leaf. In Alquimia Plata, actual silver-blue. In earth themes, the blue of a bruise on clay.
- **Cyan / Bright Cyan**: Verdigris — green-blue patina on copper and bronze. Real material from metal oxidation. In Bruma, genuinely teal.
- **Magenta / Bright Magenta**: Cochineal — insect-derived red-purple from Colombian textile tradition. Warm, organic. In gold themes, dried wine stains on linen.

### Per-Theme Variations

- Alquimia leans hardest into gold yellows — yellow becomes the star
- Alquimia Plata shifts yellow toward silver and pushes blues forward
- Bruma is the exception — vivid colors across all slots
- Sol inverts the dark background convention, flipping contrast relationships

### Usability Constraint

Stay faithful to her warmth but ensure blues/cyans/greens are at least readable, even if muted. Some themes will have blues that barely read as blue and cyans that lean green-grey. Bruma is the release valve where vivid color appears.

## File Structure

```
de-amaral/
  De Amaral — Muro Tejido.terminal
  De Amaral — Hojarasca.terminal
  De Amaral — Alquimia.terminal
  De Amaral — Alquimia Plata.terminal
  De Amaral — Strata.terminal
  De Amaral — Bruma.terminal
  De Amaral — Sol.terminal

.github/swatches/
  muro-tejido.svg
  hojarasca.svg
  alquimia.svg
  alquimia-plata.svg
  strata.svg
  bruma.svg
  sol.svg
```

## README

New section after the Rothko Collection:

```markdown
## The De Amaral Collection

Seven profiles after Olga de Amaral (b. 1932). Gold leaf and horsehair,
reconsidered as phosphor on glass.
```

Each theme gets a swatch image and one-line poetic description referencing the specific work/series. Spanish titles kept as-is.

## Naming Conventions

- Terminal files: `De Amaral — Theme Name.terminal` (em dash)
- Swatch files: `kebab-case.svg`
- Directory: `de-amaral/`

## References

- [Olga de Amaral — Lisson Gallery](https://www.lissongallery.com/artists/olga-de-amaral)
- [Alquimia 13 — The Met](https://www.metmuseum.org/art/collection/search/484848)
- [Alquimia III — Art Institute of Chicago](https://www.artic.edu/artworks/65032/alquimia-iii-alchemy-iii)
- [At 92, Still Pushing Fiber Art Forward — Artsy](https://www.artsy.net/article/artsy-editorial-92-olga-de-amaral-pushing-fiber-art-forward)
