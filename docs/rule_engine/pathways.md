# Rule engine: decision pathways

The readable version of [decision_flow.yaml](decision_flow.yaml). The first part lists, stage by
stage, every decision point (P-xxx) with its conditions, outcomes and flags. The second part
follows **worked pathways**: complete routes from a timeline to a result. New worked pathways
are added as rules are built. Diagrams of the same logic: [diagrams.md](diagrams.md). Every code
is explained in [anomalies.md](anomalies.md).

**Built** means implemented and tested; **planned** means designed but not yet built.

---

## Part 1: decision points by stage

### Stage: annotation export (Step 9b; separate from the training pipeline, D-074)

#### P-028 Annotation export (built)
`annotation/export_rule_engine_records.py` reads the CVAT backups directly. It writes
`data/rule_engine/annotation_export/<run>/records.jsonl`. No file of the training pipeline changes.

| Condition | Outcome | Export issue |
|---|---|---|
| Task found; its video is in `video_conversion.csv` | One record: every tag under its CVAT name, with frame and seconds (`frame / fps`); frame range; `duration_seconds = (stop_frame + 1) / fps`; zone tracks; zone visibility intervals | — |
| Video missing from the conversion report | No record (D-076) | `fps_missing` |
| Frame count differs from the report | Record written | `frame_count_mismatch` |
| Zone track | Visible on exactly the frames where the training dataset has a box for it (D-079); runs merged across tracks and jobs | — |
| Zone drawn as a single-frame shape | Not converted | `zone_shape_without_track` |
| Same task in two archives | The first copy kept | `duplicate_task` |
| Output inside `data/video/`, or not empty | Refused; nothing written | — |

#### P-029 Annotation audit (built)
`annotation/audit_rule_engine_checks.py` writes `annotation/reports/rule_engine_audit/<run>/`.

| Condition | Result | Code |
|---|---|---|
| Two or more boxes of one paddle label on a frame | Review list | `duplicate_paddle_box` |
| Zone centre moves more than 5% of the frame diagonal | Review list, naming any paddle it overlaps | `zone_moves_like_paddle` |
| Same tag twice within 15 frames | Review list: possibly the same incident tagged twice | `repeated_incident_tag` |
| Zone tracks differ from the view's usual pattern (missing ones not excused by a reviewed exception, or unexpected ones), including no zone | Review list; the pattern never affects a result (D-082) | `zone_pattern_off` |
| Reviewed exception for a zone that is visible | Review list | `zone_exception_contradicted` |
| Learner order; same tag further apart; no first-placement tag; never-visible zone track; confirmed exception | **Information only** | `tag_sequence`, `repeated_tag`, `first_placement_tag_missing`, `zone_track_never_visible`, `zone_exception_confirmed` |

#### P-031 Derived per-paddle placement (planned, Step 9c, D-081)
| Condition | Outcome | Notes |
|---|---|---|
| Paddle box inside its zone (overlap ≥ 0.5), steady for 5 frames (centre < 2% of the diagonal), agreeing with the tags within 15 frames | `apical_paddle_placed` / `sternal_paddle_placed`, one per placement episode | Direct evidence, flagged `derived_placement`, method in metadata |
| Zone has no track, paddle has two boxes, or disagreement with the tags | No event | Export issue |
| Validation report not yet reviewed (needs the final backups) | R8 does not use derived placements | — |

### Stage: adapter

#### P-001 Annotation timeline adapter (planned, Increment 10)
| Condition | Outcome | Flags |
|---|---|---|
| An exporter record is converted (D-074) | Events, plus a header saying video was analysed and audio was not | `annotation_coverage_assumed` on every result |
| Zone coverage per region | → P-030 | — |

#### P-030 Zone coverage for an annotated recording (planned, Increment 10)
| Condition | Coverage of the region | Decision |
|---|---|---|
| Annotator confirmed the zone was genuinely not visible (reviewed exception) | **not covered** | D-082 |
| Zone track present and visible on some frames | **covered** | D-074 |
| Zone track present but outside on every frame | **not covered** | D-080 |
| No zone track | **unknown** | D-074 |

The view's usual zone pattern plays no part here (D-082).

### Stage: preparation

#### P-002 Timeline validation (built)
| Condition | Outcome | Code |
|---|---|---|
| Not a list of events | Rejected; no assessment | `not_a_list` |
| An item is not a shared event record | Rejected | `not_an_event` |
| An event has no ID | Rejected | `missing_event_id` |
| Two events share an ID | Rejected | `duplicate_event_id` |
| More than one camera angle (audio, which has no angle, is ignored) | Rejected | `multiple_camera_angles` |
| More than one recording | Rejected | `multiple_recordings` |
| Otherwise (an empty timeline is fine) | Accepted → P-003 | — |

