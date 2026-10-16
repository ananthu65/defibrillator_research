# Rule engine: status of each rule

One row per rule, in report (display) order. **Status:** `pending` (not built), `built` (code
exists), `tested` (built and covered by the scenario tests). Every rule is also `pending` in
`configs/rules.yaml` until the supervisor approves its definition, and it is not counted until
then (D-043).

Shared steps used by every rule: P-014 (rule decision ladder) and P-008 (what a missing event
means). Failure codes are listed in [anomalies.md](anomalies.md).

| Rule | Logic in plain words | Events and key times used | Decision points | Failure codes | Increment | Status | Waiting on |
|---|---|---|---|---|---|---|---|
| **R1** Gel applied twice | Gel is applied twice, as two separate applications at least a minimum gap apart, within the approved period. Order versus paddle placement is not checked (D-018) | gel applied (every occurrence) | P-014, P-008 | `missing`, `applied_once`, `outside_time_period` | 17 | pending | OQ-016 (period), OQ-021 (more than twice), OQ-018 (gap) |
| **R2** Second paddle taken after the first is placed | First paddle taken → first paddle placed firmly → second paddle taken (D-051) | first paddle taken, first placement, second paddle taken | P-014, P-012, P-008 | `simultaneous`, `taken_before_first_placed`, `first_missing` | 11 | pending | OQ-008 (tag dropped from timelines), OQ-022 |
| **R8** Apical before sternal | Apical placed before sternal. With one zone visible, inferred from the first placement (D-013); inferred mistakes undecided (D-015); a missing placement gives Unable to Verify, `placement_missing` (D-058); the apical-first fallback gives an assumed result that blocks an overall Pass (D-060) | apical and sternal placements, first placement, zone visibility | P-015, P-012, P-007 | `wrong_order`, `simultaneous` | 12 | pending | OQ-004, OQ-005, OQ-006, OQ-007, OQ-015 |
| **R3** Paddles firmly on chest | Both paddles stable in their zones before the shock; otherwise (direct evidence weak or missing, D-057) Pass – Inferred if the shock on screen or the paddle removal is confirmed | paddles firmly on chest, shock time | P-016, P-009, P-008 | `not_in_zone`, `placed_after_shock` | 15 | pending | OQ-012, OQ-022 |
| **R4** Both discharge buttons pressed | Both buttons pressed after placement and before the shock; otherwise (weak or missing, D-057) inferred as for R3 | buttons pressed, placement, shock time | P-016, P-009, P-008 | `before_placement`, `not_pressed` | 16 | pending | OQ-023 |
| **R5** Shock confirmed on screen | One new shock indication after the preceding steps | shock on screen | P-009, P-005, P-014 | `missing`, `wrong_order` | 13 | pending | OQ-013 |
| **R6** Paddles removed after shock | Removal after the shock | paddle removal, shock time | P-009, P-014, P-008 | `removed_before_shock`, `missing` | 14 | pending | OQ-016 (limit, if any) |
| **A1** Oxygen away | Command given before the shock | oxygen-away command, shock time | P-010, P-014, P-008 | `missing`, `after_shock` | 18 | pending | OQ-010 |
| **A2** Continue compressions | Command given during preparation, before "stop" (A4 owns stop-before-continue, D-027) | continue command (including resolved "resume"), stop time | P-011, P-012, P-008 | `missing`, `wrong_stage` | 19 | pending | OQ-009, OQ-010 |
| **A3** All stand clear | Command given before the shock | stand-clear command, shock time | P-010, P-014, P-008 | `missing`, `after_shock` | 18 | pending | OQ-010 |
| **A4** Stop compressions | Command before the shock, after "continue" | stop command, continue time, shock time | P-012, P-010, P-008 | `missing`, `after_shock`, `wrong_order` | 19 | pending | OQ-009, OQ-010, OQ-016 |
| **A5** Shock command | Verbal shock command before or at the shock | shock command, shock time | P-010, P-014, P-008 | `missing` | 20 | pending | OQ-009, OQ-010, OQ-016 |
| **R7** Compressions restarted promptly | The restart command (the earliest start after the shock, D-025) within the approved delay. If a start or "resume" command is timing-ambiguous (D-053, D-059), Unable to Verify, not Fail. Under the removal fallback, a delay from the removal already over the limit is Fail `too_late`; within it, Unable to Verify (D-059) | restart time, shock time | P-012, P-011, P-009, P-008 | `missing`, `before_shock`, `too_late` | 21 | pending | OQ-016, OQ-009 |
| **A6** Start or resume compressions promptly | The same check as R7, reported under A6 (D-044) | as R7 | as R7 | as R7 | 21 | pending | as R7 |
| **A7** Command sequence | Order: oxygen away → continue → stand clear → stop → shock → start. A missing command is "not evaluable because of Ax" (D-027); a start before a confirmed on-screen shock is a sequence problem (D-025), but a timing-ambiguous one is not (D-053, D-054) | all commands; results of A1–A5 | P-014, P-011, P-012 | `wrong_order` | 22 | pending | OQ-010 |
| **A8** Pre-shock pause | "Stop CPR" to the restart within **5 s** (approved, D-016). If the restart is timing-ambiguous, Unable to Verify (D-053, D-059). Under the removal fallback with an unambiguous restart, measured normally (D-059) | stop time, restart time | P-012, P-008 | `pre_shock_pause` | 23 | pending | OQ-009, OQ-015 |

## What is built so far (Increments 0–9a, Steps 9b and 9c)

Everything every rule will rely on is built and tested:
- **Preparation:** P-002 to P-005.
- **Coverage:** P-006 to P-008.
- **Procedure context:** P-009 to P-013.
- **Rule outcome and shared checks:** `RuleOutcome`, plus P-019 to P-025 (the steps of the rule
  ladder, Increment 6).
- **Rule registry and runner:** P-026 (Increment 7). Every rule is evaluated in dependency order;
  pending rules are reported as pending, A6 reuses R7, and a crashing rule is recorded as
  `engine_error` (D-063).

- **Overall result:** P-017 (Increment 8). With every rule pending, the overall result is
  "Incomplete: rules not yet approved for R1, R2, …, R7/A6, A7, A8".
- **JSON report and command line:** P-027 (Increment 9). `python -m rules.run --events <file>`
  writes the report. Its structure, and every result, flag and code the feedback module may
  receive, are in the versioned [output contract](output_contract.md) (D-070).
- **Event counts and paddle identity:** P-005 (Increment 9a, D-071). An event expected once that
  appears more than once, or a swapped paddle identity, is flagged for review. It is never a
  Fail by itself. A rule may fail on a repeated action only once the supervisor decides that it
  is a mistake (OQ-021 to OQ-023).
- **Annotation export and audit:** P-028 and P-029 (Step 9b, D-074). The rule engine reads the
  CVAT backups through its own exporter. Records contain every tag, the duration and zone
  visibility. A separate audit lists annotation problems for review. The training pipeline is
  untouched.

- **Derived per-paddle placements:** P-031 (Step 9c, D-081, D-086 to D-089). The exporter derives
  `apical_paddle_placed` / `sternal_paddle_placed` from the annotated boxes. When the annotators
  didn't tag a first placement and both paddles went on together, they are flagged
  `possible_parallel_placement`.

**For R2 and R8:** R8 may use derived placements only after Arnikan has reviewed the validation
report of the final export, and recorded that export and its settings (the gate, D-088). A
possible parallel placement is enough for R2 and R8 to Fail with `simultaneous` once the gate is
approved (D-091).

No individual rule is built yet, so all 16 still report "pending". Next: the annotation input
adapter (Increment 10).
