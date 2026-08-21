# Workflow controller

`tools/workflow_controller.py` is intentionally orchestration-only.

It stores paths in `~/.cautious-rotary-phone/config.json`, validates the three CSV headers, launches Fiji macros via Fiji's supported `-macro` interface, opens the ROI preset manager, and starts/stops the lightweight AHK alignment helper.

It does not reimplement Fiji, ROI 1-Click Tools, Pillow processing or AHK logic. If launched from Anaconda/conda, child Python helpers use that same interpreter.

Current buttons cover the synthetic test plate, full-column alignment and global visibility. Existing matrix scripts remain untouched until their hard-coded settings are adapted through a narrow config-aware route.