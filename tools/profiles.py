#!/usr/bin/env python3
"""Synchronize and validate Gallery Zero macOS Terminal profiles."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
import plistlib
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path
from typing import Any, Sequence


ANSI_KEYS = (
    "black",
    "red",
    "green",
    "yellow",
    "blue",
    "magenta",
    "cyan",
    "white",
    "bright_black",
    "bright_red",
    "bright_green",
    "bright_yellow",
    "bright_blue",
    "bright_magenta",
    "bright_cyan",
    "bright_white",
)

CONTRAST_MINIMUM = 4.5

# Glass policy. Apple's bundled translucent profiles (Clear Light 0.93, Clear
# Dark 0.95, blur 0.5) hold alpha when unfocused and drop blur to zero; thinner
# or blurrier glass lifts a dark pane to mid-grey over a bright desktop. We keep
# a light unfocused blur so text in the window behind smears to a flat tint
# instead of ghosting through.
ALPHA_FLOOR = 0.93
BLUR_CAP = 0.5
INACTIVE_BLUR = 0.25
BACKINGS = ("#000000", "#808080", "#ffffff")

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


class RepositoryError(ValueError):
    """A theme specification does not have a one-to-one profile artifact."""


@dataclass(frozen=True)
class ProfileRecord:
    name: str
    theme: dict[str, Any]
    spec_path: Path
    artifact_path: Path


def _rgb(hex_color: str) -> tuple[float, float, float]:
    value = hex_color.removeprefix("#")
    if len(value) != 6:
        raise ValueError(f"expected #rrggbb color, got {hex_color!r}")
    return tuple(int(value[offset : offset + 2], 16) / 255 for offset in (0, 2, 4))  # type: ignore[return-value]


def _linear(component: float) -> float:
    if component <= 0.04045:
        return component / 12.92
    return ((component + 0.055) / 1.055) ** 2.4


def _luminance(color: tuple[float, float, float]) -> float:
    red, green, blue = (_linear(component) for component in color)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(
    foreground: tuple[float, float, float] | str,
    background: tuple[float, float, float] | str,
) -> float:
    foreground_rgb = _rgb(foreground) if isinstance(foreground, str) else foreground
    background_rgb = _rgb(background) if isinstance(background, str) else background
    lighter = max(_luminance(foreground_rgb), _luminance(background_rgb))
    darker = min(_luminance(foreground_rgb), _luminance(background_rgb))
    return (lighter + 0.05) / (darker + 0.05)


def composite(
    foreground: tuple[float, float, float] | str,
    background: tuple[float, float, float] | str,
    alpha: float,
) -> tuple[float, float, float]:
    foreground_rgb = _rgb(foreground) if isinstance(foreground, str) else foreground
    background_rgb = _rgb(background) if isinstance(background, str) else background
    return tuple(
        alpha * foreground_component + (1 - alpha) * background_component
        for foreground_component, background_component in zip(foreground_rgb, background_rgb)
    )  # type: ignore[return-value]


def audit_theme(artist: str, theme: dict[str, Any]) -> list[str]:
    del artist  # Profile name is supplied by the caller when reporting repository issues.
    colors = theme["colors"]
    depth = theme["depth"]
    issues: list[str] = []
    # A theme may opt out of Terminal's ANSI adjustment to show its palette raw
    # (Tanaka's Neon District keeps gamut-edge neon on white). The opt-out only
    # waives the ANSI checks; foreground and bold must still clear the minimum.
    raw_ansi = depth.get("raw_ansi", False)
    if raw_ansi and depth["dynamic_ansi_foregrounds"]:
        issues.append("raw ANSI requires dynamic ANSI foregrounds to be disabled")

    for key in ("foreground", "bold"):
        ratio = contrast_ratio(colors[key], colors["background"])
        if ratio < CONTRAST_MINIMUM:
            issues.append(f"{key} on opaque background: {ratio:.2f}:1 < {CONTRAST_MINIMUM:.2f}:1")

    if depth["background_alpha"] < ALPHA_FLOOR:
        issues.append(f"background alpha {depth['background_alpha']!r} < floor {ALPHA_FLOOR!r}")
    if depth["background_blur"] > BLUR_CAP:
        issues.append(f"background blur {depth['background_blur']!r} > cap {BLUR_CAP!r}")
    if depth["inactive_alpha"] != depth["background_alpha"]:
        issues.append("inactive alpha must equal background alpha")
    if depth["inactive_blur"] != INACTIVE_BLUR:
        issues.append(f"inactive blur {depth['inactive_blur']!r} must be {INACTIVE_BLUR!r}")

    for state, alpha_key in (
        ("active", "background_alpha"),
        ("inactive", "inactive_alpha"),
    ):
        for backing in BACKINGS:
            rendered_background = composite(colors["background"], backing, depth[alpha_key])
            for key in ("foreground", "bold"):
                ratio = contrast_ratio(colors[key], rendered_background)
                if ratio < CONTRAST_MINIMUM:
                    label = "" if key == "foreground" else "bold "
                    issues.append(
                        f"{label}{state} background over {backing}: "
                        f"{ratio:.2f}:1 < {CONTRAST_MINIMUM:.2f}:1"
                    )
            if state == "active" and not depth["dynamic_ansi_foregrounds"] and not raw_ansi:
                glass_failing = [
                    key
                    for key in ANSI_KEYS
                    if contrast_ratio(colors[key], rendered_background) < CONTRAST_MINIMUM
                ]
                if glass_failing:
                    issues.append(
                        f"dynamic ANSI foregrounds are disabled while {len(glass_failing)} "
                        f"ANSI colors are below {CONTRAST_MINIMUM:.2f}:1 over {backing}"
                    )

    failing_ansi = [
        key
        for key in ANSI_KEYS
        if contrast_ratio(colors[key], colors["background"]) < CONTRAST_MINIMUM
    ]
    if failing_ansi and not depth["dynamic_ansi_foregrounds"] and not raw_ansi:
        issues.append(
            "dynamic ANSI foregrounds are disabled while "
            f"{len(failing_ansi)} ANSI colors are below {CONTRAST_MINIMUM:.2f}:1"
        )

    return issues


def _color_root(archive: dict[str, Any]) -> dict[str, Any]:
    root_reference = archive["$top"]["root"]
    if not isinstance(root_reference, plistlib.UID):
        raise ValueError("NSColor archive root is not a UID")
    root = archive["$objects"][root_reference.data]
    if not isinstance(root, dict):
        raise ValueError("NSColor archive root is not an object")
    return root


def _replace_alpha(components: bytes, alpha: float) -> bytes:
    terminator = b"\x00" if components.endswith(b"\x00") else b""
    body = components[: -len(terminator)] if terminator else components
    prefix, separator, _ = body.rpartition(b" ")
    if not separator:
        raise ValueError("NSColor components do not contain an alpha value")
    return prefix + separator + str(float(alpha)).encode("ascii") + terminator


def _update_background_alpha(data: bytes, alpha: float) -> bytes:
    archive = plistlib.loads(data)
    root = _color_root(archive)
    for key in ("NSComponents", "NSRGB"):
        value = root.get(key)
        if not isinstance(value, bytes):
            raise ValueError(f"NSColor archive is missing byte field {key}")
        root[key] = _replace_alpha(value, alpha)
    return plistlib.dumps(archive, fmt=plistlib.FMT_BINARY, sort_keys=False)


def _replace_rgb(components: bytes, hex_color: str) -> bytes:
    terminator = b"\x00" if components.endswith(b"\x00") else b""
    body = components[: -len(terminator)] if terminator else components
    values = body.split(b" ")
    if len(values) < 3:
        raise ValueError("NSColor components do not contain an RGB triple")
    rgb = [f"{component:.10g}".encode("ascii") for component in _rgb(hex_color)]
    return b" ".join(rgb + values[3:]) + terminator


def _update_rgb(data: bytes, hex_color: str) -> bytes:
    archive = plistlib.loads(data)
    root = _color_root(archive)
    for key in ("NSComponents", "NSRGB"):
        value = root.get(key)
        if not isinstance(value, bytes):
            raise ValueError(f"NSColor archive is missing byte field {key}")
        root[key] = _replace_rgb(value, hex_color)
    return plistlib.dumps(archive, fmt=plistlib.FMT_BINARY, sort_keys=False)


def sync_colors_xml(xml: bytes, colors: dict[str, str]) -> bytes:
    """Rewrite each color's RGB from the spec, keeping its alpha and color space."""
    profile = plistlib.loads(xml)
    for color_name, profile_key in COLOR_KEYS.items():
        profile[profile_key] = _update_rgb(profile[profile_key], colors[color_name])
    return plistlib.dumps(profile, fmt=plistlib.FMT_XML, sort_keys=False)


