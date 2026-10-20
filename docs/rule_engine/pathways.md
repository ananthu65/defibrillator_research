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
(the apical paddle's placement under the team's working definition, A-027) and T2 is
`paddles_firmly_on_chest`, following the annotators' convention (A-019).

| Condition | Outcome | Code |
|---|---|---|
| Paddle box ≥ 0.5 inside its zone, steady for 5 frames (centre < 2% of the diagonal) | A placement starts; it ends after 5 frames (`exit_frames`) out of the zone | — |
| A track of the paddle ends and another track of the same label continues | The same placement (not a re-placement) | — |
| Zone not visible on a frame (occlusion) | **Unknown**: doesn't start or end a placement; in on both sides of the gap is the same placement (A-020, D-090) | counted in `frames_zone_not_visible` |
| Two boxes of one paddle on a frame during a placement | No event for that paddle | `placement_duplicate_paddle_box` (review) |
| Zone has no visible track, or the paddle never settles | No event (reason in the validation report) | — |
| Each paddle | Derived from its own box in its own zone, whatever the order (D-118); events are direct evidence, flagged `derived_placement`, method `paddle_in_zone_v2` | — |
| T1 present, the apical placement within 15 frames of T1 (T1 marks the apical paddle, A-027) | Kept | — |
| T1 present, the apical placement more than 15 frames from T1 | No event for the apical paddle; the sternal one is unaffected (T1 never decides the order) | `placement_disagrees_with_tag` |
| T1 missing, both within `simultaneous_window_seconds` | Both kept, flagged `possible_parallel_placement`; enough for R2/R8 to Fail `simultaneous` once the gate is approved (D-091) | — |
| T1 missing otherwise | No events | — |
| T2 present, a first placement after T2 + 15 | No event for that paddle (both if parallel) | `placement_disagrees_with_tag` |
| Gate: no review record for this `export_id` and these settings | The Increment 10 adapter doesn't pass derived placements to the engine (D-088) | — |

#### P-037 Derived per-zone gel application (built, Step 9d; D-111, D-112)
Built in the rule engine's exporter from the `learner_hand` box (only the hand holding the gel
bottle, A-024) and the zone boxes. Settings are placeholders.

| Condition | Outcome |
|---|---|
| Gel phase (export) | From the start to the apical tag (`first_paddle_firmly_on_the_chest`), else the earliest take of either paddle, else the end of the recording (`paddle_timing`, D-118). The export never uses 9c placements; flagged `placement_time_unknown` when the sternal placement could have been earlier |
| A frame: hand box within `gel_hand_zone_max_gap` (5% of the diagonal) of a zone box, the other visible zone at least 2× further | The frame belongs to the nearer zone (proximity, not overlap, A-025) |
| A frame: about as near to both zones | Ambiguous: belongs to neither |
| A visit to a zone (dips up to `gel_exit_frames` = 5 allowed) with at least `gel_dwell_frames` = 10 frames | An application, event `apical_gel_applied` / `sternal_gel_applied`, flagged `derived_gel_application`; separate visits count separately |
| Zone with an application | **gelled** |
| No application; zone visible and hand tracked on every frame of the bottle period | **not gelled** |
| No application; zone not visible throughout the bottle period, or the hand hidden in it | **unknown** |
| No `learner_hand` box in the gel phase | Every zone **unknown**; review issue `gel_hand_not_tracked` |
| An application without a `Gel applied` tag within 30 frames, or a tag without an application | Reported in `gel_validation.csv`/`.md`; the event is kept |
| 9d gate not passed | Neither the events nor the zone statuses reach the engine (D-112) |
| Past the 9d gate, and the 9c gate approved too | The adapter ends the gel phase at the earliest firm placement of either paddle (`gel_phase` with the 9c placements). A zone can only become more cautious: gelled with no application by then, or the bottle hand only after it → **unknown**; not gelled stays not gelled (D-118) |

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
| Derived gel applications, and the 9d gate passes for this export's ID and gel settings hash (D-112) | They become events; each zone's gel status becomes the coverage of `apical_gel` / `sternal_gel` (gelled or not gelled → covered, unknown → unknown) | — |
| Derived gel applications, 9d gate not passed, or an export before version 3 | Withheld and counted; R1 uses the tag-count proxy | — |

