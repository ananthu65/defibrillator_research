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

#### P-031 Derived per-paddle placement (built, Step 9c; D-081, D-086 to D-089)
Derived per paddle **label**, across all its tracks (D-087). T1 is `first_paddle_firmly_on_the_chest`
and T2 is `paddles_firmly_on_chest`, following the annotators' convention (A-019).

| Condition | Outcome | Code |
|---|---|---|
| Paddle box ≥ 0.5 inside its zone, steady for 5 frames (centre < 2% of the diagonal) | A placement starts; it ends after 5 frames (`exit_frames`) out of the zone | — |
| A track of the paddle ends and another track of the same label continues | The same placement (not a re-placement) | — |
| Zone not visible on a frame (occlusion) | **Unknown**: doesn't start or end a placement; in on both sides of the gap is the same placement (A-020, D-090) | counted in `frames_zone_not_visible` |
| Two boxes of one paddle on a frame during a placement | No event for that paddle | `placement_duplicate_paddle_box` (review) |
| Zone has no visible track, or the paddle never settles | No event (reason in the validation report) | — |
| T1 present, both derived, the earlier within 15 frames of T1 | Both events: direct evidence, flagged `derived_placement` | — |
| T1 present, both derived, the earlier more than 15 frames from T1 | No event for either paddle | `placement_disagrees_with_tag` |
| T1 present, one derived (one-zone view) | Event if not earlier than T1 − 15; otherwise none | `placement_disagrees_with_tag` |
| T1 missing, both within `simultaneous_window_seconds` | Both kept, flagged `possible_parallel_placement`; enough for R2/R8 to Fail `simultaneous` once the gate is approved (D-091) | — |
| T1 missing otherwise | No events | — |
| T2 present, a first placement after T2 + 15 | No event for that paddle (both if parallel) | `placement_disagrees_with_tag` |
| Gate: no review record for this `export_id` and these settings | The Increment 10 adapter doesn't pass derived placements to the engine (D-088) | — |

### Stage: adapter

#### P-001 Annotation timeline adapter (built, Increment 10)
`python -m rules.adapters.annotation --records <records.jsonl> --output <folder>` writes one
timeline file per video for `rules.run`.

| Condition | Outcome | Flags |
|---|---|---|
| An exporter record is converted (D-074) | Events from every tag under its CVAT name (the vocabulary maps them). Header: `recording_id`, `camera_angle` and `duration_seconds` from the record; video analysed, audio not | `annotation_coverage_assumed` in the header and on every result; report marked development data (D-066) |
| Zone coverage per region | → P-030 | — |
| Derived placements, and the gate passes for this export's ID and settings hash (D-088) | They become events and reach the engine | — |
| Derived placements, gate not passed | Withheld and counted; the engine never sees them | — |

#### P-030 Zone coverage for an annotated recording (built, Increment 10)
| Condition | Coverage of the region (whole recording) | Intervals in the header | Decision |
|---|---|---|---|
| Annotator confirmed the zone was genuinely not visible (reviewed exception) | **not covered** | none | D-082 |
| Zone track visible on every frame | **covered** | its interval | D-074 |
| Zone track visible on only part of the recording | **unknown** | its intervals; a time window gets its own status (P-007) | D-092 |
| Zone track present but outside on every frame | **not covered** | empty | D-080 |
| No zone track | **unknown** | none | D-074 |
| The defibrillator screen (region `screen`, R5) | the same rules (no reviewed exceptions); an export without screen fields → **unknown** | as above | D-094 |

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
| The rule asks about a time window, and the header has visibility intervals for the event's region (D-092) | **covered** if visible throughout the window; **unknown** if visible for part of it; **not covered** if never visible in it |
| Header states coverage for the event's camera region (apical or sternal zone) | that status (whole recording) |
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
The shock time comes only from the screen (D-093). `engine.yaml` `shock_time_fallback` is `none`;
the removal rows apply only when it is set to `removal`.