#### P-003 Vocabulary mapping (built)
| Condition | Outcome | Code |
|---|---|---|
| Label known for its source | Renamed to the agreed name; original kept → P-004 | — |
| Ambiguous label ("resume compressions") | Kept; resolved later by its position relative to the shock → P-011 | — |
| Known but unused (raw object detections) | Kept, ignored by rules | — |
| Not in the vocabulary | Kept but cannot count as evidence; warning | `unknown_labels_present` |

#### P-004 Confidence exclusion (built)
| Condition | Outcome | Code |
|---|---|---|
| The source has no threshold | Rejected | `no_confidence_threshold` |
| Confidence at or above the threshold (0 disables the check) | Used as evidence → P-005 | — |
| Below the threshold | Set aside; never used as evidence, but never treated as absence (D-010) | (see P-008) |

#### P-005 Anomaly detection (built)
| Condition | Outcome | Code |
|---|---|---|
| More than one confident shock | Anomaly; "possibly the same shock detected twice" if within the window; not merged → P-009 | `multiple_shocks` |
| One event reported by both a human tag and a model | Flag only | `mixed_evidence_sources` |
| Any unknown label | Warning listing the labels | `unknown_labels_present` |
| At least one confident event, count outside its expected range (D-071) | Anomaly naming the event, expected and found counts and the event IDs; never a Fail by itself | `count_violation` |
| Same, event limited to one, an extra event within the simultaneous window | Pair marked "possibly the same incident detected twice" | `count_violation` |
| No confident event of that name | No count anomaly; a missing event → P-008 (A-018) | — |
| Count unlimited (commands) or undecided (gel, buttons, paddles firmly on chest) | Not checked | — |
| Two or more apical placements and no sternal, or the reverse | Anomaly: the paddle identity may have been swapped or lost | `paddle_identity_conflict` |

Both count codes are review anomalies: the overall result is never Pass (D-072).

### Stage: coverage

#### P-006 Header validation (built)
| Condition | Outcome | Code |
|---|---|---|
| No header | Accepted; all coverage unknown → P-007 | — |
| Malformed header | Rejected | `invalid_header` |
| Header contradicts the events (camera, recording, an event ending more than 0.5 s after the stated duration, "audio did not run" but audio events exist) | Rejected | `header_mismatch` |
| Valid | Accepted → P-007 | — |

#### P-007 Coverage status lookup (built)
The most specific information wins.

| Condition | Coverage |
|---|---|
| No header | unknown |
| Header states coverage for the event's camera region (apical or sternal zone) | that status |
| Header states coverage for the event's source | that status |
| Header states coverage for the modality, or says whether that analysis ran | covered (ran) / not covered (did not run) / the stated status |
| Nothing stated | unknown |

#### P-008 Missing-event outcome (built)
| Condition | Outcome | Flags |
|---|---|---|
| A low-confidence detection of the event exists | **Unable to Verify, never Fail** | `low_confidence_evidence` |
| Coverage: covered | **Fail** | — |
| Coverage: not covered | Unable to Verify | — |
| Coverage: unknown | Unable to Verify (interim, D-008) | `coverage_policy_undecided` |

Each outcome can be overridden per region, source or modality in `engine.yaml`, except the
low-confidence rule.

### Stage: context

#### P-009 Shock time (built)
| Condition | Outcome | Flags |
|---|---|---|
| Two or more shocks | No shock time (not guessed) | `multiple_shocks` |
| One shock on screen | Shock time = the shock | — |
| No shock on screen, but a paddle removal | Shock time = first removal; every timing result using it is flagged | `shock_time_from_removal` (+ `multiple_candidates` if several removals) |
| Neither | No shock time | `no_shock` |

#### P-010 Phase of a time (built)
| Condition | Phase |
|---|---|
| No shock time | none |
| Earlier than the shock | before the shock |
| Same moment | at the shock |
| Later | after the shock |

#### P-011 Command resolution (built): what "resume compressions" means
| Condition | Outcome | Flags |
|---|---|---|
| No shock time | Unresolved | `no_shock_time` |
| Shock time from removal, command before the removal | Unresolved (D-024) | `command_before_removal`, `shock_time_from_removal` |
| Within 0.5 s of the shock | Unresolved | `command_near_shock` |
| Before the shock | "Continue compressions" | — |
| After the shock | "Start compressions" | `shock_time_from_removal` under the fallback |

#### P-012 Anchor selection (built): which event gives each key time
| Condition | Outcome | Flags |
|---|---|---|
| One candidate | Its time | — |
| Several candidates | The earliest; all recorded | `multiple_candidates` |
| Only a low-confidence candidate | Absent | `low_confidence_evidence` |
| No candidate | Absent, with a reason | — |
| A start command at or before a confirmed on-screen shock | Not the restart (D-025); a mistake A7 reports | `start_command_before_shock` |
| Shock time from removal, and a start command at or before the removal, or an unresolved "resume" before it | Timing-ambiguous: not the restart, **not a mistake** (D-053, D-059); a later start is still used, but stays flagged | `command_before_removal`, `shock_time_from_removal` |
| Shock time from removal, no start or unresolved "resume" before the removal | The first start after the removal is definitely the restart; no fallback flag on the restart itself (D-059) | — |
| No shock time (start only) | No restart time; start commands are ambiguous, not mistakes (D-054) | `no_shock_time` |

