from pathlib import Path
import csv

IMAGE_ROOT = Path(r"path here")
IMAGES_CSV = Path(r"path here")

# Read CSV properly, including commas inside quoted filenames
mapping = {}

with IMAGES_CSV.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        filename = row["Filename"].strip()

        mapping[filename] = (
            row["Experiment"].strip(),
            row["Set"].strip(),
            row["Type"].strip(),
        )

files = sorted(
    p for p in IMAGE_ROOT.rglob("*")
    if p.is_file()
    and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
)

print("\n=== E2 / B IMAGE MAPPING ===\n")

for p in files:
    if p.name not in mapping:
        continue

    exp, set_name, type_name = mapping[p.name]

    if exp == "E2" and set_name == "B":
        print(f"FILE: {p.name}")
        print(f"TYPE: {type_name}")
        print(f"PATH: {p.parent}")
        print()