| Condition | Outcome | Flags |
|---|---|---|
| Two or more shocks | No shock time (not guessed) | `multiple_shocks` |
| One shock on screen | Shock time = the shock | — |
| No shock on screen (fallback `none`, the decided setting) | **No shock time; never inferred**, even if the paddles were removed. Shock-dependent rules are Not evaluable because of R5; resume commands stay unresolved | `no_shock` |
| No shock on screen, but a paddle removal (fallback `removal` only) | Shock time = first removal; every timing result using it is flagged | `shock_time_from_removal` (+ `multiple_candidates` if several removals) |
| No shock on screen and no removal (fallback `removal`) | No shock time | `no_shock` |

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
| Shock time from removal (fallback `removal` only), command before the removal | Unresolved (D-024) | `command_before_removal`, `shock_time_from_removal` |
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
| No approved limit (null): not decided yet | **Timing not checked**: presence and order only | `timing_not_checked` |
| A value without an approver | Not used; timing not checked (D-061) | `timing_not_checked`, `limit_not_approved` |
| Approved "no limit" (`no_limit: true` with an approver) | Timing checked and within: the rule **passes fully** on presence and order (D-103) | — |
| "No limit" without an approver | Not used; timing not checked (D-061, D-103) | `timing_not_checked`, `limit_not_approved` |
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

#### P-015 R8: apical before sternal (built, Increment 12; pending until approved)
A zone counts as visible when it is covered over the placement phase, from the first paddle
taken to paddles firmly on chest (D-092, D-099). Derived placements are used only past the gate
(D-088).

| Condition | Outcome | Codes and flags |
|---|---|---|
| Derived placements flagged `possible_parallel_placement` | Fail; **R2 fails too, separately** (D-091, D-098) | `simultaneous`; `possible_parallel_placement` (shared cause flag), `derived_placement` |
| Both placements observed | Compare the two placement times: apical first → Pass – Direct | `wrong_order`, `simultaneous`; `derived_placement` if derived |
| A zone visible during the placement phase, its placement missing (both zones visible with one missing, or the one visible zone without its placement) | Unable to Verify, not `wrong_order`; R3 reports the missing placement (D-058) | `placement_missing` |
| One placement observed (the other zone not visible), within 0.5 s of the first placement | That paddle was first (inferred): apical → Pass – Inferred | — |
| One placement observed, clearly after the first placement | The other paddle was first (inferred) | — |
| Inferred mistake (sternal first) | Unable to Verify while undecided (D-015); Fail or Unable to Verify once decided | `inferred_fail_policy_undecided`; `wrong_order` if decided as fail |
| The visible paddle placed clearly before the first placement | Unable to Verify | `contradictory` |
| Not determinable (no placement and no zone visible, or no first placement) | Unable to Verify; if the fallback is on: **assumed** apical first, to be checked by the evaluator, and the overall result cannot be Pass (D-014, D-060) | — |

