from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_register_only_is_explicit_non_persisted_controller_option() -> None:
    text = (ROOT / "tools/workflow_controller_extended.py").read_text(encoding="utf-8")
    assert "self.register_only = tk.BooleanVar(value=False)" in text
    assert 'text="Register grid only (no crops)"' in text
    assert (
        "self.register_only"
        not in text[text.index("def save(") : text.index("def refresh_subfolders")]
    )
    assert 'args.append("--register-only")' in text
    assert "grid registration only; crops will not be exported" in text


def test_single_register_only_propagates_and_blocks_rerun_replacement() -> None:
    controller = (ROOT / "tools/workflow_controller_extended.py").read_text(
        encoding="utf-8"
    )
    single = controller[
        controller.index("def run_one_plate_validation") : controller.index(
            "def main()"
        )
    ]
    assert "register_only=register_only" in single
    assert (
        "Register-only mode cannot be combined with rerun or crop replacement."
        in single
    )

    launcher = (ROOT / "tools/run_one_plate_validation.py").read_text(encoding="utf-8")
    assert "register_only: bool = False" in launcher
    assert 'args.append("--register-only")' in launcher
    assert (
        "Register-only mode cannot be combined with rerun or crop replacement."
        in launcher
    )
    assert "register_only=register_only" in launcher
