import contextlib
import io
import json
import os
import plistlib
import subprocess
import sys
import tarfile
import tempfile
import unicodedata
import unittest
from pathlib import Path

from tools import ports
from tools.profiles import (
    check_port_names,
    RepositoryError,
    _install_port,
    audit_theme,
    filter_collections,
    ProfileRecord,
    load_repository,
    main,
    normalize_app,
    plan_terminal_install,
    swatch_svg,
    sync_colors_xml,
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
            "inactive_blur": 0.25,
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
        self.assertIn("inactive blur 0.85 must be 0.25", issues)

    def test_accepts_contrast_safe_glass_with_dynamic_ansi(self) -> None:
        issues = audit_theme("Fixture", dark_theme(active=0.93, inactive=0.93, dynamic=True))

        self.assertEqual([], issues)

    def test_raw_ansi_waives_only_the_ansi_checks(self) -> None:
        theme = dark_theme(active=0.93, inactive=0.93, dynamic=False)
        theme["colors"]["bright_yellow"] = "#1c1a24"
        theme["depth"]["raw_ansi"] = True

        self.assertEqual([], audit_theme("Fixture", theme))

        theme["colors"]["foreground"] = "#2a2830"
        issues = audit_theme("Fixture", theme)
        self.assertTrue(any(issue.startswith("foreground on opaque background") for issue in issues))
        self.assertFalse(any("dynamic ANSI" in issue for issue in issues))

    def test_disabled_dynamic_ansi_without_raw_ansi_still_fails(self) -> None:
        theme = dark_theme(active=0.93, inactive=0.93, dynamic=False)
        theme["colors"]["bright_yellow"] = "#1c1a24"

        issues = audit_theme("Fixture", theme)
        self.assertTrue(any("dynamic ANSI foregrounds are disabled" in issue for issue in issues))

    def test_raw_ansi_with_dynamic_ansi_enabled_is_rejected(self) -> None:
        theme = dark_theme(active=0.93, inactive=0.93, dynamic=True)
        theme["depth"]["raw_ansi"] = True

        self.assertIn(
            "raw ANSI requires dynamic ANSI foregrounds to be disabled",
            audit_theme("Fixture", theme),
        )


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


class ColorSyncTests(unittest.TestCase):
    def test_syncs_rgb_and_keeps_alpha_and_unrelated_settings(self) -> None:
        theme = dark_theme(active=0.93, inactive=0.93, dynamic=True)
        profile = plistlib.loads(complete_profile_xml(theme))
        profile["ANSIRedColor"] = archived_color(1.0, 0.0, 0.0, 1.0)
        profile["BackgroundColor"] = archived_color(1.0, 1.0, 1.0, 0.93)
        stale = plistlib.dumps(profile, fmt=plistlib.FMT_XML, sort_keys=False)

        updated = sync_colors_xml(stale, theme["colors"])
        synced = plistlib.loads(updated)
        color = plistlib.loads(synced["BackgroundColor"])
        root = color["$objects"][color["$top"]["root"].data]

        self.assertEqual([], verify_profile_xml("Fixture — Dark", updated, theme))
        self.assertEqual(b"0.09411764706 0.0862745098 0.1254901961 0.93", root["NSComponents"])
        self.assertEqual(b"0.09411764706 0.0862745098 0.1254901961 0.93\x00", root["NSRGB"])
        self.assertEqual("preserve-me", synced["UnrelatedSetting"])

    def test_color_sync_is_idempotent(self) -> None:
        theme = dark_theme(active=0.93, inactive=0.93, dynamic=True)

        once = sync_colors_xml(complete_profile_xml(theme), theme["colors"])
        twice = sync_colors_xml(once, theme["colors"])

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


ROOT = Path(__file__).resolve().parent.parent


def fixture_repository(root: Path) -> dict:
    """A one-theme repository whose profile, swatch and ports all match the spec."""
    (root / "themes").mkdir()
    (root / "fixture").mkdir()
    theme = {**dark_theme(active=0.93, inactive=0.93, dynamic=True), "slug": "dark"}
    spec = {"collection": "fixture", "artist": "Fixture", "themes": [theme]}
    (root / "themes" / "fixture.json").write_text(json.dumps(spec))
    (root / "fixture" / "Fixture — Dark.terminal").write_bytes(complete_profile_xml(theme))
    swatch = root / ".github" / "swatches" / "dark.svg"
    swatch.parent.mkdir(parents=True)
    swatch.write_text(swatch_svg(theme["colors"]))
    with contextlib.redirect_stdout(io.StringIO()):
        main(["sync-ports", "--root", str(root)])
    return theme


def run_main(args: list[str]) -> tuple[int, str]:
    report = io.StringIO()
    with contextlib.redirect_stdout(report), contextlib.redirect_stderr(report):
        code = main(args)
    return code, report.getvalue()


def fixture_record(name: str = "Fixture — Dark", collection: str = "fixture") -> ProfileRecord:
    theme = dark_theme(active=0.93, inactive=0.93, dynamic=True)
    theme["slug"] = name.split(" — ", 1)[1].lower().replace(" ", "-")
    return ProfileRecord(
        name, theme, Path(f"themes/{collection}.json"), Path(f"{collection}/{name}.terminal")
    )


class SwatchTests(unittest.TestCase):
    def test_renders_a_committed_swatch_byte_for_byte(self) -> None:
        spec = json.loads((ROOT / "themes" / "riley.json").read_text(encoding="utf-8"))
        cataract = next(theme for theme in spec["themes"] if theme["slug"] == "cataract")

        self.assertEqual(
            (ROOT / ".github" / "swatches" / "cataract.svg").read_text(encoding="utf-8"),
            swatch_svg(cataract["colors"]),
        )

    def test_verify_reports_a_drifted_swatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            theme = fixture_repository(root)
            swatch = root / ".github" / "swatches" / "dark.svg"

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, main(["verify", "--root", str(root)]))
            swatch.write_text(swatch_svg({**theme["colors"], "red": "#ff0000"}))
            report = io.StringIO()
            with contextlib.redirect_stdout(report):
                self.assertEqual(1, main(["verify", "--root", str(root)]))
            self.assertIn("dark.svg: swatch differs from spec", report.getvalue())


