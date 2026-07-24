# Phase 5 local video training

Phase 5 establishes a reproducible local baseline before any larger-model or
institutional-GPU comparison. It trains object detection from sampled video
frames; it does not train audio and does not build an audio/video pipeline.

## What is fixed

- Task: seven-class object detection.
- Model for the local baseline: pretrained YOLOv8n.
- Split: the frozen participant-grouped Phase 3 split.
- Development data: train and validation only.
- Official test data: retained unchanged and not read by the training YAML.
- Quarantine: `P50_T` is excluded from all scored data because its known-invalid
  ground truth would make validation or test metrics misleading.
- Privacy: images, labels, weights, runs, and transcripts remain in ignored
  local folders. External experiment integrations are disabled.

The seven classes are `paddle_sternal`, `paddle_apical`,
`defibrillator_screen`, `learner_hand`, `sternal_placement_zone`,
`apical_placement_zone`, and `shock_symbol`.

## Generated training views

The preparation script creates path lists and YAML files without copying the
3.96 GiB Phase 4 dataset:

| View | Participants | Videos | Images | Boxes |
| --- | ---: | ---: | ---: | ---: |
| Full train | 33 | 99 | 13,955 | 39,570 |
| Full validation | 6 | 17 | 2,326 | 6,732 |
| Official test, reserved | 9 | 27 | 3,714 | 10,172 |
| Quarantined `P50_T` | 1 | 1 | 143 | 263 |
| Smoke train | 33 | 99 | 594 | 1,736 |
| Smoke validation | 6 | 17 | 102 | 300 |

The smoke subset deliberately samples every train and validation task. It is
small enough to verify the complete training path, but it is not intended to
estimate final model quality.

## Local environment

The tested environment is Python 3.11.0, PyTorch 2.7.0 with its CUDA 12.6
runtime, torchvision 0.22.0, and Ultralytics 8.4.60. The local GPU is an NVIDIA
GeForce GTX 1650 Max-Q with 4 GiB VRAM.

Install the pinned packages inside the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install `
  -r requirements\video-training.txt

.\.venv\Scripts\python.exe -m pip check
```

The pretrained `yolov8n.pt` checkpoint must be present at
`weights\yolov8n.pt`. That ignored file was verified locally at 6,549,796
bytes.

## Commands in order

Run commands from the repository root.

1. Prepare or regenerate the views:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\run_phase5_logged.ps1 `
     -Mode prepare
   ```

2. Run the one-epoch, batch-size-2 smoke test:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\run_phase5_logged.ps1 `
     -Mode smoke
   ```

3. Measure whether batch size 8 fits the local GPU:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\run_phase5_logged.ps1 `
     -Mode batch-probe
   ```

4. After reviewing the successful batch probe, run the 50-epoch preliminary
   baseline:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\run_phase5_logged.ps1 `
     -Mode preliminary
   ```

Do not start two training commands at the same time. The launcher records GPU
state before and after the command and writes a PowerShell transcript plus a
separate Python console log under `logs\phase5\`.

## Completed smoke result

The batch-size-2 smoke experiment completed successfully:

| Item | Result |
| --- | ---: |
| Epochs | 1 |
| Image size | 640 |
| Batch size | 2 |
| Train images | 594 |
| Validation images | 102 |
| Validation instances | 300 |
| Precision | 0.417 |
| Recall | 0.309 |
| mAP50 | 0.233 |
| mAP50-95 | 0.129 |
| Training-script duration | 170.7 seconds |
| Peak allocated GPU memory | 484.8 MiB |

Both `best.pt` and `last.pt` were saved at 6,222,122 bytes each. A local visual
audit found correct class-name mapping and aligned ground-truth boxes. The
one-epoch predictions contained sensible detections along with expected misses,
duplicates, and low-confidence boxes.

These metrics prove that loading, augmentation, CUDA training, validation,
checkpointing, and report generation work. They are not final performance
metrics: one epoch on a 696-image development subset is intentionally too
small. The smoke subset also contains only 35 `shock_symbol` boxes, so
class-specific smoke results are unstable.

Ultralytics disabled AMP automatically after its device safety check. That is
an expected compatibility decision for this GTX 1650, not a training failure.

## Completed batch-size probe

Batch size 8 completed on the same smoke dataset without an out-of-memory
error:

| Item | Batch 2 smoke | Batch 8 probe |
| --- | ---: | ---: |
| Training-script duration | 170.7 s | 108.8 s |
| Peak allocated GPU memory | 484.8 MiB | 1,679.6 MiB |
| mAP50 | 0.233 | 0.271 |
| mAP50-95 | 0.129 | 0.142 |

The metrics are not a model comparison because changing batch size changes the
one-epoch optimization path. The probe establishes capacity and throughput:
batch size 8 used about 41% of the GPU's 4 GiB and reduced elapsed time by
about 36%. The tracked 50-epoch preliminary configuration therefore uses batch
size 8.

Based only on the smoke throughput, the full local run may require roughly
12–20 hours. Actual duration can differ with thermals, validation time, and
early stopping. Keep the laptop powered, ventilated, and awake.

## Outputs and interpretation

- Compact tracked run report:
  `reports\phase5\yolov8n_smoke_p50t_quarantined.json`
- Generated local plots and checkpoints:
  `runs\phase5\yolov8n_smoke_p50t_quarantined\`
- PowerShell wrapper transcript:
  `logs\phase5\20260724_180309_smoke.txt`
- Reproducible terminal summary:
  `docs\phase5-terminal-worklog.md`

The full preliminary run performs model selection using validation only. The
official test set must remain unopened until the training choices are frozen.
When that point is reached, test evaluation should be run once and reported
alongside per-class metrics, confusion matrices, participant grouping, dataset
limitations, and the `P50_T` quarantine.
