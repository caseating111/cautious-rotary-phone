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

IMAGE_ROOT = Path(r"path here")

GRID_CSV = Path(r"path here")
IMAGES_CSV = Path(r"path here")
CONDITION_ORDER_CSV = Path(r"path here")

MATRIX_ROOT = Path(r"path here")
# ALL strains, including duplicate WTs
MATRIX_OUTPUT = make_unique_folder(
    MATRIX_ROOT,
    "ALL STRAINS"
)
IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".tif", ".tiff"
}

# Your crops should already be rotated from the previous script.
# Leave False unless this is a completely fresh unrotated copy.
ROTATE_IMAGES_90_CCW = False

ROTATION_MARKER = IMAGE_ROOT / ".rotated_90ccw.done"
 

# ------------------------------------------------------------
# MATRIX LAYOUT
# ------------------------------------------------------------

OUTER_MARGIN = 30

H_GAP = 16
V_GAP = 14

ROW_LABEL_WIDTH = 220
COLUMN_HEADER_HEIGHT = 70

# ------------------------------------------------------------
# FONTS
# ------------------------------------------------------------

HEADER_FONT_PATH = r"C:\Windows\Fonts\arialbd.ttf"
HEADER_FONT_SIZE = 28

ROW_FONT_PATH = r"C:\Windows\Fonts\arialbd.ttf"
ROW_FONT_SIZE = 24

BACKGROUND = "white"
TEXT_COLOUR = "black"
# Highlight WT strain labels
HIGHLIGHT_WT_LABELS = False
WT_TEXT_COLOUR = "red"

# Missing cell:
# "blank" = white space
# "label" = write MISSING
MISSING_CELL_MODE = "blank"

DRAW_CELL_BORDER = False
CELL_BORDER_WIDTH = 1

STATES_TO_BUILD = ["Top", "Low"]


# ============================================================
# FONT HELPERS
# ============================================================

def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        print(f"WARNING: could not load font: {path}")
        return ImageFont.load_default()


HEADER_FONT = load_font(
    HEADER_FONT_PATH,
    HEADER_FONT_SIZE
)

ROW_FONT = load_font(
    ROW_FONT_PATH,
    ROW_FONT_SIZE
)


def text_size(draw, text, font):
    box = draw.textbbox(
        (0, 0),
        text,
        font=font
    )

    return (
        box[2] - box[0],
        box[3] - box[1]
    )


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
# OPTIONAL ROTATION
# ============================================================

def rotate_everything():

    if not ROTATE_IMAGES_90_CCW:
        return

    if ROTATION_MARKER.exists():
        print(
            "Rotation marker found — "
            "skipping rotation."
        )
        return

    files = [
        p
        for p in IMAGE_ROOT.rglob("*")
        if (
            p.is_file()
            and p.suffix.lower()
            in IMAGE_EXTENSIONS
        )
    ]

    print(
        f"Rotating {len(files)} images "
        "90° CCW..."
    )

    for i, path in enumerate(files, 1):

        try:
            with Image.open(path) as im:

                rotated = im.transpose(
                    Image.Transpose.ROTATE_90
                )

                if (
                    path.suffix.lower()
                    in {".jpg", ".jpeg"}
                ):
                    if rotated.mode not in (
                        "RGB",
                        "L"
                    ):
                        rotated = rotated.convert(
                            "RGB"
                        )

                    rotated.save(
                        path,
                        quality=95
                    )

                else:
                    rotated.save(path)

            print(
                f"[{i}/{len(files)}] "
                f"{path.name}"
            )

        except Exception as e:
            print(
                f"FAILED TO ROTATE: {path}"
            )
            print(e)

    ROTATION_MARKER.write_text(
        "Images recursively rotated "
        "90 degrees counter-clockwise.\n",
        encoding="utf-8"
    )


# ============================================================
# READ GRID
#
# The important difference:
# EVERY row from every experiment/set is combined.
#
# We preserve exp/set/column internally so we can find
# the corresponding crop later.
# ============================================================

def read_all_strains():

    strain_rows = []

    with GRID_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            exp = row["Experiment"].strip()
            set_name = row["Set"].strip()

            column = int(
                row["Column"].strip()
            )

            strain = row["Strain"].strip()

            strain_rows.append({
                "experiment": exp,
                "set": set_name,
                "column": column,
                "strain": strain
            })

    # --------------------------------------------------------
    # Preserve a sensible overall order:
    #
    # experiment
    # set
    # plate column
    #
    # If you later want a completely custom strain order,
    # we can add a strain_order.csv.
    # --------------------------------------------------------

    strain_rows.sort(
        key=lambda x: (
            x["experiment"],
            x["set"],
            x["column"]
        )
    )

    # Warn about duplicate strain names
    seen = {}

    for row in strain_rows:

        strain = row["strain"]

        seen.setdefault(
            strain,
            []
        )

        seen[strain].append(
            (
                row["experiment"],
                row["set"],
                row["column"]
            )
        )

    for strain, locations in seen.items():

        if len(locations) > 1:

            print(
                "\nWARNING: duplicate strain name:"
            )
            print(
                f"  {strain}"
            )

            for location in locations:
                print(
                    "   ",
                    location
                )

    return strain_rows


# ============================================================
# GLOBAL CONDITION ORDER
#
# Type,Order
# ============================================================

def read_condition_order():

    conditions = []

    with CONDITION_ORDER_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            type_name = (
                row["Type"].strip()
            )

            order = int(
                row["Order"].strip()
            )

            conditions.append(
                (
                    order,
                    type_name
                )
            )

    conditions.sort(
        key=lambda x: x[0]
    )

    return [
        condition
        for _, condition in conditions
    ]


