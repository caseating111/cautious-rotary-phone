from pathlib import Path
import csv
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import csv
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
# SETTINGS — EDIT THESE ONLY
# ============================================================

# Input/output paths

IMAGE_ROOT = Path(r"path here")

GRID_CSV = Path(r"path here")
IMAGES_CSV = Path(r"path here")
CONDITION_ORDER_CSV = Path(r"path here")

MATRIX_ROOT = Path(r"path here")
MATRIX_OUTPUT = make_unique_folder(
    MATRIX_ROOT,
    "EXP"
)

# ============================================================
# SETTINGS — EDIT THESE ONLY
# ============================================================
 

# Image extensions to include
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

# Rotation
ROTATE_IMAGES_90_CCW = True

# Prevent accidental double rotation on rerun
ROTATION_MARKER = IMAGE_ROOT / ".rotated_90ccw.done"

# Matrix layout
OUTER_MARGIN = 30
H_GAP = 16
V_GAP = 14

ROW_LABEL_WIDTH = 220
COLUMN_HEADER_HEIGHT = 70

# Fonts
HEADER_FONT_PATH = r"C:\Windows\Fonts\arialbd.ttf"
HEADER_FONT_SIZE = 28

ROW_FONT_PATH = r"C:\Windows\Fonts\arialbd.ttf"
ROW_FONT_SIZE = 24

# Appearance
BACKGROUND = "white"
TEXT_COLOUR = "black"
# Highlight WT strain labels
HIGHLIGHT_WT_LABELS = False
WT_TEXT_COLOUR = "red"

# Missing cells:
# "blank" = leave white
# "label" = write MISSING
MISSING_CELL_MODE = "blank"

# Optional thin border around each image cell
DRAW_CELL_BORDER = False
CELL_BORDER_WIDTH = 1

# Build these matrix states
STATES_TO_BUILD = ["Top", "Low"] 
# ============================================================
# HELPERS
# ============================================================

def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        print(f"Warning: could not load font {path}")
        return ImageFont.load_default()


HEADER_FONT = load_font(HEADER_FONT_PATH, HEADER_FONT_SIZE)
ROW_FONT = load_font(ROW_FONT_PATH, ROW_FONT_SIZE)


def text_size(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]
def draw_centered(draw, text, x, y, w, h, font, colour=None):
    tw, th = text_size(draw, text, font)
    tx = x + (w - tw) / 2
    ty = y + (h - th) / 2

    if colour is None:
        colour = TEXT_COLOUR

    draw.text(
        (tx, ty),
        text,
        fill=colour,
        font=font
    )


def is_wt_strain(name):
    compare = (
        name.strip()
        .upper()
        .replace("-", " ")
    )

    compare = " ".join(compare.split())

    return compare in {"WT X", "WT Y"}

# ============================================================
# ROTATE ALL CROPS RECURSIVELY
# ============================================================

def rotate_everything():

    if not ROTATE_IMAGES_90_CCW:
        print("Rotation disabled.")
        return

    if ROTATION_MARKER.exists():
        print("Rotation marker found — skipping rotation.")
        print(f"Delete this marker if you intentionally want to rotate again:\n{ROTATION_MARKER}")
        return

    files = [
        p for p in IMAGE_ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]

    print(f"Rotating {len(files)} images 90° CCW...")

    for i, path in enumerate(files, 1):
        try:
            with Image.open(path) as im:
                rotated = im.transpose(Image.Transpose.ROTATE_90)

                if path.suffix.lower() in {".jpg", ".jpeg"}:
                    if rotated.mode not in ("RGB", "L"):
                        rotated = rotated.convert("RGB")
                    rotated.save(path, quality=95)
                else:
                    rotated.save(path)

            print(f"[{i}/{len(files)}] {path.name}")

        except Exception as e:
            print(f"FAILED TO ROTATE: {path}")
            print(e)

    ROTATION_MARKER.write_text(
        "Images recursively rotated 90 degrees counter-clockwise.\n",
        encoding="utf-8"
    )

    print("Rotation complete.")


# ============================================================
# READ grid.csv
#
# Experiment,Set,GridCols,Column,Strain
#
# Row order is numeric Column ascending.
# ============================================================

def read_grid():

    groups = {}

    with GRID_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            exp = row["Experiment"].strip()
            set_name = row["Set"].strip()
            column = int(row["Column"].strip())
            strain = row["Strain"].strip()

            key = (exp, set_name)

            groups.setdefault(key, [])
            groups[key].append({
                "column": column,
                "strain": strain
            })

    for key in groups:
        groups[key].sort(key=lambda x: x["column"])

    return groups


# ============================================================
# READ condition_order.csv
#
# Type,Order
#
# Same condition order for every experiment/set.
# ============================================================

def read_condition_order():

    conditions = []

    with CONDITION_ORDER_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            type_name = row["Type"].strip()
            order = int(row["Order"].strip())

            conditions.append((order, type_name))

    conditions.sort(key=lambda x: x[0])

    return [type_name for _, type_name in conditions]


# ============================================================
# FIND ALL CROP FILES
# ============================================================

def get_all_crop_files():

    return [
        p for p in IMAGE_ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]


# ============================================================
# FIND ONE MATRIX CELL
#
# Search prefix example:
# E2_A_SALT_01_Low_
# ============================================================