Each start command is checked on its own, so a later start can still be the restart when an
earlier one does not count.
| A "resume" command is unresolved | Continue and start times may be incomplete | `unresolved_commands` |

#### P-013 Low-confidence ambiguous command (built)
| Condition | Outcome | Flags |
|---|---|---|
| A weak "resume compressions" would mean this event, or cannot be resolved | The missing event is Unable to Verify | `low_confidence_evidence` |
| It would mean the other command | Not evidence → P-008 | — |

### Stage: rule — runner (built, Increment 7)

#### P-026 Rule runner
Runs every rule in evaluation order (dependencies first) and reports in display order. When the
engine loads, it first checks that the registered rules match `rules.yaml`. Any mismatch stops the
run with a clear error, and no assessment is produced (D-064).

| Condition | Outcome |
|---|---|
| (At load) a rule is approved but has no implementation | **Rejected**: `approved_rule_not_registered` (an error, not "pending") |
| (At load) a registered rule ID is not in the full catalogue `configs/rules.yaml` (whatever config is assessed) | **Rejected**: `registered_rule_not_in_config` (probably a typo in the ID) |
| A registered rule the assessed config leaves out (e.g. a one-rule test config) | Not run; not an error |
| (At load) two different functions registered for one rule ID | **Rejected**: `duplicate_rule_registration`, naming both locations |
| (At load) a rule requires an event that is not in the vocabulary | **Rejected**: `unknown_required_event` |
| Rule disabled in configuration | Not reported |
| Rule not approved | **Pending** (reported; the overall result cannot be Pass) |
| Rule reuses another's check (A6 = R7) | That rule's outcome, under this ID |
| A rule it depends on did not pass | **Not evaluable because of** that rule (P-019) |
| The rule returns a valid outcome | That outcome (its ladder starts at P-020) |
| The rule **raises an error** or returns something invalid | **`engine_error`** with the message; every other rule still runs; dependents not evaluable; overall incomplete (D-063) |
| A shared-contract rule (`module:function`) breaks the contract | The run stops (shared contract) |

### Stage: rule — shared checks (built, Increment 6)

The building blocks every rule uses, in the order of the ladder (P-014, diagram c). Each one
either gives the rule's result or says "go on". Every result carries the flags of the anchors,
elapsed times and checks it used.

#### P-019 Rule-result dependency
| Condition | Outcome |
|---|---|
| Every rule it depends on passed | Go on → P-020 |
| One failed, was Unable to Verify, Not evaluable, pending or assumed | **Not evaluable because of that rule** |

#### P-020 Required facts
| Condition | Outcome | Flags |
|---|---|---|
| The needed key time exists (e.g. the shock time) | Go on → P-021 | — |
| It does not | **Not evaluable because of** the step that provides it (e.g. R5) | the key time's flags (e.g. `multiple_shocks`) |

#### P-021 Restart ambiguity (R7/A6, A8)
| Condition | Outcome | Flags |
|---|---|---|
| A start or "resume" command is timing-ambiguous | **Unable to Verify, never Fail** | `command_before_removal` |
| None | Go on → P-022 | — |

#### P-022 Occurrences of the required event
| Condition | Outcome | Flags |
|---|---|---|
| **Any** occurrence is valid (repeats allowed) | **Pass – Direct**, citing the earliest valid one | carried |
| Occurrences exist, none valid, but a low-confidence one exists | **Unable to Verify** (it may have been the valid one) | `low_confidence_evidence` |
| Occurrences exist, none valid | **Fail** with the rule's code (e.g. `after_shock`) | carried |
| No occurrence | → P-023 | — |

#### P-023 Weak or missing evidence
| Condition | Outcome | Flags |
|---|---|---|
| The rule has an approved inference, and a supporting event is confirmed | **Pass – Inferred**, checked **before** coverage (D-057) | carried |
| Otherwise | The missing-event outcome (P-013 → P-008): Fail, or Unable to Verify | `low_confidence_evidence` / `coverage_policy_undecided` |

#### P-024 Time-limit check
| Condition | Outcome | Flags |
|---|---|---|
| No approved limit (null) | **Timing not checked**: presence and order only | `timing_not_checked` |
| A value without an approver | Not used; timing not checked (D-061) | `timing_not_checked`, `limit_not_approved` |
| The interval cannot be measured | Timing not checked | `timing_not_checked` |
| Within the limit (boundary included) | Pass | the elapsed time's flags |
| Over the limit | **Fail** with the rule's code (`too_late`, `pre_shock_pause`) | the elapsed time's flags |

