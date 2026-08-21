from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

try:
    from tools import run_full_column_batch_from_config as batch
except ModuleNotFoundError:
    import run_full_column_batch_from_config as batch


APP_DIR = batch.APP_DIR
PROOF_IMAGES_CSV = APP_DIR / "one_plate_validation_images.csv"
PROOF_MACRO = APP_DIR / "one_plate_validation.configured.ijm"
_ACTIVE_FIJI_PROCESS: subprocess.Popen | None = None


def read_pending_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise SystemExit(f"Prepared pending-image list not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit(f"Prepared pending-image list has no header: {path}")
        return list(reader.fieldnames), [dict(row) for row in reader]


def choose_pending_row(rows: list[dict[str, str]], filename: str | None = None) -> dict[str, str]:
    if not rows:
        raise SystemExit("No pending images remain for one-plate validation.")
    if filename is None:
        return rows[0]
    wanted = filename.strip()
    matches = [row for row in rows if (row.get("Filename") or "").strip() == wanted]
    if len(matches) != 1:
        available = ", ".join((row.get("Filename") or "").strip() for row in rows[:20])
        raise SystemExit(
            f"Requested validation source {wanted!r} was not found exactly once in the prepared pending list. "
            f"Available pending sources include: {available or 'none'}"
        )
    return matches[0]


def write_one_row_csv(path: Path, fieldnames: list[str], row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in fieldnames})


def patch_prepared_macro(source: str, proof_csv: Path) -> str:
    old = f'imagesFile = "{batch.macro_path(batch.PENDING_IMAGES_CSV)}";'
    new = f'imagesFile = "{batch.macro_path(proof_csv)}";'
    if source.count(old) != 1:
        raise SystemExit(
            "Prepared full-column macro no longer contains exactly one pending-images path; refusing to guess where to patch."
        )
    return source.replace(old, new, 1)


def prepare(filename: str | None = None) -> tuple[Path, dict[str, str]]:
    result = subprocess.run(
        [sys.executable, str(Path(batch.__file__).resolve()), "--prepare-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise SystemExit(output or "Full-column preparation failed before one-plate validation.")

    fieldnames, rows = read_pending_rows(batch.PENDING_IMAGES_CSV)
    selected = choose_pending_row(rows, filename)
    write_one_row_csv(PROOF_IMAGES_CSV, fieldnames, selected)

    if not batch.CONFIGURED_MACRO.is_file():
        raise SystemExit(f"Prepared full-column macro not found: {batch.CONFIGURED_MACRO}")
    proof_text = patch_prepared_macro(batch.CONFIGURED_MACRO.read_text(encoding="utf-8"), PROOF_IMAGES_CSV)
    PROOF_MACRO.write_text(proof_text, encoding="utf-8")
    return PROOF_MACRO, selected


def proof_is_running() -> bool:
    return _ACTIVE_FIJI_PROCESS is not None and _ACTIVE_FIJI_PROCESS.poll() is None


def run(filename: str | None = None) -> dict[str, str]:
    global _ACTIVE_FIJI_PROCESS

    if proof_is_running():
        raise SystemExit(
            "A one-plate Fiji proof launched by this controller is still running. "
            "Finish or close that Fiji instance before launching another proof."
        )

    macro, selected = prepare(filename)
    config = batch.load_config(require_fiji=True, require_fiji_handoff_paths=True)
    fiji = Path(config["fiji_executable"])
    if not fiji.is_file():
        raise SystemExit(f"Fiji executable not found: {fiji}")
    try:
        _ACTIVE_FIJI_PROCESS = subprocess.Popen([str(fiji), "-macro", str(macro)])
    except OSError as exc:
        _ACTIVE_FIJI_PROCESS = None
        raise SystemExit(f"Could not launch Fiji one-plate validation: {exc}") from exc
    return selected


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Launch the prepared full-column route for exactly one pending source image."
    )
    parser.add_argument(
        "--filename",
        help="exact pending source filename to validate; default is the first authoritative pending row",
    )
    args = parser.parse_args()
    selected = run(args.filename)
    print(
        "Launched one-plate validation: "
        f"{selected.get('Filename', '')} | {selected.get('Experiment', '')}/"
        f"{selected.get('Set', '')}/{selected.get('Type', '')}"
    )


if __name__ == "__main__":
    main()