class PortSyncTests(unittest.TestCase):
    def test_sync_writes_every_port_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture_repository(root)
            files = sorted(p.relative_to(root).as_posix() for p in (root / "terminals").rglob("*") if p.is_file())
            self.assertEqual(
                [
                    "terminals/alacritty/Fixture — Dark.toml",
                    "terminals/ghostty/Fixture — Dark",
                    "terminals/iterm2/Fixture — Dark.itermcolors",
                    "terminals/kitty/Fixture — Dark.conf",
                    "terminals/warp/Fixture — Dark.yaml",
                    "terminals/wezterm/Fixture — Dark.toml",
                ],
                files,
            )
            code, out = run_main(["sync-ports", "--root", str(root)])
            self.assertEqual((0, "PORTS=6 UPDATED=0 REMOVED=0\n"), (code, out))

    def test_verify_reports_drifted_missing_and_stray_ports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture_repository(root)
            self.assertEqual(0, run_main(["verify", "--root", str(root)])[0])

            kitty = root / "terminals" / "kitty" / "Fixture — Dark.conf"
            kitty.write_text(kitty.read_text().replace("#5a3030", "#ff0000"))
            (root / "terminals" / "warp" / "Fixture — Dark.yaml").unlink()
            (root / "terminals" / "ghostty" / "Fixture — Retired").write_text("palette = 0=#000000\n")
            code, out = run_main(["verify", "--root", str(root)])
            self.assertEqual(1, code)
            self.assertIn("Fixture — Dark.conf: port differs from spec", out)
            self.assertIn("Fixture — Dark.yaml: missing port", out)
            self.assertIn("Fixture — Retired: port without a spec theme", out)
            self.assertIn("MISMATCHES=3", out)

            code, out = run_main(["sync-ports", "--root", str(root)])
            self.assertEqual((0, "PORTS=6 UPDATED=2 REMOVED=1\n"), (code, out))
            self.assertEqual(0, run_main(["verify", "--root", str(root)])[0])