#### P-025 Order of two times
| Condition | Relation |
|---|---|
| Either time absent | none |
| Within `simultaneous_window_seconds` (placeholder 0.5 s) | simultaneous |
| Earlier | before |
| Later | after |

### Stage: rule (planned)

#### P-014 Rule decision ladder (planned, Increments 6–7)
| Condition | Outcome |
|---|---|
| Rule not yet approved | Reported as pending; the overall result cannot be Pass (D-055) |
| A rule it depends on failed or was not evaluable | "Not evaluable because of …" |
| Required facts missing (e.g. no shock time) | "Not evaluable because of …", with the facts' flags |
| The restart is needed (R7/A6, A8), but a start or "resume" command is timing-ambiguous | **Unable to Verify, never Fail**; A7 does not report it (D-053, D-054, D-059) |
| R7/A6 under the removal fallback, no ambiguous start, delay **from the removal** already over the limit | **Fail `too_late`**: the real delay is even longer (D-059) |
| R7/A6 under the removal fallback, no ambiguous start, delay from the removal within the limit | Unable to Verify, `shock_time_from_removal`: the real delay may be over the limit (D-059) |
| A8 under the removal fallback, no ambiguous start | Stop → restart measured normally, without the fallback flag (D-059) |
| Evidence present, in order and in time | Pass – Direct |
| Evidence clearly shows the mistake | Fail, with the rule's failure code |
| Evidence weak **or missing**, and the rule has an approved inference (R3, R4) | → P-016, **before** the coverage step (D-057) |
| R8 order not directly observable | → P-015 |
| Required event missing, and no approved inference applies | → P-008 |

#### P-015 R8 inference (planned, Increment 12)
| Condition | Outcome | Codes |
|---|---|---|
| Both zones visible, both placements observed | Compare the two placement times | `wrong_order`, `simultaneous` |
| Both zones visible, one placement event missing | Unable to Verify, not `wrong_order`; R3 reports the missing placement (D-058) | `placement_missing` |
| One zone visible, its placement matches the first placement | That paddle was first (inferred) | `inferred_fail_policy_undecided` if it is the sternal one |
| One zone visible, its placement clearly after the first | The other paddle was first (inferred) | `inferred_fail_policy_undecided` if that means a mistake |
| One zone visible, its paddle has no placement event | Unable to Verify, no inference; R3 reports the missing placement (D-058) | `placement_missing` |
| The visible paddle placed clearly before the first placement | Unable to Verify | `contradictory` |
| Not determinable (no zone visible, or no first placement) | Unable to Verify; if the fallback is on: **assumed** apical first, to be checked by the evaluator, and the overall result cannot be Pass (D-060) | — |

#### P-016 R3/R4 inferred pass (planned, Increments 15–16)
| Condition | Outcome | Codes |
|---|---|---|
| Direct evidence in time | Pass – Direct | — |
| Direct evidence shows the mistake | Fail | `not_in_zone`, `placed_after_shock`, `before_placement`, `not_pressed` |
| Direct evidence weak **or missing**; shock on screen or removal confirmed | Pass – Inferred (D-057) | — |
| Neither | → P-008 | — |

### Stage: overall policy

#### P-017 Overall result (built, Increment 8)
Applied in this order:

| Step | Condition | Overall result | Flags |
|---|---|---|---|
| 1 | Any evaluated rule fails | **Fail** (D-001), listing every Fail and its code; R7/A6 once | `timeline_needs_review` if the timeline has a review anomaly (the Fail stays Fail) |
| 2 | No rule evaluated at all | **Incomplete** (D-068) | `no_rules_evaluated` |
| 2 | A rule is pending, assumed (R8 fallback), hit an engine error, or has timing not checked / limit not approved | **Incomplete**, listing each such rule and why (D-055, D-060, D-062, D-063) | — |
| 2 | The timeline has a review anomaly | **Incomplete**: "the timeline needs review (…)" (D-065), checked before the Unable-to-Verify setting so a data problem never fails a learner (D-069) | `timeline_needs_review` |
| 3 | Any Unable to Verify or Not evaluable | The `unable_to_verify_outcome` setting: **Fail** or **faculty review**; while undecided, **unable_to_verify** (OQ-002, D-056) | `overall_policy_undecided` while undecided |
| 4 | Every rule evaluated and passed, timing checked | **Pass** | — |
| any | A result carries `annotation_coverage_assumed` | Marked as **development data**, not a real assessment (D-066) | `development_data` |

The result explains itself (D-067): the rules that decided it, every named mistake, and the step
or setting that decided it.

### Stage: renderer

#### P-027 JSON report (built, Increment 9)
The report's structure, and every result, flag and code in it, is the versioned contract in
[output_contract.md](output_contract.md) (D-070).

