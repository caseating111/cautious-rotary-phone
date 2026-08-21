# Alpha pre-release

This branch is the first packaged alpha snapshot of the image-processing workflow. It is intentionally separate from `main` and from ongoing `workflow-dev` development.

## What is usable

- Lightweight Tkinter controller and Windows launcher.
- CSV validation, metadata reconciliation, batch preflight and pending-only resume handling.
- Preserved four-point Fiji batch route for immediate continuity on its established 10/12-column layouts.
- New full-column manual first/last-column alignment route with full-grid QC and explicit acceptance.
- Global display-only visibility helper; source pixels remain unchanged.
- AHK v2 dialog/hotkey convenience layer.
- Safe staged Pillow routes for matrices, all-strains outputs, deduplicated all-strains output and labelled individual crops; real crop inputs are not rotated or rewritten.
- Output/path/collision/freshness guards and synthetic end-to-end/contract tests.

## Validation status

GitHub Actions passes the Python glue test suite on Python 3.11 and 3.14 for this alpha snapshot.

The new full-column Fiji interaction still needs one representative real desktop plate validation. Until that is proven, use the preserved four-point route when reliability matters. Manual alignment authority is retained in both routes.

## Known alpha limitations

- Full-column peak/profile behavior has not yet been validated on a representative real plate in the target desktop Fiji installation.
- Optional quantitative Stowers plate measurement remains a proof candidate only and is not exposed as a production controller action.
- Custom Pillow comparison/subset builder, preview-first multi-output rendering, raw-vs-presentation-normalized output, TXT processing logs/JSON output recipes, and GUI-selectable control source are planned after this alpha snapshot.
- V10.2 workbook integration is deliberately deferred for later workflow discussion.

## First use

1. Use `start_controller.cmd` on Windows.
2. Configure Fiji, AutoHotkey v2, source image root, crop output, matrix output, and the three project CSV files.
3. Run CSV validation and Batch preflight before interactive processing.
4. For immediate established behavior, use **Run 4-point fallback**.
5. Treat **Run full-column batch** as alpha/representative-validation functionality until the real-plate check is completed.

No real experimental data is included in the repository.