def sync_profile_xml(xml: bytes, depth: dict[str, Any]) -> bytes:
    profile = plistlib.loads(xml)
    profile["BackgroundColor"] = _update_background_alpha(
        profile["BackgroundColor"], depth["background_alpha"]
    )
    profile["BackgroundAlphaInactive"] = depth["inactive_alpha"]
    profile["BackgroundBlur"] = depth["background_blur"]
    profile["BackgroundBlurInactive"] = depth["inactive_blur"]
    profile["BackgroundSettingsForInactiveWindows"] = True
    profile["DynamicANSIForegroundColors"] = depth["dynamic_ansi_foregrounds"]
    profile["CursorBlink"] = depth["cursor_blink"]
    profile["FontHeightSpacing"] = depth["font_height_spacing"]
    profile["WindowTitle"] = depth["window_title"]
    profile["columnCount"] = depth["columns"]
    profile["rowCount"] = depth["rows"]
    profile["ShowRepresentedURLInTitle"] = depth["show_cwd_path_in_title"]
    profile["ShowRepresentedURLPathInTitle"] = depth["show_cwd_path_in_title"]
    return plistlib.dumps(profile, fmt=plistlib.FMT_XML, sort_keys=False)


def _color_components(data: bytes) -> tuple[float, float, float, float]:
    archive = plistlib.loads(data)
    components = _color_root(archive).get("NSComponents")
    if not isinstance(components, bytes):
        raise ValueError("NSColor archive is missing byte field NSComponents")
    values = [float(value) for value in components.rstrip(b"\x00").split()]
    if len(values) != 4:
        raise ValueError(f"expected four NSColor components, found {len(values)}")
    return values[0], values[1], values[2], values[3]


