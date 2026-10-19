# Rule engine: anomaly and rejection codes

Every code the rule engine can raise, which step raises it, and why. **Extend this file in every
increment that adds a code.**

## Conventions

- **Rejection:** a `TimelineError` with `.code`. The timeline cannot be assessed and **no
  assessment is produced**.
- **Anomaly:** an `Anomaly(code, message, event_ids, details)` in `PreparedTimeline.anomalies`
  (later also in the context). The assessment still runs; the anomaly is shown in the report,
  and rules take it into account.
- **Flag:** a short code on a rule result (from Increment 6 on). It explains why a rule gave
  Unable to Verify instead of Pass or Fail.
- **Event time rule:** all order and timing comparisons use each event's **`start`** time. A
  point event has `start == end`. For an interval event (for example a spoken command), `start`
  is when it began. Gaps such as "time between two shocks" are differences of start times.
- **Config errors** (`ConfigError`) are not listed here. They stop the run before any timeline is
  read, and their messages name the file and entry (see `rules/config.py`).

## Rejections (`TimelineError`, raised by `rules/prepare.py`, Increment 3)

| Code | When | Why |
|---|---|---|
| `not_a_list` | The timeline is not a list of events (for example a number, a string or a dict) | The core only accepts the shared `Event` list |
| `not_an_event` | An item is not a `schemas.event.Event` (for example a raw dict) | Source formats must be converted by an input adapter first |
| `missing_event_id` | An event has no `event_id` | Rule results cite evidence by ID; IDs come from `pipeline.merge_timeline` or an adapter |
| `duplicate_event_id` | Two events share an `event_id` | Citations would be ambiguous |
| `multiple_camera_angles` | Events carry more than one non-null `camera_angle` | One assessment is one camera recording. Events with no angle (for example audio) are ignored by this check |
| `multiple_recordings` | Events carry more than one `metadata.task_id` | One assessment is one recording |
| `no_confidence_threshold` | An event's source has no threshold in `engine.yaml` | The safety check cannot decide whether to use the event, so it refuses rather than guessing |

## Rejections (`TimelineError`, raised by `rules/coverage.py`, Increment 4)

| Code | When | Why |
|---|---|---|
| `invalid_header` | The timeline header is not a mapping, has unknown keys, a non-positive `duration_seconds`, `analyses_run` values other than true/false, or an unknown coverage scope or status | Coverage is decided from the header, so a malformed header cannot be trusted |
| `header_mismatch` | The header contradicts its events: a different camera angle or recording ID; an event (kept or excluded) that **ends** more than `duration_tolerance_seconds` (placeholder 0.5 s) after `duration_seconds`; or `analyses_run` says a modality did not run although events of that modality exist | Contradictory input: assessing it would give coverage that conflicts with the evidence. The tolerance absorbs rounding at the end of a recording |

## Rejections (`RegistryError`, raised by `rules/engine.py` and `rules/registry.py`, Increment 7)

Checked when the engine loads, before any timeline is read (D-064). `RegistryError` is a kind of
`ConfigError` with a stable `.code`; no assessment is produced.

| Code | When | Why |
|---|---|---|
| `approved_rule_not_registered` | A rule is `approved` (and enabled, without `same_as`) in `rules.yaml`, but has neither a registered `@rule` function nor an `implementation` path | An approved rule must be evaluated. Reporting it as "pending" would hide a missing implementation |
| `registered_rule_not_in_config` | A `@rule` function is registered under an ID that is not in the full catalogue `configs/rules.yaml` (checked against the catalogue whatever config is being assessed) | Probably a typo in the ID. The rule would otherwise never run. The message names the function's location. A smaller config that leaves a catalogued rule out is **not** an error; that rule is simply not run |
| `duplicate_rule_registration` | Two different functions are registered under one rule ID | Which one runs would be ambiguous. The message names both locations (module, function, file and line). The same function imported twice is not a duplicate |
| `unknown_required_event` | A rule's `requires=` names an event that is not in the vocabulary | A typo would otherwise make the rule silently find nothing |

## Anomalies (`rules/prepare.py`, Increment 3)

