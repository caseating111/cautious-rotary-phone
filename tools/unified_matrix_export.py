from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

try:
    from tools import custom_matrix_selection as custom
    from tools import run_existing_pillow_from_config as pillow_adapter
    from tools.run_custom_matrix_job import validate_selected_freshness
    from tools.run_dedup_with_control import patch_preferred_control
except ModuleNotFoundError:
    import custom_matrix_selection as custom
    import run_existing_pillow_from_config as pillow_adapter
    from run_custom_matrix_job import validate_selected_freshness
    from run_dedup_with_control import patch_preferred_control


OUTPUT_TYPES = {
    "per-experiment": "Per-experiment matrices",
    "all-strains": "All-strain matrices",
    "all-strains-dedup": "All strains (remove extra WTs)",
    "label-individual": "Label individual crops",
}
CATEGORY_FOLDERS = {
    "all-strains": "1. All Strain Matrices",
    "all-strains-dedup": "2. All Strain Matrices -- No WT Dupe",
    "per-experiment": "3. Per Experiment Matrices",
    "label-individual": "4. Individual Labelled Crops",
}
ALL_EXPORTS_FOLDER = "!All Matrix Exports"
RUN_RE = re.compile(r"^Run(\d{3,})_", re.IGNORECASE)
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def normalize_request(request: dict) -> dict:
    if not isinstance(request, dict):
        raise SystemExit("Unified matrix request must be a JSON object.")
    selection = custom.normalize_selection(request.get("selection", {}))
    raw_outputs = request.get("outputs", [])
    if not isinstance(raw_outputs, list) or not raw_outputs:
        raise SystemExit("Select at least one matrix or labelled-crop output.")
    outputs: list[str] = []
    for raw in raw_outputs:
        alias = str(raw).strip()
        if alias not in OUTPUT_TYPES:
            raise SystemExit(f"Unsupported unified output type: {alias!r}")
        if alias not in outputs:
            outputs.append(alias)
    preferred = request.get("preferred_wt")
    clean_preferred = None
    if preferred is not None:
        if not isinstance(preferred, dict):
            raise SystemExit("Preferred WT source must contain experiment and set.")
        experiment = str(preferred.get("experiment", "")).strip()
        set_name = str(preferred.get("set", "")).strip()
        if experiment and set_name:
            clean_preferred = {"experiment": experiment, "set": set_name}
    if "all-strains-dedup" in outputs and clean_preferred is None:
        raise SystemExit("Choose a preferred WT source for the no-WT-duplicate output.")
    return {
        "selection": selection,
        "outputs": outputs,
        "preferred_wt": clean_preferred,
        "normalize_wt_names": bool(request.get("normalize_wt_names", True)),
    }


def _safe_component(value: str, *, label: str) -> str:
    component = pillow_adapter.safe_name(str(value).strip())
    reserved_stem = component.split(".", 1)[0].upper()
    if (
        not component
        or component in {".", ".."}
        or component.endswith((" ", "."))
        or reserved_stem in WINDOWS_RESERVED
        or "/" in component
        or "\\" in component
    ):
        raise SystemExit(f"Unsafe Windows {label}: {value!r}")
    return component


def _preset_folder(config: dict) -> Path:
    return Path(config["grid_csv"]).parent / "_workflow" / "matrix-presets"


def _preset_path(config: dict, name: str) -> Path:
    clean = name.strip()
    safe = _safe_component(clean, label="preset name")
    if safe != clean or safe.lower().endswith(".json"):
        raise SystemExit("Preset names must be safe Windows names and must omit .json.")
    return _preset_folder(config) / f"{safe}.json"


def preset_names(config: dict) -> list[str]:
    folder = _preset_folder(config)
    if not folder.is_dir():
        return []
    return sorted((path.stem for path in folder.glob("*.json") if path.is_file()), key=str.casefold)


def save_preset(config: dict, name: str, request: dict) -> Path:
    request = normalize_request(request)
    path = _preset_path(config, name)
    existing = {candidate.casefold(): candidate for candidate in preset_names(config)}
    old = existing.get(name.strip().casefold())
    if old is not None and old != name.strip():
        raise SystemExit(f"A preset named {old!r} already exists (Windows names are case-insensitive).")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)
    return path


