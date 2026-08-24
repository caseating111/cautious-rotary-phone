from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from PIL import Image

from tools.applets.annotation import (
    preview_plate_annotation,
    render_plate_annotation,
    write_annotation_result,
)
from tools.applets.culture_crop_export import (
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
    place_plate_crop,
)
from tools.applets.plate_orientation import (
    apply_plate_orientation,
    capture_plate_orientation,
)
from tools.applets.project_setup import prepare_working_copy
from tools.applets.v10_adapter import load_v10
from tools.applets.visibility import (
    adjust_plate_visibility,
    apply_visibility_adjustment,
    write_visibility_result,
)
from tools.grid_coordinates import validate_grid_coordinate_asset
from tools.project_state import (
    load_project_state,
    new_project_state,
    record_crop,
    record_crop_calibration,
    record_crop_export,
    record_derivative,
    record_grid_asset,
    record_matrix_export,
    record_orientation,
    record_setup_result,
    save_project_state,
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
        state_file = destination / "State" / "workflow_project.json"
        if state_file.exists():
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
    ) -> dict[str, Any]:
        return prepare_working_copy(
            self.project_model,
            self.project_root,
            raw_root=raw_root,
            options={"preview_only": True, "enable_rename": enable_rename},
        )

    def apply_setup(
        self,
        *,
        raw_root: str | Path | None = None,
        enable_rename: bool = True,
    ) -> dict[str, Any]:
        result = prepare_working_copy(
            self.project_model,
            self.project_root,
            raw_root=raw_root,
            options={"preview_only": False, "enable_rename": enable_rename},
        )
        record_setup_result(self.state, result)
        self.save()
        return result

    def source_for(self, image_uid: str, *, include_crop: bool = True) -> Path:
        record = self.image_record(image_uid)
        candidates: list[str | None] = []
        if include_crop:
            crop = record.get("crop")
            if isinstance(crop, dict) and crop.get("status") == "ACCEPTED":
                candidates.append(crop.get("output_path"))
        orientation = record.get("orientation")
        if isinstance(orientation, dict) and orientation.get("status") == "ACCEPTED":
            candidates.append(orientation.get("output_path"))
        candidates.extend((record.get("working_path"), record.get("raw_path")))
        for value in candidates:
            if not value:
                continue
            path = Path(value)
            if not path.is_absolute():
                path = self.project_root / path
            path = path.resolve()
            if path.is_file():
                return path
        raise FileNotFoundError(
            f"No existing source derivative is recorded for Image UID {image_uid}."
        )

    def _derivative_path(self, image_uid: str, stage: str, source: Path) -> Path:
        suffix = source.suffix if source.suffix else ".png"
        return (
            self.project_root / "Processed" / stage / f"{_safe_stem(image_uid)}{suffix}"
        )

    def propose_orientation(
        self,
        image_uid: str,
        line: tuple[float, float, float, float] | None,
        *,
        skip: bool = False,
    ) -> tuple[dict[str, Any], Any]:
        source = self.source_for(image_uid, include_crop=False)
        with Image.open(source) as image:
            dimensions = image.size
        result = capture_plate_orientation(
            line,
            {"width": dimensions[0], "height": dimensions[1], "image_uid": image_uid},
            {
                "image_uid": image_uid,
                "skip": skip,
                "source_path": str(source),
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
        source = Path(
            proposed.get("source_path")
            or self.source_for(image_uid, include_crop=False)
        )
        if not source.is_file():
            raise FileNotFoundError(f"Orientation source not found: {source}")
        accepted = copy.deepcopy(proposed)
        if accepted["status"] == "PROPOSED":
            accepted["status"] = "ACCEPTED"
            accepted["confidence"] = 1.0
            accepted["needs_manual_review"] = False
        output = self._derivative_path(image_uid, "Oriented", source)
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
    ) -> dict[str, Any]:
        calibration = calibrate_crop_size(
            left,
            right,
            top,
            bottom,
            increment,
            calibration_id,
            accepted=True,
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
            options={"image_uid": image_uid, "skip": skip, "source_path": str(source)},
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
        output = self._derivative_path(image_uid, "Cropped", source)
        accepted["source_path"] = str(source.resolve())
        accepted["source_sha256"] = _hash_file(source)
        accepted["output_path"] = str(output.resolve())
        apply_plate_crop(source, accepted, output)
        record_crop(self.state, image_uid, accepted)
        self.save()
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
        record_grid_asset(self.state, image_uid, asset, path)
        self.save()
        return asset

    def grid_asset(self, image_uid: str) -> dict[str, Any]:
        record = self.image_record(image_uid).get("grid")
        if not isinstance(record, dict) or record.get("status") != "ACCEPTED":
            raise ValueError(
                f"Image UID {image_uid} has no current accepted grid asset."
            )
        path = Path(record["path"])
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
        self.image_record(image_uid)["visibility_review"] = review
        self.save()
        return review

    def _model_image(self, image_uid: str) -> dict[str, Any]:
        for image in self.project_model.get("images", []):
            if image.get("image_uid") == image_uid:
                return image
        raise ValueError(f"Unknown Image UID: {image_uid}")

    def _plate_layout(self, image_uid: str) -> dict[str, Any]:
        record = self.image_record(image_uid)
        layout_id = record.get("layout_id")
        try:
            return self.project_model["layouts"][layout_id]
        except KeyError as exc:
            raise ValueError(
                f"Image UID {image_uid} has no usable embedded PlateLayout."
            ) from exc

    def _culture_crop_source(
        self, image_uid: str, tier: str
    ) -> tuple[Path, dict[str, Any]]:
        asset = self.grid_asset(image_uid)
        if tier == "Unprocessed":
            source = self.source_for(image_uid)
        elif tier == "Processed":
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
            raise ValueError("tier must be Unprocessed or Processed.")
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
        root = self.project_root / "Crops" / tier
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
    ) -> dict[str, Any]:
        source, asset = self._culture_crop_source(image_uid, tier)
        image = self._model_image(image_uid)
        metadata = {
            "exp": image.get("exp"),
            "set": image.get("set"),
            "type": image.get("condition"),
            "image_uid": image_uid,
        }
        return plan_culture_crop_export(
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

    def accept_culture_crop_export(
        self, image_uid: str, plan: dict[str, Any]
    ) -> dict[str, Any]:
        if plan.get("status") not in {"PROPOSED", "UNCHANGED_CURRENT"}:
            raise ValueError("Culture crop acceptance requires a current preview plan.")
        if plan.get("image_uid") != image_uid:
            raise ValueError("Culture crop plan belongs to a different Image UID.")
        tier = str(plan.get("tier") or "")
        source, asset = self._culture_crop_source(image_uid, tier)
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
        self.save()
        return result

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
            output_root=self.project_root / "Matrices" / "Mixed Tier",
            tile_size=tile_size,
            padding=padding,
        )
        preview = preview_mixed_tier_matrix(plan)
        return plan, preview["preview_image"]

    def accept_mixed_tier_matrix(self, plan: dict[str, Any]) -> dict[str, Any]:
        expected_root = (self.project_root / "Matrices" / "Mixed Tier").resolve()
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
    ) -> tuple[dict[str, Any], Any]:
        record = self.image_record(image_uid)
        visibility = record.get("visibility")
        if isinstance(visibility, dict) and visibility.get("status") == "ACCEPTED":
            source = Path(visibility["output_path"]).resolve()
        else:
            source = self.source_for(image_uid)
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
        output = self.project_root / "Annotated" / f"{_safe_stem(image_uid)}.png"
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