#### P-030 Zone coverage for an annotated recording (built, Increment 10)
| Condition | Coverage of the region (whole recording) | Intervals in the header | Decision |
|---|---|---|---|
| Annotator confirmed the zone was genuinely not visible (reviewed exception) | **not covered** | none | D-082 |
| Zone track visible on every frame | **covered** | its interval | D-074 |
| Zone track visible on only part of the recording | **unknown** | its intervals; a time window gets its own status (P-007) | D-092 |
| Zone track present but outside on every frame | **not covered** | empty | D-080 |
| No zone track | **unknown** | none | D-074 |
| The defibrillator screen (region `screen`, R5) | the same rules (no reviewed exceptions); an export without screen fields → **unknown** | as above | D-094 |
| Each paddle (regions `apical_paddle`, `sternal_paddle`, R4) | the same rules (no reviewed exceptions); an export without paddle fields (exporter version 1) → **unknown** | as above | D-108 |

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
| A visibility-only region asked by name (a paddle, for R4) | only that region's window or whole-recording status; nothing stated → unknown (D-108) |

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
The shock time comes only from the screen (D-093). It is never inferred, from the paddle removal
or anything else, and there is no fallback setting (D-115).

| Condition | Outcome | Flags |
|---|---|---|
| Two or more shocks | No shock time (not guessed) | `multiple_shocks` |
| One shock on screen | Shock time = the shock | — |
| No shock on screen | **No shock time; never inferred**, even if the paddles were removed (D-115). Shock-dependent rules are Not evaluable because of R5; resume commands stay unresolved | `no_shock` |

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
| Within 0.5 s of the shock | Unresolved | `command_near_shock` |
| Before the shock | "Continue compressions" | — |
| After the shock | "Start compressions" | — |

#### P-012 Anchor selection (built): which event gives each key time
| Condition | Outcome | Flags |
|---|---|---|
| One candidate | Its time | — |
| Several candidates | The earliest; all recorded | `multiple_candidates` |
| Only a low-confidence candidate | Absent | `low_confidence_evidence` |
| No candidate | Absent, with a reason | — |
| A start command at or before a confirmed on-screen shock | Not the restart (D-025); a mistake A7 reports | `start_command_before_shock` |
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
| A start or "resume" command is timing-ambiguous (no shock time, D-054) | **Unable to Verify, never Fail** | `no_shock_time` |
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
| The restart is needed (R7/A6, A8), but a start or "resume" command is timing-ambiguous | **Unable to Verify, never Fail**; A7 does not report it (D-054) |
| Evidence present, in order and in time | Pass – Direct |
| Evidence clearly shows the mistake | Fail, with the rule's failure code |
| Evidence weak **or missing**, and the rule has an approved inference (R3, R4) | → P-016, **before** the coverage step (D-057) |
| R8 order not directly observable | → P-015 |
| Required event missing, and no approved inference applies | → P-008 |

#### P-015 R8: apical before sternal (built, Increment 12; pending until approved)
A zone counts as visible when it is covered over the placement phase, from the earliest take
of either paddle (by time, D-118) to paddles firmly on chest, else the later of the two takes
(D-092, D-099). Derived placements are used only past the gate
(D-088).

