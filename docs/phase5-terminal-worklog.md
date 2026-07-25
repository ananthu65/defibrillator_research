# Phase 5 terminal worklog

This file records the terminal work performed for local video-model training.
It explains what each command did and the result. Large raw console transcripts
are stored locally under `logs/` and are ignored by Git because they may contain
machine-specific paths and generated training output.

## Rules used

- Commands are run from the repository root.
- The project virtual environment is invoked explicitly with
  `.\.venv\Scripts\python.exe`.
- Training is local and does not upload student images.
- `P50_T` is quarantined from train, validation, and official test metrics.
- The frozen Phase 3 split and original Phase 4 dataset are not modified.
- Model weights, generated datasets, training runs, and raw transcripts are
  ignored by Git.

## 1. Repository, GPU, and package inspection

Commands:

```powershell
git status --short --branch
nvidia-smi
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip show torch torchvision ultralytics
```

Purpose:

- Confirm the active branch and whether tracked files were clean.
- Identify the GPU, driver, CUDA compatibility, VRAM, temperature, and current
  usage.
- Confirm the Python version and whether training packages were installed.

Result:

- Branch: `ananthu_dev`, three local commits ahead of its remote.
- GPU: NVIDIA GeForce GTX 1650 Max-Q with 4,096 MiB VRAM.
- NVIDIA driver: 565.90; driver-reported CUDA compatibility: 12.7.
- Python: 3.11.0.
- PyTorch, torchvision, and Ultralytics were initially absent.

## 2. Official installation guidance

The current official PyTorch and Ultralytics documentation was checked before
installation. The selected local stack was:

- PyTorch 2.7.0 with CUDA 12.6 runtime;
- torchvision 0.22.0 with CUDA 12.6 runtime; and
- Ultralytics 8.4.60.

CUDA 12.6 was selected because it is supported by the installed NVIDIA driver.
The PyTorch wheel includes its CUDA runtime, so no system-wide CUDA toolkit was
installed.

## 3. First PyTorch installation attempt

Command:

```powershell
.\.venv\Scripts\python.exe -m pip install `
  torch==2.7.0 torchvision==0.22.0 `
  --index-url https://download.pytorch.org/whl/cu126
```

Result:

- The old `pip` 22.3 rejected normalized dependency metadata for
  `typing-extensions`.
- PyTorch was not installed by this attempt.

Corrective command:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

Result:

- Only the project virtual environment was changed.
- `pip` was upgraded from 22.3 to 26.1.2.

## 4. CUDA PyTorch installation

Command:

```powershell
.\.venv\Scripts\python.exe -m pip install `
  torch==2.7.0 torchvision==0.22.0 `
  --index-url https://download.pytorch.org/whl/cu126
```

Result:

- Installed `torch-2.7.0+cu126`.
- Installed `torchvision-0.22.0+cu126`.
- The PyTorch wheel download was approximately 2.8 GB.

CUDA verification command:

```powershell
.\.venv\Scripts\python.exe -c "import torch, torchvision; `
print('torch=', torch.__version__); `
print('torchvision=', torchvision.__version__); `
print('cuda_available=', torch.cuda.is_available()); `
print('cuda_runtime=', torch.version.cuda); `
print('gpu=', torch.cuda.get_device_name(0)); `
x=torch.ones((1024,1024), device='cuda'); `
y=x@x; torch.cuda.synchronize(); `
print('cuda_tensor_sum=', float(y.sum()))"
```

Result:

- `torch.cuda.is_available()` returned `True`.
- PyTorch CUDA runtime: 12.6.
- GPU detected correctly as GTX 1650 Max-Q.
- A real matrix multiplication completed on the GPU.

## 5. Ultralytics installation

Command:

```powershell
.\.venv\Scripts\python.exe -m pip install ultralytics==8.4.60
```

Verification:

```powershell
.\.venv\Scripts\python.exe -m pip check
```

Result:

