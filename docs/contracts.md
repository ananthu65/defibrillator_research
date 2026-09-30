# Handover contracts — version 1

The schemas are the shared agreement. A new model or implementation must satisfy
these formats; a research change must not silently reinterpret old records.
The active pipeline does not import the archived Version 2 schemas.

## Event

`schemas.event.Event` contains:

| Field | Meaning |
| --- | --- |
| `schema_version` | Currently 1; unsupported versions are rejected |
| `event_id` | Unique within the recording timeline; assigned by the merger if absent |
| `event_name` | Agreed observation name; new names must be documented with annotation/rules owners |
| `start`, `end` | Seconds, finite, 0 <= start <= end; a point event has equal times |
| `confidence` | 0–1; retain its interpretation/calibration in metadata |
| `source` | `video`, `audio`, or `annotation` |
| `camera_angle` | Optional camera label, e.g. T/LS/LL; audio normally uses null |
| `evidence_type` | `direct` or `inferred`; inferred events require `metadata.inferred_from` |
| `metadata` | Model/task/frame provenance and optional supporting details |

All events in an assessment must belong to **one recording/session**. Align
camera/audio times explicitly before combining streams; the merger applies
configured source offsets and sorts events, but does not infer clinical actions.
Use one camera per initial runner invocation; calibrated multi-camera fusion
is a later extension. Same-label observations from different camera angles are
not merged by postprocessing. Variable-frame-rate video must be normalized or
handled by a future timestamp-aware adapter.

Current model observations are `object_visible:<class>` for video,
configured `*_command` phrase observations for ASR, and `charging_sound` for
the charging classifier. Annotation labels retain their original CVAT names.
These vocabularies require an explicit agreed mapping before clinical rules
can use them. ASR confidence is currently an exp(log-probability) proxy, not a
calibrated command-classification probability. Phrase matching is a baseline,
not the planned trained command classifier.

## Rule result

`schemas.rule_result.RuleResult` contains `schema_version`, `rule_id`, `status`,
`supporting_events` (event IDs), named `timestamps` in seconds, and `reason`.
Allowed status values are `pass_direct`, `pass_inferred`, `fail`,
`unable_to_assess`, `manual_review`, and `critical_error`. Passing results require
supporting evidence IDs. The engine verifies evidence IDs exist in its timeline.

Rules are functions `(timeline, rule_config) -> RuleResult`. Parameters live
with each rule in `configs/rules.yaml`; configuration must identify definition
sources when the team agrees them. The engine never invents missing thresholds.
Feedback consumes results and returns text without changing status or evidence.

## ASR segments and reports

`TranscriptSegment` has `start`, `end`, `text`, and optional `confidence`.
Command-event generation requires confidence, so a new backend must supply a
documented estimate or replace that conversion explicitly.

`pipeline.run.assess_recording` is the public recording-to-report entry point;
`assess` accepts already prepared video/audio/events. The JSON report includes
schema version, timeline, rule results, feedback and configuration snapshots.
The application calls this API; it does not duplicate the model/rule chain.
Reports remain development outputs until clinical rules and validation are complete.

## Version changes

Optional fields may be added with documented defaults and backward-compatible
fixtures. Renaming fields, changing units or changing meanings requires a new
schema version and an explicit converter. Keep old run artifacts unchanged.
Review shared changes with the developers consuming that format, and test both
old fixtures and new ones. Adapter selection and model variants belong in
config; a new clinical rule belongs in the rule catalog, not the pipeline.
