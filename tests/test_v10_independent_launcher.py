from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v10_independent_launcher_is_portable_and_fail_closed() -> None:
    text = (ROOT / "start_v10_independent.cmd").read_text(
        encoding="utf-8"
    ).casefold()
    assert 'cd /d "%~dp0"' in text
    assert "workflow-c" in text
    assert "sys.version_info[:2] != (3, 11)" in text
    assert "tools\\v10_independent\\controller.py" in text
    assert "workflow_controller" not in text
    assert "no alternate python was started" in text


def test_v10_independent_controller_repairs_import_root_from_any_cwd() -> None:
    text = (
        ROOT / "tools" / "v10_independent" / "controller.py"
    ).read_text(encoding="utf-8")
    assert "Path(__file__).resolve().parents[2]" in text
    assert "from tools.workflow_applets_gui import WorkflowApp" in text
