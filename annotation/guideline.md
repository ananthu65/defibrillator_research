# Annotation — Arnikan

- Audit CVAT backups with `python -m annotation.audit_cvat_backups`.
- Generate participant-grouped assignments with
  `python -m annotation.create_grouped_video_split`. Metadata belongs in
  `annotation/splits/phase3/`; the six frozen text lists live in `data/splits/phase3/`.
- Convert to frames and YOLO labels with `python -m annotation.build_yolo_video_dataset`.
- Validate and preview with `annotation.validate_yolo_dataset` and
  `annotation.render_yolo_previews`.
- Convert audited point tags for one recording with
  `python -m annotation.to_timeline --task P03_LL --output data/outputs/P03_LL.json`.

Keep participant IDs together across train/validation/test, including every
camera view and charging-sound window. Keep the official test split untouched
during model selection. The existing P50_T quarantine remains in the training
view generator. Read `docs/phase4-yolo-dataset.md` for its annotation issue.

Shared events use seconds from recording start. A point tag has `start == end`.
Keep the original annotation label and participant/task/frame provenance;
agree label-to-rule mappings explicitly. Camera views must be synchronized
before their timestamps are combined. Do not combine multiple participants
into one assessment timeline.