- Ultralytics 8.4.60 and its required packages were installed.
- `pip check` reported no broken requirements.
- Optional analytics and external experiment integrations were disabled.
- The training entry point sets `YOLO_OFFLINE=true` before training.

## 6. Phase 5 dataset view

Command:

```powershell
.\.venv\Scripts\python.exe scripts\create_phase5_training_view.py `
  --dataset datasets\phase4_yolo `
  --output datasets\phase4_yolo\phase5 `
  --report reports\phase5\training_view.json `
  --quarantine-task P50_T `
  --smoke-images-per-task 6
```

Purpose:

- Create text file lists without copying the 3.96 GiB image dataset.
- Exclude `P50_T` from all scored splits.
- Preserve the original official test split.
- Create a small, source-diverse smoke-test subset.

Result:

| View | Participants | Videos | Images | Boxes | Classes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Full train | 33 | 99 | 13,955 | 39,570 | 7 |
| Full validation | 6 | 17 | 2,326 | 6,732 | 7 |
| Official test | 9 | 27 | 3,714 | 10,172 | 7 |
| Quarantine `P50_T` | 1 | 1 | 143 | 263 | 3 |
| Smoke train | 33 | 99 | 594 | 1,736 | 7 |
| Smoke validation | 6 | 17 | 102 | 300 | 7 |

`P50_T` was not moved into the official test split because known-invalid
ground truth cannot produce a trustworthy test score. It can later be used as
an unscored demonstration.

## 7. Unit and syntax checks

Commands:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m py_compile `
  scripts\create_phase5_training_view.py `
  scripts\train_yolo_local.py
git diff --check
```

Result:

- All 25 repository tests passed.
- Phase 5 scripts compiled successfully.
- No patch whitespace errors were found.

One attempted targeted test command used dotted names beginning with `tests`.
The installed Ultralytics distribution also contains a package named `tests`,
so Python resolved that unrelated package first. The repository-standard
discovery command shown above avoids that namespace collision and passed.

## 8. Pretrained model download

The official pretrained YOLOv8n weight was downloaded from the Ultralytics
assets release into the ignored `weights/` folder.

Result:

- File: `weights/yolov8n.pt`
- Size: 6,549,796 bytes
- The checkpoint loaded successfully with Ultralytics.

## 9. Interrupted Codex smoke run

Command:

```powershell
.\.venv\Scripts\python.exe scripts\train_yolo_local.py `
  --config configs\phase5\yolov8n_smoke.json
```

Observed before interruption:

- CUDA training started successfully.
- The YOLOv8n detection head was changed from 80 COCO classes to 7 project
  classes.
- 319 of 355 compatible pretrained weight items transferred.
- All 594 smoke-training and 102 smoke-validation labels scanned with zero
  corrupt files.
- Ultralytics automatically disabled AMP after its GTX 1650 safety check.
- Batch size 2 at image size 640 used approximately 0.51 GiB reported GPU
  training memory.
- Training progressed normally beyond half of the single epoch.

The run was deliberately stopped when the user chose to run training
personally. It is not a valid completed experiment and its metrics must not be
reported. Its partial artifacts were preserved locally at:

```text
runs\phase5\yolov8n_smoke_p50t_quarantined_interrupted_codex
```

After stopping, `nvidia-smi` confirmed there was no remaining Python compute
process and the GPU returned to idle.

## 10. User-run commands

The logged PowerShell launcher records the command, environment summary, and
all training console output:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_phase5_logged.ps1 `
  -Mode prepare

powershell -ExecutionPolicy Bypass -File scripts\run_phase5_logged.ps1 `
  -Mode smoke
```

The transcript path is printed at the beginning and end of each run. Do not
start the full 50-epoch preliminary experiment until the smoke result has been
reviewed.

## 11. Logged launcher verification

Command:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_phase5_logged.ps1 `
  -Mode prepare
```

Result:

