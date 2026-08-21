from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

from PIL import Image

try:
    from tools import custom_matrix_selection as custom
    from tools.preflight_batch import discover_sources, expected_output_names
except ModuleNotFoundError:
    import custom_matrix_selection as custom
    from preflight_batch import discover_sources, expected_output_names


def safe_file_name(value: str) -> str:
    replacements = {
        "\\": "-",
        "/": "-",
        ":": "-",
        "*": "-",
        "?": "",
        '"': "",
        "<": "(",
        ">": ")",
        "|": "-",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value


def read_key_values(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise SystemExit(f"Archived Fiji display range not found: {path}")
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def find_range_file(range_dir: Path, source_filename: str) -> Path:
    expected = range_dir / f"{safe_file_name(source_filename)}.txt"
    if expected.is_file():
        return expected
    key = expected.name.casefold()
    matches = [path for path in range_dir.glob("*.txt") if path.name.casefold() == key]
    if len(matches) == 1:
        return matches[0]
    raise SystemExit(
        f"No archived Fiji display range exists for {source_filename}. "
        "Open that source plate after accepted alignment and run Global visibility once, or use Raw display mode."
    )


def load_range(
    range_dir: Path,
    source_filename: str,
    source_path: Path | None = None,
) -> tuple[float, float]:
    path = find_range_file(range_dir, source_filename)
    values = read_key_values(path)
    archived_name = values.get("source_filename", "")
    if archived_name and archived_name.casefold() != source_filename.casefold():
        raise SystemExit(
            f"Display range identity mismatch: requested {source_filename}, archive says {archived_name}."
        )
    if source_path is not None and path.stat().st_mtime_ns < source_path.stat().st_mtime_ns:
        raise SystemExit(
            f"Archived Fiji display range is older than the current source image: {source_filename}. "
            "Run Global visibility once on the current source plate, or use Raw display mode."
        )
    try:
        black = float(values["black_point"])
        high = float(values["high_point"])
    except (KeyError, ValueError) as exc:
        raise SystemExit(f"Archived display range is incomplete or invalid: {path}") from exc
    if high <= black:
        raise SystemExit(f"Archived display range has high_point <= black_point: {path}")
    return black, high


def display_map(image: Image.Image, black: float, high: float) -> Image.Image:
    if image.mode in {"RGB", "RGBA", "CMYK", "YCbCr", "HSV", "LAB", "P"}:
        working = image.convert("L")
    elif image.mode == "L":
        working = image.copy()
    else:
        # Preserve integer intensity values before reducing the derived presentation copy to 8-bit.
        working = image.convert("I")

    span = high - black
    if working.mode == "L":
        lut = []
        for value in range(256):
            # Calculate the ratio directly rather than multiplying by a pre-rounded 2.55-style
            # scale. The epsilon only neutralizes binary float representation immediately below
            # an exact half; it is far smaller than one output intensity step.
            mapped = math.floor((((value - black) * 255.0) / span) + 0.500000001)
            lut.append(max(0, min(255, mapped)))
        return working.point(lut)

    scale = 255.0 / span
    # Pillow handles linear point transforms for I-mode images; conversion to L clamps to 0..255.
    mapped = working.point(lambda value: (value - black) * scale)
    return mapped.convert("L")


def crop_source_map(grid_csv: Path, images_csv: Path) -> dict[str, str]:
    _, grid_rows = custom.read_rows(grid_csv)
    _, image_rows = custom.read_rows(images_csv)
    grid_by_key: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in grid_rows:
        clean = {key: (value or "").strip() for key, value in row.items()}
        grid_by_key[(clean.get("Experiment", ""), clean.get("Set", ""))].append(clean)

    mapping: dict[str, str] = {}
    for raw_row in image_rows:
        row = {key: (value or "").strip() for key, value in raw_row.items()}
        grid = grid_by_key.get((row.get("Experiment", ""), row.get("Set", "")), [])
        for name in expected_output_names(row, grid):
            key = name.casefold()
            if key in mapping and mapping[key].casefold() != row.get("Filename", "").casefold():
                raise SystemExit(f"One crop filename maps to multiple source plates: {name}")
            mapping[key] = row.get("Filename", "")
    return mapping


def source_paths_by_name(image_root: Path | None) -> dict[str, list[Path]]:
    if image_root is None:
        return {}
    sources: dict[str, list[Path]] = defaultdict(list)
    for source in discover_sources(image_root):
        sources[source.name.casefold()].append(source)
    return dict(sources)


def normalize_staged_crops(
    staged_paths: list[Path],
    grid_csv: Path,
    images_csv: Path,
    range_dir: Path,
    image_root: Path | None = None,
) -> int:
    mapping = crop_source_map(grid_csv, images_csv)
    sources = source_paths_by_name(image_root)
    cache: dict[str, tuple[float, float]] = {}
    normalized = 0
    for path in staged_paths:
        source_filename = mapping.get(path.name.casefold())
        if not source_filename:
            raise SystemExit(f"Could not map staged crop back to a source plate: {path.name}")
        key = source_filename.casefold()
        if key not in cache:
            source_path = None
            if image_root is not None:
                matches = sources.get(key, [])
                if len(matches) != 1:
                    raise SystemExit(
                        f"Expected one current source image named {source_filename} before presentation normalization; "
                        f"found {len(matches)}."
                    )
                source_path = matches[0]
            cache[key] = load_range(range_dir, source_filename, source_path=source_path)
        black, high = cache[key]
        try:
            with Image.open(path) as image:
                derived = display_map(image, black, high)
                derived.save(path)
        except OSError as exc:
            raise SystemExit(f"Could not presentation-normalize staged crop {path}: {exc}") from exc
        normalized += 1
    return normalized