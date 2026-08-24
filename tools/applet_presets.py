from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any

FORMAT_VERSION = 1
DEFAULT_STORE = Path.home() / ".cautious-rotary-phone" / "applet_presets.json"


def _store_path(path: str | Path | None = None) -> Path:
    if path is not None:
        return Path(path)
    override = os.environ.get("CAUTIOUS_APPLET_PRESETS", "").strip()
    return Path(override) if override else DEFAULT_STORE


def _empty_store() -> dict[str, Any]:
    return {
        "format_version": FORMAT_VERSION,
        "last_used": {},
        "presets": {},
        "custom_colors": [],
    }


def _preset_name(name: str) -> str:
    clean = str(name).strip()
    if not clean:
        raise ValueError("Preset name is required.")
    if any(character in clean for character in '\\/:*?"<>|'):
        raise ValueError("Preset name contains a Windows-unsafe character.")
    return clean


def _category(name: str) -> str:
    clean = str(name).strip().casefold().replace(" ", "_")
    if not clean or not clean.replace("_", "").isalnum():
        raise ValueError(
            "Preset category must contain letters, numbers, or underscores."
        )
    return clean


def _validate_store(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("format_version") != FORMAT_VERSION:
        raise ValueError("Unsupported applet preset store.")
    for key in ("last_used", "presets"):
        if not isinstance(value.get(key), dict):
            raise TypeError(f"Applet preset store {key} must be an object.")
    colors = value.get("custom_colors", [])
    if not isinstance(colors, list) or any(
        not isinstance(item, str) for item in colors
    ):
        raise ValueError("Applet custom colors must be a list of hex strings.")
    return value


def load_store(path: str | Path | None = None) -> dict[str, Any]:
    destination = _store_path(path)
    if not destination.is_file():
        return _empty_store()
    try:
        value = json.loads(destination.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read applet presets: {exc}") from exc
    return _validate_store(value)


def save_store(value: dict[str, Any], path: str | Path | None = None) -> Path:
    store = _validate_store(copy.deepcopy(value))
    destination = _store_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(store, indent=2, sort_keys=True) + "\n"
    descriptor, temporary = tempfile.mkstemp(
        prefix=destination.name + ".", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return destination


def load_last(
    category: str, default: Any = None, *, path: str | Path | None = None
) -> Any:
    value = load_store(path)["last_used"].get(_category(category), default)
    return copy.deepcopy(value)


def save_last(category: str, settings: Any, *, path: str | Path | None = None) -> Path:
    store = load_store(path)
    store["last_used"][_category(category)] = copy.deepcopy(settings)
    return save_store(store, path)


def list_presets(category: str, *, path: str | Path | None = None) -> list[str]:
    values = load_store(path)["presets"].get(_category(category), {})
    if not isinstance(values, dict):
        raise TypeError("Preset category is not an object.")
    return sorted(values, key=str.casefold)


def load_preset(
    category: str, name: str, *, path: str | Path | None = None
) -> dict[str, Any]:
    store = load_store(path)
    try:
        value = store["presets"][_category(category)][_preset_name(name)]
    except KeyError as exc:
        raise ValueError(f"Unknown preset: {name}") from exc
    if not isinstance(value, dict):
        raise TypeError("Saved preset must be an object.")
    return copy.deepcopy(value)


def save_preset(
    category: str,
    name: str,
    settings: dict[str, Any],
    *,
    path: str | Path | None = None,
) -> Path:
    if not isinstance(settings, dict):
        raise TypeError("Preset settings must be an object.")
    store = load_store(path)
    values = store["presets"].setdefault(_category(category), {})
    values[_preset_name(name)] = copy.deepcopy(settings)
    return save_store(store, path)


def delete_preset(category: str, name: str, *, path: str | Path | None = None) -> Path:
    store = load_store(path)
    values = store["presets"].setdefault(_category(category), {})
    values.pop(_preset_name(name), None)
    return save_store(store, path)


def normalize_hex_color(value: str) -> str:
    clean = str(value).strip().upper()
    if len(clean) == 6:
        clean = "#" + clean
    if len(clean) != 7 or clean[0] != "#":
        raise ValueError("Colour must use #RRGGBB notation.")
    try:
        int(clean[1:], 16)
    except ValueError as exc:
        raise ValueError("Colour must use #RRGGBB notation.") from exc
    return clean


def save_custom_color(value: str, *, path: str | Path | None = None) -> Path:
    color = normalize_hex_color(value)
    store = load_store(path)
    if color not in store["custom_colors"]:
        store["custom_colors"].append(color)
        store["custom_colors"].sort()
    return save_store(store, path)


def custom_colors(*, path: str | Path | None = None) -> list[str]:
    return [normalize_hex_color(value) for value in load_store(path)["custom_colors"]]
