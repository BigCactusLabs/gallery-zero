# The Tanaka Collection

Seven profiles after Atsuko Tanaka (1932–2005). Neon circuits and painted light, rewired as phosphor on glass.

Seven studies in what happens when you wire color directly into the wall. Tanaka spent fifty years painting circles connected by lines — circuit diagrams that hum with the energy of Osaka's neon district. Her vinyl paint glows like signage. Her white grounds buzz like gallery lighting. These seven themes trace the arc from first spark to full blaze to the late-night clarity when only the essential signs are still lit.

---

### Electric Dress

<img src="../.github/swatches/electric-dress.svg" width="360" alt="Electric Dress palette" />

Two hundred bulbs in nine colors, worn like a second skin. The circuit that started everything. After *Electric Dress (Denkifuku)*, 1956.

### Red and Black

<img src="../.github/swatches/red-and-black.svg" width="360" alt="Red and Black palette" />

Two wires, one circuit. The world before the palette expanded. After *Work*, 1958.

### Thanks, Sam

<img src="../.github/swatches/thanks-sam.svg" width="360" alt="Thanks, Sam palette" />

The moment the primaries arrived and the signage lit up. After *Thanks, Sam*, 1963.

### Gate of Hell

<img src="../.github/swatches/gate-of-hell.svg" width="360" alt="Gate of Hell palette" />

Quivering lines spewing from concentric rings. The nervous system, exposed. After *Gate of Hell*, 1965.

### The Void

<img src="../.github/swatches/the-void.svg" width="360" alt="The Void palette" />

Shiny red circles. Bright blue paths. A slate void where the signal drops. After *Untitled*, 1966.

### Neon District

<img src="../.github/swatches/neon-district.svg" width="360" alt="Neon District palette" />

Every color Dotonbori could throw, jostling for space on the same wall. After the peak vibrancy paintings, 1984–88.

### Late Clarity

<img src="../.github/swatches/late-clarity.svg" width="360" alt="Late Clarity palette" />

The same wires, decades later. Every connection earned. After the late paintings, 1990s–2000s.

---

## Palette

Each palette is sampled from an image of its work, and each ground comes from that work's own surface. Tanaka painted in synthetic resin enamel, and the circle paintings sit on white or cream canvas, so *Red and Black* (after *Work*, 1958, Hyogo Prefectural Museum of Art) and *Late Clarity* (after *2001-F*) keep light grounds, warmed or cooled to their canvas. The other grounds come from inside the work. *Electric Dress* is a darkened gallery, with the lamps at full strength and the bare tubes' white as ink. *Gate of Hell* is the oxblood and charcoal of its hottest circles, with every ANSI color bent toward fire. *The Void* is the slate oval at the center of the 1966 canvas, and *Thanks, Sam* is the ultramarine of its great target, with the rings' vermilion, orange, amber and cadmium as its ANSI colors.

*Neon District* keeps its original white ground and pushes its twelve colored ANSI values to the edge of sRGB: `#fd03ff` magenta, `#23ff00` green, `#04feff` cyan, `#feff01` yellow. It is the one profile in the gallery with Terminal's dynamic ANSI foregrounds switched off, so the neon renders unadjusted. Neon yellow, green and cyan text on white is close to invisible, on purpose.

On the four dark grounds every ANSI color except black and bright black reaches 4.5:1 contrast. On *Red and Black* and *Late Clarity* every normal ANSI color passes, while white and the brights sit lighter, like lit bulbs, and Terminal's dynamic ANSI foregrounds adjust them at render time.

Sources: [Takamatsu Art Museum, *Denkifuku*](https://artplatform.go.jp/collections/W411501) (enamel on lamps) and installation photographs; [Hyogo Prefectural Museum of Art bulletin 9](https://www.artm.pref.hyogo.jp/artcenter/pdf/kiyou09.pdf) (*Work*, 1958; lit and unlit bulbs); [Moderna Museet](https://www.modernamuseet.se/en/stockholm/exhibitions/atsuko-tanaka/biography-atsuko-tanaka/) (*Thanks, Sam*); [National Museum of Art, Osaka](https://artsandculture.google.com/asset/gate-of-hell-tanaka-atsuko/0gG6D-WjdgJGBA) (*Gate of Hell*); [The Rachofsky Collection](https://thewarehousedallas.org/artists/atsuko-tanaka/) (*Untitled*, 1966); [Phillips](https://www.phillips.com/detail/atsuko-tanaka/NY010419/198) (*85-E*, 1985); [Marianne Boesky Gallery](https://marianneboeskygallery.com/exhibitions/27/works/artworks-24085-atsuko-tanaka-2001-f-2001/) (*2001-F*, 2001).

---

## Framing

Every frame is a uniform 110×30, and the glass is cut to the current. Painted light runs thin — *Electric Dress* and *Neon District* get the most translucent, blurriest panes, so the city bleeds through — while the enamel grounds of *Red and Black* and *The Void* sit dense and still. Line spacing tightens where the wires crowd and opens where the signal clears. The cursor blinks wherever the circuit is live; it rests only in the early paintings, the void, and the late clarity.

Each title bar carries a museum placard — *Electric Dress — Tanaka, 1956* — alongside the working directory. The full recipe per theme lives in [`themes/tanaka.json`](../themes/tanaka.json), and the techniques are documented in [TECHNIQUES.md](../TECHNIQUES.md).

---

## Acquisition

Double-click any `.terminal` file in this directory. It will appear in **Terminal → Preferences → Profiles**. Select it. Set it as default if you like.

Or, from the command line:

```sh
open "Tanaka — Electric Dress.terminal"
open "Tanaka — Red and Black.terminal"
```

---

[Return to the main gallery.](../README.md)