def _hex_color(components: tuple[float, float, float, float]) -> str:
    return "#" + "".join(f"{round(component * 255):02x}" for component in components[:3])


def verify_profile_xml(name: str, xml: bytes, theme: dict[str, Any]) -> list[str]:
    profile = plistlib.loads(xml)
    depth = theme["depth"]
    issues: list[str] = []

    if profile.get("name") != name:
        issues.append(f"name: expected {name!r}, found {profile.get('name')!r}")

    for color_name, profile_key in COLOR_KEYS.items():
        try:
            components = _color_components(profile[profile_key])
        except (KeyError, TypeError, ValueError, plistlib.InvalidFileException) as error:
            issues.append(f"{color_name}: invalid {profile_key}: {error}")
            continue
        expected = theme["colors"][color_name].lower()
        found = _hex_color(components)
        if found != expected:
            issues.append(f"{color_name}: expected {expected}, found {found}")
        expected_alpha = depth["background_alpha"] if color_name == "background" else 1.0
        if not math.isclose(components[3], expected_alpha, abs_tol=1e-9):
            issues.append(
                f"{color_name} alpha: expected {expected_alpha!r}, found {components[3]!r}"
            )

    expected_values = {
        "BackgroundAlphaInactive": depth["inactive_alpha"],
        "BackgroundBlur": depth["background_blur"],
        "BackgroundBlurInactive": depth["inactive_blur"],
        "BackgroundSettingsForInactiveWindows": True,
        "DynamicANSIForegroundColors": depth["dynamic_ansi_foregrounds"],
        "CursorBlink": depth["cursor_blink"],
        "FontHeightSpacing": depth["font_height_spacing"],
        "WindowTitle": depth["window_title"],
        "columnCount": depth["columns"],
        "rowCount": depth["rows"],
        "ShowRepresentedURLInTitle": depth["show_cwd_path_in_title"],
        "ShowRepresentedURLPathInTitle": depth["show_cwd_path_in_title"],
    }
    for key, expected in expected_values.items():
        found = profile.get(key)
        matches = (
            math.isclose(found, expected, abs_tol=1e-9)
            if isinstance(expected, float) and isinstance(found, (int, float))
            else found == expected
        )
        if not matches:
            issues.append(f"{key}: expected {expected!r}, found {found!r}")

    return issues


