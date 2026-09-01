from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from PIL import Image

from tools.applets.annotation import (
    preview_plate_annotation,
    render_plate_annotation,
    write_annotation_result,
)
from tools.applets.culture_crop_export import (
    culture_crop_signature,
    export_culture_crops,
    plan_culture_crop_export,
)
from tools.applets.mixed_tier_matrix import (
    enumerate_crop_candidates,
    plan_mixed_tier_matrix,
    preview_mixed_tier_matrix,
    publish_mixed_tier_matrix,
)
from tools.applets.plate_crop import (
    apply_plate_crop,
    calibrate_crop_size,
    calibrate_exact_crop_size,
    place_plate_crop,
)
from tools.applets.plate_orientation import (
    apply_plate_orientation,
    capture_plate_orientation,
)
from tools.applets.project_setup import prepare_working_copy
from tools.applets.v10_adapter import derive_plate_layout, load_v10
from tools.applets.v10_csv_snapshots import (
    compare_csv_snapshot,
    write_csv_snapshot,
)
from tools.applets.visibility import (
    adjust_plate_visibility,
    apply_visibility_adjustment,
    write_visibility_result,
)
from tools.grid_coordinates import validate_grid_coordinate_asset
from tools.project_lifecycle import (
    apply_layout_migration,
    apply_loose_image_import,
    discover_grid_assets,
    plan_layout_migration,
    plan_loose_image_import,
    rename_project_folder_date,
    subset_project_model,
)
from tools.project_lifecycle import (
    mark_working_complete as mark_working_complete_state,
)
from tools.project_paths import (
    canonical_path,
    locate_state,
    preferred_project_path,
    resolve_recorded_path,
)
from tools.project_state import (
    load_project_state,
    new_project_state,
    record_crop,
    record_crop_calibration,
    record_crop_export,
    record_culture_status,
    record_derivative,
    record_derivative_transition,
    record_grid_asset,
    record_grid_skip,
    record_matrix_export,
    record_orientation,
    record_setup_result,
    save_project_state,
    select_crop_calibration,
    validate_project_state,
)

_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_stem(value: str) -> str:
    cleaned = _INVALID_FILENAME.sub("-", value).strip(" .-") or "image"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return f"{cleaned}-{digest}"