def load_preset(config: dict, name: str) -> dict:
    requested = name.strip().casefold()
    match = next((item for item in preset_names(config) if item.casefold() == requested), None)
    if match is None:
        raise SystemExit(f"Matrix preset not found: {name}")
    path = _preset_folder(config) / f"{match}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read matrix preset {path}: {exc}") from exc
    return normalize_request(data)


def delete_preset(config: dict, name: str) -> None:
    requested = name.strip().casefold()
    match = next((item for item in preset_names(config) if item.casefold() == requested), None)
    if match is None:
        raise SystemExit(f"Matrix preset not found: {name}")
    (_preset_folder(config) / f"{match}.json").unlink()


def _control_name(name: str, normalize_separators: bool) -> str | None:
    compare = name.strip().upper()
    if normalize_separators:
        compare = compare.replace("-", " ").replace("_", " ")
    compare = " ".join(compare.split())
    return compare if compare in {"WT X", "WT Y"} else None


def control_groups_for_selection(
    config: dict,
    selection: dict,
    normalize_wt_names: bool = True,
) -> list[tuple[str, str]]:
    selection = custom.normalize_selection(selection)
    columns = {
        (group["experiment"].casefold(), group["set"].casefold()): set(group["columns"])
        for group in selection["groups"]
    }
    found: dict[tuple[str, str], tuple[str, str]] = {}
    for row in pillow_adapter.read_csv_rows(Path(config["grid_csv"])):
        exp = row.get("Experiment", "")
        set_name = row.get("Set", "")
        key = (exp.casefold(), set_name.casefold())
        try:
            column = int(row.get("Column", ""))
        except ValueError:
            continue
        if (
            key in columns
            and column in columns[key]
            and _control_name(row.get("Strain", ""), normalize_wt_names)
        ):
            found[key] = (exp, set_name)
    return sorted(found.values(), key=lambda item: (_natural_key(item[0]), _natural_key(item[1])))


def _natural_key(value: str) -> tuple:
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.split(r"(\d+)", value)
        if part
    )


def _validate_preferred(config: dict, request: dict) -> None:
    if "all-strains-dedup" not in request["outputs"]:
        return
    preferred = request["preferred_wt"]
    candidates = control_groups_for_selection(
        config, request["selection"], request["normalize_wt_names"]
    )
    wanted = (preferred["experiment"].casefold(), preferred["set"].casefold())
    if wanted not in {(exp.casefold(), set_name.casefold()) for exp, set_name in candidates}:
        available = ", ".join(f"{exp}/{set_name}" for exp, set_name in candidates) or "none"
        raise SystemExit(
            f"Preferred WT source {preferred['experiment']}/{preferred['set']} is not a selected "
            f"group with a selected recognised WT column. Available: {available}"
        )

def _next_run_number(matrix_root: Path) -> int:
    highest = 0
    if matrix_root.is_dir():
        for path in matrix_root.rglob("*"):
            if path.is_file():
                match = RUN_RE.match(path.name)
                if match:
                    highest = max(highest, int(match.group(1)))
    return highest + 1


@contextmanager
def _export_lock(matrix_root: Path):
    lock = matrix_root / ".unified-matrix-export.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise SystemExit(
            "Another matrix export appears to be running. Wait for it to finish, then try again."
        ) from exc
    try:
        os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
        os.close(descriptor)
        yield
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def _patch_wt_normalization(configured: Path, normalize: bool) -> None:
    text = configured.read_text(encoding="utf-8")
    pattern = re.compile(r'(?m)^(?P<indent>\s*)\.replace\("-", " "\)\s*$')
    matches = list(pattern.finditer(text))
    if len(matches) != 2:
        raise SystemExit("Deduplicated renderer no longer has the expected WT normalizer.")
    if normalize:
        text = pattern.sub(
            lambda match: match.group(0) + f'\n{match.group("indent")}.replace("_", " ")',
            text,
        )
    else:
        text = pattern.sub("", text)
    configured.write_text(text, encoding="utf-8")


