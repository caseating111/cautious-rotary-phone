# Four-point desktop validation

Use the smallest representative manual check after automated tests pass.

1. Start `start_controller_miniforge.cmd`.
2. Run Batch preflight and resolve only blocking problems.
3. Choose **Run one-plate 4-point proof** and an ordinary pending plate.
4. Confirm Fiji is usable, each of the four dialogs is moved upper-left, and the launcher overlay is hidden/lowered.
5. Click R1C1, R1C(last), R5C1 and R5C(last); inspect the rotated/skewed 8 x N QC grid.
6. Accept once and confirm crop export completes from the unchanged source.
7. Run one second plate in the same controller session to check that the workflow runs once and does not restart unexpectedly.

Batch the visual observations above into one report. Do not inspect every crop manually. If the same endpoint fails twice, reopen the Fiji ownership architecture documented in `docs/research/fiji-four-point-runtime.md` before adding another launcher or retry workaround.
*** Delete File: C:\Users\Grey\Desktop\Documents\!SCRIPTING\!AI\cautious-rotary-phone\docs\development\MINIMAL_DESKTOP_VALIDATION.md