class ProjectWorkflow:
    """Stateful orchestration boundary shared by GUI and scripted applet endpoints."""

    def __init__(self, state: dict[str, Any]) -> None:
        validate_project_state(state)
        self.state = state

    @classmethod
    def create_from_v10(
        cls,
        workbook: str | Path,
        project_root: str | Path,
    ) -> ProjectWorkflow:
        workbook_path = Path(workbook).resolve()
        if not workbook_path.is_file():
            raise FileNotFoundError(f"V10 workbook not found: {workbook_path}")
        destination = Path(project_root).resolve()
        try:
            state_file = locate_state(destination)
        except ValueError as exc:
            if not str(exc).startswith("Project state not found under:"):
                raise
            state_file = None
        if state_file is not None:
            raise FileExistsError(
                f"Project state already exists; open it instead of replacing it: {state_file}"
            )
        model = load_v10(str(workbook_path))
        workflow = cls(
            new_project_state(destination, model, v10_workbook=workbook_path)
        )
        workflow.save()
        return workflow

    @classmethod
    def create_from_model(
        cls,
        project_model: dict[str, Any],
        project_root: str | Path,
        *,
        v10_workbook: str | Path | None = None,
    ) -> ProjectWorkflow:
        destination = Path(project_root).resolve()
        try:
            state_file = locate_state(destination)
        except ValueError as exc:
            if not str(exc).startswith("Project state not found under:"):
                raise
            state_file = None
        if state_file is not None:
            raise FileExistsError(
                f"Project state already exists; open it instead: {state_file}"
            )
        workflow = cls(
            new_project_state(destination, project_model, v10_workbook=v10_workbook)
        )
        workflow.save()
        return workflow

    @classmethod
    def open(cls, project_root_or_state: str | Path) -> ProjectWorkflow:
        return cls(load_project_state(project_root_or_state))

    @property
    def project_root(self) -> Path:
        return Path(self.state["project_root"])

    @property
    def project_model(self) -> dict[str, Any]:
        return self.state["project_model"]

    def save(self) -> Path:
        return save_project_state(self.state)

    def select_crop_calibration(self, calibration_id: str) -> None:
        select_crop_calibration(self.state, calibration_id)
        self.save()

    def image_record(self, image_uid: str) -> dict[str, Any]:
        try:
            return self.state["images"][image_uid]
        except KeyError as exc:
            raise ValueError(f"Unknown Image UID: {image_uid}") from exc

    def record_setup(self, result: dict[str, Any]) -> Path:
        record_setup_result(self.state, result)
        return self.save()

    def preview_setup(
        self,
        *,
        raw_root: str | Path | None = None,
        enable_rename: bool = True,
        filename_date_style: str = "v10",
    ) -> dict[str, Any]:
        return prepare_working_copy(
            self.project_model,
            self.project_root,
            raw_root=raw_root,
            options={
                "preview_only": True,
                "enable_rename": enable_rename,
                "filename_date_style": filename_date_style,
            },
        )

    def apply_setup(
        self,
        *,
        raw_root: str | Path | None = None,
        enable_rename: bool = True,
        filename_date_style: str = "v10",
    ) -> dict[str, Any]:
        result = prepare_working_copy(
            self.project_model,
            self.project_root,
            raw_root=raw_root,
            options={
                "preview_only": False,
                "enable_rename": enable_rename,
                "filename_date_style": filename_date_style,
            },
        )
        record_setup_result(self.state, result)
        try:
            snapshot = write_csv_snapshot(
                self.project_model,
                self.project_root,
                filename_date_style=filename_date_style,
                pinned=str(self.state.get("settings", {}).get("csv_mode", "refreshable")).casefold()
                == "pinned",
            )
        except ValueError as exc:
            snapshot = {"status": "UNAVAILABLE", "error": str(exc)}
        self.state["csv_snapshot"] = snapshot
        result["csv_snapshot"] = copy.deepcopy(snapshot)
        self.save()
        return result

    def refresh_csv_snapshot(
        self,
        *,
        filename_date_style: str = "v10",
        pinned: bool | None = None,
    ) -> dict[str, Any]:
        if pinned is None:
            pinned = str(self.state.get("settings", {}).get("csv_mode", "refreshable")).casefold() == "pinned"
        result = write_csv_snapshot(
            self.project_model,
            self.project_root,
            filename_date_style=filename_date_style,
            pinned=bool(pinned),
        )
        self.state["csv_snapshot"] = copy.deepcopy(result)
        self.save()
        return result

    def compare_csv_snapshot(self, *, filename_date_style: str = "v10") -> dict[str, Any]:
        return compare_csv_snapshot(
            self.project_model,
            self.project_root,
            filename_date_style=filename_date_style,
        )

    def _current_v10_model(self) -> dict[str, Any]:
        workbook = self.state.get("v10_workbook")
        if not workbook:
            raise ValueError("This project has no linked V10 workbook.")
        full = load_v10(str(workbook))
        session_uids = {
            str(item.get("session_uid") or "")
            for item in self.project_model.get("sessions", [])
        }
        if len(session_uids) == 1:
            return subset_project_model(full, next(iter(session_uids)))
        return full

    def compare_current_v10(self, *, filename_date_style: str = "v10") -> dict[str, Any]:
        current_model = self._current_v10_model()
        return compare_csv_snapshot(
            current_model,
            self.project_root,
            filename_date_style=filename_date_style,
        )

    def refresh_from_v10(self, *, filename_date_style: str = "v10") -> dict[str, Any]:
        updated_model = self._current_v10_model()
        old_records = self.state["images"]
        new_records: dict[str, dict[str, Any]] = {}
        for image in updated_model.get("images", []):
            uid = str(image.get("image_uid") or "")
            if uid in old_records:
                record = copy.deepcopy(old_records[uid])
                record["session_uid"] = image.get("session_uid")
                record["layout_id"] = image.get("annotation_set")
            else:
                record = {
                    "image_uid": uid,
                    "session_uid": image.get("session_uid"),
                    "layout_id": image.get("annotation_set"),
                    "raw_path": None,
                    "working_path": None,
                }
            new_records[uid] = record
        retired = {
            uid: copy.deepcopy(record)
            for uid, record in old_records.items()
            if uid not in new_records
        }
        if retired:
            self.state.setdefault("retired_images", {}).update(retired)
        self.state["project_model"] = updated_model
        self.state["images"] = new_records
        result = write_csv_snapshot(
            updated_model,
            self.project_root,
            filename_date_style=filename_date_style,
            pinned=False,
        )
        self.state["csv_snapshot"] = copy.deepcopy(result)
        self.save()
        return result

    def source_for(
        self,
        image_uid: str,
        *,
        include_crop: bool = True,
        source_kind: str = "auto",
    ) -> Path:
        record = self.image_record(image_uid)
        kind = source_kind.strip().casefold()
        if kind not in {"auto", "processed", "cropped", "working", "raw"}:
            raise ValueError(f"Unsupported source kind: {source_kind}")
        candidates: list[str | None] = []
        if kind == "processed":
            visibility = record.get("visibility")
            if isinstance(visibility, dict) and visibility.get("status") == "ACCEPTED":
                candidates.append(visibility.get("output_path"))
            if not candidates:
                raise FileNotFoundError(
                    f"No accepted Processed source is recorded for Image UID {image_uid}."
                )
        if include_crop and kind in {"auto", "cropped"}:
            crop = record.get("crop")
            if isinstance(crop, dict) and crop.get("status") == "ACCEPTED":
                candidates.append(crop.get("output_path"))
            if kind == "cropped" and not candidates:
                raise FileNotFoundError(
                    f"No accepted Cropped source is recorded for Image UID {image_uid}."
                )
        if kind == "auto":
            orientation = record.get("orientation")
            if isinstance(orientation, dict) and orientation.get("status") == "ACCEPTED":
                candidates.append(orientation.get("output_path"))
        if kind in {"auto", "working"}:
            candidates.append(record.get("working_path"))
        if kind in {"auto", "raw"}:
            candidates.append(record.get("raw_path"))
        for value in candidates:
            if not value:
                continue
            path = resolve_recorded_path(value, self.project_root)
            if path.is_file():
                return path
        raise FileNotFoundError(
            f"No existing source derivative is recorded for Image UID {image_uid}."
        )

    def orientation_source_for(self, image_uid: str) -> Path:
        for source_kind in ("working", "raw"):
            try:
                return self.source_for(
                    image_uid, include_crop=False, source_kind=source_kind
                )
            except FileNotFoundError:
                continue
        raise FileNotFoundError(
            f"No pre-orientation source is recorded for Image UID {image_uid}."
        )

    def _derivative_path(
        self,
        image_uid: str,
        stage: str,
        source: Path,
        *,
        preserve_source_format: bool = False,
    ) -> Path:
        suffix = (source.suffix or ".png") if preserve_source_format else ".png"
        key = {"Oriented": "orientation", "Cropped": "cropped", "Visibility": "processed"}.get(stage)
        if key is None:
            raise ValueError(f"Unknown derivative stage: {stage}")
        return preferred_project_path(self.project_root, key) / f"{_safe_stem(image_uid)}{suffix}"

    def preview_loose_import(self) -> dict[str, Any]:
        return plan_loose_image_import(self.project_root)

    def apply_loose_import(self, plan: dict[str, Any]) -> dict[str, Any]:
        result = apply_loose_image_import(plan)
        self.state.setdefault("setup", {})["loose_import"] = copy.deepcopy(result)
        self.save()
        return result

    def mark_working_complete(self) -> dict[str, Any]:
        result = mark_working_complete_state(self.state)
        self.save()
        return result

    def maybe_complete_working(self) -> dict[str, Any] | None:
        if not bool(self.state.get("settings", {}).get("auto_move_working", True)):
            return None
        records = list(self.state.get("images", {}).values())
        if not records or any(
            not isinstance(record.get("crop"), dict)
            or record["crop"].get("status") not in {"ACCEPTED", "SKIPPED"}
            for record in records
        ):
            return None
        try:
            return self.mark_working_complete()
        except FileNotFoundError:
            return None

    def preview_layout_migration(self) -> dict[str, Any]:
        return plan_layout_migration(self.project_root)

    def apply_layout_migration(self, plan: dict[str, Any]) -> dict[str, Any]:
        result = apply_layout_migration(plan, self.state)
        self.save()
        return result

    def rename_project_date(self, style: str = "yyyy.mm.dd") -> Path:
        self.state, new_root = rename_project_folder_date(self.state, style=style)
        self.save()
        return new_root

    def save_project_settings(self, settings: dict[str, Any]) -> Path:
        self.state["settings"] = copy.deepcopy(settings)
        return self.save()

    def auto_attach_grids(self) -> dict[str, Any]:
        matches = discover_grid_assets(self.project_root, self.state["images"])
        attached: dict[str, str] = {}
        ambiguous: dict[str, list[str]] = {}
        missing: list[str] = []
        for uid, paths in matches.items():
            if len(paths) == 1:
                self.attach_grid_asset(uid, paths[0])
                attached[uid] = str(paths[0])
            elif len(paths) > 1:
                ambiguous[uid] = [str(path) for path in paths]
            else:
                missing.append(uid)
        result = {
            "attached": attached,
            "ambiguous": ambiguous,
            "missing": sorted(missing),
        }
        self.state.setdefault("setup", {})["grid_discovery"] = copy.deepcopy(result)
        self.save()
        return result

    def preview_grid_discovery(self) -> dict[str, Any]:
        matches = discover_grid_assets(self.project_root, self.state["images"])
        return {
            "unique": {
                uid: str(paths[0]) for uid, paths in matches.items() if len(paths) == 1
            },
            "ambiguous": {
                uid: [str(path) for path in paths]
                for uid, paths in matches.items()
                if len(paths) > 1
            },
            "missing": sorted(uid for uid, paths in matches.items() if not paths),
        }

    def propose_orientation(
        self,
        image_uid: str,
        line: tuple[float, float, float, float] | None,
        *,
        skip: bool = False,
        coordinate_provenance: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], Any]:
        source = self.orientation_source_for(image_uid)
        with Image.open(source) as image:
            dimensions = image.size
        result = capture_plate_orientation(
            line,
            {"width": dimensions[0], "height": dimensions[1], "image_uid": image_uid},
            {
                "image_uid": image_uid,
                "skip": skip,
                "source_path": str(source),
                "coordinate_provenance": coordinate_provenance,
            },
        )
        preview = apply_plate_orientation(source, result)
        return result, preview

    def accept_orientation(
        self,
        image_uid: str,
        proposed: dict[str, Any],
    ) -> tuple[dict[str, Any], Path]:
        if proposed.get("status") not in {"PROPOSED", "SKIPPED"}:
            raise ValueError(
                "Orientation acceptance requires a proposed or skipped result."
            )
        if proposed.get("image_uid") not in {None, image_uid}:
            raise ValueError("Orientation proposal belongs to a different Image UID.")
        source = self.orientation_source_for(image_uid)
        proposed_source = proposed.get("source_path")
        if proposed_source:
            previewed_source = resolve_recorded_path(
                proposed_source, self.project_root
            )
            if not previewed_source.is_file():
                raise FileNotFoundError(
                    f"Orientation source not found: {previewed_source}"
                )
            if previewed_source != source:
                raise ValueError(
                    "Orientation source changed after preview; preview again."
                )
        accepted = copy.deepcopy(proposed)
        if accepted["status"] == "PROPOSED":
            accepted["status"] = "ACCEPTED"
            accepted["confidence"] = 1.0
            accepted["needs_manual_review"] = False
        output = self._derivative_path(
            image_uid,
            "Oriented",
            source,
            preserve_source_format=accepted["status"] == "SKIPPED",
        )
        accepted["image_uid"] = image_uid
        accepted["source_path"] = str(source.resolve())
        accepted["output_path"] = str(output.resolve())
        diagnostics = accepted.setdefault("diagnostics", {})
        diagnostics["source_sha256"] = _hash_file(source)
        apply_plate_orientation(source, accepted, output)
        record_orientation(self.state, image_uid, accepted)
        self.save()
        return accepted, output

    def accept_crop_calibration(
        self,
        left: tuple[float, float],
        right: tuple[float, float],
        top: tuple[float, float],
        bottom: tuple[float, float],
        *,
        increment: int = 50,
        calibration_id: str = "plate-default",
        rounding_enabled: bool = True,
        rounding_direction: str = "down",
        margin_value: float = 0.0,
        margin_unit: str = "pixels",
        source_dimensions: tuple[int, int] | None = None,
        rounding_tolerance_pixels: float = 0.0,
        coordinate_provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        calibration = calibrate_crop_size(
            left,
            right,
            top,
            bottom,
            increment,
            calibration_id,
            accepted=True,
            rounding_enabled=rounding_enabled,
            rounding_direction=rounding_direction,
            margin_value=margin_value,
            margin_unit=margin_unit,
            source_dimensions=source_dimensions,
            rounding_tolerance_pixels=rounding_tolerance_pixels,
            coordinate_provenance=coordinate_provenance,
        )
        record_crop_calibration(self.state, calibration)
        self.save()
        return calibration

    def accept_exact_crop_calibration(
        self,
        side_pixels: int,
        *,
        calibration_id: str = "plate-exact",
        source_dimensions: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        calibration = calibrate_exact_crop_size(
            side_pixels,
            calibration_id=calibration_id,
            source_dimensions=source_dimensions,
        )
        record_crop_calibration(self.state, calibration)
        self.save()
        return calibration

    def propose_crop(
        self,
        image_uid: str,
        calibration_id: str,
        left_anchor: tuple[float, float],
        top_anchor: tuple[float, float],
        *,
        skip: bool = False,
        coordinate_provenance: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], Any]:
        try:
            calibration = self.state["crop_calibrations"][calibration_id]
        except KeyError as exc:
            raise ValueError(f"Unknown crop calibration: {calibration_id}") from exc
        source = self.source_for(image_uid, include_crop=False)
        with Image.open(source) as image:
            dimensions = image.size
        result = place_plate_crop(
            calibration,
            left_anchor,
            top_anchor,
            {"width": dimensions[0], "height": dimensions[1], "image_uid": image_uid},
            options={
                "image_uid": image_uid,
                "skip": skip,
                "source_path": str(source),
                "coordinate_provenance": coordinate_provenance,
            },
        )
        result["source_path"] = str(source)
        preview = apply_plate_crop(source, result)
        return result, preview

    def accept_crop(
        self,
        image_uid: str,
        proposed: dict[str, Any],
    ) -> tuple[dict[str, Any], Path]:
        if proposed.get("status") not in {"PROPOSED", "SKIPPED"}:
            raise ValueError("Crop acceptance requires a proposed or skipped result.")
        if proposed.get("image_uid") != image_uid:
            raise ValueError("Crop proposal belongs to a different Image UID.")
        source = Path(
            proposed.get("source_path")
            or self.source_for(image_uid, include_crop=False)
        )
        if not source.is_file():
            raise FileNotFoundError(f"Crop source not found: {source}")
        accepted = copy.deepcopy(proposed)
        if accepted["status"] == "PROPOSED":
            accepted["status"] = "ACCEPTED"
        output = self._derivative_path(
            image_uid,
            "Cropped",
            source,
            preserve_source_format=accepted["status"] == "SKIPPED",
        )
        accepted["source_path"] = str(source.resolve())
        accepted["source_sha256"] = _hash_file(source)
        accepted["output_path"] = str(output.resolve())
        apply_plate_crop(source, accepted, output)
        record_crop(self.state, image_uid, accepted)
        self.save()
        self.maybe_complete_working()
        return accepted, output

    def skip_crop(self, image_uid: str) -> dict[str, Any]:
        source = self.source_for(image_uid, include_crop=False)
        with Image.open(source) as image:
            dimensions = list(image.size)
        result = {
            "contract_version": 1,
            "asset_type": "CropResult",
            "status": "SKIPPED",
            "image_uid": image_uid,
            "calibration_id": "none",
            "crop_box": None,
            "source_dimensions": dimensions,
            "output_dimensions": dimensions,
            "transform": None,
            "source_path": str(source),
            "output_path": None,
        }
        record_crop(self.state, image_uid, result)
        self.save()
        self.maybe_complete_working()
        return result

    def attach_grid_asset(
        self, image_uid: str, asset_path: str | Path
    ) -> dict[str, Any]:
        path = Path(asset_path).resolve()
        try:
            asset = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Grid asset not found: {path}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not read grid asset {path}: {exc}") from exc
        validate_grid_coordinate_asset(asset)
        if asset.get("image_uid") not in {None, "", image_uid}:
            raise ValueError("Grid asset belongs to a different Image UID.")
        destination_root = canonical_path(self.project_root, "grid_coordinates")
        asset_name = _safe_stem(str(asset.get("asset_id") or "grid"))
        destination = destination_root / (
            f"{_safe_stem(image_uid)}__{asset_name}.grid.json"
        )
        if not path.is_relative_to(destination_root.resolve()):
            destination_root.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                if _hash_file(destination) != _hash_file(path):
                    raise FileExistsError(
                        f"Canonical grid asset already exists with different content: {destination}"
                    )
            else:
                shutil.copy2(path, destination)
            path = destination.resolve()
        record_grid_asset(self.state, image_uid, asset, path)
        self.save()
        return asset

    def skip_grid(self, image_uid: str) -> dict[str, Any]:
        record_grid_skip(self.state, image_uid)
        self.save()
        return self.image_record(image_uid)["grid"]

    def grid_asset(self, image_uid: str) -> dict[str, Any]:
        record = self.image_record(image_uid).get("grid")
        if not isinstance(record, dict) or record.get("status") != "ACCEPTED":
            raise ValueError(
                f"Image UID {image_uid} has no current accepted grid asset."
            )
        path = resolve_recorded_path(record["path"], self.project_root)
        asset = json.loads(path.read_text(encoding="utf-8"))
        validate_grid_coordinate_asset(asset)
        if asset.get("asset_id") != record.get("asset_id"):
            raise ValueError("Grid asset identity no longer matches project state.")
        return asset

    def _assert_grid_matches_source(
        self, image_uid: str, asset: dict[str, Any], source: Path
    ) -> None:
        with Image.open(source) as image:
            dimensions = image.size
        space = asset["coordinate_space"]
        if (space["image_width"], space["image_height"]) != dimensions:
            raise ValueError(
                "Accepted grid coordinates do not match the selected source derivative dimensions."
            )
        if asset.get("image_uid") not in {None, "", image_uid}:
            raise ValueError("Grid asset belongs to a different Image UID.")

    def propose_visibility(
        self,
        image_uid: str,
        preset: str | dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], Any]:
        source = self.source_for(image_uid)
        asset = self.grid_asset(image_uid)
        self._assert_grid_matches_source(image_uid, asset, source)
        result = adjust_plate_visibility(
            str(source),
            asset,
            preset,
            {
                "image_uid": image_uid,
                "status": "PROPOSED",
                "source_image_ref": str(source),
            },
        )
        return result, apply_visibility_adjustment(str(source), result)

    def accept_visibility(
        self,
        image_uid: str,
        proposed: dict[str, Any],
    ) -> tuple[dict[str, Any], Path, Path]:
        if proposed.get("status") != "PROPOSED":
            raise ValueError("Visibility acceptance requires a proposed result.")
        if proposed.get("image_uid") != image_uid:
            raise ValueError("Visibility proposal belongs to a different Image UID.")
        asset = self.grid_asset(image_uid)
        if proposed.get("grid_asset_id") != asset.get("asset_id"):
            raise ValueError(
                "Visibility proposal uses a different or stale grid asset."
            )
        source = Path(proposed["source_image_ref"]).resolve()
        if not source.is_file():
            raise FileNotFoundError(f"Visibility source not found: {source}")
        self._assert_grid_matches_source(image_uid, asset, source)
        accepted = copy.deepcopy(proposed)
        accepted["status"] = "ACCEPTED"
        accepted["needs_manual_review"] = False
        output = self._derivative_path(image_uid, "Visibility", source)
        accepted["output_path"] = str(output.resolve())
        accepted["source_sha256"] = _hash_file(source)
        apply_visibility_adjustment(str(source), accepted, str(output))
        sidecar = output.with_suffix(output.suffix + ".visibility.json")
        write_visibility_result(accepted, str(sidecar))
        record_derivative(self.state, image_uid, "visibility", accepted)
        self.image_record(image_uid).pop("visibility_review", None)
        self.save()
        return accepted, output, sidecar

    def flag_visibility_review(
        self,
        image_uid: str,
        proposed: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        if proposed.get("status") != "PROPOSED":
            raise ValueError("Manual review requires a proposed visibility result.")
        if proposed.get("image_uid") != image_uid:
            raise ValueError("Visibility proposal belongs to a different Image UID.")
        review = copy.deepcopy(proposed)
        review["status"] = "MANUAL_REVIEW"
        review["needs_manual_review"] = True
        review["manual_review_reason"] = (
            reason.strip() or "User requested manual review."
        )
        review.pop("output_path", None)
        record_derivative_transition(self.state, image_uid, "visibility", review)
        self.image_record(image_uid)["visibility_review"] = copy.deepcopy(review)
        self.save()
        return review

    def skip_derivative(self, image_uid: str, kind: str) -> dict[str, Any]:
        if kind not in {"visibility", "annotation"}:
            raise ValueError("Only visibility or annotation may be skipped here.")
        result = {
            "status": "SKIPPED",
            "image_uid": image_uid,
            "reason": "User skipped this optional derivative.",
        }
        record_derivative_transition(self.state, image_uid, kind, result)
        record = self.image_record(image_uid)
        if kind == "visibility":
            record.pop("visibility_review", None)
        self.save()
        return result

    def _model_image(self, image_uid: str) -> dict[str, Any]:
        for image in self.project_model.get("images", []):
            if image.get("image_uid") == image_uid:
                return image
        raise ValueError(f"Unknown Image UID: {image_uid}")

    def _plate_layout(self, image_uid: str) -> dict[str, Any]:
        try:
            return derive_plate_layout(self.project_model, image_uid)
        except (KeyError, ValueError) as exc:
            raise ValueError(
                f"Image UID {image_uid} has no usable embedded PlateLayout."
            ) from exc

    def _culture_crop_source(
        self, image_uid: str, tier: str, source_kind: str | None = None
    ) -> tuple[Path, dict[str, Any]]:
        asset = self.grid_asset(image_uid)
        selected = (source_kind or ("processed" if tier == "Processed" else "auto")).casefold()
        if selected in {"working", "cropped", "raw", "auto"}:
            if tier != "Unprocessed":
                raise ValueError("Working/Cropped/Raw sources publish under Unprocessed.")
            source = (
                self.source_for(image_uid)
                if selected == "auto"
                else self.source_for(image_uid, source_kind=selected)
            )
        elif selected == "processed":
            if tier != "Processed":
                raise ValueError("Processed sources publish under Processed.")
            visibility = self.image_record(image_uid).get("visibility")
            if (
                not isinstance(visibility, dict)
                or visibility.get("status") != "ACCEPTED"
            ):
                raise ValueError(
                    "Processed culture crops require an accepted visibility result."
                )
            if visibility.get("grid_asset_id") != asset.get("asset_id"):
                raise ValueError(
                    "Accepted visibility output uses stale or different grid coordinates."
                )
            source = Path(visibility.get("output_path", ""))
            if not source.is_absolute():
                source = self.project_root / source
            source = source.resolve()
            if not source.is_file():
                raise FileNotFoundError(
                    f"Processed visibility output not found: {source}"
                )
        else:
            raise ValueError("source_kind must be Working, Cropped, Processed, Raw, or Auto.")
        self._assert_grid_matches_source(image_uid, asset, source)
        return source, asset

    def _culture_crop_root(self, image_uid: str, tier: str) -> Path:
        if tier not in {"Unprocessed", "Processed"}:
            raise ValueError("tier must be Unprocessed or Processed.")
        image = self._model_image(image_uid)
        session_uid = str(image.get("session_uid") or "")
        session = next(
            (
                value
                for value in self.project_model.get("sessions", [])
                if str(value.get("session_uid") or "") == session_uid
            ),
            {},
        )
        context = (
            image.get("exp"),
            image.get("set"),
            image.get("condition"),
            session.get("date"),
        )
        root = preferred_project_path(
            self.project_root,
            "crops_processed" if tier == "Processed" else "crops_unprocessed",
        )
        for value in context:
            root /= _safe_stem(str(value or "Unknown"))
        return root / _safe_stem(image_uid)

    def preview_culture_crop_export(
        self,
        image_uid: str,
        *,
        tier: str = "Unprocessed",
        states: tuple[str, ...] = ("Top", "Low"),
        columns: tuple[int, ...] | None = None,
        crop_width: int = 130,
        crop_height: int = 546,
        source_kind: str | None = None,
    ) -> dict[str, Any]:
        source, asset = self._culture_crop_source(image_uid, tier, source_kind)
        image = self._model_image(image_uid)
        metadata = {
            "exp": image.get("exp"),
            "set": image.get("set"),
            "type": image.get("condition"),
            "image_uid": image_uid,
        }
        plan = plan_culture_crop_export(
            source,
            asset,
            self._plate_layout(image_uid),
            metadata,
            self._culture_crop_root(image_uid, tier),
            tier=tier,
            states=states,
            columns=columns,
            crop_width=crop_width,
            crop_height=crop_height,
        )
        plan["source_kind"] = (source_kind or ("processed" if tier == "Processed" else "auto")).casefold()
        return plan

    def accept_culture_crop_export(
        self, image_uid: str, plan: dict[str, Any]
    ) -> dict[str, Any]:
        if plan.get("status") not in {"PROPOSED", "UNCHANGED_CURRENT"}:
            raise ValueError("Culture crop acceptance requires a current preview plan.")
        if plan.get("image_uid") != image_uid:
            raise ValueError("Culture crop plan belongs to a different Image UID.")
        tier = str(plan.get("tier") or "")
        source, asset = self._culture_crop_source(image_uid, tier, plan.get("source_kind"))
        if plan.get("grid_asset_id") != asset.get("asset_id"):
            raise ValueError(
                "Culture crop plan uses stale or different grid coordinates."
            )
        if Path(plan["source_path"]).resolve() != source.resolve():
            raise ValueError(
                "Culture crop source changed after preview; preview again."
            )
        expected_root = self._culture_crop_root(image_uid, tier).resolve()
        planned_output = Path(plan["output_directory"]).resolve()
        if not planned_output.is_relative_to(expected_root):
            raise ValueError(
                "Culture crop plan output is outside this image's project folder."
            )
        result = export_culture_crops(plan)
        record_crop_export(self.state, image_uid, result["tier"], result)
        signature = culture_crop_signature(
            tier=result["tier"],
            source_kind=str(plan.get("source_kind") or "auto"),
            states=plan["states"],
            columns=plan.get("columns"),
            crop_width=plan["crop_width"],
            crop_height=plan["crop_height"],
        )
        record_culture_status(self.state, image_uid, "ACCEPTED", signature)
        self.save()
        return result

    def skip_culture_crop_export(
        self, image_uid: str, signature: dict[str, Any]
    ) -> dict[str, Any]:
        record_culture_status(self.state, image_uid, "SKIPPED", signature)
        self.save()
        return copy.deepcopy(self.state["images"][image_uid]["culture"])

    def mixed_tier_crop_candidates(self) -> dict[str, dict[str, Any]]:
        return enumerate_crop_candidates(self.state)

    def propose_mixed_tier_matrix(
        self,
        selections: list[dict[str, str]],
        *,
        rows: list[str],
        columns: list[str],
        tile_size: tuple[int, int] | None = None,
        padding: int = 10,
    ) -> tuple[dict[str, Any], Any]:
        plan = plan_mixed_tier_matrix(
            self.state,
            selections,
            rows=rows,
            columns=columns,
            output_root=preferred_project_path(self.project_root, "matrices") / "Mixed Tier",
            tile_size=tile_size,
            padding=padding,
        )
        preview = preview_mixed_tier_matrix(plan)
        return plan, preview["preview_image"]

    def accept_mixed_tier_matrix(self, plan: dict[str, Any]) -> dict[str, Any]:
        expected_root = (preferred_project_path(self.project_root, "matrices") / "Mixed Tier").resolve()
        if Path(plan.get("output_root", "")).resolve() != expected_root:
            raise ValueError("Mixed-tier matrix plan output is outside this project.")
        current = enumerate_crop_candidates(self.state)
        if any(
            item.get("candidate_id") not in current for item in plan.get("items", [])
        ):
            raise ValueError(
                "A selected crop is no longer current; preview the matrix again."
            )
        result = publish_mixed_tier_matrix(plan)
        record_matrix_export(self.state, result)
        self.save()
        return result

    def default_annotation_request(self, image_uid: str) -> dict[str, Any]:
        image = self._model_image(image_uid)
        session_uid = str(image.get("session_uid") or "")
        session = next(
            (
                value
                for value in self.project_model.get("sessions", [])
                if str(value.get("session_uid") or "") == session_uid
            ),
            {},
        )
        labels = {
            "date": session.get("date"),
            "plate": str(image.get("image_number") or image_uid),
            "condition": image.get("condition"),
            "session": session_uid or None,
        }
        return {
            "contract_version": 1,
            "image_uid": image_uid,
            "layout_id": str(self.image_record(image_uid).get("layout_id") or ""),
            "labels": {
                key: value for key, value in labels.items() if value not in {None, ""}
            },
        }

    def propose_annotation(
        self,
        image_uid: str,
        request: dict[str, Any] | None = None,
        preset: dict[str, Any] | None = None,
        source_kind: str = "automatic",
    ) -> tuple[dict[str, Any], Any]:
        record = self.image_record(image_uid)
        selected = source_kind.strip().casefold()
        if selected == "automatic":
            visibility = record.get("visibility")
            if isinstance(visibility, dict) and visibility.get("status") == "ACCEPTED":
                source = resolve_recorded_path(visibility["output_path"], self.project_root)
            else:
                source = self.source_for(image_uid)
        elif selected in {"processed", "cropped", "working", "raw"}:
            source = self.source_for(image_uid, source_kind=selected)
        else:
            raise ValueError("Annotation source must be Automatic, Processed, Cropped, Working, or Raw.")
        if not source.is_file():
            raise FileNotFoundError(f"Annotation source not found: {source}")
        asset = self.grid_asset(image_uid)
        self._assert_grid_matches_source(image_uid, asset, source)
        layout = self._plate_layout(image_uid)
        annotation_request = copy.deepcopy(
            request or self.default_annotation_request(image_uid)
        )
        annotation_request["image_uid"] = image_uid
        result = preview_plate_annotation(
            str(source), layout, asset, annotation_request, preset
        )
        result["annotation_request"] = annotation_request
        result["preset"] = copy.deepcopy(preset)
        result["source_kind"] = selected
        return result, result["preview_image"]

    def accept_annotation(
        self,
        image_uid: str,
        proposed: dict[str, Any],
    ) -> tuple[dict[str, Any], Path, Path]:
        if proposed.get("status") != "PROPOSED":
            raise ValueError("Annotation acceptance requires a proposed result.")
        if proposed.get("image_uid") != image_uid:
            raise ValueError("Annotation proposal belongs to a different Image UID.")
        asset = self.grid_asset(image_uid)
        if proposed.get("grid_asset_id") != asset.get("asset_id"):
            raise ValueError(
                "Annotation proposal uses a different or stale grid asset."
            )
        source = Path(proposed["source_image_ref"]).resolve()
        if not source.is_file():
            raise FileNotFoundError(f"Annotation source not found: {source}")
        self._assert_grid_matches_source(image_uid, asset, source)
        output = preferred_project_path(self.project_root, "annotated") / f"{_safe_stem(image_uid)}.png"
        accepted = render_plate_annotation(
            str(source),
            self._plate_layout(image_uid),
            asset,
            proposed["annotation_request"],
            proposed.get("preset"),
            str(output),
        )
        accepted.pop("preview_image", None)
        accepted["annotation_request"] = copy.deepcopy(proposed["annotation_request"])
        accepted["preset"] = copy.deepcopy(proposed.get("preset"))
        accepted["source_sha256"] = _hash_file(source)
        sidecar = output.with_suffix(".annotation.json")
        write_annotation_result(accepted, str(sidecar))
        record_derivative(self.state, image_uid, "annotation", accepted)
        self.save()
        return accepted, output, sidecar