def _renderer_expected(alias: str, request: dict, selected: list[Path]) -> set[str]:
    states = request["selection"]["states"]
    if alias == "per-experiment":
        return {
            f"{group['experiment']}_{group['set']}_{state}_MATRIX.png".casefold()
            for group in request["selection"]["groups"]
            for state in states
        }
    if alias == "all-strains":
        return {f"ALL_{state}_MATRIX.png".casefold() for state in states}
    if alias == "all-strains-dedup":
        return {f"WT_EXP2A_ALL_{state}.png".casefold() for state in states}
    return {path.name.casefold() for path in selected}


def _run_renderer(
    alias: str,
    request: dict,
    config: dict,
    filtered: dict[str, Path],
    staged_root: Path,
    render_root: Path,
    selected: list[Path],
) -> list[Path]:
    output_root = render_root / alias
    local_config = dict(config)
    local_config.update({key: str(path) for key, path in filtered.items()})
    local_config["matrix_output"] = str(output_root)
    script_alias = "matrices" if alias == "per-experiment" else alias
    configured = pillow_adapter.configured_copy(
        script_alias,
        local_config,
        image_root=staged_root,
        configured_dir=render_root / "configured",
    )
    if alias != "label-individual":
        custom.patch_matrix_states(configured, request["selection"]["states"])
    if alias == "all-strains-dedup":
        preferred = request["preferred_wt"]
        patch_preferred_control(configured, preferred["experiment"], preferred["set"])
        _patch_wt_normalization(configured, request["normalize_wt_names"])
    result = subprocess.run(
        [sys.executable, str(configured)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stdout + "\n" + result.stderr).strip()
        raise SystemExit(
            f"{OUTPUT_TYPES[alias]} renderer failed:\n{detail}" if detail else result.returncode
        )
    images = sorted(
        path
        for path in output_root.rglob("*")
        if path.is_file() and path.suffix.lower() in pillow_adapter.IMAGE_EXTENSIONS
    )
    by_name = {path.name.casefold(): path for path in images}
    expected = _renderer_expected(alias, request, selected)
    missing = sorted(expected - set(by_name))
    if missing:
        raise SystemExit(
            f"{OUTPUT_TYPES[alias]} renderer returned success but omitted expected outputs:\n"
            + "\n".join(f"  - {name}" for name in missing)
        )
    return [by_name[name] for name in sorted(expected)]


def _label_metadata(filtered: dict[str, Path], states: list[str]) -> dict[str, tuple[str, str]]:
    grid = pillow_adapter.read_csv_rows(filtered["grid_csv"])
    images = pillow_adapter.read_csv_rows(filtered["images_csv"])
    strains = {
        (row.get("Experiment", ""), row.get("Set", ""), int(row.get("Column", "0"))):
            row.get("Strain", "")
        for row in grid
    }
    mapping: dict[str, tuple[str, str]] = {}
    for row in images:
        exp = row.get("Experiment", "")
        set_name = row.get("Set", "")
        type_name = row.get("Type", "")
        for (grid_exp, grid_set, column), strain in strains.items():
            if (grid_exp, grid_set) != (exp, set_name):
                continue
            for state in states:
                name = (
                    f"{exp}_{set_name}_{type_name}_{column:02d}_{state}_"
                    f"{pillow_adapter.safe_name(strain)}.png"
                )
                key = name.casefold()
                if key in mapping:
                    raise SystemExit(f"Duplicate labelled-crop output identity: {name}")
                mapping[key] = (exp, strain)
    return mapping


def _selected_wt_rows(config: dict, request: dict) -> list[dict[str, str]]:
    selection = request["selection"]
    columns = {
        (group["experiment"].casefold(), group["set"].casefold()): set(group["columns"])
        for group in selection["groups"]
    }
    rows = []
    for row in pillow_adapter.read_csv_rows(Path(config["grid_csv"])):
        key = (row.get("Experiment", "").casefold(), row.get("Set", "").casefold())
        try:
            column = int(row.get("Column", ""))
        except ValueError:
            continue
        canonical = _control_name(row.get("Strain", ""), request["normalize_wt_names"])
        if key in columns and column in columns[key] and canonical:
            rows.append({**row, "_canonical": canonical.replace(" ", "")})
    rows.sort(
        key=lambda row: (
            _natural_key(row.get("Experiment", "")),
            _natural_key(row.get("Set", "")),
            int(row.get("Column", "0")),
        )
    )
    return rows


def _retained_wt_rows(config: dict, request: dict) -> list[dict[str, str]]:
    candidates = _selected_wt_rows(config, request)
    preferred = request["preferred_wt"]
    retained = []
    for canonical in ("WTY", "WTX"):
        matches = [row for row in candidates if row["_canonical"] == canonical]
        if not matches:
            continue
        chosen = next(
            (
                row for row in matches
                if row["Experiment"].casefold() == preferred["experiment"].casefold()
                and row["Set"].casefold() == preferred["set"].casefold()
            ),
            matches[0],
        )
        retained.append(chosen)
    return sorted(retained, key=lambda row: (_natural_key(row["Experiment"]), _natural_key(row["Set"]), int(row["Column"])))


def _wt_provenance(config: dict, request: dict) -> str:
    rows = _retained_wt_rows(config, request)
    if not rows:
        raise SystemExit("No selected recognised WT rows are available for deduplication.")
    by_experiment: dict[str, dict[str, list[str]]] = {}
    for row in rows:
        by_experiment.setdefault(row["Experiment"], {}).setdefault(row["Set"], []).append(
            row["_canonical"]
        )
    pieces: list[str] = []
    for experiment in sorted(by_experiment, key=_natural_key):
        sets = by_experiment[experiment]
        ordered_sets = sorted(sets, key=_natural_key)
        if len(ordered_sets) == 1:
            set_name = ordered_sets[0]
            pieces.append(f"{experiment}.{set_name}-" + "".join(sets[set_name]))
        else:
            detail = ".".join(
                f"{set_name}.{''.join(sets[set_name])}" for set_name in ordered_sets
            )
            pieces.append(f"{experiment}-{detail}")
    return "_".join(pieces)


def _canonical_name(
    alias: str,
    source: Path,
    state: str | None,
    export_date: str,
    wt_provenance: str | None,
) -> str:
    suffix = f"_{state}" if state else ""
    if alias == "all-strains":
        return f"{export_date}_ALLmatrix{suffix}.png"
    if alias == "all-strains-dedup":
        return f"{export_date}_{wt_provenance}_Unique_WT_ALLmatrix{suffix}.png"
    return source.name

def _state_from_name(path: Path, states: list[str]) -> str | None:
    lower = path.stem.casefold()
    return next((state for state in states if f"_{state}".casefold() in lower), None)


def _publish_plan(
    matrix_root: Path,
    run_id: str,
    rendered: dict[str, list[Path]],
    request: dict,
    filtered: dict[str, Path],
    config: dict,
) -> list[tuple[Path, Path]]:
    plan: list[tuple[Path, Path]] = []
    label_meta = _label_metadata(filtered, request["selection"]["states"])
    export_date = datetime.now().strftime("%d.%m.%y")
    provenance = (
        _wt_provenance(config, request)
        if "all-strains-dedup" in request["outputs"]
        else None
    )
    seen: set[str] = set()
    for alias in request["outputs"]:
        category = matrix_root / CATEGORY_FOLDERS[alias]
        for source in rendered[alias]:
            state = _state_from_name(source, request["selection"]["states"])
            canonical = _canonical_name(alias, source, state, export_date, provenance)
            if alias == "per-experiment":
                canonical = re.sub(r"_MATRIX(?=\.png$)", "_Matrix", canonical, flags=re.IGNORECASE)
            filename = f"{run_id}_{canonical}"
            if alias == "label-individual":
                metadata = label_meta.get(source.name.casefold())
                if metadata is None:
                    raise SystemExit(
                        f"Could not map labelled crop to exact selected metadata: {source.name}"
                    )
                experiment, strain = metadata
                destinations = [
                    category
                    / _safe_component(experiment, label="Experiment folder")
                    / _safe_component(strain, label="Strain folder")
                    / filename
                ]
            else:
                destinations = [
                    category / filename,
                    matrix_root / ALL_EXPORTS_FOLDER / filename,
                ]
            for destination in destinations:
                key = str(destination.resolve()).casefold()
                if key in seen:
                    raise SystemExit(f"Unified export destination collision: {destination}")
                seen.add(key)
                plan.append((source, destination))
    existing = [target for _source, target in plan if target.exists()]
    if existing:
        raise SystemExit(
            "Unified export would overwrite existing files:\n"
            + "\n".join(str(path) for path in existing)
        )
    return plan


def _commit_plan(plan: list[tuple[Path, Path]]) -> list[Path]:
    pending: list[tuple[Path, Path]] = []
    created: list[Path] = []
    try:
        for source, target in plan:
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_name(f".{target.name}.{os.getpid()}.pending")
            shutil.copy2(source, temp)
            pending.append((temp, target))
        for temp, target in pending:
            os.replace(temp, target)
            created.append(target)
        return created
    except BaseException:
        for temp, _target in pending:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass
        for target in created:
            try:
                target.unlink()
            except FileNotFoundError:
                pass
        raise


def _write_records(
    matrix_root: Path,
    run_id: str,
    request: dict,
    published: list[Path],
    used: int,
) -> tuple[Path, Path]:
    log_folder = matrix_root / "Processing Logs"
    recipe_folder = matrix_root / "_workflow" / "output-recipes"
    log_folder.mkdir(parents=True, exist_ok=True)
    recipe_folder.mkdir(parents=True, exist_ok=True)
    log = log_folder / "Unified Matrix Exports.log"
    recipe = recipe_folder / f"{run_id}_unified.json"
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    divider = f"==== Unified Matrix Export: {run_id} " + "=" * 32
    lines = [
        divider,
        f"Completed: {timestamp}",
        "Outputs: " + ", ".join(OUTPUT_TYPES[item] for item in request["outputs"]),
        f"Selected crops used: {used}",
        f"Published files: {len(published)}",
        *(f"  - {path}" for path in published),
        "",
    ]
    with log.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    payload = {
        "schema": 1,
        "run_id": run_id,
        "completed_at": timestamp,
        "request": request,
        "used_crops": used,
        "published_paths": [str(path) for path in published],
    }
    recipe.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return log, recipe


def run_job(request: dict, no_open_output: bool = False) -> dict:
    request = normalize_request(request)
    config = pillow_adapter.load_config()
    pillow_adapter.validate_csvs(config)
    matrix_root = pillow_adapter.ensure_matrix_output_root(config)
    _validate_preferred(config, request)
    custom.APP_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="unified-matrix-", dir=custom.APP_DIR) as temp:
        temp_root = Path(temp)
        filtered = custom.filter_project_csvs(config, request["selection"], temp_root / "csv")
        selected = pillow_adapter.validate_unique_crop_matches(
            Path(config["crop_output"]),
            filtered["grid_csv"],
            filtered["images_csv"],
            states=request["selection"]["states"],
        )
        if not selected:
            raise SystemExit("No current crops match the selected matrix request.")
        validate_selected_freshness(config, filtered, selected)
        staged_root = temp_root / "crops"
        staged = pillow_adapter.stage_selected_crops(selected, staged_root)
        pillow_adapter.normalize_crop_orientation(
            staged_root,
            config["crop_width"],
            config["crop_height"],
            paths=staged,
            strict=True,
        )
        rendered = {
            alias: _run_renderer(
                alias,
                request,
                config,
                filtered,
                staged_root,
                temp_root / "rendered",
                staged,
            )
            for alias in request["outputs"]
        }

        with _export_lock(matrix_root):
            run_id = f"Run{_next_run_number(matrix_root):03d}"
            plan = _publish_plan(
                matrix_root, run_id, rendered, request, filtered, config
            )
            published = _commit_plan(plan)
            try:
                log, recipe = _write_records(
                    matrix_root, run_id, request, published, len(staged)
                )
            except BaseException:
                for path in published:
                    try:
                        path.unlink()
                    except FileNotFoundError:
                        pass
                raise

    custom.save_last_selection(request["selection"])
    pillow_adapter.record_output(matrix_root)
    if not no_open_output:
        pillow_adapter.open_output(matrix_root)
    return {
        "run_id": run_id,
        "published_paths": published,
        "log": log,
        "recipe": recipe,
    }


__all__ = [
    "OUTPUT_TYPES",
    "normalize_request",
    "run_job",
    "control_groups_for_selection",
    "preset_names",
    "save_preset",
    "load_preset",
    "delete_preset",
]
