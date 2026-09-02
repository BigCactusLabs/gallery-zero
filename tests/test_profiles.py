import json
import plistlib
import tempfile
import unittest
from pathlib import Path

from tools.profiles import (
    RepositoryError,
    audit_theme,
    load_repository,
    sync_profile_xml,
    verify_profile_xml,
)


COLOR_KEYS = {
    "black": "ANSIBlackColor",
    "red": "ANSIRedColor",
    "green": "ANSIGreenColor",
    "yellow": "ANSIYellowColor",
    "blue": "ANSIBlueColor",
    "magenta": "ANSIMagentaColor",
    "cyan": "ANSICyanColor",
    "white": "ANSIWhiteColor",
    "bright_black": "ANSIBrightBlackColor",
    "bright_red": "ANSIBrightRedColor",
    "bright_green": "ANSIBrightGreenColor",
    "bright_yellow": "ANSIBrightYellowColor",
    "bright_blue": "ANSIBrightBlueColor",
    "bright_magenta": "ANSIBrightMagentaColor",
    "bright_cyan": "ANSIBrightCyanColor",
    "bright_white": "ANSIBrightWhiteColor",
    "background": "BackgroundColor",
    "foreground": "TextColor",
    "bold": "TextBoldColor",
    "cursor": "CursorColor",
    "cursor_text": "CursorTextColor",
    "selection": "SelectionColor",
}


def archived_color(red: float, green: float, blue: float, alpha: float) -> bytes:
    components = f"{red} {green} {blue} {alpha}".encode()
    rgb = components + b"\x00"
    archive = {
        "$version": 100000,
        "$archiver": "NSKeyedArchiver",
        "$top": {"root": plistlib.UID(1)},
        "$objects": [
            "$null",
            {
                "$class": plistlib.UID(2),
                "NSComponents": components,
                "NSRGB": rgb,
            },
            {"$classname": "NSColor", "$classes": ["NSColor", "NSObject"]},
        ],
    }
    return plistlib.dumps(archive, fmt=plistlib.FMT_BINARY, sort_keys=False)


def profile_xml() -> bytes:
    profile = {
        "BackgroundColor": archived_color(0.1, 0.2, 0.3, 0.50),
        "BackgroundAlphaInactive": 0.50,
        "BackgroundBlur": 0.25,
        "BackgroundBlurInactive": 0.25,
        "BackgroundSettingsForInactiveWindows": True,
        "DynamicANSIForegroundColors": False,
        "CursorBlink": False,
        "FontHeightSpacing": 1.0,
        "WindowTitle": "Fixture",
        "columnCount": 80,
        "rowCount": 24,
        "UnrelatedSetting": "preserve-me",
    }
    return plistlib.dumps(profile, fmt=plistlib.FMT_XML, sort_keys=False)


def dark_theme(*, active: float, inactive: float, dynamic: bool) -> dict:
    return {
        "name": "Dark",
        "colors": {
            "black": "#181620",
            "red": "#5a3030",
            "green": "#405040",
            "yellow": "#c0a050",
            "blue": "#303050",
            "magenta": "#503050",
            "cyan": "#405060",
            "white": "#9090a8",
            "bright_black": "#282838",
            "bright_red": "#a86858",
            "bright_green": "#507858",
            "bright_yellow": "#d0b060",
            "bright_blue": "#5868a8",
            "bright_magenta": "#886098",
            "bright_cyan": "#507888",
            "bright_white": "#a8a8c0",
            "background": "#181620",
            "foreground": "#9090a8",
            "bold": "#a8a8c0",
            "cursor": "#c0a050",
            "cursor_text": "#181620",
            "selection": "#282838",
        },
        "depth": {
            "background_alpha": active,
            "background_blur": 0.5,
            "inactive_alpha": inactive,
            "inactive_blur": 0.0,
            "columns": 110,
            "rows": 30,
            "font_height_spacing": 1.16,
            "window_title": "Dark — Fixture",
            "cursor_blink": False,
            "dynamic_ansi_foregrounds": dynamic,
            "show_cwd_path_in_title": True,
        },
    }


def complete_profile_xml(theme: dict, profile_name: str = "Fixture — Dark") -> bytes:
    depth = theme["depth"]
    profile = plistlib.loads(profile_xml())
    profile["name"] = profile_name
    for color_name, profile_key in COLOR_KEYS.items():
        red, green, blue = (
            int(theme["colors"][color_name][offset : offset + 2], 16) / 255
            for offset in (1, 3, 5)
        )
        alpha = depth["background_alpha"] if color_name == "background" else 1.0
        profile[profile_key] = archived_color(red, green, blue, alpha)
    return sync_profile_xml(
        plistlib.dumps(profile, fmt=plistlib.FMT_XML, sort_keys=False), depth
    )


