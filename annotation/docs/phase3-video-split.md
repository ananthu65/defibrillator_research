# Phase 3: Grouped Video Split

## Purpose

The Phase 3 split is designed for the 48 currently available participant sets.
The participant—not an individual video or extracted frame—is the independent
split unit.

Every participant contributes three camera recordings:

```text
Pxx_T
Pxx_LS
Pxx_LL
```

All three recordings remain in the same split. This prevents participant,
procedure, background, equipment, and recording-session leakage.

## Split result

| Split | Participant sets | Videos | Frames | Event tags | Tracks |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 33 | 99 | 59,371 | 559 | 602 |
| Validation | 6 | 18 | 10,354 | 100 | 115 |
| Test | 9 | 27 | 15,522 | 154 | 172 |

Approximate frame proportions are 69.6% train, 12.1% validation, and 18.2%
test.

## Participant assignments

### Train

```text
P03 P04 P06 P07 P12 P13 P14 P16 P19 P20 P22
P23 P24 P26 P27 P28 P29 P30 P31 P32 P33 P37
P39 P40 P42 P44 P46 P47 P48 P49 P52 P54 P55
```

### Validation

```text
P01 P18 P38 P45 P50 P56
```

### Test

```text
P05 P15 P17 P21 P25 P41 P43 P51 P53
```

## Annotation-source balancing

| Annotation source | Train | Validation | Test | Total |
| --- | ---: | ---: | ---: | ---: |
| defibliration2 | 11 | 1 | 3 | 15 |
| kartheepan | 10 | 1 | 2 | 13 |
| Kishonithan 37 to 41 | 3 | 1 | 1 | 5 |
| Rashad | 3 | 1 | 1 | 5 |
| Sharmilan | 3 | 1 | 1 | 5 |
| sujeevan | 3 | 1 | 1 | 5 |

Every source is represented in all three splits. This avoids making validation
or test performance depend on only one member's annotation style.

## Balance checks

- All seven event labels occur in train, validation, and test.
- All seven tracked object/region labels occur in train, validation, and test.
- Train contains 23 warning and 55 review findings.
- Validation contains 4 warning and 8 review findings.
- Test contains 6 warning and 13 review findings.
- All 144 canonical video IDs are assigned exactly once.
- Each split has the expected number of videos: three per participant.
- There is no participant or video overlap between splits.
- The split is tied to the Phase 1 dataset digest.

The assignment was selected from 30,000 deterministic, source-constrained
candidates using seed 42. The objective balances frames, annotation totals,
per-label coverage, rotated/outside keyframes, and annotation-review burden.

## Generated files

| File | Purpose |
| --- | --- |
| `train_sets.txt` | Training participant IDs. |
| `val_sets.txt` | Validation participant IDs. |
| `test_sets.txt` | Locked test participant IDs. |
| `train_videos.txt` | Training T/LS/LL task IDs. |
| `val_videos.txt` | Validation T/LS/LL task IDs. |
| `test_videos.txt` | Test T/LS/LL task IDs. |
| `participant_split.csv` | Participant-level assignment and balancing features. |
| `video_split_manifest.csv` | Source archive and media mapping for every video. |
| `split_summary.csv` | Split-level size and annotation totals. |
| `source_distribution.csv` | Annotation-source counts by split. |
| `label_distribution.csv` | Per-label representation by split. |
| `split_config.json` | Seed, optimization score, source quotas, digest, and complete assignment. |

## Freeze policy

This split is valid for the current Phase 1 digest:

```text
ec4c810df4e17197e697e4b5c80f2167d84a273fe4375843fa41ea18be6e9305
```

If annotations are corrected or additional participant sets are added before
training, rerun Phase 1 and create a versioned Phase 3 split. Once model
development starts, do not change assignments or use the test set for model,
threshold, augmentation, or epoch decisions.

The Phase 3 files are manifests. Source CVAT archives were not extracted,
moved, renamed, or modified. Phase 4 will use `video_split_manifest.csv` to
extract and convert the selected videos into model-ready data.
