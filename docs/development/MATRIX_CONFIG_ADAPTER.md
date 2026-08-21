# Matrix config adapter

`tools/run_matrices_from_config.py` reuses the existing `existing scripts clean/make_matrices.py` unchanged.

It reads controller paths from `~/.cautious-rotary-phone/config.json`, replaces only the five explicit `Path(r"path here")` setting lines in memory, writes a temporary configured copy under the app config directory, and runs that copy with the same Python/conda interpreter.

The adapter deliberately checks that each expected setting line occurs exactly once. If the legacy script changes, it fails rather than guessing or patching unrelated code.

This avoids importing the legacy script (which has output-folder side effects at import time) and avoids maintaining a second matrix implementation.