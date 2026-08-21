# Deferred legacy output questions

These are non-blocking questions discovered while auditing reused Pillow scripts. They must not stop unrelated workflow work.

## Extra-WT-removed control source

`existing scripts clean/allstrainmatrix extra WT removed.py` has inconsistent legacy intent markers:

- comments say to prefer the `E2/B` WT controls;
- the implemented selection condition actually prefers `E2/A`;
- the output filename is `WT_EXP2A_ALL_<state>.png`, which also points toward `E2/A`.

Do **not** change this biological/output-selection behavior based on comments alone. Keep the current executable behavior until the intended preferred control source is confirmed from real workflow requirements or a stronger authoritative artifact.

## Standard matrix optional WT highlight

`existing scripts clean/make_matrices.py` exposes `HIGHLIGHT_WT_LABELS` / `WT_TEXT_COLOUR` and calculates a `label_colour`, but the strain-label `draw_centered(...)` call does not pass that calculated colour. Therefore the optional highlight setting is inert in that one legacy script.

This does not affect the normal controller workflow because the default is `False` and the controller does not expose that setting. Do not spend a large legacy-file rewrite on it unless WT highlighting becomes a real requested output; if it does, the narrow fix is to pass `colour=label_colour`, matching the all-strains scripts.
