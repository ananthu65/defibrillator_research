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

## Anomalies (`rules/prepare.py`, Increment 3)

| Code | When | Why | Details |
|---|---|---|---|
| `multiple_shocks` | More than one confident `shock_delivered_on_screen` | Every recording has exactly one shock, so more than one is a data problem. Shock-dependent rules give Unable to Verify. Duplicates are **not merged** (merging is upstream's job) | `within_simultaneous_window` (true means "possibly the same shock detected twice"), `smallest_gap_seconds`, `simultaneous_window_seconds` |
| `mixed_evidence_sources` | The same canonical event comes from human annotation **and** a model | One assessment should use one kind of evidence; otherwise a human tag could silently fill a model miss. Flag only | — |
| `unknown_labels_present` | Any label is not in `vocabulary.yaml` | Shows a possible naming mismatch, instead of silently treating the event as missing | `labels` (`source:label`) |

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
| `shock_time_from_removal` | Shock anchor, every elapsed time using it, and commands resolved against it | No confident shock on screen, so the shock time is the first `paddles_removed_after_shock` | Removal happens **after** the shock, so a delay measured from it looks **shorter** than it really was. A command between the real shock and the removal may be classified as "before the shock" |
| `no_shock` | Shock anchor | Neither a shock on screen nor a paddle removal | No shock time. Shock-dependent rules report "not evaluable because of R5" |
| `multiple_shocks` | Shock anchor, and every elapsed time using it | The `multiple_shocks` anomaly is present | No shock time is chosen (**not guessed**, even if a removal exists). Candidates are listed |
| `multiple_candidates` | Any anchor | More than one event could be the anchor (for example two `first_paddle_placed`) | The **earliest** is used, and all candidate IDs are recorded in `Anchor.candidates` |
| `command_near_shock` | Command resolution | A `resume_compressions_command` starts within `simultaneous_window_seconds` of the shock time | Left **unresolved**: it cannot be classified as continue (before) or start (after) |
| `command_before_removal` | Command resolution; start anchor | The shock time comes from removal, and a `resume_compressions_command` (D-024) or an explicit `start_compressions_command` (D-053) starts at or **before** the removal | **Timing-ambiguous:** the real shock happened at an unknown time before the removal, so the command may be a genuine restart. A resume command is left unresolved. A start command is listed in `Anchor.ambiguous`: not counted as the restart and **not a mistake**. R7/A6 and A8 give Unable to Verify (not Fail), and A7 does not report it |
| `start_command_before_shock` | Start anchor | A `start_compressions_command` starts at or before a **confirmed on-screen** shock (D-025) | It does **not** count as the restart (it is listed in `Anchor.ineligible`). A7 reports it as a sequence problem. Never raised under the removal fallback (D-053) or without a shock time (D-054) |
| `no_shock_time` | Command resolution, start anchor | A `resume_compressions_command` while there is no shock time (no shock, or multiple shocks); or the start anchor when there is no shock time | Left **unresolved**; the start anchor is absent, because "the earliest start after the shock" cannot be identified, and every start command is listed as ambiguous (not a mistake, D-054) |
| `unresolved_commands` | Continue and start anchors | At least one ambiguous command is unresolved | An unresolved command might have been the continue or start command, so these anchors may be incomplete |
| `low_confidence_evidence` | Absent anchor | No confident event, but an excluded low-confidence event of the same name exists | The anchor is absent because of weak evidence, not because nothing happened |

`ProcedureContext.missing(name)` extends `Coverage.missing`. A low-confidence ambiguous command
that could have been `name` (resolved to it, or unresolvable) also gives Unable to Verify,
flagged `low_confidence_evidence`.

## Planned flags (later increments)

The decision points that will raise these are P-001, P-015 and P-018 in
[decision_flow.yaml](decision_flow.yaml).

| Code | Step | Meaning |
|---|---|---|
| `annotation_coverage_assumed` | Annotation adapter and report (Increment 10) | The timeline comes from CVAT annotation, and its `analyses_run: {video: true}` is a development assumption: annotators tag only what is visible from that angle, so a missing tag may mean "not visible". Every result built on it carries this flag, so it is never mistaken for a real assessment |
| `inferred_fail_policy_undecided` | R8 (Increment 12) | An inferred Fail gives Unable to Verify until `inferred_fail_outcome` is decided |
| `contradictory` | Rules (for example R8) | Evidence contradicts itself; Unable to Verify |
| `placement_missing` | R8 (Increment 12; proposed, OQ-040) | A visible zone's paddle has no placement event, or one of two visible placements is missing. R8 gives Unable to Verify, not `wrong_order`, and R3 reports the missing placement (one mistake reported once) |

## Rule failure codes (planned, Increments 11 to 23)

A Fail carries one of these codes; they come from the brief's rule table. They become code as
each rule is built. Per-rule status is in [rules_status.md](rules_status.md).

| Rule | Failure codes |
|---|---|
| R1 Gel applied twice | `missing`, `applied_once`, `outside_time_period` |
| R2 Second paddle after first placed | `simultaneous`, `taken_before_first_placed`, `first_missing` |
| R8 Apical before sternal (P-015) | `wrong_order`, `simultaneous` |
| R3 Paddles firmly on chest (P-016) | `not_in_zone`, `placed_after_shock` |
| R4 Both discharge buttons pressed (P-016) | `before_placement`, `not_pressed` |
| R5 Shock confirmed on screen | `missing`, `wrong_order` |
| R6 Paddles removed after shock | `removed_before_shock`, `missing` |
| A1 Oxygen away | `missing`, `after_shock` |
| A2 Continue compressions | `missing`, `wrong_stage` |
| A3 All stand clear | `missing`, `after_shock` |
| A4 Stop compressions | `missing`, `after_shock`, `wrong_order` |
| A5 Shock command | `missing` |
| R7 / A6 Restart compressions promptly | `missing`, `before_shock`, `too_late` |
| A7 Command sequence | `wrong_order` (a missing command is "not evaluable because of Ax", D-027) |
| A8 Pre-shock pause | `pre_shock_pause` (mistake label "Pre-Shock Pause") |