SWATCH_ROWS = (ANSI_KEYS[:8], ANSI_KEYS[8:])


def swatch_svg(colors: dict[str, str]) -> str:
    """The 360x200 palette card: foreground band, then normal and bright rows."""
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="360" height="200" viewBox="0 0 360 200">',
        f'  <rect width="360" height="200" rx="8" fill="{colors["background"]}"/>',
        "",
        "  <!-- foreground band -->",
        f'  <rect x="16" y="16" width="328" height="28" rx="4" fill="{colors["foreground"]}" opacity="0.9"/>',
    ]
    for y, row in zip((56, 102), SWATCH_ROWS):
        for index, key in enumerate(row):
            lines.append(
                f'  <rect x="{16 + index * 41.75:.1f}" y="{y}" width="35.8" height="40" rx="3" fill="{colors[key]}"/>'
            )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def swatch_path(root: Path, theme: dict[str, Any]) -> Path:
    return root / ".github" / "swatches" / f"{theme['slug']}.svg"


def load_repository(root: Path) -> list[ProfileRecord]:
    records: list[ProfileRecord] = []
    expected_artifacts: set[Path] = set()
    names: set[str] = set()

    for spec_path in sorted((root / "themes").glob("*.json")):
        with spec_path.open("rb") as handle:
            spec = json.load(handle)
        collection = spec["collection"]
        artist = spec["artist"]
        for theme in spec["themes"]:
            name = f"{artist} — {theme['name']}"
            if name in names:
                raise RepositoryError(f"duplicate profile name: {name}")
            names.add(name)
            artifact_path = root / collection / f"{name}.terminal"
            relative_artifact = artifact_path.relative_to(root)
            if not artifact_path.is_file():
                raise RepositoryError(f"missing artifact: {relative_artifact}")
            expected_artifacts.add(artifact_path)
            records.append(ProfileRecord(name, theme, spec_path, artifact_path))

    actual_artifacts = set(root.glob("*/*.terminal"))
    unexpected = sorted(actual_artifacts - expected_artifacts)
    if unexpected:
        raise RepositoryError(f"unexpected artifact: {unexpected[0].relative_to(root)}")
    if not records:
        raise RepositoryError("no themes found")
    return records


def _sync_depth(records: Sequence[ProfileRecord]) -> int:
    updated = 0
    for record in records:
        original = record.artifact_path.read_bytes()
        result = sync_profile_xml(original, record.theme["depth"])
        if result != original:
            record.artifact_path.write_bytes(result)
            updated += 1
    print(f"PROFILES={len(records)} UPDATED={updated}")
    return 0


def _sync_colors(records: Sequence[ProfileRecord]) -> int:
    updated = 0
    for record in records:
        original = record.artifact_path.read_bytes()
        result = sync_colors_xml(original, record.theme["colors"])
        if result != original:
            record.artifact_path.write_bytes(result)
            updated += 1
    print(f"PROFILES={len(records)} UPDATED={updated}")
    return 0


def _sync_swatches(root: Path, records: Sequence[ProfileRecord]) -> int:
    updated = 0
    for record in records:
        path = swatch_path(root, record.theme)
        result = swatch_svg(record.theme["colors"])
        if not path.is_file() or path.read_text(encoding="utf-8") != result:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(result, encoding="utf-8")
            updated += 1
    print(f"SWATCHES={len(records)} UPDATED={updated}")
    return 0


