#!/usr/bin/env python3
"""Synchronize and validate Gallery Zero macOS Terminal profiles."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
import plistlib
import sys
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
            if state == "active" and not depth["dynamic_ansi_foregrounds"]:
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
    if failing_ansi and not depth["dynamic_ansi_foregrounds"]:
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


def _verify(records: Sequence[ProfileRecord]) -> int:
    mismatches = 0
    for record in records:
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("sync-depth", "verify", "audit-contrast")
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
    if arguments.command == "sync-depth":
        return _sync_depth(records)
    if arguments.command == "verify":
        return _verify(records)
    return _audit_contrast(records)


if __name__ == "__main__":
    raise SystemExit(main())
