# Phase 4 YOLO Dataset Build

| Split | Sets | Videos | Images | Labelled | Empty | Boxes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 33 | 99 | 13,955 | 13,502 | 453 | 39,570 |
| val | 6 | 18 | 2,469 | 2,399 | 70 | 6,995 |
| test | 9 | 27 | 3,714 | 3,564 | 150 | 10,172 |

- Conversion errors: 0
- Conversion warnings: 14
- Manual-review findings: 1
- Phase 1 digest: `ec4c810df4e17197e697e4b5c80f2167d84a273fe4375843fa41ea18be6e9305`
- Phase 3 config SHA-256: `abf66708768851574526b836178718fd3e62f0f2387946445794dfaa2c5cd78b`

Images and YOLO labels are generated under the ignored `datasets/` folder.
The source CVAT ZIP archives were opened read-only and were not modified.

## Independent validation

`validation.json` records a complete PASS across all 20,138 image/label pairs:
all 144 videos match the frozen split, every YOLO box is valid, all seven
classes occur in each split, participant leakage is zero, and all JPEGs decode.

## Manual visual QA

Train/validation overlays confirm the conversion geometry and portrait handling
are aligned. `manual_qa.csv` records one source-label concern in validation task
`P50_T`: a `paddle_sternal` track is present before a paddle is visible and
creates duplicate boxes later. Correct that CVAT source annotation and rebuild
before treating final model-selection metrics as clean.
