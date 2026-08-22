# Whole-plate rotation prototype handoff

Status: Planned

## Target

Research and prototype physical whole-plate rotation estimation independently of the colony/grid alignment system.

Prefer mature Fiji/ImageJ, OpenCV, scikit-image or other established methods before custom vision code. Use synthetic/public non-confidential images only.

## Contract

Input: image path handled by the local prototype runtime.

Output: `RotationResult` v1 containing angle, method, optional confidence, manual-review flag and non-pixel diagnostics.

Do not modify the current four-click grid alignment route or current Fiji/AHK/controller runtime.

## Completion record

- Branch:
- Commit:
- Interface: `estimate_plate_rotation(path) -> RotationResult`
- Methods compared:
- Tests:
- Dependencies:
- Proven cases:
- Known limitations:
- Contract changes proposed:
- Integration/cherry-pick notes:
