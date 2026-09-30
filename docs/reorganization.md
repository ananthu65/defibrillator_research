# Repository reorganization

Starting point: `origin/main` at `2c3508e`. `ananthu_dev` was fast-forwarded
to that commit before these local changes. No remote branch was modified.

| Previous location | Current location |
| --- | --- |
| `assessment_pipeline/` | `legacy/assessment_pipeline/` (unchanged archive) |
| `docs/rule_*.md` | `legacy/docs/` |
| `scripts/evaluate_defib_commands.py`, `rubric_json/`, `google_sheet/` | `legacy/audio_commands/` |
| CVAT audit, conversion, split, validation and preview scripts | `annotation/` |
| `scripts/train_yolo_local.py` | `video/train.py` |
| `scripts/create_phase5_training_view.py` | `video/create_training_view.py` |
| `scripts/run_phase5_logged.ps1` | `video/run_training_logged.ps1` |
| `scripts/extract_audio_batch.py` | `audio/extract_audio.py` |
| `configs/phase5/` | `configs/video/` |
| `reports/phase1/`, `reports/phase4/` | `annotation/reports/` |
| `reports/phase5/` | `video/reports/phase5/` (historical originals) |
| `splits/phase3/*.txt` | `data/splits/phase3/` |
| Other `splits/phase3/` metadata | `annotation/splits/phase3/` |
| Phase 1/3/4 guides | `annotation/docs/` |
| Phase 5 guide and terminal worklog | `video/docs/` |
| `datasets/phase4_yolo/` | `data/video/phase4_yolo/` |
| `weights/yolov8n.pt` | `data/weights/video/yolov8n.pt` |
| `runs/` | `data/runs/video/` |
| `extracted_audio/` | `data/audio/extracted/` |
| `logs/` | `data/logs/` |

Historical reports and the terminal worklog intentionally retain original
paths and checksums. Imported experiment configs also describe the original
runs. Active configs, commands, imports and generated Phase 5 image lists use
new paths. The original generated lists/YAMLs are backed up locally under
`data/migration_backup/`. Raw frame images, labels, recordings and checkpoints
were moved intact; their contents were not rewritten. Saved Ultralytics run
arguments retain their historical paths; start new runs with the active configs.

Existing completed experiments keep their names. For another run, copy a
training config and change `name`; the runner refuses to overwrite a saved run.
`yolov8n_preliminary.json` remains available for the next planned training run.

## Development status

Working: existing annotation/training tools; shared schemas; fixture runner;
model registry; local YOLO/RT-DETR and faster-whisper adapters; MFCC/random-forest
charging baseline; experiment recorder; feedback renderer; report viewer.
Adapters and the charging baseline need their dependencies, local models and
real inputs. The existing detector has only preliminary one-epoch training.

Pending: Faster R-CNN integration, agreed event vocabulary and semantic video
postprocessing, supervisor-approved R1–R7/A1–A7 implementations, charging labels
and a trained charging model, YAMNet alternative, and full real-data integration
validation. The new rule engine explicitly returns `unable_to_assess` for
every pending rule. `configs/rules.yaml` contains no inherited timing defaults.

CI is defined locally. GitHub branch protection and required reviewer settings
must be enabled in repository settings; a workflow file alone does not enforce
them. Team policy: feature branch, one other member's PR review, passing tests,
then merge. Do not push directly to main.

## Reorganization verification

- 48 unit/integration tests pass, including synthetic charging training and
  prediction, configurable model/rule extensions and independent feedback fixtures.
- The relocated dataset passes full validation including image decoding:
  144 videos, 20,138 images, 56,737 boxes, zero corrupt images or structural findings.
- All 20,834 entries across generated training/evaluation image lists resolve.
- The existing YOLO checkpoint loads and runs inference on a synthetic video.
- All 36 archived pipeline files match their original Git content, allowing
  for checkout line endings; all six frozen split lists are preserved.
- Git sees only those six split text lists under `data/`; weights, media and
  local run artifacts remain ignored.

The live Streamlit UI, Whisper adapter and RT-DETR adapter have not been run
with real inputs here. The charging test uses synthetic audio, not clinical
performance evidence. GitHub Actions will run after the changes are pushed.