- The launcher completed successfully.
- It recorded GPU state before and after dataset preparation.
- It regenerated the same Phase 5 counts:
  13,955 train, 2,326 validation, 3,714 official test, 143 quarantine,
  594 smoke-train, and 102 smoke-validation images.
- The GPU remained idle at 127 MiB display usage.
- Raw local transcript:
  `logs/phase5/20260724_180200_prepare.txt`.

The timestamped transcript is ignored by Git. The reproducible command and its
outcome are retained in this worklog.

## 12. Clean logged smoke run

Command:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_phase5_logged.ps1 `
  -Mode smoke
```

Result:

- The complete one-epoch train and validation workflow succeeded.
- Dataset scans found 594 training images and 102 validation images with zero
  corrupt files.
- The run used batch size 2 and image size 640.
- AMP was requested but Ultralytics disabled it after its GTX 1650 safety
  check; training continued normally in full precision.
- Precision: 0.417; recall: 0.309.
- mAP50: 0.233; mAP50-95: 0.129.
- Training-script duration: 170.7 seconds.
- Peak PyTorch allocated GPU memory: 484.8 MiB.
- `best.pt` and `last.pt` were written successfully.
- GPU usage returned to 117 MiB display usage with no Python compute process.
- Raw local transcript:
  `logs/phase5/20260724_180309_smoke.txt`.

The authoritative compact report is
`reports/phase5/yolov8n_smoke_p50t_quarantined.json`. The smoke metrics are a
pipeline check, not a final model-quality result.

## 13. Artifact and metadata verification

Reproducibly equivalent commands:

```powershell
Get-Content reports\phase5\yolov8n_smoke_p50t_quarantined.json -Raw
Get-Content runs\phase5\yolov8n_smoke_p50t_quarantined\results.csv -Raw
Get-ChildItem runs\phase5\yolov8n_smoke_p50t_quarantined\weights
Get-ChildItem runs\phase5\yolov8n_smoke_p50t_quarantined -Recurse -File
```

Result:

- The report status is `completed`.
- Report and `results.csv` metrics agree within normal saved precision.
- `best.pt`: 6,222,122 bytes.
- `last.pt`: 6,222,122 bytes.
- The run contains 21 generated artifacts, including label distributions,
  training mosaics, validation labels/predictions, curves, and checkpoints.

A first combined PowerShell inspection serialized nested PowerShell objects and
did not return promptly. Its exact PID was stopped; it performed read-only
inspection and changed no project data. A follow-up attempt to inspect process
command lines through WMI returned `Access denied`, so standard `Get-Process`
was used to identify only that new process. The simpler explicit commands above
then completed normally.

## 14. Local visual audit

Inspected generated files:

```text
runs\phase5\yolov8n_smoke_p50t_quarantined\labels.jpg
runs\phase5\yolov8n_smoke_p50t_quarantined\train_batch0.jpg
runs\phase5\yolov8n_smoke_p50t_quarantined\val_batch0_labels.jpg
runs\phase5\yolov8n_smoke_p50t_quarantined\val_batch0_pred.jpg
```

Result:

- Class names matched the intended objects.
- Ground-truth boxes aligned with visible objects.
- Predictions appeared in plausible regions.
- Misses, duplicate detections, and low-confidence predictions remained, as
  expected after one epoch.
- The smoke distribution has only 35 `shock_symbol` instances, so its
  class-specific metric is not stable.

No image or annotation was uploaded during this review.

## 15. Post-smoke checks

Commands:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m py_compile `
  scripts\create_phase5_training_view.py `
  scripts\train_yolo_local.py
git diff --check
```

Result:

- All 25 tests passed again.
- Both Phase 5 Python scripts compiled.
- Patch whitespace validation passed; Git printed only expected Windows
  LF-to-CRLF conversion warnings.

The first PowerShell parser-check expression referenced undeclared variables
and returned a checker-only error. It did not execute the launcher or change
data. The corrected check initialized the token and error variables before
passing them by reference:

```powershell
$tokens = $null
$parseErrors = $null
$null = [System.Management.Automation.Language.Parser]::ParseFile(
  (Resolve-Path 'scripts\run_phase5_logged.ps1'),
  [ref]$tokens,
  [ref]$parseErrors
)
```

The corrected launcher syntax check passed.

## 16. Batch-size-8 capacity probe

Command:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_phase5_logged.ps1 `
  -Mode batch-probe
