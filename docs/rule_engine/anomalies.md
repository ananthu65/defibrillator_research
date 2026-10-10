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

## Anomalies (`rules/prepare.py`, Increment 3)

| Code | When | Why | Details |
|---|---|---|---|
| `multiple_shocks` | More than one confident `shock_delivered_on_screen` | Every recording has exactly one shock, so more than one is a data problem. Shock-dependent rules give Unable to Verify. Duplicates are **not merged** (merging is upstream's job) | `within_simultaneous_window` (true means "possibly the same shock detected twice"), `smallest_gap_seconds`, `simultaneous_window_seconds` |
| `mixed_evidence_sources` | The same canonical event comes from human annotation **and** a model | One assessment should use one kind of evidence; otherwise a human tag could silently fill a model miss. Flag only | — |
| `unknown_labels_present` | Any label is not in `vocabulary.yaml` | Shows a possible naming mismatch, instead of silently treating the event as missing | `labels` (`source:label`) |

Low-confidence events are not anomalies. They are listed in `PreparedTimeline.excluded`
(`ExcludedEvent`, reason `below_confidence_threshold`) and can be looked up with
`excluded_named(name)`.

## Planned flags (later increments)

| Code | Step | Meaning |
|---|---|---|
| `low_confidence_evidence` | Rules (Increment 6 on) | A required event is missing, but a low-confidence event of the same canonical name exists. The outcome is Unable to Verify, never Fail |
| `coverage_policy_undecided` | Coverage policy (Increment 4) | A missing event with `unknown` coverage gives Unable to Verify under the interim policy |
| `inferred_fail_policy_undecided` | R8 (Increment 12) | An inferred Fail gives Unable to Verify until `inferred_fail_outcome` is decided |
| `contradictory` | Rules (for example R8) | Evidence contradicts itself; Unable to Verify |