def _verify(root: Path, records: Sequence[ProfileRecord]) -> int:
    mismatches = 0
    for record in records:
        path = swatch_path(root, record.theme)
        if not path.is_file():
            print(f"{path.relative_to(root)}: missing swatch")
            mismatches += 1
        elif path.read_text(encoding="utf-8") != swatch_svg(record.theme["colors"]):
            print(f"{path.relative_to(root)}: swatch differs from spec (run sync-swatches)")
            mismatches += 1
        for issue in verify_profile_xml(
            record.name, record.artifact_path.read_bytes(), record.theme
        ):
            print(f"{record.artifact_path}: {issue}")
            mismatches += 1
    print(f"PROFILES={len(records)} MISMATCHES={mismatches}")
    return int(bool(mismatches))


def _audit_contrast(records: Sequence[ProfileRecord]) -> int:
    failures = 0
    for record in records:
        for issue in audit_theme(record.name, record.theme):
            print(f"{record.name}: {issue}")
            failures += 1
    print(f"PROFILES={len(records)} FAILURES={failures}")
    return int(bool(failures))

# --- Terminal.app installation -------------------------------------------------
#
# Terminal stores profiles in com.apple.Terminal "Window Settings", keyed by
# name in NFD; repo names are NFC, so every comparison normalizes. Opening a
# .terminal file never replaces a same-named profile: it adds "X 1" (or nothing,
# if an identical copy is installed) and opens a window. So an update imports,
# moves tabs onto the new set, deletes the old one, renames the new one, and
# closes the import window. Deleting the default or startup profile silently
# resets both, so they are restored at the end. Terminal rewrites color blobs
# on import, so "current" means verify_profile_xml passes, not equal bytes.


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def plan_terminal_install(
    records: Sequence[ProfileRecord], installed: dict[str, dict[str, Any]]
) -> tuple[list[ProfileRecord], list[str]]:
    """Return (records to install or update, installed names to prune)."""
    by_name = {_nfc(name): profile for name, profile in installed.items()}
    stale = []
    for record in records:
        profile = by_name.get(_nfc(record.name))
        if profile is None:
            stale.append(record)
            continue
        profile = {**profile, "name": record.name}
        xml = plistlib.dumps(profile, fmt=plistlib.FMT_XML, sort_keys=False)
        if verify_profile_xml(record.name, xml, record.theme):
            stale.append(record)
    current = {_nfc(record.name) for record in records}
    artists = {record.name.split(" — ", 1)[0] for record in records}
    retired = sorted(
        name
        for name in installed
        if _nfc(name).split(" — ", 1)[0] in artists
        and " — " in name
        and _nfc(name) not in current
    )
    return stale, retired


def _osascript(script: str) -> str:
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def _quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _tell(body: str) -> str:
    return _osascript(f'tell application "Terminal"\n{body}\nend tell')


def _set_names() -> list[str]:
    # One name per line: a profile name can hold a comma ("Buildings, Lancaster"),
    # so AppleScript's default ", " list rendering cannot be split back apart.
    listing = _tell(
        "set AppleScript's text item delimiters to linefeed\n"
        "return (name of every settings set) as text"
    )
    return [_nfc(name) for name in listing.split("\n") if name]


def _window_ids() -> set[str]:
    return {wid for wid in _tell("get id of every window").split(", ") if wid}


def _retarget_tabs(old: str, new: str, skip: set[str] | frozenset[str] = frozenset()) -> None:
    # Loop over window ids: "repeat with w in windows" fails partway as windows change.
    for wid in _window_ids() - skip:
        _tell(
            "try\n"
            f"repeat with t in (tabs of (first window whose id is {wid}))\n"
            f"if name of current settings of t is {_quote(old)} then "
            f"set current settings of t to settings set {_quote(new)}\n"
            "end repeat\nend try"
        )


def _installed_profiles() -> dict[str, Any]:
    exported = subprocess.run(
        ["defaults", "export", "com.apple.Terminal", "-"], capture_output=True, check=True
    ).stdout
    return plistlib.loads(exported)


