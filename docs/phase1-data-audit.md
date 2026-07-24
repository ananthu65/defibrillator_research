# Phase 1: CVAT Backup Audit

## Purpose

Phase 1 establishes a read-only, reproducible inventory of the annotated video
data before any source archive is extracted, corrected, split, or converted for
model training.

The auditor is implemented in `scripts/audit_cvat_backups.py`. It uses only the
Python standard library and supports both CVAT project-backup and task-backup
ZIP structures.

## Current audit result

The audit was run with CRC verification against the available backup folder.

| Item | Result |
| --- | ---: |
| ZIP archives | 44 |
| CRC failures | 0 |
| CVAT tasks/videos | 144 |
| Complete three-camera participant sets | 48 |
| T videos | 48 |
| LS videos | 48 |
| LL videos | 48 |
| Frames | 85,247 |
| Event tags | 813 |
| Standalone shapes | 2 |
| Tracks | 889 |
| Track keyframes | 15,430 |

All 144 canonical task identifiers are unique. Every available participant has
exactly one T, LS, and LL task.

The planned P01-P57 collection is currently missing P02, P08-P11, P34-P36, and
P57.

## Annotation findings

The audit found no fatal/error-severity structural problems. Items requiring
review are recorded individually in `annotation_issues.csv`.

| Finding | Count | Meaning |
| --- | ---: | --- |
| Nonstandard task names normalized | 19 | Extensions, punctuation, or P48 naming typos were normalized using media filenames. |
| Object labels used as event tags | 14 | These annotations need correction, safe conversion, or exclusion. |
| Standalone shapes in video tasks | 2 | Review whether they should be tracks. |
| Repeated event tags | 28 | Confirm whether repetition is intentional and which timestamp is canonical. |
| Suspected event-order violations | 4 | Review P21_LS, P42_T, P52_LS, and P52_T visually. |
| Task/label groups with coordinates outside the frame | 42 | Often related to rotated or leaving-frame tracks; review before box conversion. |
| Tasks missing one or more event tags | 111 | Absence may mean not visible, not performed, unassessable, or missed annotation. |
| Tasks missing one or more track labels | 101 | Review against camera visibility rather than automatically treating as an error. |
| Blank CVAT subset metadata | 84 | Safe to ignore because participant-grouped splits will be generated separately. |

The 14-label declaration is consistent across all 144 tasks:

- Seven tracked object/region labels.
- Seven single-frame procedural event tags.

The event tags are preserved as timestamp ground truth. They must not be
silently discarded or treated as YOLO bounding boxes.

## Generated reports

| File | Contents |
| --- | --- |
| `dataset_inventory.csv` | One normalized record per CVAT task/video. |
| `annotation_summary.csv` | One aggregate record per source ZIP. |
| `annotation_issues.csv` | Structured errors, warnings, manual-review items, and informational gaps. |
| `class_distribution.csv` | Global counts by label and annotation kind. |
| `class_distribution_by_view.csv` | Label coverage for T, LS, and LL views. |
| `dataset_manifest.json` | Machine-readable participant sets, totals, and dataset digest. |
| `README.md` | Concise generated run summary. |

Reports contain relative archive paths and normalized participant identifiers,
not the absolute source-data path.

## Reproducibility

The current normalized inventory digest is:

```text
ec4c810df4e17197e697e4b5c80f2167d84a273fe4375843fa41ea18be6e9305
```

The digest changes when task identity, frame totals, or annotation totals
change, making later source-data revisions detectable.

## Phase 1 completion gate

Before proceeding to split generation and training-data conversion:

1. Review the 14 annotation-kind mistakes and two standalone shapes.
2. Visually adjudicate the four event-order warnings.
3. Decide how repeated event tags should be interpreted.
4. Classify important missing annotations as not visible, not performed,
   unassessable, or missed annotation.
5. Decide whether the remaining nine planned participant sets will be added.

The original ZIP archives must remain unchanged. Corrections should be made in
CVAT or captured in a separate, versioned correction manifest.
