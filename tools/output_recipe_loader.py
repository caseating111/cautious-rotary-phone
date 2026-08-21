from __future__ import annotations

import json
from pathlib import Path

try:
    from tools.custom_matrix_selection import normalize_selection
except ModuleNotFoundError:
    from custom_matrix_selection import normalize_selection


def load_output_recipe(path: str | Path) -> dict:
    recipe_path = Path(path)
    if not recipe_path.is_file():
        raise SystemExit(f"Output recipe not found: {recipe_path}")
    try:
        data = json.loads(recipe_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read output recipe: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("Output recipe must contain a JSON object.")
    if data.get("recipe_version") != 1:
        raise SystemExit(f"Unsupported output recipe version: {data.get('recipe_version')!r}")
    if data.get("output_type") != "custom matrix":
        raise SystemExit(
            f"This comparison builder can reopen only custom matrix recipes, not {data.get('output_type')!r}."
        )
    selection = normalize_selection(data.get("selection", {}))
    display_text = str(data.get("display_mode", "raw")).casefold()
    display_mode = "Presentation normalized" if "presentation normalized" in display_text else "Raw"
    return {
        "selection": selection,
        "display_mode": display_mode,
        "source_recipe": str(recipe_path),
        "output_path": str(data.get("output_path", "")),
    }


def default_recipe_folder(matrix_output: str | Path) -> Path:
    return Path(matrix_output) / "_workflow" / "output-recipes"
