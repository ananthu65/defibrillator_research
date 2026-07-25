# Phase 4: sampled YOLO video dataset

Phase 4 converts the frozen Phase 3 participant-grouped split into a local
object-detection dataset. The CVAT project/task backup ZIPs are opened
read-only. One video is temporarily extracted at a time; the original archives
are not changed.

## Dataset

The generated dataset is stored at `datasets/phase4_yolo`. That directory is
ignored by Git because it contains identifiable recordings and is about
3.96 GiB. It must remain on approved private storage or compute.

| Split | Participants | Videos | Images | Labelled | Empty | Boxes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 33 | 99 | 13,955 | 13,502 | 453 | 39,570 |
| validation | 6 | 18 | 2,469 | 2,399 | 70 | 6,995 |
| test | 9 | 27 | 3,714 | 3,564 | 150 | 10,172 |
| **Total** | **48** | **144** | **20,138** | **19,465** | **673** | **56,737** |

All T, LS, and LL recordings for a participant remain in one split. No
participant is shared between train, validation, and test.

## Detection classes

| ID | Class |
| ---: | --- |
| 0 | `paddle_sternal` |
| 1 | `paddle_apical` |
| 2 | `defibrillator_screen` |
| 3 | `learner_hand` |
| 4 | `sternal_placement_zone` |
| 5 | `apical_placement_zone` |
| 6 | `shock_symbol` |

The seven event/tag classes remain temporal metadata in
`metadata/events.jsonl`; they are not converted into artificial bounding boxes.

## Sampling and conversion

Regular frames are sampled at 5 FPS. The converter additionally retains:

- event frames and ±0.10 seconds of context;
- standalone-shape frames;
- track-boundary frames; and
- all `shock_symbol` keyframes.

CVAT track geometry is interpolated between keyframes. Rotated rectangles and
polygons are converted to enclosing, axis-aligned YOLO boxes and clipped to the
image. An empty label file is retained for every sampled negative frame.

Rebuild into a new or empty output directory:

```powershell
.\.venv\Scripts\python.exe scripts\build_yolo_video_dataset.py `
  --backup-root 'C:\path\to\cvat-backups' `
  --split-manifest splits\phase3\video_split_manifest.csv `
  --split-config splits\phase3\split_config.json `
  --output datasets\phase4_yolo `
  --report-output reports\phase4 `
  --sample-fps 5 `
  --event-context-seconds 0.10 `
  --jpeg-quality 85
```

The converter refuses a non-empty dataset output directory to prevent an old
and new build from being mixed.

## Validation

The independent validator reconciles the generated files with the Phase 3
manifest and reports. It checks:

- every manifest image and label exists, with no unlisted extras;
- image and label stems match and every sampled task/frame is unique;
- every YOLO line has a valid class and an in-bounds normalized box;
- label counts and class names match the sample manifest;
- all seven classes occur in every split;
- every Phase 3 task and participant occurs in exactly its frozen split;
- event metadata covers all 144 videos; and
- every JPEG can be decoded by Pillow.

Run the complete check:

```powershell
.\.venv\Scripts\python.exe scripts\validate_yolo_dataset.py `
  --dataset datasets\phase4_yolo `
  --split-manifest splits\phase3\video_split_manifest.csv `
  --class-report reports\phase4\class_distribution.csv `
  --split-report reports\phase4\split_summary.csv `
  --output reports\phase4\validation.json `
  --verify-images
```

The current result is **PASS**: 20,138 image/label pairs, 56,737 boxes, no
structural findings, no participant leakage, and zero corrupt images.

For local visual QA, render train/validation overlays only:

```powershell
.\.venv\Scripts\python.exe scripts\render_yolo_previews.py `
  --dataset datasets\phase4_yolo `
  --output datasets\phase4_yolo\qa_previews `
  --splits train val `
  --per-class 3
```

The preview tool does not accept the test split. Its output remains ignored by
Git.

## Findings requiring annotation review

The automated conversion reported no error-severity findings. Fourteen CVAT
object-name tags had no geometry and were correctly excluded. One degenerate
training box in `P13_T` was skipped.

Manual overlay review found a source-annotation issue in validation video
`P50_T`: a `paddle_sternal` polygon is present in every sampled frame even when
the paddle is absent, and 43 sampled frames contain two `paddle_sternal` boxes.
The CVAT source track begins at frame 0, has keyframes at 0, 48, 261, and 399,
and has no outside termination. This is recorded in
`reports/phase4/manual_qa.csv`.

The conversion itself is reproducible and structurally valid, but final model
selection metrics should not be treated as clean until this CVAT track is
reviewed/corrected and Phases 1 and 4 are rerun. A local Phase 5 baseline may
still be run to verify the training code and estimate memory/runtime; label it
as preliminary and do not inspect the locked test images or metrics during
development.

## Reproducibility records

The dataset build is tied to:

- Phase 1 dataset digest:
  `ec4c810df4e17197e697e4b5c80f2167d84a273fe4375843fa41ea18be6e9305`
- Phase 3 split configuration SHA-256:
  `abf66708768851574526b836178718fd3e62f0f2387946445794dfaa2c5cd78b`

Detailed counts and findings are in `reports/phase4`.
