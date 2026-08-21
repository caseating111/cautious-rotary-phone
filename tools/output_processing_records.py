from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def record_paths(output_root: Path, output_path: Path) -> tuple[Path, Path]:
    identifier = output_path.name
    human = output_root / "Processing Logs" / f"{identifier}.txt"
    machine = output_root / "_workflow" / "output-recipes" / f"{identifier}.json"
    return human, machine


def write_output_records(
    output_root: str | Path,
    output_path: str | Path,
    *,
    output_type: str,
    selection: dict,
    required_crops: int,
    available_crops: int,
    used_crops: int,
    display_mode: str = "raw",
    control_source: dict | None = None,
    notes: list[str] | None = None,
) -> tuple[Path, Path]:
    root = Path(output_root)
    output = Path(output_path)
    human_path, machine_path = record_paths(root, output)
    human_path.parent.mkdir(parents=True, exist_ok=True)
    machine_path.parent.mkdir(parents=True, exist_ok=True)

    created = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    recipe = {
        "recipe_version": 1,
        "created": created,
        "output_type": output_type,
        "output_path": str(output),
        "selection": selection,
        "display_mode": display_mode,
        "control_source": control_source,
        "crops": {
            "required": int(required_crops),
            "available": int(available_crops),
            "used": int(used_crops),
        },
        "notes": list(notes or []),
    }
    machine_path.write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")

    lines = [
        "OUTPUT PROCESSING LOG",
        "",
        f"Created: {created}",
        f"Output type: {output_type}",
        f"Output: {output}",
        f"Display processing: {display_mode}",
        "",
        "Selection:",
    ]
    for group in selection.get("groups", []):
        columns = ", ".join(str(value) for value in group.get("columns", [])) or "none"
        lines.append(f"  {group.get('experiment', '')} / {group.get('set', '')}: columns {columns}")
    conditions = ", ".join(str(value) for value in selection.get("conditions", [])) or "none"
    states = ", ".join(str(value) for value in selection.get("states", [])) or "none"
    lines.extend([
        f"  Conditions/types: {conditions}",
        f"  Crop states: {states}",
        "",
    ])
    if control_source:
        lines.append(
            "Control source: "
            f"{control_source.get('experiment', '')} / {control_source.get('set', '')}"
        )
        lines.append("")
    lines.extend(
        [
            "Input crops:",
            f"  Required: {required_crops}",
            f"  Available: {available_crops}",
            f"  Used: {used_crops}",
        ]
    )
    if notes:
        lines.extend(["", "Notes:"])
        lines.extend(f"  - {note}" for note in notes)
    else:
        lines.extend(["", "Notes:", "  No warnings recorded."])
    human_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return human_path, machine_path