class PortInstallTests(unittest.TestCase):
    def install(self, app: str, records, home: Path, **options) -> tuple[int, str]:
        report = io.StringIO()
        options = {"dry_run": False, "prune": False, "platform": "linux"} | options
        with contextlib.redirect_stdout(report), contextlib.redirect_stderr(report):
            code = _install_port(app, records, env={"HOME": str(home)}, **options)
        return code, report.getvalue()

    def test_names_the_terminal_loosely(self) -> None:
        self.assertEqual("terminal", normalize_app(None))
        self.assertEqual("terminal", normalize_app("Terminal.app"))
        self.assertEqual("iterm2", normalize_app("iTerm.app"))
        self.assertEqual("iterm2", normalize_app("iTerm2"))
        self.assertEqual("wezterm", normalize_app("WezTerm"))
        with self.assertRaises(RepositoryError):
            normalize_app("hyper")

    def test_installs_changed_files_and_prunes_only_its_own_retired_works(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            themes = home / ".config" / "ghostty" / "themes"
            code, out = self.install("ghostty", [fixture_record()], home, dry_run=True)
            self.assertEqual(0, code)
            self.assertIn("STALE=1", out)
            self.assertFalse(themes.exists())

            code, out = self.install("ghostty", [fixture_record()], home)
            self.assertEqual(0, code)
            self.assertIn("THEMES=1 STALE=0 RETIRED=0", out)
            self.assertIn("theme = Fixture — Dark", out)
            installed = themes / "Fixture — Dark"
            self.assertEqual(ports.ghostty(ports.Work("Fixture — Dark", "fixture-dark", "Dark — Fixture", fixture_record().theme["colors"])), installed.read_text())

            retired = ports.Work("Fixture — Retired", "fixture-retired", "Retired — Fixture", fixture_record().theme["colors"])
            (themes / "Fixture — Retired").write_text(ports.ghostty(retired))
            (themes / "Fixture — My own study").write_text("# mine\nbackground = #000000\n")
            (themes / "Someone Else — Theirs").write_text("")
            (themes / "my-theme").write_text("")
            code, out = self.install("ghostty", [fixture_record()], home)
            self.assertNotIn("install:", out)
            self.assertIn("retired (keep; --prune deletes): Fixture — Retired", out)
            self.assertNotIn("My own study", out)
            self.assertTrue((themes / "Fixture — Retired").exists())

            code, out = self.install("ghostty", [fixture_record()], home, prune=True)
            self.assertIn("pruned: Fixture — Retired", out)
            self.assertEqual(
                ["Fixture — Dark", "Fixture — My own study", "Someone Else — Theirs", "my-theme"],
                sorted(p.name for p in themes.iterdir()),
            )

    def test_iterm2_gets_one_dynamic_profiles_file_per_collection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            records = [fixture_record(), fixture_record("Other — Light", "other")]
            self.assertEqual(2, self.install("iterm2", records, home)[0])  # not on Linux

            code, out = self.install("iterm2", records, home, platform="darwin")
            self.assertEqual(0, code)
            self.assertIn("Choose one in iTerm2", out)
            folder = home / "Library" / "Application Support" / "iTerm2" / "DynamicProfiles"
            self.assertEqual(
                ["Gallery Zero — Fixture.json", "Gallery Zero — Other.json"],
                sorted(p.name for p in folder.iterdir()),
            )
            profile = json.loads((folder / "Gallery Zero — Fixture.json").read_text())["Profiles"][0]
            self.assertEqual("Fixture — Dark", profile["Name"])
            self.assertEqual(["Gallery Zero", "Fixture"], profile["Tags"])
            self.assertAlmostEqual(0x5A / 255, profile["Ansi 1 Color"]["Red Component"], places=5)
            self.assertIn("THEMES=2 STALE=0", self.install("iterm2", records, home, platform="darwin")[1])

    def test_iterm2_keeps_retired_profiles_until_pruned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            both = [fixture_record(), fixture_record("Fixture — Gone")]
            path = home / "Library" / "Application Support" / "iTerm2" / "DynamicProfiles" / "Gallery Zero — Fixture.json"

            def names() -> list[str]:
                return [profile["Name"] for profile in json.loads(path.read_text())["Profiles"]]

            self.assertEqual(0, self.install("iterm2", both, home, platform="darwin")[0])
            self.assertEqual(["Fixture — Dark", "Fixture — Gone"], names())

            code, out = self.install("iterm2", both[:1], home, platform="darwin")
            self.assertEqual(0, code)
            self.assertNotIn("install:", out)
            self.assertIn("retired (keep; --prune deletes): Fixture — Gone", out)
            self.assertIn("STALE=0 RETIRED=1", out)
            self.assertEqual(["Fixture — Dark", "Fixture — Gone"], names())

            code, out = self.install("iterm2", both[:1], home, platform="darwin", prune=True)
            self.assertEqual(0, code)
            self.assertIn("pruned: Fixture — Gone", out)
            self.assertIn("STALE=0 RETIRED=0", out)
            self.assertEqual(["Fixture — Dark"], names())

    def test_refuses_works_whose_port_files_would_collide(self) -> None:
        check_port_names([fixture_record(), fixture_record("Fixture — Light")])
        with self.assertRaisesRegex(RepositoryError, "Ghostty file 'Fixture — A B'"):
            check_port_names([fixture_record("Fixture — A, B"), fixture_record("Fixture — A B")])
        with self.assertRaisesRegex(RepositoryError, "Fixture — Dusk and Fixture — DUSK"):  # macOS disks ignore case
            check_port_names([fixture_record("Fixture — Dusk"), fixture_record("Fixture — DUSK")])

    def test_theme_folders_follow_each_terminal(self) -> None:
        home = {"HOME": "/h"}
        self.assertEqual(Path("/h/.config/ghostty/themes"), ports.theme_dir("ghostty", home, "darwin"))
        self.assertEqual(Path("/x/ghostty/themes"), ports.theme_dir("ghostty", home | {"XDG_CONFIG_HOME": "/x"}, "linux"))
        self.assertEqual(Path("/k/themes"), ports.theme_dir("kitty", home | {"KITTY_CONFIG_DIRECTORY": "/k"}, "linux"))
        self.assertEqual(Path("/h/.config/wezterm/colors"), ports.theme_dir("wezterm", home, "linux"))
        self.assertEqual(Path("/h/.config/alacritty/themes"), ports.theme_dir("alacritty", home, "linux"))
        self.assertEqual(Path("/h/.warp/themes"), ports.theme_dir("warp", home, "darwin"))
        self.assertEqual(Path("/h/.local/share/warp-terminal/themes"), ports.theme_dir("warp", home, "linux"))


class TerminalInstallPlanTests(unittest.TestCase):
    def installed(self, record: ProfileRecord) -> dict:
        return plistlib.loads(complete_profile_xml(record.theme, record.name))

    def test_current_profile_needs_nothing(self) -> None:
        record = fixture_record()

        self.assertEqual(([], []), plan_terminal_install([record], {record.name: self.installed(record)}))

    def test_missing_and_stale_profiles_are_installed(self) -> None:
        current, missing = fixture_record(), fixture_record("Fixture — Light")
        stale = self.installed(current)
        stale["ANSIRedColor"] = archived_color(1.0, 0.0, 0.0, 1.0)

        install, prune = plan_terminal_install([current, missing], {current.name: stale})

        self.assertEqual([current, missing], install)
        self.assertEqual([], prune)

    def test_matches_names_stored_decomposed(self) -> None:
        record = fixture_record("Fixture — Nébula 8")
        stored = unicodedata.normalize("NFD", record.name)

        self.assertEqual(([], []), plan_terminal_install([record], {stored: self.installed(record)}))

    def test_retires_only_this_galleries_unlisted_works(self) -> None:
        record = fixture_record("Fixture — Red with Red 1")
        installed = {
            record.name: self.installed(record),
            "Fixture — Retired Work": {},
            "Clear Dark": {},
            "Other — Not Ours": {},
        }

        self.assertEqual(([], ["Fixture — Retired Work"]), plan_terminal_install([record], installed))

    def test_filters_by_collection_and_leaves_other_packs_unretired(self) -> None:
        rothko = fixture_record("Rothko — Four Darks in Red", collection="rothko")
        de_amaral = fixture_record("De Amaral — Pirámide D", collection="de-amaral")
        demuth = fixture_record("Demuth — My Egypt", collection="demuth")
        records = [rothko, de_amaral, demuth]

        self.assertEqual(records, filter_collections(records, None))
        self.assertEqual([rothko, de_amaral], filter_collections(records, ["Rothko,De Amaral"]))
        self.assertEqual([rothko, demuth], filter_collections(records, ["rothko", "demuth"]))

        installed = {
            rothko.name: self.installed(rothko),
            demuth.name: self.installed(demuth),
        }
        selected = filter_collections(records, ["rothko"])
        self.assertEqual(([], []), plan_terminal_install(selected, installed))

    def test_rejects_unknown_or_empty_collection_names(self) -> None:
        records = [
            fixture_record("Rothko — Four Darks in Red", collection="rothko"),
            fixture_record("Demuth — My Egypt", collection="demuth"),
        ]

        with self.assertRaisesRegex(RepositoryError, r"unknown collection\(s\): picasso"):
            filter_collections(records, ["rothko", "picasso"])
        with self.assertRaisesRegex(RepositoryError, "no collection specified"):
            filter_collections(records, [" , "])

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["install-terminal", "--dry-run", "--pack", "picasso"])
        self.assertEqual(2, code)
        self.assertIn("unknown collection(s): picasso", stderr.getvalue())

    def test_lists_available_collections(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["install-terminal", "--list"])
        self.assertEqual(0, code)
        output = stdout.getvalue()
        self.assertIn("rothko", output)
        self.assertIn("de-amaral", output)
        self.assertIn("Demuth (7)", output)


