# V10 project lifecycle

This is the operating protocol for the numbered, resume-aware V10 path. The older basic CSV controller remains supported and intentionally simpler.

## Prepare one experiment

1. Put loose originals directly in a dated experiment folder, for example `14.08.26 EXP2`. Do not rename `image1.jpg`, `image2.jpg`, and so on.
2. Open **V10 project applets** and choose **Prepare one folder**. Select the current V10 workbook and the experiment folder.
3. Review the one setup summary (default on). Blockers such as collisions always stop; missing expected images are listed but do not block other images.
4. Apply. Originals move unchanged to `1. a. Raw`; copies go to `1. b. Working`. Working filenames use V10 by default or the saved `yyyy.mm.dd` option. The human name map and CSV snapshots go under `z. Metadata`.
5. Continue with orientation, whole-plate crop, grid, visibility, annotation, individual cultures, and matrices. Each accepted stage writes to its own numbered folder and never overwrites Working.

## Prepare a parent folder

Choose **Prepare parent** and select the folder containing dated experiment subfolders. The program matches each folder to V10 `Date*`, narrows with Exp/session and original filenames, and asks for sessionUID only if still ambiguous. It shows one combined confirmation before creating new state or moving images. Every experiment keeps its own independent numbered project tree.

## Resume or update

- Choose **Open project** for any partially processed project. Canonical and legacy Raw/Working/Cropped/Crops/Metadata/State/GridCoordinates names are recognized.
- Choose **Upgrade old folders** only when ready; the preview refuses conflicting merges.
- Use **Mark Working complete** after cropping in this program or elsewhere. It moves/renames Working to `2. Cropped/1. b. Working`. The saved automatic option does this after every project crop is accepted or skipped.
- **Keep current** pins the active CSV snapshot. **Compare** checks it against the linked V10 workbook. **Refresh V10** deliberately imports the current workbook and creates a new immutable snapshot.
- The project may be renamed in Explorer or with **Rename project-folder date now**. On next open, in-project state paths rebase to the new root; external workbook paths remain external.

## Source choices

- Annotation **Automatic** uses Processed, then Cropped, then Working. The explicit radios force one stage and fail clearly if it is unavailable.
- Individual culture export explicitly chooses Working, Cropped, or Processed. Output tier remains independently Unprocessed or Processed.
- Grid search checks `z. Metadata/State/GridCoordinates` plus older project grid locations. One valid Image UID match attaches automatically; multiple matches are reported for manual selection.

The saved setup choices—review, filename-date style, optional folder-date rename, automatic Working completion, and CSV mode—load in later sessions and are also stored in the project.
