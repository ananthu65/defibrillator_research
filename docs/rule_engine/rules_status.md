# Rule engine: status of each rule

One row per rule, in report (display) order. **Status:** `pending` (not built), `built` (code
exists), `tested` (built and covered by the scenario tests). Every rule is also `pending` in
`configs/rules.yaml` until the supervisor approves its definition, and it is not counted until
then (D-043).

Shared steps used by every rule: P-014 (rule decision ladder) and P-008 (what a missing event
means). Failure codes are listed in [anomalies.md](anomalies.md).

| Rule | Logic in plain words | Events and key times used | Decision points | Failure codes | Increment | Status | Waiting on |
|---|---|---|---|---|---|---|---|
| **R1** Gel applied twice | Gel once on each placement zone (either order) before the paddles are placed (D-109, D-110). Gel only after the first placement → `after_placement`. Past the 9d gate, per zone: both gelled → Pass, one → `applied_once`, neither → `missing`, unknown → Unable to Verify. Before it, the tag-count proxy: separate tags against the zones' visibility in the gel phase (D-113, A-026). Period unset → `timing_not_checked` | gel applied tags, per-zone gel applications (past the 9d gate), the gel regions, first placement, zone visibility in the gel phase | P-038, P-037, P-024, P-007 | `after_placement`, `applied_once`, `missing`, `outside_time_period` | 17 | **implemented** (Increment 17); pending until the supervisor confirms its definition | OQ-016 (period), OQ-021 (more than twice), OQ-018 (9d settings, gap) |
| **R2** Second paddle taken after the first is placed | First paddle taken → first paddle placed firmly → second paddle taken (D-051) | first paddle taken, first placement, second paddle taken; zone coverage over that window; derived placements past the gate | P-032, P-012, P-007 | `simultaneous`, `taken_before_first_placed`, `first_placement_not_observed` (D-097) | 11 | **implemented** (Increment 11); pending until the supervisor confirms its definition | OQ-022 |
| **R8** Apical before sternal | Apical placed before sternal, judged only when both placements are observed. With one zone visible, Unable to Verify, `one_zone_in_view`: no inference, because the first-placement tag is the apical placement under the team's labelling (A-027, D-116); a missing placement gives Unable to Verify, `placement_missing` (D-058); the apical-first fallback gives an assumed result that blocks an overall Pass (D-060) | apical and sternal placements (derived ones past the gate), zone coverage over the placement phase (D-099) | P-015, P-012, P-007 | `wrong_order`, `simultaneous` (a parallel placement, with the cause flag shared with R2, D-098) | 12 | **implemented** (Increment 12); pending until the supervisor confirms its definition | OQ-004, OQ-006, OQ-015, OQ-059 |
| **R3** Paddles firmly on chest | Paddles firmly on chest at or before the shock on the screen, or (past the gate) both derived placements before it → Pass – Direct; only after the shock → `placed_after_shock`. Otherwise Pass – Inferred if the shock on screen is confirmed; a paddle removal never infers (D-115). Then no shock time → Not evaluable because of R5; a missing tag fails only if both zones were visible from first paddle taken to the shock (the tag isn't made with one paddle visible, A-019). **Placement timing and presence only** until the chest regions are approved (D-106) | paddles firmly on chest, derived placements, shock time, `inference_sources`, zone coverage over the placement phase | P-035, P-016, P-009, P-007 | `placed_after_shock`, `missing` (D-106; unreachable while the shock is an inference source, OQ-061); `not_in_zone` not produced until OQ-012 | 15 | **implemented** (Increment 15); pending until the supervisor confirms its definition | OQ-012, OQ-022, OQ-061 |
| **R4** Both discharge buttons pressed | Both buttons pressed after the placement (the firm-placement tag, or past the gate the later derived placement) and at or before the shock → Pass – Direct; clearly before the placement → `before_placement`. Otherwise inferred from the shock on screen as for R3; never from a removal (D-115). Then no shock time → Not evaluable because of R5; no press fails `not_pressed` only if both paddles were visible from the placement to the shock (unreachable while the shock is an inference source). Repeated presses undecided (OQ-023) (D-108) | buttons pressed, placement, shock time, `inference_sources`, paddle visibility (regions `apical_paddle`, `sternal_paddle`) | P-036, P-016, P-009, P-007 | `before_placement`, `not_pressed` | 16 | **implemented** (Increment 16); pending until the supervisor confirms its definition | OQ-023, OQ-061 |
| **R5** Shock confirmed on screen | One new shock indication after the preceding steps (a setting, unset until OQ-013: presence only, `order_not_checked`, D-100); a missing shock fails only if the screen was visible throughout paddles firmly on chest → paddles removed (D-101) | shock on screen, preceding steps, screen coverage | P-033, P-005, P-007 | `missing`, `wrong_order` | 13 | **implemented** (Increment 13); pending until the supervisor confirms its definition | OQ-013 |
| **R6** Paddles removed after shock | Removal after the shock on the screen; within `removal_before_screen_tolerance_seconds` before it counts as at the shock (the screen may lag the discharge, D-105). A removal doesn't prove a shock, so without a shock time R6 is Not evaluable because of R5. Past the gate, a derived placement ending before the shock is also `removed_before_shock`. A missing removal fails only if both placement zones were visible from the shock to the end of the recording. The removal limit is unset (`timing_not_checked`); the answer may be "no limit" (D-103, D-104) | paddle removal, shock time (screen only), derived placements with their end, placement zone coverage after the shock | P-034, P-009, P-024, P-007 | `removed_before_shock`, `missing`, `too_late` (only with an approved limit) | 14 | **implemented** (Increment 14); pending until the supervisor confirms its definition | OQ-016 (limit, or no limit), OQ-057 |
| **A1** Oxygen away | Command given before the shock. Any time limit is for the supervisor, and the answer may be "no limit" (D-103) | oxygen-away command, shock time | P-010, P-014, P-008 | `missing`, `after_shock` | 18 | pending | OQ-010, OQ-016 |
| **A2** Continue compressions | Command given during preparation, before "stop" (A4 owns stop-before-continue, D-027) | continue command (including resolved "resume"), stop time | P-011, P-012, P-008 | `missing`, `wrong_stage` | 19 | pending | OQ-009, OQ-010 |
| **A3** All stand clear | Command given before the shock. Any time limit is for the supervisor, and the answer may be "no limit" (D-103) | stand-clear command, shock time | P-010, P-014, P-008 | `missing`, `after_shock` | 18 | pending | OQ-010, OQ-016 |
| **A4** Stop compressions | Command before the shock, after "continue" | stop command, continue time, shock time | P-012, P-010, P-008 | `missing`, `after_shock`, `wrong_order` | 19 | pending | OQ-009, OQ-010, OQ-016 |
| **A5** Shock command | Verbal shock command before or at the shock | shock command, shock time | P-010, P-014, P-008 | `missing` | 20 | pending | OQ-009, OQ-010, OQ-016 |
| **R7** Compressions restarted promptly | The restart command (the earliest start after the shock, D-025) within the approved delay. No shock time (the screen only, never the removal, D-115) → Not evaluable because of R5 | restart time, shock time | P-012, P-011, P-009, P-008 | `missing`, `before_shock`, `too_late` | 21 | pending | OQ-016, OQ-009 |
| **A6** Start or resume compressions promptly | The same check as R7, reported under A6 (D-044) | as R7 | as R7 | as R7 | 21 | pending | as R7 |
| **A7** Command sequence | Order: oxygen away → continue → stand clear → stop → shock → start. A missing command is "not evaluable because of Ax" (D-027); a start before a confirmed on-screen shock is a sequence problem (D-025), but a timing-ambiguous one is not (D-053, D-054) | all commands; results of A1–A5 | P-014, P-011, P-012 | `wrong_order` | 22 | pending | OQ-010 |
| **A8** Pre-shock pause | "Stop CPR" to the restart within **5 s** (approved, D-016). If the restart is timing-ambiguous (no shock time, D-054), Unable to Verify | stop time, restart time | P-012, P-008 | `pre_shock_pause` | 23 | pending | OQ-009, OQ-015 |

## What is built so far (Increments 0–17, with 9a to 9d)

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
  shock time, and shock-dependent rules are Not evaluable. A paddle removal never stands in for
  the shock, and there is no fallback (D-115). Which rules each camera view can check:
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
- **R3/R4 inference sources:** a setting in `rules.yaml`: the shock on the screen only (D-115).
  R3/R4 themselves are Increments 15-16.

- **R6 screen delay (D-105):** R6 tolerates a removal shortly before the shock appears on the
  screen, with its own placeholder setting `removal_before_screen_tolerance_seconds` (0.5 s).
- **R3 (Increment 15, P-035):** implemented and tested; pending until the supervisor confirms its
  definition. It checks placement timing and presence only until the chest regions are approved
  (OQ-012, D-106).

- **No inference from the paddle removal (D-115, 2026-10-19):** a removal doesn't show that a
  shock was delivered, so it is neither a shock time nor an R3/R4 inference source. R3/R4 infer only
  from the shock on the screen; while it is listed, R3's `missing` and R4's `not_pressed` can't be
  reached (OQ-061).
- **R4 (Increment 16, P-036):** implemented and tested; pending until the supervisor confirms its
  definition. The exporter and adapter now give each paddle's visibility (D-108).

- **Derived gel applications (Step 9d, P-037):** the exporter derives a gel application per zone
  from the `learner_hand` and zone boxes, with each zone's status and its own gate (D-111, D-112).
  It needs a re-export with exporter version 3.
- **R1 (Increment 17, P-038):** implemented and tested; pending until the supervisor confirms its
  definition. Gel once on each zone, before the placement (D-109, D-110); per zone past the 9d
  gate, the tag-count proxy before it (D-113).

All 16 rules still report "pending" (R1 to R6 and R8 are implemented but not yet approved). On
the interim annotation data the engine gives Incomplete, marked as development data. Next: the
audio rules, A1 and A3 (Increment 18).