| Condition | Outcome | Codes and flags |
|---|---|---|
| Derived placements flagged `possible_parallel_placement` | Fail; **R2 fails too, separately** (D-091, D-098) | `simultaneous`; `possible_parallel_placement` (shared cause flag), `derived_placement` |
| Both placements observed | Compare the two placement times: apical first → Pass – Direct | `wrong_order`, `simultaneous`; `derived_placement` if derived |
| A zone visible during the placement phase, its placement missing (both zones visible with one missing, or the one visible zone without its placement) | Unable to Verify, not `wrong_order`; R3 reports the missing placement (D-058) | `placement_missing` |
| One placement observed, the other paddle's zone not in view | **Unable to Verify**, no inference: the first-placement tag is the apical placement under the team's working definition (A-027), so comparing with it would be circular (D-116) | `one_zone_in_view` |
| Not determinable (no placement observed and no zone visible) | Unable to Verify; if the fallback is on and the apical paddle was taken first (by time): **assumed** apical first, to be checked by the evaluator, and the overall result cannot be Pass (D-014, D-060); the sternal paddle taken first → Unable to Verify (D-118) | — |

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
| No direct evidence (or no shock time to judge it against); the shock on screen confirmed | Pass – Inferred (D-057, D-115) | — |
| No inference and no shock time | **Not evaluable because of R5** | — |
| No inference; a low-confidence firm placement | Unable to Verify | `low_confidence_evidence` |
| No inference; both placement zones visible throughout the earliest take of either paddle → shock (D-118) | Fail | `missing` |
| No inference; a zone not visible throughout that window (for example one paddle visible: the tag is not made then, A-019) | Unable to Verify, never Fail | — |

With the shock on screen as the inference source, the coverage rows are unreachable: a shock time
always means a shock on the screen, which infers, and without one the rule is Not evaluable
because of R5 (OQ-061). A paddle removal never infers (D-115).

#### P-038 R1: gel applied twice, once to each zone, before placement (built, Increment 17; pending until approved)
The gel phase ends at the earliest firm placement of either paddle, else the earliest take of
either paddle (`paddle_order`, D-118). The order between the zones and more than two applications
are not checked (D-110, OQ-021).

| Condition | Outcome | Code and flags |
|---|---|---|
| Gel only after the first placement | Fail (D-109) | `after_placement` |
| A pass, but the other paddle's placement is unknown and could have been earlier, and gel may fall after it | Unable to Verify, never Pass (D-118) | `placement_time_unknown` |
| Past the 9d gate: both zones gelled | Pass – Direct, then the period check (P-024) | `derived_gel_application`; `timing_not_checked` while the period is unset |
| Past the gate: one gelled, the other not gelled | Fail | `applied_once` |
| Past the gate: neither gelled | Fail | `missing` |
| Past the gate: a zone unknown | Unable to Verify | — |
| Proxy (before the gate): both zones visible throughout the gel phase, 2+ separate tags | Pass – Direct, then the period check | `timing_not_checked` while unset |
| Proxy: both zones visible, 1 separate tag | Fail | `applied_once` |
| Proxy: a zone visible, no tag | Fail | `missing` |
| Proxy: one zone visible and 1+ tags, or no zone visible | Unable to Verify (the tags may all be on one zone, A-026) | — |
| Proxy: a low-confidence gel tag, no pass | Unable to Verify | `low_confidence_evidence` |
| A pass, an approved period exceeded | Fail | `outside_time_period` |

#### P-036 R4: both discharge buttons pressed (built, Increment 16; pending until approved)
The placement is `paddles_firmly_on_chest`, or past the gate the later derived placement. The
window `w` is `simultaneous_window_seconds` (annotation lag, as R3). Repeated presses: any valid
one counts; the count stays undecided (OQ-023).

