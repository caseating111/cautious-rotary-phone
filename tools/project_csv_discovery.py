from __future__ import annotations

from pathlib import Path


CSV_TARGETS = {
    "grid_csv": "grid.csv",
    "images_csv": "images.csv",
    "condition_order_csv": "condition_order.csv",
}


def _matching_csvs(folder: Path, target_name: str) -> list[Path]:
    target = target_name.casefold()
    csv_files = sorted(
        (
            path
            for path in folder.iterdir()
            if path.is_file() and path.suffix.casefold() == ".csv"
        ),
        key=lambda path: path.name.casefold(),
    )

    exact = [path for path in csv_files if path.name.casefold() == target]
    if exact:
        return exact
    return [path for path in csv_files if target in path.name.casefold()]


def discover_project_csvs(folder: Path) -> dict[str, Path]:
    folder = folder.resolve()
    if not folder.is_dir():
        raise ValueError(f"CSV folder not found: {folder}")

    found: dict[str, Path] = {}
    problems: list[str] = []

    for key, target_name in CSV_TARGETS.items():
        matches = _matching_csvs(folder, target_name)
        if not matches:
            problems.append(f"No CSV filename containing {target_name!r} was found.")
            continue
        if len(matches) > 1:
            names = ", ".join(path.name for path in matches)
            problems.append(
                f"More than one CSV matches {target_name!r}: {names}. Rename/remove the ambiguity or select the file manually."
            )
            continue
        found[key] = matches[0]

    if problems:
        raise ValueError("Could not identify the three project CSVs safely:\n- " + "\n- ".join(problems))

    return found
