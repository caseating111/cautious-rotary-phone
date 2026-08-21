from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path.home() / ".cautious-rotary-phone"
REVIEW = APP_DIR / "images_reconciliation.csv"
CANDIDATE = APP_DIR / "images_candidate.csv"


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
        ttk.Button(self, text="Open config folder", command=lambda: self.open_path(APP_DIR)).grid(
            row=2, column=1, sticky="ew", **pad
        )
        ttk.Label(self, textvariable=self.status, wraplength=520).grid(
            row=3, column=0, columnspan=2, sticky="w", **pad
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