def find_crop(all_files, exp, set_name, type_name, column, state):

    prefix = (
        f"{exp}_{set_name}_{type_name}_"
        f"{column:02d}_{state}_"
    ).lower()

    matches = [
        p for p in all_files
        if p.stem.lower().startswith(prefix)
    ]

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        print(f"WARNING: multiple matches for {prefix}")
        for m in matches:
            print("   ", m)
        print("Using first match.")
        return matches[0]

    return None


# ============================================================
# BUILD ONE MATRIX
# ============================================================

def build_matrix(exp, set_name, state, rows, conditions, all_files):

    example = None

    for row in rows:
        for condition in conditions:
            example = find_crop(
                all_files,
                exp,
                set_name,
                condition,
                row["column"],
                state
            )
            if example:
                break

        if example:
            break

    if example is None:
        print(f"No {state} crops found for {exp}_{set_name}; skipping matrix.")
        return

    with Image.open(example) as im:
        cell_w, cell_h = im.size

    n_rows = len(rows)
    n_cols = len(conditions)

    matrix_width = (
        OUTER_MARGIN
        + ROW_LABEL_WIDTH
        + n_cols * cell_w
        + max(0, n_cols - 1) * H_GAP
        + OUTER_MARGIN
    )

    matrix_height = (
        OUTER_MARGIN
        + COLUMN_HEADER_HEIGHT
        + n_rows * cell_h
        + max(0, n_rows - 1) * V_GAP
        + OUTER_MARGIN
    )

    canvas = Image.new(
        "RGB",
        (matrix_width, matrix_height),
        BACKGROUND
    )

    draw = ImageDraw.Draw(canvas)

    # --------------------------------------------------------
    # CONDITION HEADERS
    # --------------------------------------------------------

    for c, condition in enumerate(conditions):

        x = (
            OUTER_MARGIN
            + ROW_LABEL_WIDTH
            + c * (cell_w + H_GAP)
        )

        y = OUTER_MARGIN

        draw_centered(
            draw,
            condition,
            x,
            y,
            cell_w,
            COLUMN_HEADER_HEIGHT,
            HEADER_FONT
        )

    # --------------------------------------------------------
    # STRAIN ROWS
    # --------------------------------------------------------

    missing_count = 0

    for r, row in enumerate(rows):

        column = row["column"]
        strain = row["strain"]

        y = (
            OUTER_MARGIN
            + COLUMN_HEADER_HEIGHT
            + r * (cell_h + V_GAP)
        )

        label_colour = TEXT_COLOUR

        if HIGHLIGHT_WT_LABELS and is_wt_strain(row["strain"]):
            label_colour = WT_TEXT_COLOUR

        # Left-side strain label
        draw_centered(
            draw,
            strain,
            OUTER_MARGIN,
            y,
            ROW_LABEL_WIDTH - 10,
            cell_h,
            ROW_FONT
        )

        for c, condition in enumerate(conditions):

            x = (
                OUTER_MARGIN
                + ROW_LABEL_WIDTH
                + c * (cell_w + H_GAP)
            )

            crop = find_crop(
                all_files,
                exp,
                set_name,
                condition,
                column,
                state
            )

            if DRAW_CELL_BORDER:
                draw.rectangle(
                    [
                        x,
                        y,
                        x + cell_w - 1,
                        y + cell_h - 1
                    ],
                    outline=TEXT_COLOUR,
                    width=CELL_BORDER_WIDTH
                )

            if crop is None:
                missing_count += 1

                if MISSING_CELL_MODE == "label":
                    draw_centered(
                        draw,
                        "MISSING",
                        x,
                        y,
                        cell_w,
                        cell_h,
                        ROW_FONT
                    )

                continue

            with Image.open(crop) as im:
                cell = im.convert("RGB")

            # Usually all crops are identical.
            # Centre them if one differs slightly.
            px = x + (cell_w - cell.width) // 2
            py = y + (cell_h - cell.height) // 2

            canvas.paste(cell, (px, py))

    MATRIX_OUTPUT.mkdir(parents=True, exist_ok=True)

    out_path = MATRIX_OUTPUT / f"{exp}_{set_name}_{state}_MATRIX.png"

    canvas.save(out_path)

    print(f"CREATED: {out_path}")

    if missing_count:
        print(f"  Missing cells left blank: {missing_count}")


# ============================================================
# MAIN
# ============================================================

def main():

    MATRIX_OUTPUT.mkdir(parents=True, exist_ok=True)

    rotate_everything()

    grids = read_grid()
    conditions = read_condition_order()
    all_files = get_all_crop_files()

    print(f"\nFound {len(all_files)} crop images.")
    print("Condition order:")
    for i, condition in enumerate(conditions, 1):
        print(f"  {i}. {condition}")

    for (exp, set_name), rows in grids.items():

        print("\n====================================")
        print(f"Building matrices for {exp}_{set_name}")
        print("====================================")

        for state in STATES_TO_BUILD:
            build_matrix(
                exp,
                set_name,
                state,
                rows,
                conditions,
                all_files
            )

    print("\nDONE")
    print(f"Output folder:\n{MATRIX_OUTPUT}")


if __name__ == "__main__":
    main()