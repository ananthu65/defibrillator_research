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
| **R2** Second paddle taken after the first is placed | First paddle taken → first paddle placed firmly → second paddle taken (D-051) | first paddle taken, first placement, second paddle taken; zone coverage over that window; derived placements past the gate | P-032, P-012, P-007 | `simultaneous`, `taken_before_first_placed`, `first_placement_not_observed` (D-097) | 11 | **implemented** (Increment 11); pending until the supervisor confirms its definition | OQ-022 |
| **R8** Apical before sternal | Apical placed before sternal. With one zone visible, inferred from the first placement (D-013); inferred mistakes undecided (D-015); a missing placement gives Unable to Verify, `placement_missing` (D-058); the apical-first fallback gives an assumed result that blocks an overall Pass (D-060) | apical and sternal placements (derived ones past the gate), first placement, zone coverage over the placement phase (D-099) | P-015, P-012, P-007 | `wrong_order`, `simultaneous` (a parallel placement, with the cause flag shared with R2, D-098) | 12 | **implemented** (Increment 12); pending until the supervisor confirms its definition | OQ-004, OQ-005, OQ-006, OQ-015, OQ-059 |
| **R3** Paddles firmly on chest | Both paddles stable in their zones before the shock; otherwise (direct evidence weak or missing, D-057) Pass – Inferred if an event in `inference_sources` is confirmed: the shock on screen or the paddle removal (the proposal, kept although paddles are sometimes removed without a successful shock, D-102, A-021) | paddles firmly on chest, shock time; `inference_sources` | P-016, P-009, P-008 | `not_in_zone`, `placed_after_shock` | 15 | pending | OQ-012, OQ-022, OQ-060 |
| **R4** Both discharge buttons pressed | Both buttons pressed after placement and before the shock; otherwise (weak or missing, D-057) inferred as for R3 (D-102) | buttons pressed, placement, shock time; `inference_sources` | P-016, P-009, P-008 | `before_placement`, `not_pressed` | 16 | pending | OQ-023, OQ-060 |
| **R5** Shock confirmed on screen | One new shock indication after the preceding steps (a setting, unset until OQ-013: presence only, `order_not_checked`, D-100); a missing shock fails only if the screen was visible throughout paddles firmly on chest → paddles removed (D-101) | shock on screen, preceding steps, screen coverage | P-033, P-005, P-007 | `missing`, `wrong_order` | 13 | **implemented** (Increment 13); pending until the supervisor confirms its definition | OQ-013 |
| **R6** Paddles removed after shock | Removal after the shock on the screen; within the simultaneous window before it counts as at the shock. A removal doesn't prove a shock, so without a shock time R6 is Not evaluable because of R5. Past the gate, a derived placement ending before the shock is also `removed_before_shock`. A missing removal fails only if both placement zones were visible from the shock to the end of the recording. The removal limit is unset (`timing_not_checked`); the answer may be "no limit" (D-103, D-104) | paddle removal, shock time (screen only), derived placements with their end, placement zone coverage after the shock | P-034, P-009, P-024, P-007 | `removed_before_shock`, `missing`, `too_late` (only with an approved limit) | 14 | **implemented** (Increment 14); pending until the supervisor confirms its definition | OQ-016 (limit, or no limit), OQ-057 |
| **A1** Oxygen away | Command given before the shock. Any time limit is for the supervisor, and the answer may be "no limit" (D-103) | oxygen-away command, shock time | P-010, P-014, P-008 | `missing`, `after_shock` | 18 | pending | OQ-010, OQ-016 |
| **A2** Continue compressions | Command given during preparation, before "stop" (A4 owns stop-before-continue, D-027) | continue command (including resolved "resume"), stop time | P-011, P-012, P-008 | `missing`, `wrong_stage` | 19 | pending | OQ-009, OQ-010 |
| **A3** All stand clear | Command given before the shock. Any time limit is for the supervisor, and the answer may be "no limit" (D-103) | stand-clear command, shock time | P-010, P-014, P-008 | `missing`, `after_shock` | 18 | pending | OQ-010, OQ-016 |
| **A4** Stop compressions | Command before the shock, after "continue" | stop command, continue time, shock time | P-012, P-010, P-008 | `missing`, `after_shock`, `wrong_order` | 19 | pending | OQ-009, OQ-010, OQ-016 |
| **A5** Shock command | Verbal shock command before or at the shock | shock command, shock time | P-010, P-014, P-008 | `missing` | 20 | pending | OQ-009, OQ-010, OQ-016 |
| **R7** Compressions restarted promptly | The restart command (the earliest start after the shock, D-025) within the approved delay. If a start or "resume" command is timing-ambiguous (D-053, D-059), Unable to Verify, not Fail. Under the removal fallback, a delay from the removal already over the limit is Fail `too_late`; within it, Unable to Verify (D-059) | restart time, shock time | P-012, P-011, P-009, P-008 | `missing`, `before_shock`, `too_late` | 21 | pending | OQ-016, OQ-009 |
| **A6** Start or resume compressions promptly | The same check as R7, reported under A6 (D-044) | as R7 | as R7 | as R7 | 21 | pending | as R7 |
| **A7** Command sequence | Order: oxygen away → continue → stand clear → stop → shock → start. A missing command is "not evaluable because of Ax" (D-027); a start before a confirmed on-screen shock is a sequence problem (D-025), but a timing-ambiguous one is not (D-053, D-054) | all commands; results of A1–A5 | P-014, P-011, P-012 | `wrong_order` | 22 | pending | OQ-010 |
| **A8** Pre-shock pause | "Stop CPR" to the restart within **5 s** (approved, D-016). If the restart is timing-ambiguous, Unable to Verify (D-053, D-059). Under the removal fallback with an unambiguous restart, measured normally (D-059) | stop time, restart time | P-012, P-008 | `pre_shock_pause` | 23 | pending | OQ-009, OQ-015 |

