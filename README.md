# Defibrillator Research

Research code and reproducible experiment metadata for the ARTS defibrillation
assessment project.

## Video dataset Phase 1

The CVAT backup auditor reads project/task backup ZIPs without extracting or
modifying them. It normalizes participant/camera identifiers and produces the
inventory, class distribution, integrity, and annotation-review reports needed
before dataset conversion or model training.

Run the audit from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\audit_cvat_backups.py `
  --input 'C:\path\to\cvat-backups' `
  --output reports\phase1 `
  --expected-participants 57 `
  --verify-crc `
  --strict
```

Run its standard-library tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

See [Phase 1 data audit](docs/phase1-data-audit.md) for the current findings and
report descriptions.

## Video dataset Phase 3

The grouped split generator consumes the Phase 1 reports and keeps all T, LS,
and LL videos from a participant in the same split. It constrains every
annotation source to appear in train, validation, and test, then balances frame,
label, and review-issue distributions.

```powershell
.\.venv\Scripts\python.exe scripts\create_grouped_video_split.py `
  --phase1-reports reports\phase1 `
  --output splits\phase3 `
  --train 33 `
  --val 6 `
  --test 9 `
  --seed 42 `
  --iterations 30000
```

See [Phase 3 grouped video split](docs/phase3-video-split.md) for the frozen
assignments and validation results.

## Video dataset Phase 4

The Phase 4 converter samples frames from the frozen split, interpolates CVAT
video tracks, and generates local YOLO images and labels. Source ZIPs are read
only, and generated recordings remain under the Git-ignored `datasets/`
directory.

```powershell
.\.venv\Scripts\python.exe scripts\build_yolo_video_dataset.py `
  --backup-root 'C:\path\to\cvat-backups' `
  --output datasets\phase4_yolo `
  --report-output reports\phase4

.\.venv\Scripts\python.exe scripts\validate_yolo_dataset.py `
  --dataset datasets\phase4_yolo `
  --output reports\phase4\validation.json `
  --verify-images
```

The current build contains 20,138 frames and 56,737 boxes from all 144 videos.
Its structural validation passes with zero corrupt images and no participant
leakage. One source-annotation issue in validation task `P50_T` must be reviewed
before final model-selection metrics are considered clean.

See [Phase 4 sampled YOLO dataset](docs/phase4-yolo-dataset.md) for class
mapping, sampling rules, validation, privacy constraints, and known findings.