def _install_terminal(records: Sequence[ProfileRecord], *, dry_run: bool, prune: bool) -> int:
    if sys.platform != "darwin":
        print("error: install-terminal needs macOS Terminal.app", file=sys.stderr)
        return 2
    prefs = _installed_profiles()
    installed = prefs.get("Window Settings", {})
    stale, retired = plan_terminal_install(records, installed)
    for record in stale:
        print(f"install: {record.name}")
    for name in retired:
        print(f"{'prune' if prune else 'retired (keep; --prune deletes)'}: {_nfc(name)}")
    if dry_run or (not stale and not (prune and retired)):
        print(f"PROFILES={len(records)} STALE={len(stale)} RETIRED={len(retired)}")
        return 0

    default = _nfc(prefs.get("Default Window Settings", ""))
    startup = _nfc(prefs.get("Startup Window Settings", ""))
    by_name = {_nfc(name): profile for name, profile in installed.items()}
    fallback_font = by_name.get(default, {}).get("Font")

    with tempfile.TemporaryDirectory() as scratch:
        for record in stale:
            name = _nfc(record.name)
            profile = plistlib.loads(record.artifact_path.read_bytes())
            font = by_name.get(name, {}).get("Font", fallback_font)
            if font is not None:
                profile["Font"] = font  # Repo files carry no font; keep the user's.
            staged = Path(scratch) / record.artifact_path.name
            staged.write_bytes(plistlib.dumps(profile, fmt=plistlib.FMT_XML, sort_keys=False))

            before, windows_before = set(_set_names()), _window_ids()
            subprocess.run(["open", "-a", "Terminal", str(staged)], check=True)
            added: set[str] = set()
            for _ in range(40):
                time.sleep(0.25)
                added = set(_set_names()) - before
                if added:
                    break
            time.sleep(0.4)
            import_windows = _window_ids() - windows_before
            if len(added) != 1:
                raise RuntimeError(f"{record.name}: expected one imported set, found {sorted(added)}")
            imported = added.pop()
            if imported != name:
                if name in before:
                    _retarget_tabs(name, imported, skip=import_windows)
                    _tell(f"delete settings set {_quote(name)}")
                _tell(f"set name of settings set {_quote(imported)} to {_quote(name)}")
            for wid in import_windows:
                _tell(f"close (first window whose id is {wid})")
            print(f"installed: {record.name}")

        if prune:
            for name in retired:
                if _nfc(name) in (default, startup):
                    print(f"kept (default/startup): {_nfc(name)}")
                    continue
                _retarget_tabs(_nfc(name), default)
                _tell(f"delete settings set {_quote(_nfc(name))}")
                print(f"pruned: {_nfc(name)}")

    for setting, value in (("default settings", default), ("startup settings", startup)):
        if value and value in _set_names():
            _tell(f"set {setting} to settings set {_quote(value)}")
    stale_after, retired_after = plan_terminal_install(
        records, _installed_profiles().get("Window Settings", {})
    )
    print(f"PROFILES={len(records)} STALE={len(stale_after)} RETIRED={len(retired_after)}")
    return int(bool(stale_after))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "sync-colors",
            "sync-depth",
            "sync-swatches",
            "verify",
            "audit-contrast",
            "install-terminal",
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="install-terminal: print the plan without touching Terminal.app",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="install-terminal: also delete installed gallery profiles that are no longer in the repo",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="repository root (default: parent of tools/)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        records = load_repository(arguments.root.resolve())
    except (KeyError, OSError, RepositoryError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if arguments.command == "sync-colors":
        return _sync_colors(records)
    if arguments.command == "sync-depth":
        return _sync_depth(records)
    if arguments.command == "sync-swatches":
        return _sync_swatches(arguments.root.resolve(), records)
    if arguments.command == "verify":
        return _verify(arguments.root.resolve(), records)
    if arguments.command == "install-terminal":
        return _install_terminal(records, dry_run=arguments.dry_run, prune=arguments.prune)
    return _audit_contrast(records)


if __name__ == "__main__":
    raise SystemExit(main())
