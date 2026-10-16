# Rule-engine export: how to run it on the final backups

**For:** Ananth · **From:** Arnikan · **Date:** 2026-10-16 · Decisions D-074, D-083 and D-085
in [decisions.md](../rule_engine/decisions.md)

The rule engine needs the annotation facts of each video: every tag, the frame range and
duration, and when each placement zone is visible. Two scripts read these directly from the CVAT
backups. Please run them once on the **final** backup set and send me the outputs listed below.

## It changes nothing in your training data

- **Nothing is edited:** the scripts don't change any existing file: not your scripts
  (`build_yolo_video_dataset.py`, `create_grouped_video_split.py`, `validate_yolo_dataset.py`,
  `audit_cvat_backups.py`), and not their outputs (`events.jsonl`, `sample_manifest.csv`, the
  split files, `annotation/reports/phase1/`, `annotation/reports/phase4/`).
- **Nothing is written in your data:** they refuse to write anywhere inside `data/video/`, and
  your training pipeline never reads their outputs.
- **The backups are only read**, and only the annotation JSON (`task.json`, `annotations.json`).
  Video files inside the backups are never opened, hashed or printed. A test checks this.
- **Two imports from your scripts:** the exporter imports your task discovery and your box
  geometry (`track_box_at`, `clip_box`). A zone therefore counts as visible on exactly the frames
  where your training labels have a box for it. Nothing in your scripts is modified.

## What you need

| Input | Where |
|---|---|
| The final CVAT backup ZIPs | Any folder; subfolders are searched (`*.zip`), both task and project backups |
| `annotation/reports/phase4/video_conversion.csv` | Already in the repo. The exporter takes fps, width and height from it. A video missing from it is reported as `fps_missing` and gets no record |
| The repo on branch `feature/rule-engine` | The two scripts and `configs/rule_engine/annotation_export.yaml` |
| Python with PyYAML | The project's usual environment (`requirements.txt`); no extra packages |

## Commands

Run them from the repository root. Use a new, empty output folder each time; both scripts
refuse a folder that isn't empty.

```powershell
python -m annotation.export_rule_engine_records `
  --backup-root "<folder with the final CVAT backups>" `
  --output data/rule_engine/annotation_export/final-<date>

python -m annotation.audit_rule_engine_checks `
  --backup-root "<folder with the final CVAT backups>" `
  --output annotation/reports/rule_engine_audit/final-<date>
```

- **Exit code 0:** a report was written. A one-line summary is printed.
- **Exit code 2:** nothing was written, for example a missing backup folder or a refused output
  path. The reason is printed.

## Outputs

| Folder | Files |
|---|---|
| `data/rule_engine/annotation_export/final-<date>/` (gitignored) | `records.jsonl` (one line per video), `export_manifest.json` (backup names and sizes, a SHA-256 of each backup's annotation JSON, counts), `export_issues.csv` |
| `annotation/reports/rule_engine_audit/final-<date>/` | `README.md`, `issues.csv` (review list), `info.csv` (information only), `zone_patterns.csv`, `audit_manifest.json` |

## What to send me

**Send:**
- `records.jsonl`;
- `export_manifest.json`;
- the whole audit folder.

**Never send media:** no backup ZIPs, no videos, no frames, no images. Please don't commit
`records.jsonl`; exported records stay out of git.

## Items to fix in the backups (found in a trial run on 39 corrected backups)

1. **`P14_LL.zip` contains a task named `P14_LS`.** Both it and `P14_LS.zip` resolve to
   P14_LS, so the P14_LL video seems to be missing from that set. Please check which video is
   inside `P14_LL.zip` and correct the task name or the file.
2. **8 zone tracks move.** A placement zone should stay still while the paddles move. These
   tracks' centres move more than 5% of the frame diagonal:

   | Video (archive) | Zone | Moved | Between frames |
   |---|---|---|---|
   | P06_T | sternal_placement_zone | 5.8% | 72 and 658 |
   | P07_T | sternal_placement_zone | 6.8% | 0 and 637 |
   | P07_T | apical_placement_zone | 8.1% | 0 and 637 |
   | P14_LS (in `P14_LL.zip`) | apical_placement_zone | 7.6% | 0 and 461 |
   | P14_LS (in `P14_LL.zip`) | sternal_placement_zone | 6.8% | 0 and 481 |
   | P31_LL | apical_placement_zone | 5.7% | 24 and 467 |
   | P31_T | sternal_placement_zone | 13.2% | 871 and 894 |
   | P31_T | apical_placement_zone | 11.2% | 358 and 892 |

   None overlapped a paddle box at the end frame. Some may be slow camera or mannequin drift
   rather than a mislabel, but P31_T (13.2% in 23 frames) looks like a mislabel.
3. **2 near-duplicate gel tags:** "Gel applied" twice within 15 frames, possibly the same
   application tagged twice:
   - P06_LS, frames 259 and 260;
   - P12_LS, frames 164 and 179.

The audit on the final backups will show whether these are fixed. The rest of the review list
(`issues.csv`) is also worth a look. Everything in `info.csv` is information only: for example,
the learner's order of steps is never an annotation problem.

## Questions for you

- **When will the final export be available?** (OQ-054)
- **Constant frame rate:** are the converted videos constant frame rate? If not, `frame / fps`
  only approximates real time, which matters when video times are compared with audio times,
  for example in R7. (OQ-053)
- **Camera view from the file name:** does anything in your pipeline take the camera view or task
  ID from the backup **file name**, instead of from inside the backup? See item 1. (OQ-055)

## If something goes wrong

| Message or issue | Meaning |
|---|---|
| `fps_missing` | The video isn't in `video_conversion.csv`; add it there (no record is written meanwhile) |
| `frame_count_mismatch` | The backup's frame count differs from the conversion report |
| `duplicate_task` | Two backups contain the same task; the first, in path order, is used |
| `unrecognized_task_name` | Neither the task name nor the media file name gives a `PXX_VIEW` ID |
| "refusing to write inside …data\video" | Choose an output folder outside `data/video/` |
| "output folder is not empty" | Use a new run folder |