## What is built so far (Increments 0–14, with 9a, 9b and 9c)

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

- **Annotation adapter:** P-001 and P-030 (Increment 10). Exporter records become timelines with
  a header (duration, analyses run, zone coverage and visible intervals). Results are marked as
  development data. A zone visible for only part of the recording is judged per time window
  (D-092). For example, a placement expected while the zone was out of view gives Unable to
  Verify, never a Fail. Derived placements reach the engine only past the gate (D-088).

- **Shock time only from the screen (D-093):** without a shock seen on the screen there is no
  shock time, and shock-dependent rules are Not evaluable. The removal fallback is kept behind
  `shock_time_fallback: removal`. Which rules each camera view can check:
  [camera_angle_evidence.md](camera_angle_evidence.md) (interim).
- **Screen coverage for R5 (D-094):** a missing shock on screen while the screen is out of view is
  Unable to Verify, never Fail.
- **R2 (Increment 11, P-032):** implemented and tested. It reports "pending" until it is approved
  in `rules.yaml`.

- **R8 (Increment 12, P-015):** implemented and tested; pending until the supervisor confirms its
  definition. A parallel placement fails **both R2 and R8** with `simultaneous`, each carrying the
  cause flag `possible_parallel_placement`, so the feedback can explain that one action caused
  both (D-098; one or two mistakes: OQ-059).

- **R5 (Increment 13, P-033):** implemented and tested; pending until the supervisor confirms its
  definition. Until the preceding steps are set (OQ-013), it checks presence only, and the
  overall result cannot be Pass (D-100).

- **R6 (Increment 14, P-034):** implemented and tested; pending until the supervisor confirms its
  definition. A removal is judged against the shock on the screen; it doesn't prove a shock
  (D-104). The removal limit is unset, so a Pass is flagged `timing_not_checked`.
- **"No limit" (D-103):** a clinical value can record an approved `no_limit: true`. The rule then
  passes fully on presence and order. `null` still means "not decided yet".
- **R3/R4 inference sources (D-102):** a setting in `rules.yaml`, following the proposal (shock on
  screen or removal). R3/R4 themselves are Increments 15-16.

All 16 rules still report "pending" (R2, R8, R5 and R6 are implemented but not yet approved). On
the interim annotation data the engine gives Incomplete, marked as development data. Next: R3
(Increment 15).
