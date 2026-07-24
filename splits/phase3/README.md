# Phase 3 Grouped Video Split

Each participant is the split unit. T, LS, and LL videos always remain together.

| Split | Sets | Videos | Frames | Event tags | Tracks |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 33 | 99 | 59,371 | 559 | 602 |
| val | 6 | 18 | 10,354 | 100 | 115 |
| test | 9 | 27 | 15,522 | 154 | 172 |

## Source constraints

- Every annotation source appears in train, validation, and test.
- Validation contains one participant set from every source.
- Test contains three sets from defibliration2, two from kartheepan, and one from every other source.
- No participant or camera view appears in more than one split.

Optimization seed: `42`  
Assignments evaluated: `30,000`  
Phase 1 dataset digest: `ec4c810df4e17197e697e4b5c80f2167d84a273fe4375843fa41ea18be6e9305`

This split is a manifest only. The source CVAT archives were not moved, extracted, or modified.