class InstallScriptTests(unittest.TestCase):
    def test_help_and_list_from_local_checkout(self) -> None:
        script = ROOT / "install.sh"
        help_run = subprocess.run(["sh", str(script), "--help"], capture_output=True, text=True, check=True)
        self.assertIn("install.sh [OPTIONS] [COLLECTION...]", help_run.stdout)

        list_run = subprocess.run(["sh", str(script), "--list"], capture_output=True, text=True, check=True)
        self.assertIn("rothko", list_run.stdout)
        self.assertIn("de-amaral", list_run.stdout)

    def test_piped_stdin_fetches_tarball_and_cleans_up(self) -> None:
        script_bytes = (ROOT / "install.sh").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            archive_path = tmp / "gallery-zero.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tf:
                tf.add(ROOT / "tools" / "profiles.py", arcname="gallery-zero-main/tools/profiles.py")
                tf.add(ROOT / "tools" / "ports.py", arcname="gallery-zero-main/tools/ports.py")
                tf.add(ROOT / "themes", arcname="gallery-zero-main/themes")
                for folder in ("condo", "de-amaral", "demuth", "monet", "pelton", "riley", "rothko", "tanaka"):
                    tf.add(ROOT / folder, arcname=f"gallery-zero-main/{folder}")
            scratch_tmp = tmp / "worktmp"
            scratch_tmp.mkdir()
            env = {
                **os.environ,
                "GALLERY_ZERO_TARBALL": archive_path.as_uri(),
                "TMPDIR": str(scratch_tmp),
            }
            run = subprocess.run(
                ["sh", "-s", "--", "--list"],
                input=script_bytes,
                capture_output=True,
                env=env,
                check=True,
            )
            self.assertIn(b"Rothko (7)", run.stdout)
            self.assertEqual([], list(scratch_tmp.iterdir()))

    @unittest.skipUnless(sys.platform == "darwin", "dry-run reads macOS Terminal defaults")
    def test_dry_run_accepts_bare_and_spaced_pack_names(self) -> None:
        run = subprocess.run(
            ["sh", str(ROOT / "install.sh"), "--dry-run", "rothko", "De Amaral"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("PROFILES=14 ", run.stdout)

    def test_terminal_flag_installs_ports_on_any_platform(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env = {"PATH": os.environ["PATH"], "HOME": directory}
            run = subprocess.run(
                ["sh", str(ROOT / "install.sh"), "--terminal", "Ghostty", "--dry-run", "rothko"],
                capture_output=True, text=True, env=env, check=True,
            )
            self.assertIn("THEMES=7 STALE=7 RETIRED=0", run.stdout)
            self.assertEqual([], list(Path(directory).iterdir()))

            missing = subprocess.run(["sh", str(ROOT / "install.sh"), "-t"], capture_output=True, text=True)
            self.assertEqual(2, missing.returncode)
            self.assertIn("requires a terminal name", missing.stderr)


if __name__ == "__main__":
    unittest.main()
