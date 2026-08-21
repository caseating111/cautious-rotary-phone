# Branch audit

## Active development line

`workflow-dev` is the only active development line. Routine implementation, fixes, tests, adapters, UI changes and documentation go directly there.

## `alpha-pre-release`

Audited against `workflow-dev` on 2026-08-21.

The branch is **diverged**, not a simple ancestor. At the original audit point GitHub reported four commits unique to `alpha-pre-release` and 98 commits unique to `workflow-dev`.

The original alpha-only tree differences were:
- `ALPHA_RELEASE_NOTES.md` (archival release notes);
- an older/smaller `tools/run_full_column_batch_from_config.py` implementation;
- older/smaller `tests/test_preflight_batch.py` coverage;
- older/smaller `tests/test_controller_contract.py` coverage.

Those runtime/test differences have been superseded by the newer durable `workflow-dev` implementations and should **not** be merged or used as a development base.

### Targeted launcher hotfix after the audit

After the user installed Anaconda, the packaged alpha `start_controller.cmd` stopped reaching its Python fallback because Windows `conda` is commonly a batch/cmd entry point and the launcher invoked it without `call`.

A narrowly scoped alpha hotfix was therefore made on 2026-08-21:
- `start_controller.cmd` now uses `call conda run ...`, allowing control to return to the launcher and continue to its Python fallbacks when the named environment is unavailable;
- `ALPHA_RELEASE_NOTES.md` records that launcher-only hotfix.

This does **not** make `alpha-pre-release` an active development line and does not authorize carrying newer feature work there. All project-layout, custom-composition and normal implementation work remains on `workflow-dev`.

Treat `alpha-pre-release` as an archival release snapshot with one targeted launcher compatibility hotfix. Do not cherry-pick its old runtime/test changes into `workflow-dev` merely because Git reports unique commits.
