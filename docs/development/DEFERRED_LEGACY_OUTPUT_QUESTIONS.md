# Deferred legacy output questions

These are non-blocking questions discovered while auditing reused Pillow scripts. They must not stop unrelated workflow work.

## Extra-WT-removed control source

`existing scripts clean/allstrainmatrix extra WT removed.py` has inconsistent legacy intent markers:

- comments say to prefer the `E2/B` WT controls;
- the implemented selection condition actually prefers `E2/A`;
- the output filename is `WT_EXP2A_ALL_<state>.png`, which also points toward `E2/A`.

Do **not** change this biological/output-selection behavior based on comments alone. Keep the current executable behavior until the intended preferred control source is confirmed from real workflow requirements or a stronger authoritative artifact.