| Condition | Outcome | Flags |
|---|---|---|
| An assessment was produced | Report: `report_version`, overall result and explanation, every enabled rule in display order, timeline, context, configuration | — |
| The overall result is development data | Top-level `development_data: true` (D-066) | `development_data` |
| No assessment (rejected configuration or timeline, unreadable file) | No report; `rules.run` prints the error and exits with code 2 | — |
| A report field or code is added, removed or renamed, or its meaning changes | `report_version` and output_contract.md change together, with a changelog line (D-070; OQ-045) | — |
| A planned code becomes built | Version unchanged; its status in the contract becomes built | — |

#### P-018 Checklist and feedback handover (planned, Increment 25)
| Condition | Outcome | Flags |
|---|---|---|
| Annotation timeline | Development flag on the checklist and every result | `annotation_coverage_assumed` |
| Model timeline | No development flag | — |

---

## Part 2: worked pathways

Times are seconds from the start of the recording. "→" means "goes to". The rule results are
what the planned rule will report once built; everything before them is built and tested
today.

### W-1 Audio analysed, "stand clear" never said → Fail
1. The header says audio was analysed (`analyses_run: {audio: true}`). There are no
   stand-clear events, confident or weak.
2. P-007: stand-clear coverage = **covered** (the audio ran).
3. P-008: covered + missing → **Fail**.
4. A3 (Increment 18) reports Fail `missing`.

### W-2 "Stand clear" heard at confidence 0.3 → Unable to Verify
1. P-004: 0.3 is below the audio threshold (0.5), so the event is set aside.
2. P-008: a low-confidence detection exists → **Unable to Verify**, `low_confidence_evidence`.
   This holds even if audio was analysed: low confidence is never absence (D-010).

### W-3 No timeline header, "stand clear" missing → Unable to Verify (interim)
1. P-006: no header → accepted. P-007: coverage **unknown**.
2. P-008: unknown → **Unable to Verify**, `coverage_policy_undecided` (D-008, OQ-001).

### W-4 Audio not analysed → Unable to Verify
1. The header says `analyses_run: {audio: false}`, and there are no audio events.
2. P-007: coverage **not covered**. P-008 → **Unable to Verify**. The learner is not blamed
   for missing data (D-004).

### W-5 No shock on screen, paddles removed at 52 s → timing flagged
1. P-009: no shock indication; first removal at 52 s → shock time **52 s**, flagged
   `shock_time_from_removal`.
2. "Start compressions" at 55 s, and none before the removal → P-012: the restart is
   **definitely** 55 s, so the restart itself carries no fallback flag (D-059).
3. Shock → restart = 3 s, flagged `shock_time_from_removal`. Removal comes after the real
   shock, so the real delay was **longer** than 3 s.
4. R7/A6 (Increment 21): see W-15 and W-16. A8 (Increment 23): see W-19.

### W-6 Under the removal fallback, "resume compressions" at 50 s
1. Shock time from removal at 52 s (W-5).
2. P-011: the command is before the removal → **unresolved**, `command_before_removal`
   (D-024). It counts as neither continue nor restart.
3. P-012: the continue and start anchors are flagged `unresolved_commands`.