| Condition | Outcome | Code and flags |
|---|---|---|
| Shock time; a press after the placement (within `w` before it counts) and at or before the shock (within `w` after it counts) | Pass – Direct | `derived_placement` if the placement is derived |
| Shock time; a valid press, no placement observed | Pass – Direct, order not checked; the overall result can't be Pass | `order_not_checked` |
| A press clearly before the placement, none valid (without a shock time: only if no press came after the placement) | Fail; comes before the inference | `before_placement` |
| Shock time; presses only clearly after the shock | Unable to Verify | `contradictory` |
| No direct evidence (or no shock time to judge it against); the shock on screen confirmed | Pass – Inferred (P-016) | — |
| No inference and no shock time | **Not evaluable because of R5** | — |
| No inference; a low-confidence press | Unable to Verify | `low_confidence_evidence` |
| No inference; both paddles visible throughout the placement → the shock (the recording's start when no placement is known) | Fail (unreachable while the shock on screen is an inference source) | `not_pressed` |
| No inference; a paddle not visible throughout that window | Unable to Verify, never Fail | — |

#### P-034 R6: paddles removed after the shock (built, Increment 14; pending until approved)
`paddles_removed_after_shock` means the paddles were removed; it doesn't prove a shock (D-104).

| Condition | Outcome | Code and flags |
|---|---|---|
| No shock time (no shock on the screen, or several) | **Not evaluable because of R5**, even if a removal is tagged: a removal doesn't show a shock (D-093, D-115) | — |
| Removal clearly before the shock (more than `removal_before_screen_tolerance_seconds`: the screen may show the shock after the discharge, D-105) | Fail | `removed_before_shock` |
| Past the gate: a derived placement ended by a real exit clearly before the shock, that paddle not placed again by the shock | Fail | `removed_before_shock`; `derived_placement` |
| Removal after the shock, or before it within `removal_before_screen_tolerance_seconds` (treated as at the shock) | Pass – Direct; limit unset, so the overall result can't be Pass (D-062); an approved "no limit" passes fully (D-103) | `timing_not_checked` |
| Removal later than an approved `shock_to_removal_seconds` | Fail | `too_late` |
| No removal, a low-confidence one exists | Unable to Verify | `low_confidence_evidence` |
| No removal, both placement zones visible throughout from the shock to the end of the recording (A-022) | Fail | `missing` |
| No removal, a placement zone not visible throughout that window | Unable to Verify, never Fail | — |

#### P-032 R2: the paddle taken first is placed before the other is taken (built, Increment 11; order-neutral since D-118; pending until approved)
"First" and "second" are by time (`paddle_order`), never by tag name: under A-027 the tag names
give identity only.

| Condition | Outcome | Code |
|---|---|---|
| Derived placements flagged `possible_parallel_placement` (only once the gate is approved) | Fail (D-091) | `simultaneous` |
| Both paddles taken within `simultaneous_window_seconds` of each other, whichever is named first | Fail (D-118) | `simultaneous` |
| Which paddle was taken first can't be established (a take missing, and that paddle not placed before the other was taken) | Unable to Verify | — |
| A take missing, but that paddle was placed before the other was taken | It was taken first; judged as below, with the flag | `take_order_from_placement` |
| The paddle taken first is placed before the other is taken | Pass – Direct, whichever paddle it is | — |
| Within `simultaneous_window_seconds` | Fail | `simultaneous` |
| The other paddle taken before the first-taken one was placed | Fail | `taken_before_first_placed` |
| The sternal paddle taken first, its placement unknown (no tag marks it) | Unable to Verify, never Fail (D-118) | `placement_time_unknown` |
| The apical paddle taken first, its placement not seen, a low-confidence one exists | Unable to Verify (D-010) | — |
| The apical paddle taken first, its placement not seen, both zones visible throughout the window between the two takes | Fail: either the paddles were placed in parallel, or the second paddle was taken before the first was placed (A-019; D-095, D-097) | `first_placement_not_observed` |
| First placement not seen, a zone not visible throughout that window | Unable to Verify | — |

#### P-016 R3/R4 inferred pass (built, Increments 15–16; direct evidence and coverage in P-035 and P-036)
The only inference source is the shock on the screen (D-115). A paddle removal is never one: it
doesn't show that a shock was delivered, and the rules refuse it as a source.

| Condition | Outcome | Flags |
|---|---|---|
| Direct evidence weak **or missing**; the shock on screen confirmed | Pass – Inferred, citing the shock (D-057) | — |
| No listed source confirmed | Back to the rule: no shock time → Not evaluable because of R5; otherwise its coverage step | — |

**R3's `missing` and R4's `not_pressed` are unreachable:** with a shock time there is a shock on
the screen, which infers; without one the rule is Not evaluable because of R5 (OQ-061 asks the
supervisor).

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

> **W-5, W-6, W-14, W-15, W-16, W-19 and W-24 are withdrawn** (D-115): they described the
> removal fallback, which no longer exists. A recording with no shock on screen has no shock time
> at all: see W-54.

### W-5 No shock on screen, paddles removed at 52 s → timing flagged (fallback `removal` only) — *withdrawn*
*Withdrawn on 2026-10-19 (D-115): a paddle removal is never taken as the shock or its time, so this pathway no longer exists.*

### W-6 Under the removal fallback, "resume compressions" at 50 s — *withdrawn*
*Withdrawn on 2026-10-19 (D-115): a paddle removal is never taken as the shock or its time, so this pathway no longer exists.*

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

### W-14 Under the removal fallback, "start compressions" before the removal → Unable to Verify — *withdrawn*
*Withdrawn on 2026-10-19 (D-115): a paddle removal is never taken as the shock or its time, so this pathway no longer exists.*

### W-15 R7/A6 under the removal fallback, delay from the removal already too long → Fail — *withdrawn*
*Withdrawn on 2026-10-19 (D-115): a paddle removal is never taken as the shock or its time, so this pathway no longer exists.*

### W-16 R7/A6 under the removal fallback, delay from the removal within the limit → Unable to Verify — *withdrawn*
*Withdrawn on 2026-10-19 (D-115): a paddle removal is never taken as the shock or its time, so this pathway no longer exists.*

### W-17 R8, one zone visible, its paddle has no placement event → Unable to Verify
*(Built in Increment 12, D-058.)*
1. Only the apical zone is visible. The first paddle was placed at 12 s, but there is no
   apical placement event.
2. P-015: the visible paddle's placement is not observed, so the order cannot be established.
   **No inference** ("the apical paddle was never placed, so sternal was first" is not shown by
   the evidence).
3. R8 → **Unable to Verify**, `placement_missing`. R3 reports the missing placement (a
   mistake in one step is never evidence of a mistake in another, D-119).

### W-18 R8, both zones visible, one placement event missing → Unable to Verify
*(Built in Increment 12, D-058.)*
1. Both zones are visible. Apical placed at 12 s; no sternal placement event.
2. P-015: the order cannot be compared → **Unable to Verify**, `placement_missing`, and **not**
   Fail `wrong_order`. R3 reports the missing sternal placement.

### W-19 A8 under the removal fallback, no ambiguous start → measured normally — *withdrawn*
*Withdrawn on 2026-10-19 (D-115): a paddle removal is never taken as the shock or its time, so this pathway no longer exists.*

### W-20 R3 with no direct placement evidence, removal confirmed → Pass – Inferred — *withdrawn*
*Withdrawn on 2026-10-19 (D-115): R3 no longer infers from the paddle removal. With no direct evidence and no shock on the screen, R3 is Not evaluable because of R5; with a shock on the screen, it is Pass – Inferred from the shock.*

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
4. Since D-118 the fallback applies only when the apical paddle was taken first (by time). With the
   sternal paddle taken first, R8 stays Unable to Verify.

### W-24 Under the removal fallback, "resume compressions" before the removal → restart ambiguous — *withdrawn*
*Withdrawn on 2026-10-19 (D-115): a paddle removal is never taken as the shock or its time, so this pathway no longer exists.*

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

### W-49 The apical placement disagrees with the first-placement tag → no event for the apical paddle
*(Revised by D-118.)*
1. Both zones visible. The derived apical placement is at frame 20, but T1 (the apical placement
   under the team's working definition, A-027) is at frame 36, 16 frames later.
2. P-031: more than the 15-frame window → **no event for the apical paddle**, review issue
   `placement_disagrees_with_tag` (D-086). The sternal placement is unaffected: T1 never decides
   the order.
3. One-zone view instead (LL, apical only): the same check. An apical placement at frame 50 with
   T1 at 30 gives no event.

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
*(Built; D-093, D-094, D-115.)*
1. P-001/P-030: LL shows the apical zone throughout. There is no sternal zone track and no
   `defibrillator_screen` track, so the sternal zone and the screen are **unknown**. The paddles
   were removed at 15.94 s.
2. P-009: no shock on screen → **no shock time**, `no_shock`. The removal is never used as a
   shock (D-115).
3. R5 (Increment 13): no shock on screen while the screen is unknown → **Unable to Verify**,
   never Fail. Had the screen been in view throughout and no shock seen, R5 would fail.
4. Every shock-dependent rule (R3, R4, R6, R7/A6, A1–A4, A7, A8) → **Not evaluable because of
   R5**. Resume commands stay unresolved (`no_shock_time`).
5. R3/R4 don't infer from the removal: it doesn't show that a shock was delivered (D-115).

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
5. P-017: **Fail**, listing two mistakes, R2 and R8, each on its own evidence (D-119). Whether this
   should count as one mistake is OQ-059 (supervisor).
6. Gate not approved: neither rule sees the derived placements. R2 → `first_placement_not_observed`;
   R8 → Unable to Verify, `placement_missing` (both zones in view, no placement observed).

### W-58 R8 from an LL view: only one zone in view
*(Built in Increment 12; changed 2026-10-19, D-116.)*
1. LL: the apical zone is visible throughout the placement phase; there is no sternal zone track
   (unknown, so not visible). First placement (the first-placement tag) at 7.0 s.
2. Apical placement at 7.2 s, 11 s or 4 s → **Unable to Verify**, `one_zone_in_view`. The order
   can't be established from one zone.
3. **Why there is no inference any more:** under the team's working definition (A-027) the first-placement
   tag is the apical placement. A sternal-first learner (sternal taken and placed first) still gets
   the tag at the apical placement, so the apical placement always "matches" it. The old one-zone
   inference therefore gave a false **Pass – Inferred**.
4. No apical placement although the apical zone was in view → **Unable to Verify**,
   `placement_missing` (D-058), as before.

### W-59 A zone in view only after the placement phase does not count
*(Built in Increment 12; D-099.)*
1. Placement phase 5–14 s (the earliest take of either paddle → paddles firmly on chest). The apical zone is
   visible throughout it; the sternal zone only from 20 s.
2. Only the apical placement is observed. The sternal zone was not in view during the phase, so
   its missing placement is **not** `placement_missing`. It is a one-zone view: **Unable to
   Verify**, `one_zone_in_view`, as in W-58 (D-116).

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

### W-69 R3 from the removal, without a shock on the screen — *withdrawn*
*Withdrawn on 2026-10-19 (D-115): without a shock on the screen R3 is Not evaluable because of R5, even with a removal tagged.*

### W-70 R3 from derived placements
*(Built in Increment 15; D-088, D-106.)*
1. No firm placement tag. Derived placements: apical at 7 s, sternal at 12 s; shock at 15 s.
2. Gate approved → **Pass – Direct**, flagged `derived_placement`.
3. Gate not approved → the placements never reach R3 → **Pass – Inferred** from the shock.
4. Only one derived placement, or one after the shock → not direct evidence; the inference or
   coverage decides.

### W-71 R3 and R4 from the removal alone, in a view without the screen — *withdrawn*
*Withdrawn on 2026-10-19 (D-115): in a view without the screen, R3 and R4 are Not evaluable because of R5; a removal doesn't infer them.*

### W-72 R4 with a press and a placement
*(Built in Increment 16; D-108.)*
1. Paddles firmly on chest at 10 s, shock on the screen at 15 s.
2. Press at 13 s → **Pass – Direct**. Press at 8 s → **Fail `before_placement`**, even though the
   shock would support an inference. Press at 9.5 s (within 0.5 s of the placement) → Pass.
3. Press only at 17 s → **Unable to Verify**, `contradictory`: the screen showed the shock first.
4. No placement tag, gate not approved, press at 13 s → **Pass – Direct**, `order_not_checked`; the
   overall result is Incomplete.

### W-73 R4 from derived placements
*(Built in Increment 16; D-088, D-108.)*
1. Gate approved; no firm placement tag. Derived placements: apical at 7 s, sternal at 12 s, so the
   placement is 12 s. Shock on the screen at 15 s.
2. Press at 13 s → **Pass – Direct**, `derived_placement`. Press at 10 s, between the two placements
   → **Fail `before_placement`**.

### W-74 R4's coverage: the paddles in view
*(Built in Increment 16; D-108. Reached only if the shock on screen isn't an inference source.)*
1. Placement at 10 s, shock at 15 s, no press, no inference.
2. Both paddles visible from 10 s to 15 s → **Fail `not_pressed`**.
3. The sternal paddle visible only until 12 s, out of view, or no paddle tracks → **Unable to
   Verify**.

### W-75 R1 by the tag-count proxy, both zones in view
*(Built in Increment 17; D-109, D-113, A-026. Before the 9d gate.)*
1. LS view: both zones visible from 0 s; first placement tagged at 10 s, so the gel phase is 0–10 s.
2. `Gel applied` at 3 s and 6 s → two separate applications → **Pass – Direct**,
   `timing_not_checked` (period unset); the overall result is Incomplete.
3. Only one tag, or two tags 0.3 s apart (under `gel_minimum_gap_seconds`, 0.4 s) → **Fail
   `applied_once`**. No tag → **Fail `missing`**.
4. The risk: the learner's arm can hide the nozzle while the zone is visible (A-026).

### W-76 R1 by the proxy with one zone in view
*(Built in Increment 17; D-113.)*
1. LL view: only the apical zone is visible in the gel phase.
2. No tag → **Fail `missing`**. One or two tags → **Unable to Verify**: they may all be on the
   apical zone.

### W-77 Gel only after the paddles were placed
*(Built in Increment 17; D-109.)*
1. First placement at 10 s; the only `Gel applied` tag at 12 s.
2. **Fail `after_placement`**, whatever the zones show. With a tag at 3 s as well, the late tag
   doesn't matter: the 3 s tag is counted, and the proxy decides (one application → `applied_once`).

### W-78 Step 9d on one video
*(Built in Step 9d; D-111.)*
1. Gel phase 0–80 frames; the bottle hand is tracked from frame 5 to 70.
2. Frames 20–35: the hand touches the apical zone; the sternal zone is far away → one apical
   application (16 frames ≥ 10). Frames 45–60 near the sternal zone → one sternal application.
   Both zones gelled.
3. The hand only 30 px from each of two neighbouring zones → ambiguous frames, no application.
4. The hand marked out of view on frames 50–55, and the sternal zone had no application →
   sternal **unknown**.
5. No hand box in the gel phase → both zones unknown, review issue `gel_hand_not_tracked`.

### W-79 R1 per zone, past the 9d gate
*(Built in Increment 17; D-110, D-112, D-113.)*
1. The 9d gate is approved for this export; regions `apical_gel` and `sternal_gel` are set.
2. Derived applications on both zones before the placement → **Pass – Direct**,
   `derived_gel_application`.
3. Apical gelled, sternal not gelled → **Fail `applied_once`**, even with two `Gel applied` tags
   (the per-zone status wins over the tag count).
4. Apical gelled, sternal unknown (hand hidden) → **Unable to Verify**.
5. Gate not approved → the same video uses the proxy (W-75).

### W-80 R1's time period
*(Built in Increment 17; D-103, D-110.)*
1. Applications at 3 s and 6 s.
2. Period unset → Pass with `timing_not_checked`. An approved 2 s → **Fail
   `outside_time_period`**. An approved "no limit" → Pass, fully checked.

### W-81 A sternal-first learner, one paddle at a time
*(Built; D-118, A-027.)*
1. Gel at 1 s and 2 s. Sternal paddle taken at 3 s (`second_paddle_taken`, the sternal paddle under
   A-027) and placed at 5 s (a per-paddle placement). Apical paddle taken at 6 s
   (`first_paddle_taken`) and placed firmly at 9 s (`first_paddle_firmly_on_the_chest`).
2. `paddle_order`: the sternal paddle was taken first; the earliest firm placement is 5 s, certain.
3. **R2 Pass – Direct:** the paddle taken first (sternal) was placed before the other was taken.
4. **R8 Fail `wrong_order`:** the sternal paddle was placed first. Only R8 reports the order.
5. **R1 Pass:** the gel came before the first placement, at 5 s (not the apical one at 9 s). Gel at
   6.5 s and 7.5 s instead → **Fail `after_placement`**.

### W-82 A sternal-first learner whose sternal placement isn't seen
*(Built; D-118.)*
1. As W-81, but no event marks the sternal placement: no tag exists for it, and derived placements
   reach the engine only past the gate.
2. **R2 → Unable to Verify**, `placement_time_unknown`: the sternal paddle was taken first, but when it
   was placed is unknown. Never a Fail.
3. **R1:** the sternal placement could be any time after its take at 3 s. Gel at 1 s and 2 s is
   certainly before it → Pass. Gel at 4 s may be after it → **Unable to Verify**,
   `placement_time_unknown`, never Pass.

### W-83 Step 9c on a sternal-first video
*(Built; D-118.)*
1. Sternal placement derived at frame 30, apical at frame 60; T1 tagged at frame 60.
2. Before D-118, T1 was taken as "the earlier placement": the earliest (sternal, frame 30) was 30
   frames from T1, so both placements were dropped (`placement_disagrees_with_tag`).
3. Now T1 cross-checks only the apical placement (frame 60, in agreement). Both events are kept,
   and R8 can report `wrong_order`.

### W-84 Step 9d with and without the 9c gate
*(Built; D-118.)*
1. A sternal-first video: sternal paddle taken at 2 s, placed at 3 s (only 9c sees it), apical
   paddle taken at 4 s, tagged placed at 5 s. Gel on the apical zone at 1.2 s and on the sternal
   zone at 3.6 s. The 9d gate is approved.
2. The export's gel phase ends at the apical tag (5 s), flagged `placement_time_unknown` from 2 s:
   no tag marks the sternal placement, and the export never uses 9c.
3. **9c gate closed:** both zones gelled, but the sternal gel at 3.6 s may come after the sternal
   placement → R1 **Unable to Verify**, `placement_time_unknown`.
4. **9c gate approved:** the adapter ends the gel phase at the sternal placement (3 s). The sternal
   zone's only application is later, so it becomes **unknown** → R1 Unable to Verify (apical zone
   gelled, sternal zone unknown).

### W-85 A sternal-first learner and the R3 and R8 windows
*(Built; D-118.)*
1. Sternal paddle taken at 3 s (`second_paddle_taken`, the sternal paddle under A-027), apical at
   6 s, paddles firmly on the chest at 14 s.
2. R8's placement phase and R3's missing-placement window start at 3 s, the earliest take of
   either paddle, not at `first_paddle_taken` (6 s). A zone in view only from 4 s therefore doesn't
   count as visible over them.
