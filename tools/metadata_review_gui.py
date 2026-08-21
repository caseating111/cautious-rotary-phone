from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path.home() / ".cautious-rotary-phone"
CONFIG = APP_DIR / "config.json"
REVIEW = APP_DIR / "images_reconciliation.csv"
CANDIDATE = APP_DIR / "images_candidate.csv"


def configured_images_csv(config_path: Path = CONFIG) -> Path:
    if not config_path.is_file():
        raise ValueError(f"Config not found: {config_path}")
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read config: {exc}") from exc
    raw = str(data.get("images_csv", "")).strip()
    if not raw:
        raise ValueError("Configured images_csv path is missing.")
    return Path(raw)


def unique_backup_path(destination: Path) -> Path:
    base = destination.with_name(destination.name + ".before-reconciliation.bak")
    if not base.exists():
        return base
    index = 1
    while True:
        candidate = destination.with_name(destination.name + f".before-reconciliation.{index}.bak")
        if not candidate.exists():
            return candidate
        index += 1


def adopt_candidate(candidate: Path, destination: Path) -> Path | None:
    if not candidate.is_file():
        raise ValueError(f"Validated candidate not found: {candidate}")
    if candidate.resolve() == destination.resolve():
        raise ValueError("Candidate and configured images.csv resolve to the same file; no adoption is needed.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    if destination.is_file():
        backup = unique_backup_path(destination)
        shutil.copy2(destination, backup)

    staged_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=destination.name + ".candidate-",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as handle:
            staged_path = Path(handle.name)
        shutil.copy2(candidate, staged_path)
        os.replace(staged_path, destination)
        staged_path = None
    finally:
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)

    return backup


class MetadataReview(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Image metadata review")
        self.resizable(False, False)
        self.status = tk.StringVar(value="Reconcile scans source folders without changing images.csv.")
        pad = {"padx": 8, "pady": 5}

        ttk.Button(self, text="Reconcile / refresh review CSV", command=self.reconcile).grid(
            row=0, column=0, columnspan=2, sticky="ew", **pad
        )
        ttk.Button(self, text="Open review CSV", command=lambda: self.open_path(REVIEW)).grid(
            row=1, column=0, sticky="ew", **pad
        )
        ttk.Button(self, text="Finalize validated candidate", command=self.finalize).grid(
            row=1, column=1, sticky="ew", **pad
        )
        ttk.Button(self, text="Open candidate CSV", command=lambda: self.open_path(CANDIDATE)).grid(
            row=2, column=0, sticky="ew", **pad
        )
        ttk.Button(self, text="Validate + use candidate as images.csv", command=self.finalize_and_adopt).grid(
            row=2, column=1, sticky="ew", **pad
        )
        ttk.Button(self, text="Open config folder", command=lambda: self.open_path(APP_DIR)).grid(
            row=3, column=0, columnspan=2, sticky="ew", **pad
        )
        ttk.Label(self, textvariable=self.status, wraplength=520).grid(
            row=4, column=0, columnspan=2, sticky="w", **pad
        )

    def run_helper(self, script_name: str) -> subprocess.CompletedProcess[str]:
        script = REPO_ROOT / "tools" / script_name
        return subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            check=False,
        )

    def reconcile(self) -> None:
        result = self.run_helper("reconcile_images_csv.py")
        output = (result.stdout + result.stderr).strip() or "No reconciliation output."
        self.status.set(output)
        if REVIEW.is_file():
            self.open_path(REVIEW)
        if result.returncode not in (0, 1):
            messagebox.showerror("Metadata reconciliation", output)

    def finalize(self) -> None:
        result = self.run_helper("finalize_images_reconciliation.py")
        output = (result.stdout + result.stderr).strip() or "No finalization output."
        self.status.set(output)
        if result.returncode == 0:
            messagebox.showinfo("Metadata candidate", output)
            self.open_path(CANDIDATE)
        else:
            messagebox.showerror("Metadata candidate", output)

    def finalize_and_adopt(self) -> None:
        result = self.run_helper("finalize_images_reconciliation.py")
        output = (result.stdout + result.stderr).strip() or "No finalization output."
        if result.returncode != 0:
            self.status.set(output)
            messagebox.showerror("Metadata candidate", output)
            return

        try:
            destination = configured_images_csv()
        except ValueError as exc:
            self.status.set(str(exc))
            messagebox.showerror("Use metadata candidate", str(exc))
            return

        confirmed = messagebox.askyesno(
            "Use validated metadata candidate",
            "The reconciliation has just been rebuilt and validated.\n\n"
            f"Replace the configured images.csv with this candidate?\n\n{destination}\n\n"
            "If the current file exists, an adjacent backup will be created first.",
        )
        if not confirmed:
            self.status.set("Validated candidate kept; authoritative images.csv unchanged.")
            return

        try:
            backup = adopt_candidate(CANDIDATE, destination)
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))
            messagebox.showerror("Use metadata candidate", str(exc))
            return

        detail = f"Updated authoritative images.csv: {destination}"
        if backup is not None:
            detail += f"\nBackup: {backup}"
        self.status.set(detail)
        messagebox.showinfo("Metadata updated", detail)

    def open_path(self, path: Path) -> None:
        if not path.exists():
            messagebox.showerror("Open", f"Not found:\n{path}")
            return
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except (AttributeError, OSError) as exc:
            messagebox.showerror("Open", str(exc))


if __name__ == "__main__":
    MetadataReview().mainloop()