```

Result:

- The same 594-image train and 102-image validation smoke views were used.
- Batch size 8 and image size 640 completed without out-of-memory errors.
- Duration: 108.8 seconds.
- Peak PyTorch allocated GPU memory: 1,679.6 MiB.
- Precision: 0.715; recall: 0.200.
- mAP50: 0.271; mAP50-95: 0.142.
- GPU usage returned to 151 MiB display usage and no Python compute process.
- Compact report:
  `reports/phase5/yolov8n_batch8_probe_p50t_quarantined.json`.
- PowerShell transcript:
  `logs/phase5/20260724_181132_batch-probe.txt`.

The one-epoch metrics must not be interpreted as a fair batch-size comparison.
The probe shows that batch 8 fits and is about 36% faster end to end than the
batch-2 smoke run. The preliminary configuration was updated to batch 8.

Windows PowerShell 5.1 `Start-Transcript` retained the wrapper commands and
timestamps but did not persist every native Python progress line. Commands,
outcomes, metrics, and generated artifacts were still retained in this tracked
worklog and compact reports. The launcher was then changed to use `Tee-Object`
for a separate Python console log on all future commands.

## 17. Corrected logger verification

Command:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_phase5_logged.ps1 `
  -Mode prepare
```

Result:

- Dataset preparation completed with the same authoritative counts.
- The PowerShell wrapper transcript was created at
  `logs/phase5/20260724_182030_prepare_powershell.txt` (1,726 bytes).
- Native Python output was separately captured at
  `logs/phase5/20260724_182030_prepare_console.txt` (220 bytes).
- Reading the console file reproduced both Python summary lines.
- The GPU remained idle before and after the command.

Future smoke, batch-probe, and preliminary training invocations use this
two-file logging arrangement.

## 18. Final pre-commit validation

Commands:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m py_compile `
  scripts\create_phase5_training_view.py `
  scripts\train_yolo_local.py
git diff --check
rg -n --fixed-strings 'C:\Personal\defibrillator_research' `
  README.md configs docs reports requirements scripts tests
```

Result:

- All 25 tests passed.
- Python compilation and PowerShell launcher parsing passed.
- Patch whitespace validation passed with only expected Windows line-ending
  warnings.
- No machine-specific absolute repository path was present in tracked project
  content.

## 19. One-epoch user workflow inspection

Read-only commands inspected the generated Phase 5 file lists, full-data YAML,
installed YOLO executable, training configuration, logged launcher, and preview
renderer.

Result:

- `dataset_preliminary.yaml` points to `train.txt`, `val.txt`, and `test.txt`.
- The full view contains 13,955 training and 2,326 scored validation frames.
- `.\.venv\Scripts\yolo.exe` is installed.
- The existing `preliminary` mode is a continuous 50-epoch experiment.
- The first validation-list frame is an intentional background frame with an
  empty label.
- The first validation frame with a non-empty label is
  `P18_LL_f000132.jpg`, containing an `apical_placement_zone` box.

A distinct `full-one-epoch` configuration and launcher mode were added so the
user can measure a complete pass through all 33 training participants without
accidentally starting the long run. No training was started during this step.

Validation after the change:

- All 25 repository tests passed.
- The new configuration loaded successfully and confirmed `epochs=1` with the
  full preliminary dataset YAML.
- PowerShell launcher parsing passed.
- Patch whitespace validation found no errors.

## Continuing this record

Every later terminal action should be added here with:

1. the exact or reproducibly equivalent command;
2. why it was run;
3. the result and any warnings;
4. whether it changed files or environment state; and
5. which generated outputs are authoritative.
