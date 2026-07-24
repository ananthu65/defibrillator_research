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

