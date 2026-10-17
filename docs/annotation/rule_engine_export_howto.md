# Rule-engine export: how to run it on the final backups

**For:** Ananth · **From:** Arnikan · **Date:** 2026-10-16 (updated for Step 9c; for paddle
visibility and Step 9d gel on 2026-10-17) · Decisions D-074, D-083, D-085, D-086 to D-089, D-108,
D-111 and D-112
in [decisions.md](../rule_engine/decisions.md)

The rule engine needs the annotation facts of each video: every tag, the frame range and
duration, when each placement zone, the defibrillator screen and each paddle is visible, and
the gel applications derived from the gel-bottle hand (`learner_hand`). Two scripts read these
directly from the CVAT backups. Please run them once on the **final** backup set and send me the outputs listed below.

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

## Use exporter version 3 or later

The final export must be run with **exporter version 3 or later**.
- **Version 2** adds when each paddle is visible (`paddle_tracks`, `paddle_visibility`). The rule
  engine needs it to judge a missing button press (R4, D-108).
- **Version 3** adds the gel applications derived from the `learner_hand` and zone boxes, per zone
  (`derived_gel_events`, `gel`), and `gel_validation.csv`/`.md` (R1, D-111).

With an older export, the paddles and the gel per zone are "unknown". R4 can then never fail a
missing press, and R1 can only count `Gel applied` tags. The interim export has neither.

- **Before running:** pull the latest `feature/rule-engine`.
- **After running:** check that `export_manifest.json` says `"exporter_version": 3` (or higher),
  that its `counts` include `paddle_intervals` and `derived_gel_events`, and that it has
  `gel_settings_sha256`.
- **If it says 1 or 2:** the checkout is out of date. Pull, and run again into a new output
  folder.

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
| `data/rule_engine/annotation_export/final-<date>/` (gitignored) | `records.jsonl` (one line per video, including the per-paddle placements derived from the boxes and when the placement zones, the defibrillator screen and each paddle were visible), `export_manifest.json` (`exporter_version`, backup names and sizes, a SHA-256 of each backup's annotation JSON, counts, `export_id`, `placement_settings_sha256`, `gel_settings_sha256`), `export_issues.csv`, `placement_validation.csv` and `placement_validation.md` (how well the derived placements agree with the tags), `gel_validation.csv` and `gel_validation.md` (the derived gel applications per video and zone, and how well they agree with the `Gel applied` tags) |
| `annotation/reports/rule_engine_audit/final-<date>/` | `README.md`, `issues.csv` (review list), `info.csv` (information only), `zone_patterns.csv`, `audit_manifest.json` |

## What to send me

**Send:**
- `records.jsonl`;
- `export_manifest.json`;
- `placement_validation.csv` and `placement_validation.md`;
- `gel_validation.csv` and `gel_validation.md`;
- the whole audit folder.

Please send `records.jsonl` and `export_manifest.json` from the same run, unchanged, made with
exporter version 3 or later.
`export_id` is the SHA-256 of that exact `records.jsonl`. My reviews of the derived placements
and of the derived gel applications apply only to that export and its settings.

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

4. **An object label used as a tag:** P05_LL has a tag `apical_placement_zone` at frame 287
   (found 2026-10-17). It is a track label, not an event tag, and the rule engine reports it as
   an unknown label.
5. **Overlapping tracks of the same paddle** (a general point, not from the trial run). Some paddles were annotated with several tracks of
   one label (different IDs). That is fine where one track ends and the next one continues. But
   where two `paddle_apical` (or two `paddle_sternal`) tracks **overlap** on the same frames,
   please fix them: there are then two boxes of one paddle in those frames, which also affects
   your training labels. Where to look:
   - the audit's `duplicate_paddle_box` (review list) gives the frame ranges;
   - the exporter's `placement_duplicate_paddle_box` gives the ones that blocked a placement.

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
| `placement_duplicate_paddle_box` | Two tracks of one paddle overlap during its placement (item 5); no placement is derived for it |
| `placement_disagrees_with_tag` | A derived placement contradicts `first_paddle_firmly_on_the_chest` or `paddles_firmly_on_chest`; no placement is derived. Worth a look: either a tag or the boxes may be off |
| "refusing to write inside …data\video" | Choose an output folder outside `data/video/` |
| "output folder is not empty" | Use a new run folder |
| `"exporter_version": 1` or `2` in the manifest | An out-of-date checkout: no paddle visibility (1) or no derived gel (1 and 2). Pull `feature/rule-engine` and export again |
| `gel_hand_not_tracked` (export issues and the audit's review list) | No `learner_hand` box before the first paddle placement, so the gel can't be derived for that video. The hand holding the gel bottle should be tracked during gel application (A-024) |
