# Branch audit

## Active development line

`workflow-dev` is the only active development line. Routine implementation, fixes, tests, adapters, UI changes and documentation go directly there.

## `alpha-pre-release`

Audited against `workflow-dev` on 2026-08-21.

The branch is **diverged**, not a simple ancestor: GitHub reports four commits unique to `alpha-pre-release` and 98 commits unique to `workflow-dev` at the audit point.

The alpha-only tree differences are:
- `ALPHA_RELEASE_NOTES.md` (archival release notes);
- an older/smaller `tools/run_full_column_batch_from_config.py` implementation;
- older/smaller `tests/test_preflight_batch.py` coverage;
- older/smaller `tests/test_controller_contract.py` coverage.

These runtime/test differences have been superseded by the newer durable `workflow-dev` implementations and should **not** be merged or used as a development base. The release-notes file is archival information only and does not justify carrying forward the old runtime code.

Treat `alpha-pre-release` as an obsolete archival release pointer. Do not continue development on it. Do not cherry-pick its old runtime/test changes into `workflow-dev` merely because Git reports unique commits.

The current GitHub connector does not expose branch deletion, so this audit records the intended status without rewriting refs.
