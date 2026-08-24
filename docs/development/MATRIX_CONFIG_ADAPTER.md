# Matrix config adapter — internal compatibility route

The old `tools/run_matrices_from_config.py` entry point was removed because it could expose production crops to a legacy renderer's in-place rotation.

The current user endpoint is the controller's **Build matrices and labelled crops** applet, documented in `CUSTOM_COMPOSITION.md`. It filters the chosen dataset subset, stages exact current crops, normalizes only disposable copies, runs the mature Pillow implementations, and publishes one numbered multi-output action.

`tools/run_existing_pillow_from_config.py` remains a strict internal adapter and diagnostic CLI for the established renderers. It intentionally validates the complete requested metadata contract; it is no longer exposed as a competing controller dropdown. `docs/development/EXISTING_PILLOW_ADAPTERS.md` documents those retained renderer adapters.