class ContrastAuditTests(unittest.TestCase):
    def test_rejects_translucent_background_and_disabled_dynamic_ansi(self) -> None:
        issues = audit_theme("Fixture", dark_theme(active=0.87, inactive=0.78, dynamic=False))

        self.assertIn("active background over #ffffff: 3.92:1 < 4.50:1", issues)
        self.assertIn("inactive background over #ffffff: 2.84:1 < 4.50:1", issues)
        self.assertTrue(any(issue.startswith("bold inactive background") for issue in issues))
        self.assertTrue(any("dynamic ANSI foregrounds are disabled" in issue for issue in issues))
        self.assertTrue(any("over #808080" in issue for issue in issues))

    def test_rejects_glass_outside_policy(self) -> None:
        theme = dark_theme(active=0.92, inactive=0.85, dynamic=True)
        theme["depth"]["background_blur"] = 0.85
        theme["depth"]["inactive_blur"] = 0.85

        issues = audit_theme("Fixture", theme)

        self.assertIn("background alpha 0.92 < floor 0.93", issues)
        self.assertIn("background blur 0.85 > cap 0.5", issues)
        self.assertIn("inactive alpha must equal background alpha", issues)
        self.assertIn("inactive blur 0.85 must be 0", issues)

    def test_accepts_contrast_safe_glass_with_dynamic_ansi(self) -> None:
        issues = audit_theme("Fixture", dark_theme(active=0.93, inactive=0.93, dynamic=True))

        self.assertEqual([], issues)


class ProfileSyncTests(unittest.TestCase):
    def test_syncs_depth_without_changing_rgb_or_unrelated_settings(self) -> None:
        original = profile_xml()
        depth = {
            "background_alpha": 0.95,
            "background_blur": 0.60,
            "inactive_alpha": 0.90,
            "inactive_blur": 0.70,
            "columns": 110,
            "rows": 30,
            "font_height_spacing": 1.12,
            "window_title": "Updated",
            "cursor_blink": True,
            "dynamic_ansi_foregrounds": True,
            "show_cwd_path_in_title": True,
        }

        updated = sync_profile_xml(original, depth)
        profile = plistlib.loads(updated)
        color = plistlib.loads(profile["BackgroundColor"])
        root = color["$objects"][color["$top"]["root"].data]

        self.assertEqual(b"0.1 0.2 0.3 0.95", root["NSComponents"])
        self.assertEqual(b"0.1 0.2 0.3 0.95\x00", root["NSRGB"])
        self.assertEqual(0.90, profile["BackgroundAlphaInactive"])
        self.assertEqual(0.60, profile["BackgroundBlur"])
        self.assertEqual(0.70, profile["BackgroundBlurInactive"])
        self.assertTrue(profile["DynamicANSIForegroundColors"])
        self.assertEqual("preserve-me", profile["UnrelatedSetting"])

    def test_sync_is_idempotent(self) -> None:
        depth = {
            "background_alpha": 0.50,
            "background_blur": 0.25,
            "inactive_alpha": 0.50,
            "inactive_blur": 0.25,
            "columns": 80,
            "rows": 24,
            "font_height_spacing": 1.0,
            "window_title": "Fixture",
            "cursor_blink": False,
            "dynamic_ansi_foregrounds": False,
            "show_cwd_path_in_title": True,
        }

        once = sync_profile_xml(profile_xml(), depth)
        twice = sync_profile_xml(once, depth)

        self.assertEqual(once, twice)


class ProfileVerificationTests(unittest.TestCase):
    def test_accepts_profile_that_matches_all_colors_and_depth(self) -> None:
        theme = dark_theme(active=0.93, inactive=0.93, dynamic=True)

        issues = verify_profile_xml("Fixture — Dark", complete_profile_xml(theme), theme)

        self.assertEqual([], issues)

    def test_reports_color_and_depth_mismatches(self) -> None:
        theme = dark_theme(active=0.93, inactive=0.93, dynamic=True)
        profile = plistlib.loads(complete_profile_xml(theme))
        profile["ANSIRedColor"] = archived_color(1.0, 0.0, 0.0, 1.0)
        profile["DynamicANSIForegroundColors"] = False

        issues = verify_profile_xml(
            "Fixture — Dark",
            plistlib.dumps(profile, fmt=plistlib.FMT_XML, sort_keys=False),
            theme,
        )

        self.assertIn("red: expected #5a3030, found #ff0000", issues)
        self.assertIn("DynamicANSIForegroundColors: expected True, found False", issues)

    def test_repository_loader_requires_one_artifact_per_theme(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "themes").mkdir()
            (root / "fixture").mkdir()
            spec = {
                "collection": "fixture",
                "artist": "Fixture",
                "themes": [dark_theme(active=0.93, inactive=0.93, dynamic=True)],
            }
            (root / "themes" / "fixture.json").write_text(json.dumps(spec))

            with self.assertRaisesRegex(
                RepositoryError, "missing artifact: fixture/Fixture — Dark.terminal"
            ):
                load_repository(root)


if __name__ == "__main__":
    unittest.main()