#### P-033 R5: shock confirmed on screen (built, Increment 13; pending until approved)
| Condition | Outcome | Code and flags |
|---|---|---|
| Two or more shock indications | Unable to Verify (one shock can't be confirmed) | `multiple_shocks` |
| Shock on screen, preceding steps unset (OQ-013) | Pass – Direct, presence only; the overall result can't be Pass (D-100) | `order_not_checked` |
| Shock on screen before an observed preceding step | Fail | `wrong_order` |
| Shock on screen, a preceding step not observed | Pass – Direct; that step's order not checked | `order_not_checked` |
| Shock on screen after every preceding step | Pass – Direct | — |
| No shock, a low-confidence one exists | Unable to Verify | `low_confidence_evidence` |
| No shock, screen visible throughout paddles firmly on chest → paddles removed (or the whole recording if a tag is missing, D-101) | Fail | `missing` |
| No shock, screen not visible throughout that window | Unable to Verify, never Fail (D-094) | — |

#### P-035 R3: paddles placed firmly on the chest (built, Increment 15; pending until approved)
Placement timing and presence only: `not_in_zone` is not produced until the supervisor approves
the chest regions (OQ-012, D-106).

| Condition | Outcome | Code and flags |
|---|---|---|
| Shock time; a `paddles_firmly_on_chest` tag at or before the shock (within `simultaneous_window_seconds` after it counts as at it) | Pass – Direct | — |
| Shock time; past the gate, both derived placements at or before the shock | Pass – Direct | `derived_placement` |
| Shock time; only tags clearly after the shock | Fail; comes before the inference | `placed_after_shock` |
| No direct evidence (or no shock time to judge it against); an event in `inference_sources` confirmed | Pass – Inferred (D-057, D-102) | — |
| No inference and no shock time | **Not evaluable because of R5** | — |
| No inference; a low-confidence firm placement | Unable to Verify | `low_confidence_evidence` |
| No inference; both placement zones visible throughout first paddle taken → shock | Fail | `missing` |
| No inference; a zone not visible throughout that window (for example one paddle visible: the tag is not made then, A-019) | Unable to Verify, never Fail | — |

With the proposal's sources, a shock time always means a shock on the screen, which is itself
an inference source, so the coverage rows are reached only if `inference_sources` drops it.

#### P-034 R6: paddles removed after the shock (built, Increment 14; pending until approved)
`paddles_removed_after_shock` means the paddles were removed; it doesn't prove a shock (D-104).

| Condition | Outcome | Code and flags |
|---|---|---|
| No shock time (no shock on the screen, or several) | **Not evaluable because of R5**, even if a removal is tagged (D-093) | — |
| Shock time taken from the removal itself (`shock_time_fallback: removal` only) | Unable to Verify | `shock_time_from_removal` |
| Removal clearly before the shock (more than `removal_before_screen_tolerance_seconds`: the screen may show the shock after the discharge, D-105) | Fail | `removed_before_shock` |
| Past the gate: a derived placement ended by a real exit clearly before the shock, that paddle not placed again by the shock | Fail | `removed_before_shock`; `derived_placement` |
| Removal after the shock, or before it within `removal_before_screen_tolerance_seconds` (treated as at the shock) | Pass – Direct; limit unset, so the overall result can't be Pass (D-062); an approved "no limit" passes fully (D-103) | `timing_not_checked` |
| Removal later than an approved `shock_to_removal_seconds` | Fail | `too_late` |
| No removal, a low-confidence one exists | Unable to Verify | `low_confidence_evidence` |
| No removal, both placement zones visible throughout from the shock to the end of the recording (A-022) | Fail | `missing` |
| No removal, a placement zone not visible throughout that window | Unable to Verify, never Fail | — |

#### P-032 R2: second paddle taken after the first is placed (built, Increment 11; pending until approved)
| Condition | Outcome | Code |
|---|---|---|
| Derived placements flagged `possible_parallel_placement` (only once the gate is approved) | Fail (D-091) | `simultaneous` |
| No confident second paddle taken | Unable to Verify | — |
| First placement before the second paddle is taken | Pass – Direct | — |
| Within `simultaneous_window_seconds` | Fail | `simultaneous` |
| Second paddle taken before the first placement | Fail | `taken_before_first_placed` |
| First placement not seen, a low-confidence one exists | Unable to Verify (D-010) | — |
| First placement not seen, both zones visible throughout the window from first paddle taken to second paddle taken | Fail: either the paddles were placed in parallel, or the second paddle was taken before the first was placed (A-019; D-095, D-097) | `first_placement_not_observed` |
| First placement not seen, a zone not visible throughout that window | Unable to Verify | — |

#### P-016 R3/R4 inferred pass (built for R3 in Increment 15, see P-035; R4 planned, Increment 16)
| Condition | Outcome | Codes |
|---|---|---|
| Direct evidence in time | Pass – Direct | — |
| Direct evidence shows the mistake | Fail | R3: see P-035; R4: `before_placement`, `not_pressed` |
| Direct evidence weak **or missing**; an event in `inference_sources` confirmed (the shock on screen or the removal) | Pass – Inferred (D-057). A removal can happen without a successful shock (A-021); the overall result then still can't be Pass, because R5 fails or is Unable to Verify (D-102, OQ-060) | — |
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

> **W-5, W-6, W-14, W-15, W-16, W-19 and W-24 apply only with `shock_time_fallback: removal`.**
> With the decided setting `none` (D-093), a recording with no shock on screen has no shock time
> at all: see W-54.

### W-5 No shock on screen, paddles removed at 52 s → timing flagged (fallback `removal` only)
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
*(Built in Increment 12, D-058.)*
1. Only the apical zone is visible. The first paddle was placed at 12 s, but there is no
   apical placement event.
2. P-015: the visible paddle's placement is not observed, so the order cannot be established.
   **No inference** ("the apical paddle was never placed, so sternal was first" is not shown by
   the evidence).
3. R8 → **Unable to Verify**, `placement_missing`. R3 reports the missing placement (one
   mistake reported once, D-003).

### W-18 R8, both zones visible, one placement event missing → Unable to Verify
*(Built in Increment 12, D-058.)*
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
*(Built in Increment 15; D-057, D-106.)*
1. The camera never shows both paddles stable in their zones (no `paddles_firmly_on_chest`).
2. P-014: R3 has an approved inference, so it is checked **before** the coverage step.
3. P-016: paddle removal is confidently confirmed → **Pass – Inferred**, naming the removal
   event. The coverage step (P-008) is not reached.
4. If no shock appeared on the screen (paddles removed without a successful shock), R5 is Fail
   `missing` or Unable to Verify, so the overall result is still not Pass (D-102, A-021).

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
*(Built in Increment 12, D-014 and D-060; the fallback is off by default.)*
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

### W-45 Correct, fully visible placement → both placements derived
*(Step 9c, built.)*
1. LS view, both zones visible. Tags: first paddle firmly on the chest at frame 21; paddles
   firmly on chest at 45.
2. P-031: the apical paddle settles in its zone at frame 20 and the sternal one at 40.
3. The earlier (20) is 1 frame from T1 → both events kept, flagged `derived_placement`. Both are
   at or before T2 + 15 → kept.
4. R8 (Increment 12), once the gate is passed: apical first → Pass – Direct.

### W-46 Both paddles placed at the same time, no first-placement tag → possible parallel placement
1. The learner places both paddles together. Following their convention, the annotators don't tag
   `first_paddle_firmly_on_the_chest` (A-019).
2. P-031: apical derived at frame 20, sternal at 30 (0.4 s at 25 fps), within
   `simultaneous_window_seconds` (0.5 s).
3. Both events are kept, flagged **`possible_parallel_placement`**.
4. Once the gate is approved for this export and its settings (D-088), R2 and R8 **Fail** with
   **`simultaneous`** on this positive evidence alone (D-091). Before that, the adapter doesn't
   pass the events on.

### W-47 No first-placement tag, placements far apart → no events
1. T1 is missing, and the derived placements are at frames 20 and 40 (0.8 s apart).
2. P-031: neither the tag (one paddle went first, but it wasn't tagged) nor a parallel placement
   explains this → **no events**. The validation report gives the reason.
3. R8 → Unable to Verify (placements missing), never a guessed order.

### W-48 A paddle tracked with two track IDs
1. `paddle_apical` track A ends at frame 50, and track B (a new ID) continues from frame 50 in the
   same place.
2. P-031 works per label: the paddle stays in its zone throughout → **one placement**, at frame 20.
   It is not mistaken for a re-placement at 50 (D-087).
3. Had the two tracks overlapped (two `paddle_apical` boxes on the same frames): no event,
   review issue `placement_duplicate_paddle_box`, for Ananth to fix, because the overlap also
   affects the training labels.

### W-49 Placement disagrees with the first-placement tag → no event for either paddle
1. Both zones visible. The earlier derived placement is at frame 20, but T1 is at frame 36, 16
   frames later.
2. P-031: more than the 15-frame window → **no event for either paddle**, review issue
   `placement_disagrees_with_tag` (D-086).
3. One-zone view instead (LL, apical only): the apical placement must not be earlier than T1 − 15.
   Placed at frame 50 with T1 at 30 is fine: the visible paddle was simply the second.

### W-50 The zone is hidden for 6 frames during a placement → still one placement
*(Step 9c, A-020, D-090.)*
1. The apical paddle settles in its zone at frame 20 and stays there. On frames 41 to 46 the
   annotator marked the apical zone outside (the paddle or a hand covers it), and it is visible
   again from frame 47.
2. P-031: frames 41 to 46 are **unknown**, neither in nor out. They don't end the placement, and
   the paddle is in its zone on both sides of the gap → **one placement**, at frame 20.
   `frames_zone_not_visible` is 6 in the validation report.
3. Had those 6 frames counted as "out", they would have exceeded `exit_frames` (5) and invented a
   re-placement at frame 47.
4. Compare: the paddle really lifted off for frames 41 to 46, with the zone visible → 6 out
   frames → **two placements**, at 20 and 47 (a re-placement, D-012; `count_violation` in the
   engine, D-071).

### W-51 A placement expected while the zone was out of view → Unable to Verify, never Fail
*(Built in Increment 10; D-092.)*
1. The apical zone is visible from 0 to 1.56 s and from 2.4 to 3.96 s. P-030: the zone is
   **unknown** for the whole recording, and both intervals go into the header.
2. A rule expects the apical placement between 1.7 and 2.2 s and finds none.
3. P-007 with that window: the zone is never visible in it → **not covered**. P-008 → **Unable to
   Verify** (D-004): the camera couldn't have shown it.
4. Same rule, window 0.2 to 1.0 s (zone visible throughout) → **covered** → a missing placement is
   a **Fail**.
5. Window 1.0 to 2.0 s (visible for only part of it) → **unknown** → Unable to Verify (interim,
   `coverage_policy_undecided`).

### W-52 Derived placements from an export that hasn't been reviewed → withheld
*(Built in Increment 10; D-088.)*
1. The records contain derived placements. The review record in `annotation_export.yaml` is
   empty, or names another `export_id` or other settings.
2. P-001: `derived_placements_approved()` fails → the placements are **withheld** and counted in
   `adapter_summary.json` ("not approved: …"). The engine never sees them, so R8 finds no
   per-paddle placement → Unable to Verify.
3. After Arnikan reviews this export's `placement_validation.md` and fills in the review record
   with its `export_id` and settings hash, they reach the engine, and R8 can use them (D-091 for
   parallel placements).

### W-53 An interim record through the adapter and the engine (P06_T)
*(Run on 2026-10-17 on the smoke-run export, D-084.)*
1. P-001: 6 events, for example `first_paddle_firmly_on_the_chest` mapped to
   `first_paddle_placed` at 14.03 s. Header: duration 25.0 s, video analysed, audio not, flagged
   `annotation_coverage_assumed`.
2. P-030: the sternal zone is visible throughout → covered. The apical zone is visible only from
   10.1 s → **unknown** for the recording. The first placement (14.03 s) lies inside its visible
   interval, so a rule asking about that time would get **covered** (D-092).
3. No shock on screen is tagged. When this ran, the removal fallback still gave a shock time of
   21.57 s; under D-093 (2026-10-17) there is **no shock time** (see W-54).
4. Every rule is pending → **Incomplete**, `development_data`, every result flagged.

### W-54 An LL video: no screen, no shock time, nothing guessed
*(Built; D-093, D-094.)*
1. P-001/P-030: LL shows the apical zone throughout. There is no sternal zone track and no
   `defibrillator_screen` track, so the sternal zone and the screen are **unknown**. The paddles
   were removed at 15.94 s.
2. P-009 (fallback `none`): no shock on screen → **no shock time**, `no_shock`. The removal is
   not used.
3. R5 (Increment 13): no shock on screen while the screen is unknown → **Unable to Verify**,
   never Fail. Had the screen been in view throughout and no shock seen, R5 would fail.
4. Every shock-dependent rule (R6, R7/A6, A1–A4, A7, A8; R3's direct check) → **Not evaluable
   because of R5**. Resume commands stay unresolved (`no_shock_time`).
5. R3/R4 can still pass by inference from the removal (P-016, unchanged).

### W-55 R2: the first placement isn't seen
*(Built in Increment 11; D-095, D-097.)*
1. First paddle taken at 5 s, second paddle taken at 9 s, no first-placement tag.
2. P-032 asks coverage of both placement zones from 5 to 9 s.
   - **Both zones visible throughout** → **Fail `first_placement_not_observed`**: no first
     placement was seen although it would have been visible. Following the annotators'
     convention (A-019), either the paddles were placed in parallel, or the second paddle was
     taken before the first was placed.
   - **Zones out of view between 4 and 10 s** → not covered → **Unable to Verify**. The
     placement may have happened unseen.
   - **One zone visible until only 7 s** → unknown → **Unable to Verify**.

### W-56 R2: a parallel placement, with and without the gate
*(Built in Increment 11; D-091, D-088.)*
1. Both paddles placed together, so the annotators didn't tag the first placement (A-019). The
   exporter derives both placements 0.08 s apart and flags them `possible_parallel_placement`.
2. **Gate approved** for this export and its settings → the derived placements reach the engine
   → R2 **Fail `simultaneous`** (D-091).
3. **Gate not approved** → the placements are withheld. R2 sees "first placement missing", and
   with the zones visible throughout it gives **Fail `first_placement_not_observed`**: either a
   parallel placement or the second paddle taken first (D-097). The approved gate refines this
   to `simultaneous`.

### W-57 One parallel placement fails R2 and R8, sharing the cause flag
*(Built in Increment 12; D-091, D-098.)*
1. Both paddles placed together (derived 0.08 s apart, flagged `possible_parallel_placement`). The
   gate is approved for this export and its settings.
2. R2 (P-032) → **Fail `simultaneous`**: the second paddle wasn't taken after the first was
   placed.
3. R8 (P-015) → **Fail `simultaneous`**: the apical paddle was not placed first. This is not
   "not evaluable because of R2". R8 has no dependency on R2 and is evaluated on its own
   evidence.
4. Both results carry **`possible_parallel_placement`** (and `derived_placement`). The feedback
   module can say that one action caused both failures.
5. P-017: **Fail**, listing two mistakes, R2 and R8. Whether this should count as one mistake is
   OQ-059 (supervisor).
6. Gate not approved: neither rule sees the derived placements. R2 → `first_placement_not_observed`;
   R8 → Unable to Verify, `placement_missing` (both zones in view, no placement observed).

### W-58 R8 from an LL view: the one-zone inference
*(Built in Increment 12; D-013, D-099.)*
1. LL: the apical zone is visible throughout the placement phase; there is no sternal zone track
   (unknown, so not visible). First placement (the first-placement tag) at 7.0 s.
2. Apical placement at 7.2 s, within 0.5 s of the first placement → the apical paddle was first
   → **Pass – Inferred**, citing both events.
3. Apical placement at 11 s, clearly after → the sternal paddle was first, an inferred mistake →
   **Unable to Verify**, `inferred_fail_policy_undecided` (D-015, OQ-005). Once decided as fail:
   **Fail `wrong_order`**.
4. Apical placement at 4 s, clearly before the first placement → **Unable to Verify**,
   `contradictory`.
5. No apical placement although the apical zone was in view → **Unable to Verify**,
   `placement_missing` (D-058).

### W-59 A zone in view only after the placement phase does not count
*(Built in Increment 12; D-099.)*
1. Placement phase 5–14 s (first paddle taken → paddles firmly on chest). The apical zone is
   visible throughout it; the sternal zone only from 20 s.
2. Only the apical placement is observed. The sternal zone was not in view during the phase, so
   its missing placement is **not** `placement_missing`. The one-zone inference applies, as in
   W-58.

### W-60 R5 with a shock seen and the preceding steps not yet set → Incomplete
*(Built in Increment 13; D-100.)*
1. Shock on the screen at 15 s. `preceding_steps` is unset (OQ-013).
2. P-033: **Pass – Direct**, presence only, flagged `order_not_checked`.
3. P-017: no Fail → **Incomplete**, "order not checked for R5", never Pass (like D-062).
4. Once the supervisor sets the steps (for example paddles firmly on chest, both buttons
   pressed): buttons at 13 s → Pass; buttons at 16 s → **Fail `wrong_order`**; no button press
   observed → Pass with `order_not_checked` (R4 reports the missing press).

### W-61 R5 with no shock seen: the screen over the shock window
*(Built in Increment 13; D-094, D-101.)*
1. Paddles firmly on chest at 10 s, paddles removed at 20 s, no shock on the screen.
2. P-033 asks the screen's coverage over 10–20 s:
   - **visible throughout** → **Fail `missing`**;
   - **out of view in that window** (visible only before 8 s and after 22 s) → **Unable to
     Verify**;
   - **visible until 15 s only** → unknown → **Unable to Verify**;
   - **no screen track** (for example LL) → **Unable to Verify**.
3. No paddles-firmly-on-chest tag: the whole recording is used. The screen is visible
   throughout → Fail; visible for part of it → Unable to Verify.

### W-62 R5 with two shocks on the screen → Unable to Verify
*(Built in Increment 13; D-039, D-101.)*
1. Shock indications at 14 s and 16 s. Preparation raises `multiple_shocks`, and there is no
   shock time.
2. P-033: **Unable to Verify**, citing both, flagged `multiple_shocks`. The timeline needs review
   (D-065), so the overall result can't be Pass.

### W-63 R6 with the removal after the shock → Incomplete while the limit is unset
*(Built in Increment 14; D-103, D-104.)*
1. Shock on the screen at 15 s, paddles removed at 20 s.
2. P-034: **Pass – Direct**, 5 s after the shock. `shock_to_removal_seconds` is unset → flagged
   `timing_not_checked` (P-024).
3. P-017: no Fail → **Incomplete**, "timing not checked for R6" (D-062).
4. If the supervisor answers "no limit" and it is recorded as approved (`no_limit: true`):
   **Pass – Direct** with no flag, and the overall result can be Pass (D-103). With an approved
   limit of 3 s: **Fail `too_late`**.

### W-64 R6 with the removal before the shock
*(Built in Increment 14; D-104, D-105.)*
1. Shock on the screen at 15 s; `removal_before_screen_tolerance_seconds` is 0.5 s (placeholder,
   separate from the simultaneous window, D-105).
2. Paddles removed at 14.5 s → within the tolerance, treated as at the shock → **Pass – Direct**,
   0 s.
3. Paddles removed at 14.4 s → clearly before → **Fail `removed_before_shock`**.

### W-65 R6 from derived placements: a paddle off its zone before the shock
*(Built in Increment 14; D-088, D-104.)*
1. Gate approved. The apical paddle is placed at 7 s and leaves its zone at 12 s by a real exit
   (`ended_by_exit`). Shock on the screen at 15 s, removal tagged at 20 s.
2. P-034: no apical placement is on at the shock → **Fail `removed_before_shock`**, citing the
   derived placement and the shock, flagged `derived_placement`.
3. If the apical paddle was placed again at 12.8 s, it is on at the shock → no early removal →
   **Pass – Direct** (the tag at 20 s).
4. Gate not approved: the derived placements never reach R6 → **Pass – Direct** from the tag.

### W-66 R6 with no shock time or no removal
*(Built in Increment 14; D-093, D-104.)*
1. No shock on the screen, removal tagged at 20 s → **Not evaluable because of R5**. The removal
   doesn't prove a shock.
2. Shock at 15 s, no removal, recording 30 s long:
   - both placement zones visible from 15 s to 30 s → **Fail `missing`** (A-022);
   - the zones out of view after 22 s, or no zone tracks → **Unable to Verify**.

### W-67 R3 with a firm placement tag
*(Built in Increment 15; D-106.)*
1. First paddle taken at 5 s, paddles firmly on chest at 12 s, shock on the screen at 15 s.
2. P-035: **Pass – Direct**. Where the paddles were is not checked (OQ-012).
3. Firm placement tagged only at 17 s → **Fail `placed_after_shock`**, even though the shock on
   the screen would otherwise support an inference.

### W-68 R3 when only one paddle is visible
*(Built in Increment 15; A-019, D-106.)*
1. LL-like view: the apical zone is visible, the sternal zone has no track. The annotators don't
   tag paddles firmly on chest, because only one paddle is visible.
2. Shock on the screen at 15 s → **Pass – Inferred** from the shock (the proposal's sources).
3. If `inference_sources` didn't include the shock: the sternal zone was not visible over
   5–15 s → **Unable to Verify**. With both zones visible throughout → **Fail `missing`**.

### W-69 R3 from the removal, without a shock on the screen
*(Built in Increment 15; D-093, D-102.)*
1. No shock on the screen; paddles removed at 20 s.
2. P-035: no shock time, so a firm placement tag can't be checked directly. The removal is an
   inference source → **Pass – Inferred**, citing the removal. R5 is Fail or Unable to Verify,
   so the overall result is not Pass (A-021).
3. Without the removal → **Not evaluable because of R5**.

### W-70 R3 from derived placements
*(Built in Increment 15; D-088, D-106.)*
1. No firm placement tag. Derived placements: apical at 7 s, sternal at 12 s; shock at 15 s.
2. Gate approved → **Pass – Direct**, flagged `derived_placement`.
3. Gate not approved → the placements never reach R3 → **Pass – Inferred** from the shock.
4. Only one derived placement, or one after the shock → not direct evidence; the inference or
   coverage decides.
