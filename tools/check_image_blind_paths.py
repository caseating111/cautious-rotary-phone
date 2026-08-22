from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".webp",
    ".nd2", ".czi", ".lif", ".ims",
}


def is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def git_paths(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit((result.stderr or result.stdout).strip() or "git command failed")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def image_like(path_text: str) -> bool:
    lower = path_text.casefold()
    if lower.endswith(".ome.tif") or lower.endswith(".ome.tiff"):
        return True
    return Path(lower).suffix in IMAGE_SUFFIXES


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify image-blind local-test path/Git boundaries without opening image contents."
    )
    parser.add_argument("config", type=Path, help="Local config.json used for the desktop test")
    parser.add_argument(
        "--private-temp-root",
        type=Path,
        default=Path(r"C:\LocalWorkflowData\PrivateTemp"),
        help="External private TEMP/TMP/java.io.tmpdir root",
    )
    args = parser.parse_args()

    if not args.config.is_file():
        raise SystemExit(f"Config not found: {args.config}")
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read config JSON: {exc}") from exc

    errors: list[str] = []
    for key in ("image_root", "crop_output", "matrix_output"):
        raw = str(config.get(key, "")).strip()
        if not raw:
            errors.append(f"missing config path: {key}")
            continue
        path = Path(raw)
        if is_inside(path, REPO_ROOT):
            errors.append(f"{key} must be outside the Git worktree: {path}")

    if is_inside(args.private_temp_root, REPO_ROOT):
        errors.append(f"private temp root must be outside the Git worktree: {args.private_temp_root}")

    tracked_images = [path for path in git_paths("ls-files") if image_like(path)]
    if tracked_images:
        errors.append("tracked image-format files are forbidden: " + ", ".join(tracked_images))

    staged_images = [
        path for path in git_paths("diff", "--cached", "--name-only", "--diff-filter=ACMR") if image_like(path)
    ]
    if staged_images:
        errors.append("staged image-format files are forbidden: " + ", ".join(staged_images))

    if errors:
        print("IMAGE-BLIND PRIVACY CHECK: FAIL")
        for error in errors:
            print(f"- {error}")
        return 2

    print("IMAGE-BLIND PRIVACY CHECK: PASS")
    print(f"repo={REPO_ROOT}")
    print(f"private_temp_root={args.private_temp_root.resolve()}")
    print("No image contents were opened by this check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