# ============================================================
# FIND ALL CROPS
# ============================================================

def get_all_crop_files():

    return [
        p
        for p in IMAGE_ROOT.rglob("*")
        if (
            p.is_file()
            and p.suffix.lower()
            in IMAGE_EXTENSIONS
        )
    ]


# ============================================================
# FIND ONE CELL
#
# We still use exp/set internally to avoid ambiguity.
#
# Example:
# E2_A_SALT_01_Low_
# ============================================================

def find_crop(
    all_files,
    row,
    condition,
    state
):

    prefix = (
        f"{row['experiment']}_"
        f"{row['set']}_"
        f"{condition}_"
        f"{row['column']:02d}_"
        f"{state}_"
    ).lower()

    matches = [
        p
        for p in all_files
        if p.stem.lower().startswith(
            prefix
        )
    ]

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:

        print(
            "\nWARNING: multiple matches:"
        )
        print(prefix)

        for m in matches:
            print("   ", m)

        print("Using first match.")

        return matches[0]

    return None


# ============================================================
# BUILD ALL-STRAINS MATRIX
# ============================================================

def build_matrix(
    state,
    rows,
    conditions,
    all_files
):

    # --------------------------------------------------------
    # Find one real image to establish cell dimensions.
    # --------------------------------------------------------

    example = None

    for row in rows:

        for condition in conditions:

            example = find_crop(
                all_files,
                row,
                condition,
                state
            )

            if example:
                break

        if example:
            break

    if example is None:

        print(
            f"No {state} crops found; "
            "skipping."
        )

        return

    with Image.open(example) as im:
        cell_w, cell_h = im.size

    n_rows = len(rows)
    n_cols = len(conditions)

    width = (
        OUTER_MARGIN
        + ROW_LABEL_WIDTH
        + n_cols * cell_w
        + max(
            0,
            n_cols - 1
        ) * H_GAP
        + OUTER_MARGIN
    )

    height = (
        OUTER_MARGIN
        + COLUMN_HEADER_HEIGHT
        + n_rows * cell_h
        + max(
            0,
            n_rows - 1
        ) * V_GAP
        + OUTER_MARGIN
    )

    canvas = Image.new(
        "RGB",
        (width, height),
        BACKGROUND
    )

    draw = ImageDraw.Draw(canvas)


    # ========================================================
    # CONDITION HEADERS
    # ========================================================

    for c, condition in enumerate(
        conditions
    ):

        x = (
            OUTER_MARGIN
            + ROW_LABEL_WIDTH
            + c * (
                cell_w + H_GAP
            )
        )

        draw_centered(
            draw,
            condition,
            x,
            OUTER_MARGIN,
            cell_w,
            COLUMN_HEADER_HEIGHT,
            HEADER_FONT
        )


    # ========================================================
    # ALL STRAIN ROWS
    # ========================================================

    missing_count = 0

    for r, row in enumerate(rows):

        y = (
            OUTER_MARGIN
            + COLUMN_HEADER_HEIGHT
            + r * (
                cell_h + V_GAP
            )
        )

        # -----------------------------------------------
        # Strain label
        # -----------------------------------------------

# WT labels can optionally be highlighted
        label_colour = TEXT_COLOUR

        if HIGHLIGHT_WT_LABELS and is_wt_strain(row["strain"]):
            label_colour = WT_TEXT_COLOUR


        draw_centered(
            draw,
            row["strain"],
            OUTER_MARGIN,
            y,
            ROW_LABEL_WIDTH - 10,
            cell_h,
            ROW_FONT,
            colour=label_colour
        )


        # -----------------------------------------------
        # Condition cells
        # -----------------------------------------------

        for c, condition in enumerate(
            conditions
        ):

            x = (
                OUTER_MARGIN
                + ROW_LABEL_WIDTH
                + c * (
                    cell_w + H_GAP
                )
            )

            crop = find_crop(
                all_files,
                row,
                condition,
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

                if (
                    MISSING_CELL_MODE
                    == "label"
                ):

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

            px = (
                x
                + (
                    cell_w
                    - cell.width
                ) // 2
            )

            py = (
                y
                + (
                    cell_h
                    - cell.height
                ) // 2
            )

            canvas.paste(
                cell,
                (px, py)
            )


    # ========================================================
    # SAVE
    # ========================================================

    MATRIX_OUTPUT.mkdir(
        parents=True,
        exist_ok=True
    )

    out_path = (
        MATRIX_OUTPUT
        / f"ALL_{state}_MATRIX.png"
    )

    canvas.save(out_path)

    print(
        f"\nCREATED:\n{out_path}"
    )

    if missing_count:

        print(
            "Missing cells left blank: "
            f"{missing_count}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    MATRIX_OUTPUT.mkdir(
        parents=True,
        exist_ok=True
    )

    rotate_everything()

    rows = read_all_strains()

    conditions = (
        read_condition_order()
    )

    all_files = (
        get_all_crop_files()
    )

    print(
        f"\nFound {len(all_files)} "
        "crop images."
    )

    print(
        f"Found {len(rows)} "
        "strain rows."
    )

    print("\nConditions:")

    for i, condition in enumerate(
        conditions,
        1
    ):
        print(
            f"  {i}. {condition}"
        )

    for state in STATES_TO_BUILD:

        print(
            "\n================================"
        )

        print(
            f"Building ALL {state} matrix"
        )

        print(
            "================================"
        )

        build_matrix(
            state,
            rows,
            conditions,
            all_files
        )

    print("\nDONE")
    print(
        f"Output folder:\n"
        f"{MATRIX_OUTPUT}"
    )


if __name__ == "__main__":
    main()