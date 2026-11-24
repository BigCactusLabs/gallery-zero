import json
import plistlib
import tomllib
import unicodedata
import unittest
from pathlib import Path

from tools import ports
from tools.profiles import load_repository, work_of

ROOT = Path(__file__).resolve().parent.parent
WORKS = [work_of(record) for record in load_repository(ROOT)]


def hex_of(component: dict) -> str:
    return "#" + "".join(f"{round(component[f'{c} Component'] * 255):02x}" for c in ("Red", "Green", "Blue"))


def pairs(text: str, separator: str) -> dict[str, str]:
    """key/value lines of a Ghostty or kitty theme, comments skipped."""
    found = {}
    for line in text.splitlines():
        if line and not line.startswith("#"):
            key, _, value = line.partition(separator)
            found[key.strip()] = value.strip()
    return found


class PortRenderTests(unittest.TestCase):
    """Every port carries the spec's palette into its own terminal's format."""

    def test_the_whole_gallery_is_ported(self) -> None:
        self.assertEqual(56, len(WORKS))

    def test_ghostty(self) -> None:
        for work in WORKS:
            c = work.colors
            found = pairs(ports.ghostty(work), " = ")
            palette = [line.split(" = ", 1)[1].split("=") for line in ports.ghostty(work).splitlines() if line.startswith("palette")]
            self.assertEqual([[str(i), c[slot]] for i, slot in enumerate(ports.SLOTS)], palette, work.name)
            self.assertEqual(c["background"], found["background"])
            self.assertEqual(c["cursor_text"], found["cursor-text"])
            self.assertEqual("cell-foreground", found["selection-foreground"])
            self.assertNotIn("bold-color", found)  # it would force bold-as-bright on

    def test_kitty(self) -> None:
        for work in WORKS:
            found = pairs(ports.kitty(work), " ")
            self.assertEqual([work.colors[s] for s in ports.SLOTS], [found[f"color{i}"] for i in range(16)])
            self.assertEqual("none", found["selection_foreground"])
            self.assertIn(f"## name: {work.name}", ports.kitty(work))

    def test_wezterm(self) -> None:
        for work in WORKS:
            scheme = tomllib.loads(ports.wezterm(work))
            self.assertEqual([work.colors[s] for s in ports.SLOTS[:8]], scheme["colors"]["ansi"])
            self.assertEqual([work.colors[s] for s in ports.SLOTS[8:]], scheme["colors"]["brights"])
            self.assertEqual(work.name, scheme["metadata"]["name"])

    def test_alacritty(self) -> None:
        for work in WORKS:
            colors = tomllib.loads(ports.alacritty(work))["colors"]
            for name in ports.ANSI:
                self.assertEqual(work.colors[name], colors["normal"][name])
                self.assertEqual(work.colors[f"bright_{name}"], colors["bright"][name])
            self.assertEqual(work.colors["bold"], colors["primary"]["bright_foreground"])
            self.assertEqual("CellForeground", colors["selection"]["text"])

    def test_iterm2_round_trips_every_color(self) -> None:
        for work in WORKS:
            preset = plistlib.loads(ports.iterm2(work).encode())
            for key, slot in ports.ITERM_KEYS.items():
                self.assertEqual(work.colors[slot], hex_of(preset[key]), f"{work.name} {key}")
                self.assertEqual("sRGB", preset[key]["Color Space"])

    def test_warp(self) -> None:
        for work in WORKS:
            text = ports.warp(work)
            for name in ports.ANSI:
                self.assertIn(f'    {name}: "{work.colors[name]}"', text)
                self.assertIn(f'    {name}: "{work.colors["bright_" + name]}"', text.split("  bright:")[1])
            details = "lighter" if ports.is_light(work.colors["background"]) else "darker"
            self.assertIn(f"details: {details}", text)

    def test_light_and_dark_backgrounds(self) -> None:
        self.assertTrue(ports.is_light("#f4efe6"))
        self.assertFalse(ports.is_light("#181620"))

    def test_dynamic_profiles_are_stable_and_distinct(self) -> None:
        profiles = json.loads(ports.iterm_dynamic_profiles(WORKS))["Profiles"]
        self.assertEqual(len(WORKS), len({p["Guid"] for p in profiles}))
        self.assertEqual(ports.iterm_guid(WORKS[0]), profiles[0]["Guid"])


class PortNameTests(unittest.TestCase):
    def test_ghostty_theme_names_cannot_be_misread(self) -> None:
        ghostty = ports.BY_APP["ghostty"]
        for work in WORKS:
            self.assertFalse(set(ghostty.theme_name(work)) & set(",:="), work.name)
        thanks = next(w for w in WORKS if w.name.startswith("Tanaka — Thanks"))
        self.assertEqual("Tanaka — Thanks Sam", ghostty.filename(thanks))

    def test_file_names_are_distinct_on_case_insensitive_disks(self) -> None:
        for port in ports.PORTS:
            names = {unicodedata.normalize("NFC", port.filename(w)).casefold() for w in WORKS}
            self.assertEqual(len(WORKS), len(names), port.app)


if __name__ == "__main__":
    unittest.main()