| Code | When | Why | Details |
|---|---|---|---|
| `multiple_shocks` | More than one confident `shock_delivered_on_screen` | Every recording has exactly one shock, so more than one is a data problem. Shock-dependent rules give Unable to Verify. Duplicates are **not merged** (merging is upstream's job) | `within_simultaneous_window` (true means "possibly the same shock detected twice"), `smallest_gap_seconds`, `simultaneous_window_seconds` |
| `mixed_evidence_sources` | The same canonical event comes from human annotation **and** a model | One assessment should use one kind of evidence; otherwise a human tag could silently fill a model miss. Flag only | — |
| `unknown_labels_present` | Any label is not in `vocabulary.yaml` | Shows a possible naming mismatch, instead of silently treating the event as missing | `labels` (`source:label`) |
| `count_violation` *(Increment 9a, D-071)* | At least one confident event of a canonical event, and the count is outside its `engine.yaml` `expected_counts` range. One anomaly per event. Not raised for unlimited or undecided counts, or when there is no confident event at all (that is a missing event, A-018) | A one-off event seen twice usually means a detection or annotation problem. **Never a Fail by itself**; nothing is merged. A rule may fail on a repeated action only once the supervisor decides it is a mistake. Two shocks raise both this and `multiple_shocks` | `event`, `expected` (for example `{exactly: 1}`), `found`; for events limited to one: `possible_duplicates` (pairs of event IDs within the window, "possibly the same incident detected twice") and `simultaneous_window_seconds` |
| `paddle_identity_conflict` *(Increment 9a, D-071)* | Two or more confident `apical_paddle_placed` and no `sternal_paddle_placed`, or the reverse | The paddle identity was probably swapped or lost (detection or annotation), so placement order cannot be trusted. Never a Fail by itself | `apical_paddle_placed`, `sternal_paddle_placed` (the counts) |

`count_violation` and `paddle_identity_conflict` are review anomalies: with either, the overall
result is never Pass (D-072).

Low-confidence events are not anomalies. They are listed in `PreparedTimeline.excluded`
(`ExcludedEvent`, reason `below_confidence_threshold`) and can be looked up with
`excluded_named(name)`.

## Flags on missing-event outcomes (`rules/coverage.py`, Increment 4)

`Coverage.missing(event_name)` returns a `MissingOutcome`. Rules copy its flags onto their
result (from Increment 6 on).

| Code | When | Meaning |
|---|---|---|
| `low_confidence_evidence` | A required event is missing, but an excluded low-confidence event of the same canonical name exists | The outcome is Unable to Verify, **never Fail**, under every policy setting. Not configurable. The excluded event IDs are listed |
| `coverage_policy_undecided` | The policy setting that decided the outcome is marked `undecided` (today: `coverage_policy.outcomes.unknown`) | The outcome follows the interim value (Unable to Verify) until the team decides |

## Context flags (`rules/context.py`, Increment 5)

Flags on **anchors** (key times such as the shock time), on **command resolutions**, and on
**elapsed times** between anchors. `elapsed()` carries the flags of both anchors, so every
timing result built on a flagged anchor is flagged too. Rules copy them onto their results
(from Increment 6 on).

| Code | On | When | Meaning |
|---|---|---|---|
| `no_shock` | Shock anchor | No confident shock on screen (D-093) | No shock time; it is never inferred, and a paddle removal never stands in for it (D-115). Shock-dependent rules report "not evaluable because of R5", and resume commands stay unresolved |
| `multiple_shocks` | Shock anchor, and every elapsed time using it | The `multiple_shocks` anomaly is present | No shock time is chosen (**not guessed**, even if a removal exists). Candidates are listed |
| `multiple_candidates` | Any anchor | More than one event could be the anchor (for example two `first_paddle_placed`) | The **earliest** is used, and all candidate IDs are recorded in `Anchor.candidates` |
| `command_near_shock` | Command resolution | A `resume_compressions_command` starts within `simultaneous_window_seconds` of the shock time | Left **unresolved**: it cannot be classified as continue (before) or start (after) |
| `start_command_before_shock` | Start anchor | A `start_compressions_command` starts at or before a **confirmed on-screen** shock (D-025) | It does **not** count as the restart (it is listed in `Anchor.ineligible`). A7 reports it as a sequence problem. Never raised under the removal fallback (D-053) or without a shock time (D-054) |
| `no_shock_time` | Command resolution, start anchor | A `resume_compressions_command` while there is no shock time (no shock, or multiple shocks); or the start anchor when there is no shock time | Left **unresolved**; the start anchor is absent, because "the earliest start after the shock" cannot be identified, and every start command is listed as ambiguous (not a mistake, D-054) |
| `unresolved_commands` | Continue and start anchors | At least one ambiguous command is unresolved | An unresolved command might have been the continue or start command, so these anchors may be incomplete |
| `low_confidence_evidence` | Absent anchor | No confident event, but an excluded low-confidence event of the same name exists | The anchor is absent because of weak evidence, not because nothing happened |

`ProcedureContext.missing(name)` extends `Coverage.missing`. A low-confidence ambiguous command
that could have been `name` (resolved to it, or unresolvable) also gives Unable to Verify,
flagged `low_confidence_evidence`.

## Shared-check flags (`rules/checks.py`, Increment 6)

Flags that the shared checks (P-019 to P-025) put on rule results. Every result also carries the
flags of each anchor, elapsed time and missing-event outcome it used (`flags_of`).

| Code | On | When | Meaning |
|---|---|---|---|
| `timing_not_checked` | Rule result (P-024) | The rule's time limit is null, not approved, or the interval cannot be measured | The rule judged presence and order only; its reason says "timing not checked" (D-005). It stays a Pass at rule level, but the overall result cannot be Pass (D-062). **Not raised** for an approved "no limit" (`no_limit: true`), which is a decision that timing doesn't matter (D-103) |
| `limit_not_approved` | Rule result (P-024) | A time limit has a value, or `no_limit: true`, but no approver | The value is not used (D-061). Timing is not checked, and the overall result cannot be Pass (D-062) |
| `order_not_checked` | Rule result (R5, P-033; R4, P-036) | An order requirement is not set (R5's `preceding_steps`, OQ-013), or one of the steps it needs was not observed (R4: no placement observed, so the press can't be checked against it) | The rule checked presence only, or the order against the observed steps only. Like `timing_not_checked`, the overall result cannot be Pass (D-100) |

Rule outcome kinds (`rules/outcome.py`) are not codes, but for reference: `pass_direct`,
`pass_inferred`, `fail`, `unable_to_verify`, `not_evaluable`, `pending`, `assumed`,
`engine_error`. The last five map to the shared status `unable_to_assess` (D-045). `pending`,
`assumed` and `engine_error` prevent an overall Pass (D-055, D-060, D-063). An `engine_error`
result names the exception in its reason (P-026).

## Overall-result flags (`rules/policy.py`, Increment 8)

Flags on the overall result (P-017), not on rule results.

| Code | When | Meaning |
|---|---|---|
| `timeline_needs_review` | The timeline has an anomaly listed in `review_anomalies` (`unknown_labels_present`, `multiple_shocks`, `mixed_evidence_sources`, D-069; `count_violation`, `paddle_identity_conflict`, D-072) | The result can never be Pass. A Fail stays Fail with this flag; otherwise the result is Incomplete. The anomalies are listed (D-065) |
| `development_data` | Any rule result carries `annotation_coverage_assumed` | The result comes from annotation data and is not a real assessment (D-066) |
| `overall_policy_undecided` | No Fail and nothing incomplete, but something is unverified, while `unable_to_verify_outcome` is undecided | The result is `unable_to_verify`, naming the undecided setting (OQ-002) |
| `no_rules_evaluated` | No rule was evaluated (e.g. every rule disabled) | Incomplete, never Pass (D-068) |
| `demo_only` | The config is a demo (`demo: true`, `configs/rule_engine/demo/rules_demo.yaml`) | DEMO ONLY: the rules are not approved by the supervisor; never a real assessment (D-114) |

## Header flags (`rules/coverage.py` `HEADER_FLAGS`, Increment 10)

Set in the timeline header by an adapter. The engine copies them onto every rule result of
that timeline (`rules/engine.py`).

| Code | Raised by | Meaning |
|---|---|---|
| `annotation_coverage_assumed` | Annotation adapter (P-001, Increment 10) | The timeline comes from CVAT annotation, and its `analyses_run: {video: true}` is a development assumption: annotators tag only what is visible from that angle, so a missing tag may mean "not visible". Every result carries this flag, and the overall result is marked `development_data` (D-066), so it is never mistaken for a real assessment |

## Rule-result flags (`rules/video_rules.py` `FLAGS`, Increments 11 to 17)

Raised by R2, R8, R3, R4 and R1 (P-032, P-015, P-035, P-036, P-038). They report pending until they are approved.

| Code | Raised by | Meaning |
|---|---|---|
| `possible_parallel_placement` | R2 and R8 | **Shared cause flag** (D-098). Derived placements, past the gate, show both paddles placed at the same time. R2 and R8 are separate checklist criteria, so **both fail with `simultaneous`**, and both carry this flag so the feedback can explain that one action caused both failures. Not a dependency cascade: R8 is evaluated on its own (the apical paddle was not placed first). One mistake or two: OQ-059 |
| `derived_placement` | R2 and R8 | The result rests on a placement derived from the annotated boxes (D-081), used only past the gate (D-088) |
| `placement_missing` | R8 (D-058) | A paddle's zone was in view during the placement phase (D-099), but its placement event is missing: either the one visible zone's paddle, or one of two visible placements. R8 gives Unable to Verify, not `wrong_order`, and R3 reports the missing placement (one mistake reported once) |
| `contradictory` | R8, R4 | R8: the only visible paddle was placed clearly before the first placement. R4: the buttons were pressed only after the shock on the screen (D-108). Unable to Verify |
| `derived_gel_application` | R1 (D-111, D-112) | The result rests on a per-zone gel application derived from the `learner_hand` and zone boxes, used only past the 9d gate |
| `inferred_fail_policy_undecided` | R8 (D-015) | The one-zone inference shows the sternal paddle first (an inferred mistake). It is Unable to Verify until `inferred_fail_outcome` is decided (OQ-005) |

## Annotation export and audit codes (Step 9b; not rule-engine codes)

These come from the separate exporter and audit (`annotation/export_rule_engine_records.py`,
`annotation/audit_rule_engine_checks.py`, D-074). They describe the annotation data, never the
learner, and never reach a rule result or the report.

**Exporter (`export_issues.csv`, P-028):**

| Code | Severity | When |
|---|---|---|
| `fps_missing` | error | The video is not in `video_conversion.csv`; no record is written (D-076) |
| `frame_count_mismatch` | warning | The backup's frame count differs from the conversion report |
| `tag_outside_frames` | warning | A tag lies outside the task's frame range (it is still exported) |
| `zone_shape_without_track` | review | A zone drawn as a single-frame shape; not converted to visibility |
| `duplicate_task` | error | The same task in a second archive; the first copy is kept |
| `unrecognized_task_name`, `invalid_cvat_json`, `missing_annotations_json`, `no_tasks_in_archive`, `no_zip_archives`, `unreadable_zip` | error | The backup cannot be read as a CVAT task |
| `placement_duplicate_paddle_box` | review | Step 9c (P-031): two boxes of one paddle label overlap during its placement, so no event for that paddle (D-087). Ananth fixes the tracks, which also affect the training labels |
| `placement_disagrees_with_tag` | review | Step 9c: a derived placement contradicts T1 or T2 (D-086), so no event (for both paddles when the earlier one disagrees with T1) |
| `gel_hand_not_tracked` | review | Step 9d (P-037): no `learner_hand` box in the gel phase, so every zone's gel is unknown (D-111) |

**Flags on derived placement events (`derived_events[].flags`, Step 9c):** `derived_placement`
(every derived event; it is direct evidence with the method in metadata, D-081) and
`possible_parallel_placement` (T1 not tagged and both placements within
`simultaneous_window_seconds`, D-086; enough for R2/R8 to Fail `simultaneous` once the gate is
approved, D-091). They start as exporter flags. Since Increment 12, R2 and R8 carry both onto
their results as rule-result flags (see above; output contract v5). The reasons for "no event" (zone unknown, never settled, T1 missing) are
in `placement_validation.csv`, not export issues.

**Flags on derived gel events (`derived_gel_events[].flags`, Step 9d):** `derived_gel_application`
(every derived gel event; direct evidence with the zone, method and settings in metadata, D-111).
R1 carries it onto its results. Disagreements with the `Gel applied` tags are in
`gel_validation.csv`, not export issues.

**Audit review list (`issues.csv`, P-029):**

| Code | When |
|---|---|
| `duplicate_paddle_box` | Two or more boxes of one paddle label on the same frames (frame range) |
| `zone_moves_like_paddle` | A zone track's centre moves more than 5% of the frame diagonal; names any paddle box it overlaps (IoU ≥ 0.5) |
| `repeated_incident_tag` | The same tag twice within 15 frames: possibly the same incident tagged twice |
| `zone_pattern_off` | Zone tracks differ from the view's usual pattern (config), including no zone; missing zones excused by a reviewed exception don't count (D-077, D-082) |
| `zone_exception_contradicted` | A reviewed "not visible" exception for a zone that is visible |
| `zone_pattern_unknown_view` | No usual pattern is configured for the view |
| `gel_hand_not_tracked` | No `learner_hand` box before the first-placement tag (else `first_paddle_taken`): gel applications can't be derived (9d, D-111) |

**Audit information only (`info.csv`), never annotation issues:** `tag_sequence` (the learner's
order), `repeated_tag` (the same tag further apart than 15 frames), `first_placement_tag_missing`,
`zone_track_never_visible` (counts as not covered, D-080), `zone_exception_confirmed`.

## Rule failure codes (planned, Increments 11 to 23)

A Fail carries one of these codes; they come from the brief's rule table. They become code as
each rule is built. Per-rule status is in [rules_status.md](rules_status.md).

| Rule | Failure codes |
|---|---|
| R1 Gel applied twice, once to each zone, before placement (**built**, Increment 17, P-038; reported pending until approved) | `after_placement` (gel only after the first placement, D-109), `applied_once` (one zone gelled and the other not, or one separate tag with both zones visible), `missing` (no gel while it could have been seen), `outside_time_period` (only once an approved period is exceeded; unset now) (D-110, D-113) |
| R2 Second paddle after first placed (**built**, Increment 11, P-032; reported pending until approved) | `simultaneous` (also a possible parallel placement once the gate is approved, D-091), `taken_before_first_placed`, `first_placement_not_observed` (no first placement seen while both zones were visible throughout the window: either a parallel placement or the second paddle taken first, A-019, D-097; it replaces the brief's original "first missing" code) |
| R8 Apical before sternal (**built**, Increment 12, P-015; reported pending until approved) | `wrong_order` (direct, or inferred once the inferred-fail setting is decided as fail, D-015), `simultaneous` (also a parallel placement past the gate, with the cause flag, D-098) |
| R3 Paddles firmly on chest (**built**, Increment 15, P-035; reported pending until approved) | `placed_after_shock` (a firm placement tagged only after the shock), `missing` (no firm placement and no inference, while both placement zones were visible from first paddle taken to the shock, D-106); `not_in_zone` is not produced until the chest regions are approved (OQ-012) |
| R4 Both discharge buttons pressed (**built**, Increment 16, P-036; reported pending until approved) | `before_placement` (a press clearly before the placement, none valid), `not_pressed` (no press and no inference, while both paddles were visible from the placement to the shock, D-108; unreachable while either inference source is listed, D-107) |
| R5 Shock confirmed on screen (**built**, Increment 13, P-033; reported pending until approved) | `missing` (no shock while the screen was visible throughout paddles firmly on chest → paddles removed, D-101), `wrong_order` (shock before a preceding step, once those are set, D-100) |
| R6 Paddles removed after shock (**built**, Increment 14, P-034; reported pending until approved) | `removed_before_shock` (a removal more than the removal-before-screen tolerance before the shock, D-105, or, past the gate, a derived placement ended by a real exit before it, D-104), `missing` (no removal while both placement zones were visible from the shock to the end of the recording, A-022), `too_late` (only once an approved removal time limit is exceeded; the limit is unset now) |
| A1 Oxygen away | `missing`, `after_shock` |
| A2 Continue compressions | `missing`, `wrong_stage` |
| A3 All stand clear | `missing`, `after_shock` |
| A4 Stop compressions | `missing`, `after_shock`, `wrong_order` |
| A5 Shock command | `missing` |
| R7 / A6 Restart compressions promptly | `missing`, `before_shock`, `too_late` |
| A7 Command sequence | `wrong_order` (a missing command is "not evaluable because of Ax", D-027) |
| A8 Pre-shock pause | `pre_shock_pause` (mistake label "Pre-Shock Pause") |

**Built (Increment 7, P-026):** `unspecified` is the failure code of a Fail from a rule plugged
in through the shared-contract `implementation: module:function` path. The shared `RuleResult`
has no failure code, so the engine cannot name the mistake. No catalogued rule uses that path.

The codes the feedback module may receive, with their status, are listed in
[output_contract.md](output_contract.md) (D-070).
