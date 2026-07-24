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

