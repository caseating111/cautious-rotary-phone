from pathlib import Path
import csv
import re
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# UNIQUE OUTPUT FOLDER
# ============================================================

def make_unique_folder(parent, base_name):
    parent.mkdir(parents=True, exist_ok=True)

    candidate = parent / base_name

    if not candidate.exists():
        candidate.mkdir()
        return candidate

    i = 1

    while True:
        candidate = parent / f"{base_name}_{i}"

        if not candidate.exists():
            candidate.mkdir()
            return candidate

        i += 1


# ============================================================
# SETTINGS — EDIT THESE
# ============================================================


IMAGE_ROOT = Path(r"path here")

GRID_CSV = Path(r"path here")
IMAGES_CSV = Path(r"path here")
CONDITION_ORDER_CSV = Path(r"path here")

MATRIX_ROOT = Path(r"path here")
MATRIX_OUTPUT = make_unique_folder(
    MATRIX_ROOT,
    "Labelled Individual Images"
)


IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff"
}

# Shared adapter compatibility setting. This script never rotates internally;
# the wrapper supplies already-normalized disposable staged inputs.
ROTATE_IMAGES_90_CCW = False


# ------------------------------------------------------------
# LABEL APPEARANCE
# ------------------------------------------------------------
ROW_LABEL_WIDTH = 220

FONT_PATH = r"C:\Windows\Fonts\arialbd.ttf"
FONT_SIZE = 24

TEXT_COLOUR = "black"
BACKGROUND_COLOUR = "white"

# Recommended:
# adds a separate white label area instead of covering colonies.
LABEL_POSITION = "top"

# Padding around label
LABEL_PADDING = 8


# ============================================================
# FONT
# ============================================================

try:
    FONT = ImageFont.truetype(
        FONT_PATH,
        FONT_SIZE
    )
except Exception:
    print(
        "WARNING: Arial Bold not found. "
        "Using Pillow default font."
    )
    FONT = ImageFont.load_default()


# ============================================================
# READ grid.csv
# ============================================================

def read_grid():
    mapping = {}

    with GRID_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            exp = row["Experiment"].strip()
            set_name = row["Set"].strip()
            column = int(row["Column"].strip())
            strain = row["Strain"].strip()
            mapping[(exp, set_name, column)] = strain

    return mapping


# ============================================================
# SAFE NAMES
# ============================================================

def safe_folder_name(name):
    name = name.strip()

    replacements = {
        "/": "-",
        "\\": "-",
        ":": "-",
        "*": "-",
        "?": "",
        '"': "",
        "<": "(",
        ">": ")",
        "|": "-",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    return name


# ============================================================
# AUTHORITATIVE EXACT FILENAME -> STRAIN MAP
#
# Normal controller/staged use should not reparse metadata from generated
# filenames. Build the current exporter filenames from grid.csv + images.csv
# instead. This also supports Experiment/Set/Type values containing underscores.
# ============================================================

def read_exact_filename_labels(grid):
    labels = {}

    with IMAGES_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        reader = csv.DictReader(f)

        for image_row in reader:
            exp = image_row["Experiment"].strip()
            set_name = image_row["Set"].strip()
            type_name = image_row["Type"].strip()

            for (grid_exp, grid_set, column), strain in grid.items():
                if grid_exp != exp or grid_set != set_name:
                    continue

                safe_strain = safe_folder_name(strain)
                for state in ("Top", "Low"):
                    filename = (
                        f"{exp}_{set_name}_{type_name}_"
                        f"{column:02d}_{state}_{safe_strain}.png"
                    )
                    labels[filename.lower()] = strain

    return labels


# ============================================================
# LEGACY FILENAME PARSER FALLBACK
#
# Retained only for direct/manual use with old inputs that are not represented
# by the current exact metadata map. Normal staged controller inputs use the
# authoritative exact map above.
# ============================================================

def parse_crop_filename(path):
    stem = path.stem
    first_parts = stem.split("_", 2)

    if len(first_parts) < 3:
        return None

    exp = first_parts[0]
    set_name = first_parts[1]

    match = re.search(
        r"_(\d+)_"
        r"(?:Top|Low)_",
        stem,
        flags=re.IGNORECASE
    )

    if not match:
        return None

    column = int(match.group(1))
    return exp, set_name, column


# ============================================================
# DRAW LABEL
# ============================================================

def add_strain_label(image, strain):
    image = image.convert("RGB")
    w, h = image.size

    # Separate white band avoids drawing over colony pixels.
    canvas = Image.new(
        "RGB",
        (w + ROW_LABEL_WIDTH, h),
        BACKGROUND_COLOUR
    )
    canvas.paste(image, (ROW_LABEL_WIDTH, 0))

    draw = ImageDraw.Draw(canvas)
    box = draw.textbbox((0, 0), strain, font=FONT)
    text_w = box[2] - box[0]
    text_h = box[3] - box[1]

    x = (ROW_LABEL_WIDTH - text_w) / 2
    y = (h - text_h) / 2

    draw.text(
        (x, y),
        strain,
        fill=TEXT_COLOUR,
        font=FONT
    )

    return canvas


# ============================================================
# SAVE IMAGE
# ============================================================

def save_image(image, output_path):
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    suffix = output_path.suffix.lower()

    if suffix in {".jpg", ".jpeg"}:
        image.save(output_path, quality=95)
    else:
        image.save(output_path)


# ============================================================
# MAIN
# ============================================================

def main():
    grid = read_grid()
    exact_labels = read_exact_filename_labels(grid)

    files = [
        p
        for p in IMAGE_ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]

    labelled = 0
    skipped = 0

    print(f"Found {len(files)} images.")

    for i, path in enumerate(files, 1):
        strain = exact_labels.get(path.name.lower())

        if strain is None:
            parsed = parse_crop_filename(path)
            if parsed is None:
                print(
                    "SKIPPED — filename not recognised and not in current metadata map: "
                    f"{path.name}"
                )
                skipped += 1
                continue

            exp, set_name, column = parsed
            strain = grid.get((exp, set_name, column))

            if strain is None:
                print(
                    "SKIPPED — no grid.csv mapping for legacy-parsed crop "
                    f"{(exp, set_name, column)}: {path.name}"
                )
                skipped += 1
                continue

        strain_folder = safe_folder_name(strain)
        output_path = MATRIX_OUTPUT / strain_folder / path.name

        try:
            with Image.open(path) as im:
                labelled_image = add_strain_label(im, strain)
                save_image(labelled_image, output_path)

            labelled += 1
            print(f"[{i}/{len(files)}] {strain}: {path.name}")

        except Exception as e:
            print(f"FAILED: {path}")
            print(e)
            skipped += 1

    print("\nDONE")
    print(f"Labelled: {labelled}")
    print(f"Skipped: {skipped}")
    print("\nOutput folder:\n" f"{MATRIX_OUTPUT}")


if __name__ == "__main__":
    main()
