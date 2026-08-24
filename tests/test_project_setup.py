from __future__ import annotations

from pathlib import Path

import pytest

from tools.applets.project_setup import prepare_working_copy


def _model(*, unsafe_name: str | None = None) -> dict:
    return {
        "contract_version": 1,
        "sessions": [
            {"session_uid": "S1", "exp": "E1"},
            {"session_uid": "S2", "exp": "E1"},
        ],
        "images": [
            {
                "image_uid": "I1",
                "session_uid": "S1",
                "original": "one.dat",
                "working_filename": unsafe_name or "renamed/one.dat",
                "exp": "E1",
                "set": "A",
            },
            {
                "image_uid": "I2",
                "session_uid": "S2",
                "original": "two.dat",
                "working_filename": "two.dat",
                "exp": "E1",
                "set": "A",
            },
        ],
    }


def _sources(root: Path) -> tuple[Path, Path]:
    first = root / "Raw" / "camera" / "2026" / "S1" / "one.dat"
    second = root / "Raw" / "camera" / "2026" / "S2" / "two.dat"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_bytes(b"one-source")
    second.write_bytes(b"two-source")
    return first, second


def test_recursive_preview_apply_idempotence_and_versioned_map(tmp_path: Path) -> None:
    first, second = _sources(tmp_path)
    preview = prepare_working_copy(_model(), tmp_path, options={"preview_only": True})
    assert preview["preview_only"] is True
    assert preview["summary"]["ready_to_copy_count"] == 2
    assert not (tmp_path / "Working").exists()
    assert not (tmp_path / "Metadata").exists()

    applied = prepare_working_copy(_model(), tmp_path)
    assert applied["summary"]["copied_count"] == 2
    assert (
        tmp_path / "Working" / "renamed" / "one.dat"
    ).read_bytes() == first.read_bytes()
    assert (tmp_path / "Working" / "two.dat").read_bytes() == second.read_bytes()
    mapping = tmp_path / "Metadata" / "image_name_conversions.txt"
    text = mapping.read_text(encoding="utf-8")
    assert str(tmp_path) not in text
    assert "Raw/camera/2026/S1/one.dat" in text

    rerun = prepare_working_copy(_model(), tmp_path)
    assert rerun["summary"]["unchanged_current_count"] == 2
    first_history = list((tmp_path / "Metadata" / "History").glob("*.txt"))
    assert len(first_history) == 1
    assert "Status=COPIED_RENAMED" in first_history[0].read_text(encoding="utf-8")

    changed_map = prepare_working_copy(
        _model(), tmp_path, options={"enable_rename": False}
    )
    assert changed_map["summary"]["copied_count"] == 1
    history = list((tmp_path / "Metadata" / "History").glob("*.txt"))
    assert len(history) == 2
    assert any(
        "Working/renamed/one.dat" in item.read_text(encoding="utf-8")
        for item in history
    )


def test_same_size_changed_target_fails_closed(tmp_path: Path) -> None:
    first, _second = _sources(tmp_path)
    prepare_working_copy(_model(), tmp_path)
    target = tmp_path / "Working" / "renamed" / "one.dat"
    target.write_bytes(b"x" * len(first.read_bytes()))
    result = prepare_working_copy(_model(), tmp_path, options={"preview_only": True})
    by_uid = {item["image_uid"]: item for item in result["images"]}
    assert by_uid["I1"]["disposition"] == "TARGET_COLLISION"


@pytest.mark.parametrize(
    "unsafe",
    ["../escape.dat", "C:/escape.dat", "CON.dat", "bad?.dat", "trail. "],
)
def test_unsafe_working_names_are_rejected(tmp_path: Path, unsafe: str) -> None:
    _sources(tmp_path)
    with pytest.raises(ValueError, match="working_filename"):
        prepare_working_copy(
            _model(unsafe_name=unsafe), tmp_path, options={"preview_only": True}
        )


def test_shared_source_without_session_evidence_is_ambiguous(tmp_path: Path) -> None:
    source = tmp_path / "Raw" / "camera" / "same.dat"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"same")
    model = _model()
    for image in model["images"]:
        image["original"] = "same.dat"
        image["working_filename"] = f"{image['image_uid']}.dat"
    result = prepare_working_copy(model, tmp_path, options={"preview_only": True})
    assert {item["disposition"] for item in result["images"]} == {"AMBIGUOUS_SOURCE"}