### W-7 Two shocks 0.3 s apart → no shock time
1. P-005: two confident shocks → `multiple_shocks`, within the 0.5 s window ("possibly the
   same shock detected twice").
2. P-009: **no shock time** (not guessed). P-010: no phases. P-011: every "resume" command is
   unresolved (`no_shock_time`).
3. Shock-dependent rules (Increments 13–23) report "not evaluable because of R5", carrying
   the flags (D-003, D-039).

### W-8 "Resume compressions" before and after the shock
1. Shock on screen at 30 s.
2. P-011: "resume" at 10 s → **continue**; "resume" at 33 s → **start**.
3. P-012: the restart anchor is 33 s. A2 uses the continue command and R7/A6 the restart.

### W-9 "Resume compressions" 0.2 s after the shock
1. P-011: within 0.5 s of the shock → **unresolved**, `command_near_shock` (D-041).
2. P-012: the continue and start anchors are flagged `unresolved_commands`. If no other start
   command exists, the restart is absent, and the missing outcome comes from P-008.

### W-10 "Start compressions" said before and after the shock
1. Shock **confirmed on screen** at 30 s. Start commands at 20 s and 35 s.
2. P-012: the restart is the earliest start **after** the shock → **35 s**. The 20 s command
   is ineligible, flagged `start_command_before_shock` (D-025).
3. R7/A6 and A8 use 35 s. A7 (Increment 22) reports the 20 s command as a sequence problem.

### W-11 First placement tagged twice
1. Two `first_paddle_firmly_on_the_chest` tags, at 12 s and 14 s.
2. P-003: both become "first paddle placed". P-012: the key time is **12 s**, both IDs
   recorded, `multiple_candidates` (D-040; OQ-022 asks which placement should count).

### W-12 A label with a typo
1. The tag "gel applied" (lower case) is not in the vocabulary.
2. P-003/P-005: `unknown_labels_present` lists `annotation:gel applied`. The event cannot
   count as gel.
3. R1 (Increment 17) then finds gel missing → P-008. The warning shows a possible naming
   mismatch.

### W-13 A timeline mixing two camera angles → no assessment
1. Video events from camera "T" and camera "LS".
2. P-002: rejected, `multiple_camera_angles`; no assessment is produced (D-032).

### W-14 Under the removal fallback, "start compressions" before the removal → Unable to Verify
1. P-009: no shock on screen; paddles removed at 52 s → shock time **52 s** (from removal),
   flagged `shock_time_from_removal`. The real shock was at an unknown time before 52 s.
2. Explicit "start compressions" at 50 s, and again at 58 s.
3. P-012: the 50 s command is **timing-ambiguous**. It may have been the genuine restart after
   the real shock, so it is not counted and is **not a mistake**. It is listed as ambiguous and
   flagged `command_before_removal` (D-053). The 58 s command is used as the restart time, but
   the anchor stays flagged.
4. R7/A6 (Increment 21) and A8 (Increment 23): the restart is ambiguous → **Unable to Verify**,
   not Fail, not even `too_late` or `pre_shock_pause` measured to 58 s.
5. A7 (Increment 22) does **not** report the 50 s command as a sequence error. Compare W-10,
   where the shock was confirmed on screen and an early start command is a sequence problem.

### W-15 R7/A6 under the removal fallback, delay from the removal already too long → Fail
*(Planned, D-059. The R7 limit is not approved yet, OQ-016; a limit of 10 s is used here for
illustration only.)*
1. No shock on screen; removal at 52 s → shock time 52 s (`shock_time_from_removal`).
2. No start command before 52 s. First start after it at 64 s → definitely the restart.
3. Delay from the removal = 12 s, already over 10 s. The real shock was earlier, so the real
   delay is even longer.
4. R7/A6 → **Fail `too_late`**, a confident Fail even under the fallback, flagged
   `shock_time_from_removal` for transparency.

### W-16 R7/A6 under the removal fallback, delay from the removal within the limit → Unable to Verify
*(Planned, D-059; illustrative 10 s limit.)*
1. As W-15, but the first start after the removal is at 58 s → delay from the removal = 6 s.
2. The real delay is longer than 6 s by an unknown amount, so it may exceed 10 s.
3. R7/A6 → **Unable to Verify**, flagged `shock_time_from_removal`.

### W-17 R8, one zone visible, its paddle has no placement event → Unable to Verify
*(Planned, D-058.)*
1. Only the apical zone is visible. The first paddle was placed at 12 s, but there is no
   apical placement event.
2. P-015: the visible paddle's placement is not observed, so the order cannot be established.
   **No inference** ("the apical paddle was never placed, so sternal was first" is not shown by
   the evidence).
3. R8 → **Unable to Verify**, `placement_missing`. R3 reports the missing placement (one
   mistake reported once, D-003).

### W-18 R8, both zones visible, one placement event missing → Unable to Verify
*(Planned, D-058.)*
1. Both zones are visible. Apical placed at 12 s; no sternal placement event.
2. P-015: the order cannot be compared → **Unable to Verify**, `placement_missing`, and **not**
   Fail `wrong_order`. R3 reports the missing sternal placement.

### W-19 A8 under the removal fallback, no ambiguous start → measured normally
*(Planned, D-059.)*
1. Removal at 52 s (the shock time comes from removal). "Stop compressions" at 48 s; first
   start after the removal at 55 s; no start before the removal.
2. The restart is certain (P-012), and stop → restart = 7 s does not depend on the shock time,
   so it carries no fallback flag.
3. A8 (limit 5 s, approved, D-016) → **Fail `pre_shock_pause`**.

### W-20 R3 with no direct placement evidence, removal confirmed → Pass – Inferred
*(Planned, D-057.)*
1. The camera never shows both paddles stable in their zones (no `paddles_firmly_on_chest`).
2. P-014: R3 has an approved inference, so it is checked **before** the coverage step.
3. P-016: paddle removal is confidently confirmed → **Pass – Inferred**, naming the removal
   event. The coverage step (P-008) is not reached.

### W-21 Overall result with a pending rule → Incomplete
*(Planned, D-055.)*
1. Fifteen rules pass; R8 is still pending (not approved).
2. P-017: no Fail, but a rule is pending → **Incomplete: "rules not yet approved"**, never Pass.
3. If any evaluated rule had failed, the overall result would be **Fail** regardless (D-001).

### W-22 Overall result with a "not evaluable" rule → Unable to Verify policy
*(Planned, D-056.)*
1. No shock time (W-7). R7/A6 and A8 are "not evaluable because of R5"; R5 itself is Unable to
   Verify; every other rule passes; none is pending.
2. P-017: "not evaluable" counts like Unable to Verify → **Fail or faculty review**, per the
   undecided setting (OQ-002).

### W-23 R8 by the apical-first fallback → overall Incomplete
*(Planned, D-014 and D-060; the fallback is off by default.)*
1. No placement zone is visible, so R8 cannot be determined. The fallback is switched on.
2. P-015: R8's result is **assumed** ("apical first, to be checked by the evaluator"), not
   evaluated.
3. P-017: no rule fails → **Incomplete**, never Pass, exactly as if R8 were pending. Any Fail
   elsewhere would still make the overall result Fail.

### W-24 Under the removal fallback, "resume compressions" before the removal → restart ambiguous
*(D-059; the context part is built and tested.)*
1. Shock time from removal at 52 s. "Resume compressions" at 49 s → P-011: unresolved,
   `command_before_removal`.
2. "Start compressions" at 58 s → P-012: used as the restart time, but the restart is
   **ambiguous** (the 49 s command may have been the real restart). It is flagged
   `command_before_removal`.
3. R7/A6 and A8 → **Unable to Verify**, never Fail. A7 does not report the 49 s command.

### W-25 "Stand clear" said after the shock, and again before it → Pass
*(Shared checks, built in Increment 6; A3 itself is built in Increment 18.)*
1. Shock on screen at 30 s. "Stand clear" at 40 s and at 20 s.
2. P-022: the rule is satisfied when **any** occurrence is valid (D-012). The 20 s one is before
   the shock → **Pass – Direct**, citing the 20 s command. The 40 s one does not make it fail.
3. Had there been only the 40 s command → **Fail `after_shock`**. Had there also been a weak
   (0.2) "stand clear" at 20 s → **Unable to Verify**, `low_confidence_evidence`, because the
   weak one may have been the valid one.

### W-26 No approved R7 limit → timing not checked
*(Shared checks, built in Increment 6; R7 itself is built in Increment 21.)*
1. Shock at 30 s; restart at 40 s → 10 s.
2. P-024: `shock_to_compressions_seconds` is null (OQ-016) → **timing not checked**. R7 judges
   presence and order only: a restart after the shock → Pass, with its reason saying "timing
   not checked" and the flag `timing_not_checked`.
3. Once the supervisor approves a limit, the same timeline is judged against it, with no code
   change.

### W-27 Every rule passes, but R7's limit is not approved → Incomplete
*(Planned overall policy, D-062.)*
1. Every rule is approved and passes. R7's limit (`shock_to_compressions_seconds`) is still
   null (OQ-016).
2. P-024: R7 checks presence and order only. Its result is **Pass**, flagged
   `timing_not_checked` (D-005).
3. P-017: no Fail and nothing pending, but R7's timing was not checked → **Incomplete: "timing
   not checked for R7"**, never Pass. The same happens for a limit with a value but no
   approver (`limit_not_approved`, D-061).

### W-28 A rule crashes → recorded, the others still run, overall Incomplete
*(Runner built in Increment 7; overall policy in Increment 8.)*
1. R2's code raises an error, for example a division by zero, while evaluating a timeline.
2. P-026: R2's result is **`engine_error`**, with the message
   ("ZeroDivisionError: division by zero"). R1, R8 and every other rule are still evaluated.
3. Any rule that depends on R2 is **not evaluable because of R2**.
4. P-017: no Fail elsewhere → **Incomplete** ("engine error in R2"), never Pass (D-063). The
   report shows the error, so it is fixed rather than hidden.

### W-29 A Fail on a timeline with two shocks → Fail, flagged for review
*(Overall policy built in Increment 8.)*
1. R1 fails (`applied_once`). The timeline has two shock indications (`multiple_shocks`).
2. P-017 step 1: **Fail**, listing R1 `applied_once` as the mistake. Because `multiple_shocks` is
   a review anomaly, the Fail is flagged `timeline_needs_review`, with the anomaly listed (D-065).

### W-30 No Fail, but an unknown label in the timeline → Incomplete
1. Every approved rule passes. The timeline contains "gel applied" (lower case):
   `unknown_labels_present`.
2. P-017 step 2: **Incomplete**, "the timeline needs review (unknown_labels_present)", never Pass.
   A naming mismatch may have hidden evidence.

### W-31 Some steps unverified, setting undecided → unable_to_verify
1. No Fail, nothing pending; A1 is Unable to Verify (audio unclear), and A7 is not evaluable
   because of A1.
2. P-017 step 3: `unable_to_verify_outcome` is undecided → **unable_to_verify**, flagged
   `overall_policy_undecided`. The explanation names A1 and A7 and the undecided setting
   (OQ-002). Once the supervisor decides, the same timeline gives Fail or faculty review.

### W-32 R7 too late → one mistake, not two
1. R7 fails `too_late`; A6 (the same check, D-044) therefore fails too.
2. P-017: **Fail**, with one mistake entry for **R7/A6** `too_late`, not two.

### W-33 An annotation timeline → development data
1. A timeline built from CVAT annotations: every result carries `annotation_coverage_assumed`
   (Increment 10).
2. P-017: the result is computed as usual, but marked **development data**, not a real
   assessment (D-066).

### W-34 The command line on a timeline file → JSON report
*(Built in Increment 9.)*
1. `python -m rules.run --events timeline.json`. The file is a list of events, or
   `{"header": {...}, "events": [...]}`. Events without an ID get `event_000001`, … in file order.
2. P-002 to P-017 run as usual. P-027: the report is written (by default to
   `data/outputs/rule_engine_report.json`) and the overall result and each rule are printed.
3. With every rule pending today: **Incomplete**, "rules not yet approved for R1, R2, …".
4. Had the file held two events with the same ID: P-002 rejects it (`duplicate_event_id`), the
   error is printed, **no report** is written, and the exit code is 2.

### W-35 Paddles removed twice, 0.3 s apart → count anomaly, possibly one removal
*(Built in Increment 9a; the counts are placeholders.)*
1. Confident `paddles_removed_after_shock` at 40.0 s and 40.3 s. The expected count is exactly 1.
2. P-005: **`count_violation`**, "expected exactly 1, found 2". The pair is within the 0.5 s
   window, so it is marked "possibly the same incident detected twice". Both events are kept.
3. No rule fails because of the count. P-012 uses the earliest removal (`multiple_candidates`).
4. P-017 (D-072): no Fail elsewhere → **Incomplete**, "the timeline needs
   review (count_violation)". A Fail elsewhere would stay Fail, flagged.

### W-36 Two apical placements and no sternal → paddle identity conflict
*(Built in Increment 9a.)*
1. Confident `apical_paddle_placed` at 10 s and 14 s; no `sternal_paddle_placed`.
2. P-005: **`paddle_identity_conflict`** (the paddle identity was probably swapped or lost), and
   **`count_violation`** for the apical placement.
3. R8 (Increment 12) cannot trust the placement order. P-017: the overall result can't be Pass
   (D-072).

### W-37 Stand clear said three times → nothing
1. Three confident `stand_clear_command`. Commands are unlimited.
2. P-005: no count anomaly. A3 uses any valid occurrence (D-012).

### W-38 First paddle taken never detected → missing, not a count anomaly
1. No confident `first_paddle_taken` (its expected count is exactly 1).
2. P-005: **no** `count_violation` (A-018). The missing event goes to the coverage step (P-008),
   which decides Fail or Unable to Verify, as before.

### W-39 An LL video with its apical zone tracked → covered
*(Export and audit built in Step 9b; coverage in Increment 10.)*
1. P-028: P01_LL has one `apical_placement_zone` track, visible from frame 0 to 472 (fps 24.91
   from the conversion report) → interval 0.0 to 18.948 s. There is no sternal track.
2. P-029: LL's usual pattern is apical only, so the video is not on the review list.
3. P-030: apical → **covered**; sternal → **unknown** (no track).

### W-40 A T video with no zone track at all → unknown, on the review list
1. P-028: no zone track, so no intervals.
2. P-029: T's usual pattern is both zones → **`zone_pattern_off`** (missing both). It is one of
   the 6 videos with no zone in the current backups.
3. P-030: both zones **unknown**. R8 (Increment 12) cannot rely on zone visibility, so it reports
   Unable to Verify rather than guessing.

### W-41 An annotator confirms that the apical zone was genuinely not visible → not covered
1. Arnikan adds `{task: P14_T, zone: apical_placement_zone, confirmed_by: …, confirmed_on: …}` to
   `reviewed_zone_exceptions`.
2. P-029: the missing apical zone is excused → off the review list (information
   `zone_exception_confirmed`).
3. P-030: apical → **not covered**, instead of unknown. R8 can then use its one-visible-zone logic
   for the sternal zone.
4. Had the apical zone actually been visible: **`zone_exception_contradicted`** on the review list.

### W-42 A zone track that is outside on every frame → not covered
1. P-028: the track exists, but no frame has a training box → `zone_tracks` 1, no interval.
2. P-029: information `zone_track_never_visible`, not an issue.
3. P-030: **not covered** (D-080). The annotator saw no zone.

### W-43 The same tag twice, 1 frame apart → possibly one incident
1. P-028: both tags exported (every tag is kept).
2. P-029: **`repeated_incident_tag`**, "possibly the same incident tagged twice" (within 15
   frames). Had they been 40 frames apart: information `repeated_tag` only. The learner may have
   repeated the action, and only the rule engine judges that (D-071).

### W-44 A video missing from the conversion report → no record
1. P-028: its fps is unknown, so frames cannot become seconds → export issue **`fps_missing`**; no
   record (D-076).
2. The adapter never sees it. The fix is in Ananth's conversion report, not in a guessed fps.
