from __future__ import annotations

import copy
from pathlib import Path

from tools.applets.v10_adapter import load_v10
from tools.applets.v10_csv_snapshots import (
    build_csv_payload,
    compare_csv_snapshot,
    write_csv_snapshot,
)


def model() -> dict:
    return {
        "contract_version": 1,
        "sessions": [{"session_uid": "S1", "exp": "2", "date": "2026-08-14"}],
        "images": [
            {
                "image_uid": "I1",
                "session_uid": "S1",
                "image_number": 1,
                "original": "image1.jpg",
                "working_filename": "14.08.26_SetA.jpg",
                "exp": "2",
                "set": "A",
                "media": "YPDA",
                "condition": "Heat",
                "rep": 1,
                "annotation_set": "L1",
            }
        ],
        "layouts": {
            "L1": {
                "contract_version": 1,
                "layout_id": "L1",
                "grid_rows": 2,
                "grid_cols": 2,
                "vertical_labels": [{"pos": 1, "label": "Top"}, {"pos": 2, "label": "Low"}],
                "strain_bands": [
                    {
                        "order": 1,
                        "profile": "P1",
                        "row_start": 1,
                        "row_end": 2,
                        "local_grid_cols": 2,
                        "row_mapping_provenance": "full_rows",
                        "labels": [{"pos": 1, "label": "WT"}, {"pos": 2, "label": "mut"}],
                    }
                ],
            }
        },
    }


def test_csv_snapshots_create_reuse_pin_and_compare(tmp_path: Path) -> None:
    first = write_csv_snapshot(model(), tmp_path, filename_date_style="yyyy.mm.dd")
    assert first["status"] == "CREATED"
    metadata = tmp_path / "z. Metadata"
    assert "2026.08.14_SetA.jpg" in (metadata / "images.csv").read_text(encoding="utf-8")
    assert "sessionUID*" in (metadata / "v10_master_registry.csv").read_text(
        encoding="utf-8"
    )
    assert "BandOrder" in (metadata / "v10_plate_layout.csv").read_text(
        encoding="utf-8"
    )
    layout_header = (metadata / "v10_plate_layout.csv").read_text(
        encoding="utf-8"
    ).splitlines()[0]
    assert "Set" in layout_header
    assert "Profile" in layout_header
    assert first["legacy_grid_available"] is True
    unchanged = write_csv_snapshot(model(), tmp_path, filename_date_style="yyyy.mm.dd")
    assert unchanged["status"] == "UNCHANGED_CURRENT"
    pinned = write_csv_snapshot(model(), tmp_path, filename_date_style="v10", pinned=True)
    assert pinned["status"] == "PINNED_CURRENT"
    comparison = compare_csv_snapshot(model(), tmp_path, filename_date_style="v10")
    assert comparison["status"] == "CHANGED"


def test_rich_row_bands_export_losslessly_without_unsafe_legacy_grid(
    tmp_path: Path,
) -> None:
    rich = copy.deepcopy(model())
    rich["layouts"]["L1"]["strain_bands"] = [
        {
            "order": 1,
            "profile": "P1",
            "row_start": 1,
            "row_end": 1,
            "local_grid_cols": 2,
            "row_mapping_provenance": "equal_partition",
            "labels": [{"pos": 1, "label": "culture1"}, {"pos": 2, "label": "culture2"}],
        },
        {
            "order": 2,
            "profile": "P2",
            "row_start": 2,
            "row_end": 2,
            "local_grid_cols": 2,
            "row_mapping_provenance": "equal_partition",
            "labels": [{"pos": 1, "label": "strain1"}, {"pos": 2, "label": "strain2"}],
        },
    ]
    result = write_csv_snapshot(rich, tmp_path)
    metadata = tmp_path / "z. Metadata"
    assert result["legacy_grid_available"] is False
    assert not (metadata / "grid.csv").exists()
    layout_text = (metadata / "v10_plate_layout.csv").read_text(encoding="utf-8")
    assert "culture1" in layout_text
    assert "strain1" in layout_text


def test_sanitized_snapshot_keeps_safe_grid_groups_despite_unmapped_set() -> None:
    workbook = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "v10"
        / "v10_sample_synthetic_sanitized.xlsx"
    )
    payload = build_csv_payload(load_v10(str(workbook)))
    assert "grid.csv" in payload
    assert "Strain" in payload["grid.csv"]
    assert ",c," not in payload["grid.csv"].casefold()
    master_header = payload["v10_master_registry.csv"].splitlines()[0]
    assert "Base filename*" in master_header
    assert "Base count*" in master_header
    assert "Set filename*" in master_header
    assert "Set filename count*" in master_header
