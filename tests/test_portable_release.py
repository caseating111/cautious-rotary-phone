from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from tools import build_portable_release as release


def test_release_allowlist_excludes_repository_and_development_material() -> None:
    selected = release.release_sources()
    assert release.REQUIRED_ARCHIVE_FILES <= set(selected)
    for relative in selected:
        release.validate_destination(relative)
        assert not relative.startswith(("docs/", "tests/", "fixtures/", ".git/"))
    assert not release.NON_RUNTIME_TOOL_FILES & set(selected)
    assert not any(
        relative.casefold().endswith((".xlsx", ".pyc")) for relative in selected
    )


def test_release_zip_is_anonymous_complete_and_deterministic(tmp_path: Path) -> None:
    first = release.build_release(tmp_path / "first.zip")
    second = release.build_release(tmp_path / "second.zip")
    assert (
        hashlib.sha256(first.read_bytes()).digest()
        == hashlib.sha256(second.read_bytes()).digest()
    )

    with zipfile.ZipFile(first) as archive:
        names = set(archive.namelist())
        prefix = release.ARCHIVE_ROOT + "/"
        relative = {name.removeprefix(prefix) for name in names}
        assert release.REQUIRED_ARCHIVE_FILES <= relative
        assert f"{prefix}RELEASE-MANIFEST.json" in names
        assert not any(
            "docs/" in name or "tests/" in name or "fixtures/" in name for name in names
        )
        manifest = json.loads(archive.read(f"{prefix}RELEASE-MANIFEST.json"))
        assert manifest["runtime"] == "Windows + Miniforge workflow-c + Python 3.11"
        for name, expected_hash in manifest["files"].items():
            assert (
                hashlib.sha256(archive.read(prefix + name)).hexdigest() == expected_hash
            )
        grid_sample = archive.read(f"{prefix}samples/grid.csv").decode("utf-8")
        assert "Experiment,Set,GridCols,Column,Strain" in grid_sample
        assert "STRAIN1" in grid_sample

        extracted = tmp_path / "extracted"
        archive.extractall(extracted)

    product_root = extracted / release.ARCHIVE_ROOT
    subprocess.run(
        [sys.executable, "-m", "compileall", "-q", str(product_root / "tools")],
        check=True,
    )
    for relative in sorted(release.PORTABLE_PYTHON_ENTRYPOINTS):
        subprocess.run(
            [
                sys.executable,
                "-c",
                "from pathlib import Path; import runpy,sys; "
                "sys.path.insert(0, str(Path(sys.argv[1]).parent)); "
                "runpy.run_path(sys.argv[1], run_name='release_import_probe')",
                str(product_root / relative),
            ],
            cwd=tmp_path,
            check=True,
        )
    subprocess.run(
        [
            sys.executable,
            str(product_root / "tools" / "validate_project_csvs.py"),
            str(product_root / "samples" / "grid.csv"),
            str(product_root / "samples" / "images.csv"),
            str(product_root / "samples" / "condition_order.csv"),
        ],
        check=True,
    )
