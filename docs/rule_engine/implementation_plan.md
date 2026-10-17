# Rule Engine Implementation Plan

Status: approved by Arnikan on 2026-10-10 (Step 0 of `agent_brief.md`).
Sources: `docs/rule_engine/agent_brief.md` (source of truth) and the supervisor document
*ARTS-DEFIBRILLATION — Proposed Rule-Based Assessment Implementation*. Where they differ, the
brief wins: R1 = gel applied **twice** (order relative to paddle placement is not checked),
R2 = second paddle taken after the first is **placed**, new rules R8 (apical before sternal)
and A8 (pre-shock pause ≤ 5 s), and no severity levels (`critical_error` is never used to grade
mistakes).

---

## A. What the repo already has

| Existing piece | What it does today | How the plan extends it |
|---|---|---|
| `rules/engine.py` `evaluate(events, config)` | Checks `schema_version` and duplicate IDs, returns `unable_to_assess` for pending rules, loads `implementation: module:function` rules, checks that cited event IDs exist | Keep the signature and return type (`list[RuleResult]`) because `pipeline/run.py:39` calls it. Put the new core behind it and add `assess()`, which returns the full engine report. Keep the `implementation:` path working (`test_new_rule_can_be_added_without_engine_changes` uses it). |
| `rules/base.py` `Rule` protocol | `(timeline, config) -> RuleResult` | Kept for path-based rules; a registry-based rule base is added next to it. |
| `rules/video_rules.py`, `rules/audio_rules.py` | Stubs ("implement here") | R1–R6 and R8 go in `video_rules.py`; A1–A8 and R7/A6 in `audio_rules.py`. |
| `schemas/event.py`, `schemas/rule_result.py` | Shared v1 contracts | **No schema changes proposed.** Extra rule-engine detail (failure code, coverage, timing checked, blocked by, flags) lives in a rules-internal `RuleOutcome` that converts to `RuleResult`. |
| `configs/rules.yaml` | 14 pending rules, `timing_limits` all null | Extended in place (schema_version stays 1, backward compatible): add R8, A8, `same_as`, approval records and links to the new rule-engine config files. List order = **display order** (report and checklist) only. |
| `annotation/to_timeline.py` `convert()` | CVAT point tags → `Event` (source `annotation`, confidence 1.0, original label kept) | The annotation adapter reuses `convert()` and only adds vocabulary mapping and coverage information. |
| `feedback/generate.py` | Uses `result.status.value` and `result.reason` | Unchanged; it still receives `list[RuleResult]`. A richer handover dict is produced on the rules side only. |
| `tests/test_pipeline_contracts.py:53-55` | Asserts 14 rules, all `unable_to_assess` | Change 14 → 16 when R8/A8 are added (Arnikan's decision), and update it whenever rules are added or removed. Logged in the increment report and `progress.md`. Rules stay `status: pending` in the real config, so "all `unable_to_assess`" still holds. |

### Event names found

- CVAT tags: the current CVAT project has **8** tag labels: the 7 in
  `annotation/audit_cvat_backups.py:24` (`Gel applied`, `first_paddle_taken`,
  `second_paddle_taken`, `paddles_firmly_on_chest`, `both_paddle_buttons_pressed`,
  `shock_delivered_on_screen`, `paddles_removed_after_shock`) plus
  `first_paddle_firmly_on_the_chest` (type "any"), which maps to `first_paddle_placed`. Arnikan
  updates the audit list; the rule engine does not change `annotation/`.
- CVAT tracks/boxes: `paddle_sternal`, `paddle_apical`, `defibrillator_screen`, `learner_hand`,
  `sternal_placement_zone`, `apical_placement_zone`, `shock_symbol`.
- **No separate apical / sternal placement tags exist.** Placeholders: `apical_paddle_placed`,
  `sternal_paddle_placed`.
- Audio command events (`configs/pipeline.yaml:34`): only `oxygen_away_command`,
  `stand_clear_command` and `resume_compressions_command` (which also matches "continue
  compressions"). The canonical command names follow the A1–A6 wording in the supervisor's
  proposal: `oxygen_away_command`, `continue_compressions_command`, `stand_clear_command`,
  `stop_compressions_command`, `shock_command`, `start_compressions_command`. All of them are
  **provisional** until the medical-faculty supervisor confirms them. `resume_compressions_command`
  is ambiguous, so it stays a source label that the procedure context (Increment 5) resolves
  into `continue_compressions_command` before the shock or `start_compressions_command` after
  it. `configs/pipeline.yaml` is not changed by the rule engine.
- Video model events are `object_visible:<class>`; rules cannot use them until semantic
  postprocessing exists.

### Where canonical names come from (decided 2026-10-10)

Canonical names are mostly assigned **upstream**, before the procedure transcript is built:
video postprocessing and audio command detection will emit the agreed canonical names directly.
`configs/rule_engine/vocabulary.yaml` stays as a thin safety layer that will mostly map names to
themselves, and it is **the team's reference list of agreed names**. What upstream must emit is
listed in `docs/rule_engine/upstream_requirements.md` (for Ananth and Sanjeevan). No code change
was needed for this decision.

### Annotation data findings (affect Increment 10)

- `EVENT_LABELS` is defined separately in three `annotation/` scripts:
  `audit_cvat_backups.py:24`, `build_yolo_video_dataset.py:39` and
  `create_grouped_video_split.py:26`. `events.jsonl` keeps only tags in
  `build_yolo_video_dataset.py`'s list (line 811), so `first_paddle_firmly_on_the_chest` is
  dropped until that list is updated as well as the audit list.
- `events.jsonl` records hold only tag events (label, frame, timestamp). They contain **no zone
  track information**, so zone visibility cannot be derived from them as they are now.

### Environment

- The system Python 3.11 lacks PyYAML, so `test_pipeline_contracts` fails to import and the
  pipeline command fails before any change. Fixed in Increment 0 with a `.venv`.
- `.venv/` is already in `.gitignore`.
- `data/video/phase4_yolo/metadata/events.jsonl` is not present locally, so development uses
  synthetic fixtures.

---

## B. Target design

```
configs/rules.yaml                     rule list in display order, status, clinical values + approvals
configs/rule_engine/vocabulary.yaml    source label -> canonical event name (one line per label)
configs/rule_engine/engine.yaml        engineering placeholders, coverage policy, overall policy
configs/rule_engine/checklist.yaml     checklist items -> rule IDs (placeholder 1:1)
rules/config.py                load + validate all rule-engine config; clear errors
rules/vocabulary.py            map names, keep the original label in metadata
rules/prepare.py               timeline validation, confidence filtering (logged), anomalies
rules/coverage.py              coverage model + the single coverage policy
rules/context.py               ProcedureContext, computed once
rules/outcome.py               RuleOutcome (rules-internal) -> RuleResult
rules/checks.py                presence, count, order, time_limit, simultaneity, inference, dependency
rules/registry.py              @rule decorator + discovery
rules/policy.py                overall result
rules/render.py                JSON report, checklist, feedback handover
rules/adapters/annotation.py   CVAT timeline -> prepared events + coverage
rules/run.py                   CLI: python -m rules.run --events <timeline.json>
rules/engine.py                evaluate() (compatible) + assess() (full report)
```

### Status mapping (existing `RuleStatus` values only)

| Brief term | `RuleStatus` |
|---|---|
| Pass – Direct | `pass_direct` |
| Pass – Inferred | `pass_inferred` |
| Fail | `fail` |
| Unable to Verify, not evaluable because of X, pending | `unable_to_assess` (told apart by `RuleOutcome.kind` and the reason text) |

`manual_review` and `critical_error` are not produced.

### Display order vs evaluation order

The list order in `rules.yaml` is the display order for the report and checklist only. The
engine works out the evaluation order itself (a topological sort) from **rule-result
dependencies** only. For example, A7 depends on the results of A1–A5, so A1–A5 are evaluated
first. Event dependencies come from the procedure context and impose no order: shock time,
command times, and R2's dependency on the first paddle placement are all event dependencies.
Config validation rejects only **circular** rule-result dependencies (the error names the cycle)
and dependencies on unknown rule IDs. Ties are broken by display order, so evaluation is
deterministic.

### Evidence rules (decided 2026-10-10)

- **Event time:** all order and timing comparisons use each event's `start` time (a point event
  has `start == end`). Also stated in `anomalies.md`.
- **Repeated events are kept:** every occurrence stays in the timeline, in time order, and none
  is merged or dropped. Each rule decides which occurrence counts.
- **Low confidence is not absence:** when a rule finds an event missing, but an excluded
  low-confidence event of the same canonical name exists
  (`PreparedTimeline.excluded_named(name)`), the outcome is Unable to Verify, flagged
  `low_confidence_evidence`, **never Fail**.
- **Detection quality is upstream's job:** merging duplicate detections and choosing confidence
  thresholds belong upstream (`upstream_requirements.md`). The engine's confidence step is a
  configurable safety check, and a threshold of 0 disables it.
- **Codes are documented:** every anomaly and rejection code is listed in
  `docs/rule_engine/anomalies.md`, which is extended in every increment.

### Coverage

Rules never decide what missing evidence means. A rule that finds a required event missing
returns a raw finding, `missing`, plus a coverage status (`covered`, `not_covered` or
`unknown`). `rules/coverage.py` alone turns that into an outcome using
`engine.yaml: coverage_policy`. The policy can be set per modality (video, audio) and per source
(annotation, video, audio), and explicit coverage carried in the timeline overrides it.

**As built (Increment 4):**
- **Coverage status of an event**, most specific first:
  1. `region:<r>` in the header's `coverage`, for events in that region (`apical_paddle_placed`
     is in `apical_zone`, `sternal_paddle_placed` in `sternal_zone`).
  2. `source:<s>` in the header's `coverage`, for the single source that produced the event's
     modality.
  3. `modality:<m>` in the header's `coverage`, else `analyses_run[<m>]` (ran → covered, did not
     run → not covered).
  4. If there is no header, or the header states nothing for the event, the status is
     `unknown`.
- **Outcome:** the most specific configured setting wins: `by_region` > `by_source` >
  `by_modality` > `outcomes`.
- **Low confidence:** low-confidence evidence overrides every setting and gives Unable to Verify
  (`low_confidence_evidence`).
- **Granularity:** coverage covers the whole recording. There are no time windows for now
  (decided 2026-10-13). `status()` and `missing()` already receive the event name plus an
  optional `window=(start, end)` in which the rule expected the event. Time-windowed coverage
  can therefore be added later inside `rules/coverage.py` without changing any rule. **Rules
  should pass `window` whenever they know it.**
- **Header duration:** an event may end up to `duration_tolerance_seconds` (placeholder 0.5 s)
  after `duration_seconds`; beyond that the header is a `header_mismatch`.
- **Approval date:** `approved_on` may be null only when the clinical-value record has
  `date_pending: true`. `note` is a human-readable explanation only and is never read by the
  engine.

| Coverage | Outcome | Status |
|---|---|---|
| `covered` + missing | Fail | approved |
| `not_covered` + missing | Unable to Verify | approved |
| `unknown` + missing | Unable to Verify, flagged `coverage_policy_undecided` | interim, `undecided: true` in config |

Changing the config is the only change needed once the policy is decided. Rule tests run under
every policy setting.

### Command-rule overlaps (approved)

- A7 checks command order only. When a command is missing it reports "not evaluable because of
  Ax" instead of a second Fail.
- A4 owns the stop-before-continue mistake (`wrong_order`); A2 does not fail for that same
  mistake.

### R8 logic: apical before sternal (decided 2026-10-10)

In some camera angles only one placement zone is annotated. Every recording has at least one,
and the two zones are far apart. The inference lives in the rule engine; upstream only reports
what is visible (placement events and zone visibility).

| Situation | Logic | Result |
|---|---|---|
| Both zones visible | Compare `apical_paddle_placed` and `sternal_paddle_placed` times | Pass – Direct, or Fail (`wrong_order`; `simultaneous` if within the simultaneous window) |
| Only one zone visible, and that zone's paddle placement is within `placement_match_window_seconds` of `first_paddle_placed` | That paddle was placed first | Inferred: apical visible → Pass – Inferred; sternal visible → inferred `wrong_order` |
| Only one zone visible, and its placement is clearly **after** `first_paddle_placed` | The other paddle was placed first | Inferred: apical visible → inferred `wrong_order`; sternal visible → Pass – Inferred |
| Only one zone visible, and its placement is clearly **before** `first_paddle_placed` | Contradictory evidence | Unable to Verify, flagged contradictory |
| Not determinable (no `first_paddle_placed`, no zone visible, or the visible zone's placement event missing) | — | Unable to Verify (missing placement is R3's mistake, so not a second Fail) |
| Last-resort fallback `assume_first_taken_is_apical` (config, **off by default**) | Used only when not determinable | Not counted toward the overall result; reason "assumed apical first, to be checked by the evaluator" |

- **Inferred Fail:** whether an inferred `wrong_order` counts as Fail is one config setting,
  `engine.yaml: inferred_fail_outcome` (`fail` / `unable_to_verify`), currently **undecided**.
  The interim follows the coverage interim: Unable to Verify, flagged
  `inferred_fail_policy_undecided`.
- **Status mapping:** an inferred Pass is `pass_inferred`, citing the placement and
  `first_paddle_placed` event IDs. An inferred Fail is `fail` (once decided), with
  `RuleOutcome.evidence = inferred`. The assumed fallback is `unable_to_assess` with
  `kind = assumed` and `counted = false`.

---

## C. Increments

Every increment adds tests, runs the full suite and
`python -m pipeline.run --events tests/fixtures/sample_timeline.json` in `.venv`, and ends with a
report that is shown to Arnikan **and appended to `docs/rule_engine/progress.md`**. Then work
stops until Arnikan says "continue". **Commits (updated 2026-10-14; replaces every earlier
rule):** the agent commits only when Arnikan explicitly tells it to commit, and pushes only when
explicitly told to push (`feature/rule-engine` only). This includes documentation-only commits.
It shows the commit message first, and never includes a Co-Authored-By line or any other Claude
attribution. AI use is disclosed in `docs/rule_engine/ai_usage_log.md` instead. Each increment also adds a short row to the coding-agent table of that log: what the
agent produced, and what Arnikan decided, changed or rejected.
**Definition of done (from 2026-10-13):** see [methods.md §4](methods.md#4-definition-of-done-for-every-increment).
In short: decision points in `decision_flow.yaml` and `pathways.md`, decisions, assumptions and
open questions in their registers (answered ones closed with their decision ID), rule status,
diagrams and `anomalies.md` all kept current. Each report lists the documents updated and every
new OQ-ID.
Rule-engine tests go in flat files `tests/test_rule_engine_*.py` (matching the existing layout);
fixtures go in `tests/fixtures/rule_engine/`.

| # | Increment | Files | Tests | Needs from Arnikan |
|---|---|---|---|---|
| 0 | Environment + branch: create `.venv` (Python 3.11), install `requirements.txt`, confirm the existing tests and the pipeline pass, create `feature/rule-engine`, commit brief/plan/progress | docs only | baseline run | — |
| 1 | Event vocabulary: YAML mapping + `map_events()`; unknown labels kept and flagged; placeholders for missing tags/commands | `vocabulary.yaml`, `rules/vocabulary.py` | mapping, original label kept, unknown label, IDs preserved | Real apical/sternal/first-placed tag names; command names |
| 2 | Config format + validation: `rules.yaml` in display order, add R8/A8, `same_as: R7` on A6, approval records `{value, approved_by, approved_on, source}` (plain `null` still accepted), `engine.yaml` placeholders; loader errors on bad config; **test 14 → 16** | `rules.yaml`, `engine.yaml`, `rules/config.py`, `test_pipeline_contracts.py` | each invalid config → clear error; circular rule-result dependency → error naming the cycle; unknown dependency ID → error; null limit allowed | — (A8 record: provided by Arnikan 2026-10-10, team discussion; approved by Dr. Senani Samarasinghe) |
| 3 | Validation + preparation: confidence threshold per source (below → excluded, logged), anomalies (shock count ≠ 1, contradictory events), malformed input errors | `rules/prepare.py` | below-threshold logged; >1 shock flagged; malformed → error, no report | — |
| 4 | Coverage model + policy: coverage records from timeline/adapter for modalities (video, audio) **and regions** (`apical_zone`, `sternal_zone`); event → region mapping in config; policy lookup (explicit timeline coverage > region > source > modality); `undecided` handling; **timeline header** (`recording_id`, `camera_angle`, `duration_seconds`, `analyses_run`) used when present: an analysis that did not run means its modality is `not_covered`, and a missing header means `unknown`; **low confidence is not absence**: a missing event with an excluded event of the same name gives Unable to Verify (`low_confidence_evidence`), never Fail | `rules/coverage.py`, `engine.yaml` | every policy value × every coverage status; region visible / not visible / unknown; header present / absent / analysis not run; low-confidence event present | Unknown-coverage policy; header format |
| 5 | Procedure context: shock time (R5, R6 fallback, anomaly), phases, **first placement time** (`first_paddle_placed`), **per-paddle placement times** (apical, sternal), **zone visibility** (apical, sternal), stop/start times, `resume_compressions_command` resolved into `continue_compressions_command` (before shock) or `start_compressions_command` (after shock), coverage. **Edge cases (decided 2026-10-13):** shock time from removal is recorded and flagged `shock_time_from_removal` on every timing result that uses it; a resume command within `simultaneous_window_seconds` of the shock stays unresolved (`command_near_shock`), as does any resume command with no shock time (`no_shock_time`); an anchor with several candidates uses the earliest and records all IDs (`multiple_candidates`); with `multiple_shocks` there is no shock time and shock-dependent anchors are absent and flagged, not guessed | `rules/context.py` | one/zero/two shocks, fallback, classification, every edge case above | — |
| 6 | `RuleOutcome` + shared checks; the presence check uses **`ProcedureContext.missing`** (which wraps `Coverage.missing` and also counts low-confidence ambiguous commands), so that "missing but low-confidence evidence exists" becomes Unable to Verify (`low_confidence_evidence`), never Fail; all comparisons use start time; **every result copies the flags of the anchors and `Elapsed` values it used** (for example `shock_time_from_removal`); rules use `ctx.named()` (commands resolved), not `prepared.named()` | `rules/outcome.py`, `rules/checks.py` | each helper incl. simultaneous window, null limit → "timing not checked", repeated event satisfies, low-confidence evidence → Unable to Verify | — |
| 7 | Registry + base rule + engine wiring: discovery, evaluation order from rule-result dependencies (topological sort, display-order tie-break), results reported in display order, dependency → "not evaluable because of X", pending → not counted, `same_as` reporting, all rules always run; `evaluate()` unchanged for the pipeline | `rules/registry.py`, `rules/base.py`, `rules/engine.py` | dummy rules; existing contract tests still pass | — |
| 8 | Overall result policy: any Fail → Fail; else any Unable → `engine.yaml: unable_to_verify_outcome` (`fail` / `faculty_review`, currently undecided); else Pass | `rules/policy.py` | all branches incl. pending not counted | Unable-to-Verify policy |
| 9 | JSON report renderer + `python -m rules.run` CLI; versioned output contract for the feedback module (added 2026-10-14 by Arnikan) | `rules/render.py`, `rules/run.py`, `docs/rule_engine/output_contract.md` | report shape, round-trip; contract checked against the code and decision_flow.yaml | — |
| 9a | **Event count and consistency checks** (added 2026-10-14 by Arnikan; extends P-005, D-071): `expected_counts` per canonical event in `engine.yaml` (`exactly` / `at_least` / `at_most` / `unlimited`; undecided = not checked; every value a placeholder); only confident events counted; `count_violation` naming the event, expected and found counts and event IDs; for events limited to one, pairs within `simultaneous_window_seconds` marked "possibly the same incident detected twice"; `paddle_identity_conflict` (≥ 2 placements of one paddle, none of the other); never a Fail by itself; both proposed as review anomalies (OQ-046); upstream sanity checks in `upstream_requirements.md` | `rules/prepare.py`, `rules/config.py`, `engine.yaml` | every count form met / violated; zero found; low confidence not counted; unlimited; undecided; duplicate marking; identity conflict both ways and its non-cases; config validation; overall Incomplete | Repeated-action answers (OQ-021–023); OQ-046 |
| 9b | **Rule-engine annotation exporter and audit (built 2026-10-16; D-073, D-074, D-076 to D-080, D-082; P-028, P-029).** No existing file in `annotation/` changes, and nothing the training pipeline reads changes. (1) **`annotation/export_rule_engine_records.py`** reads the CVAT backup ZIPs directly. It reuses, by import only, the task discovery of `audit_cvat_backups.py` and the box geometry of `build_yolo_video_dataset.py`, pinned by tests (D-079). It writes `data/rule_engine/annotation_export/<run>/`: `records.jsonl`, `export_issues.csv` and `export_manifest.json` (a SHA-256 per backup ZIP). It refuses `data/video/` and non-empty folders. Each record holds: every CVAT tag under its CVAT name (frame and seconds); `fps`, `width` and `height` from `video_conversion.csv` only (D-076); `start_frame`, `stop_frame`, `duration_seconds = (stop_frame + 1) / fps`; zone track counts; zone visibility intervals under the CVAT zone names, visible on exactly the frames with a training box. (2) **`annotation/audit_rule_engine_checks.py`** writes `annotation/reports/rule_engine_audit/<run>/` (D-078). Review list: `duplicate_paddle_box`, `zone_moves_like_paddle`, `repeated_incident_tag`, `zone_pattern_off` (fixed usual pattern, D-077), `zone_exception_contradicted`. Information only: learner order, repeats further apart, no first-placement tag, never-visible tracks (D-080), confirmed exceptions (D-082). The README prints the actual distribution per view beside the usual pattern. (3) Config: `configs/rule_engine/annotation_export.yaml` (zone and paddle labels, usual pattern, `reviewed_zone_exceptions`, thresholds). (4) **Ananth runs both scripts on the final backups (D-083)**, following [docs/annotation/rule_engine_export_howto.md](../annotation/rule_engine_export_howto.md). He sends only `records.jsonl`, `export_manifest.json` and the audit outputs, never media. (5) **Privacy (D-085):** only `task.json` and `annotations.json` are read from a backup; the manifest hashes only those; a test checks it. (6) A smoke run on 39 corrected backups is kept as interim development data in gitignored `data/rule_engine/` (D-084). Its findings for Ananth are in the how-to | `annotation/export_rule_engine_records.py`, `annotation/audit_rule_engine_checks.py`, `configs/rule_engine/annotation_export.yaml` (all new), `tests/test_rule_engine_annotation_export.py`, `docs/annotation/rule_engine_export_howto.md` | visibility equals the training boxes frame by frame; `track_box_at` behaviour pinned; every tag kept; missing fps; frame-count mismatch; duplicates; refused outputs; each audit check and its non-cases; order never an issue; exceptions; only annotation JSON opened | OQ-054 (date of the final export), OQ-055 |
| 9c | **Derived per-paddle placements (built 2026-10-16; D-073, D-081, D-086 to D-089, D-090, D-091, A-019, A-020; P-031).** A frame where the zone isn't visible is unknown: it neither starts nor ends a placement (D-090). `annotation/derive_paddle_placements.py`, called by the exporter. Derives `apical_paddle_placed` / `sternal_paddle_placed` from the annotated paddle and zone boxes, per paddle **label** across all its tracks (D-087). A placement starts where the paddle box is ≥ 0.5 inside its zone, steady for 5 frames (centre < 2% of the diagonal), and ends after `exit_frames` (5) frames out. Every placement episode is kept. Tag rules (D-086): T1 present → the earlier of two placements within 15 frames of T1, else no event for either; one paddle not earlier than T1 − 15. T1 missing → both kept, flagged `possible_parallel_placement`, if within `simultaneous_window_seconds` (from `engine.yaml`), else none. T2 used only when present. Overlapping tracks of one paddle → no event (`placement_duplicate_paddle_box`). Events: direct evidence, flagged `derived_placement`, method and settings hash in metadata. **Validation report** (D-089): `placement_validation.csv/.md`. **Gate** (D-088): `reviewed_for_r8` names the `export_id` and `placement_settings_sha256`; `derived_placements_approved()` is enforced by the Increment 10 adapter. Only annotation JSON is read (D-085) | `annotation/derive_paddle_placements.py` (new), exporter, `annotation_export.yaml`, `vocabulary.yaml` (the two annotation entries no longer placeholders), `tests/test_rule_engine_derived_placements.py` | each setting at its boundary; re-placement and `exit_frames`; split and overlapping tracks; every tag rule incl. parallel; validation rows and summary; the gate; settings from `engine.yaml` | Review of the validation report of the final export; OQ-056 |
| 10 | **Built 2026-10-17 (P-001, P-030; D-092).** Annotation input adapter `rules/adapters/annotation.py` (command `python -m rules.adapters.annotation`), writing timeline files that `rules.run` reads. **Partial zone visibility (D-092):** the zone intervals go into the header (`visibility`), and `Coverage.status(event, window)` gives covered (visible throughout the window), unknown (part of it) or not covered (never in it); without a window, partial visibility is unknown. The header flag `annotation_coverage_assumed` is carried onto every result by the engine. Output contract version 3 (header fields). **Revised by D-074:** it reads the 9b exporter records, not `events.jsonl`; `to_timeline.convert` stays for the pipeline contract test. **Development data until the final export (D-084):** `data/rule_engine/annotation_export/smoke-kartheepan/records.jsonl` (38 videos; P14_LS unreliable, OQ-055). It was exported before Step 9c, so it has no derived placements. It stays gitignored, and exported records are never committed or copied into test fixtures. Tests use synthetic records. **Derived placements** go into the timeline only when `derived_placements_approved()` holds for the record set's manifest (D-088). Zone coverage per region (P-030): reviewed exception → not covered (D-082); zone track visible → covered; track never visible → not covered (D-080); no zone track → `unknown` (D-074). The usual zone pattern is never used here; builds a `TimelineHeader` with `analyses_run: {video: true, audio: false}`, where **`video: true` is a development assumption**; the report for annotation timelines carries the flag **`annotation_coverage_assumed`** (and every rule result built on it), so these results are never mistaken for real assessments | `rules/adapters/annotation.py` | CVAT record → mapped events + header + coverage; one zone / both zones / no zone info; `annotation_coverage_assumed` present on every annotation-based result and absent for model timelines; each P-030 row | OQ-053 (constant frame rate) |
| 11 | **Built 2026-10-17 (P-032; pending until approved).** R2 second paddle after first placed (`simultaneous`, `taken_before_first_placed`, `first_placement_not_observed`). First placement missing → coverage of both placement zones over the window from first paddle taken to second paddle taken: visible throughout → `first_placement_not_observed`, "either a parallel placement or the second paddle taken first" (D-097), otherwise Unable to Verify (D-095). Derived placements flagged `possible_parallel_placement` → `simultaneous`, once the gate is approved (D-091). **Also in this step:** shock time only from the screen (`shock_time_fallback: none`, D-093); screen visibility in the exporter and adapter (D-094); the camera-angle evidence report (interim) | `video_rules.py`, `context.py`, `config.py`, `engine.yaml`, exporter, adapter, `tests/test_rule_engine_r2.py` | order cases; first placement missing with zones visible / out of view / partly / unknown; low confidence; parallel with and without the gate; shock time without the screen; screen coverage incl. an LL video with no screen | R2: the supervisor confirms its definition (pending until then); OQ-057 |
| 12 | R8 apical before sternal: direct comparison when both zones are visible; one-visible-zone inference against `first_paddle_placed` with `placement_match_window_seconds`; Unable to Verify when not determinable; `assume_first_taken_is_apical` fallback (off by default, not counted); `inferred_fail_outcome` setting (`wrong_order`, `simultaneous`). For annotation data, per-paddle placements come from Step 9c, only past the gate (D-088). `possible_parallel_placement` → Fail `simultaneous` once the gate is approved (D-091). The engine flag `derived_placement` enters the decision flow, anomalies.md and the output contract here, raising the report version (D-070, D-088) | `video_rules.py` | every row of the R8 logic table; fallback on/off; inferred-fail setting × values; derived and parallel placements | Gate review |
| 13 | R5 shock on screen (`missing`, `wrong_order`). Missing shock: coverage of the `screen` region, so the screen out of view → Unable to Verify, never Fail (D-094) | `video_rules.py` | applicable matrix rows; screen in / out of view / unknown | Which "preceding steps" |
| 14 | R6 paddles removed after shock (`removed_before_shock`, `missing`). Needs the shock time, which comes only from the screen (D-093): without it, Not evaluable because of R5 | `video_rules.py` | applicable matrix rows | — |
| 15 | R3 paddles firmly on chest + inferred pass (`not_in_zone`, `placed_after_shock`) | `video_rules.py` | direct; inferred via R5 or R6 | Evidence for "not in zone" |
| 16 | R4 both buttons pressed + inferred pass (`before_placement`, `not_pressed`) | `video_rules.py` | direct; inferred via R5 or R6 | — |
| 17 | R1 gel twice (`missing`, `applied_once`, `outside_time_period`); minimum gap placeholder | `video_rules.py` | applicable matrix rows | Time period (null) |
| 18 | A1 oxygen away + A3 stand clear (`missing`, `after_shock`) | `audio_rules.py` | no audio → Unable | — |
| 19 | A2 continue + A4 stop (`missing`, `wrong_stage`, `after_shock`, `wrong_order`) | `audio_rules.py` | applicable matrix rows | A4 limit (null) |
| 20 | A5 shock command (`missing`) | `audio_rules.py` | applicable matrix rows | Tolerance (null) |
| 21 | R7 / A6 restart promptly, one check reported under two IDs (`missing`, `before_shock`, `too_late`) | `audio_rules.py` | applicable matrix rows | R7 limit (null) |
| 22 | A7 command sequence: order only (`wrong_order`); missing command → "not evaluable because of Ax" | `audio_rules.py` | applicable matrix rows | — |
| 23 | A8 pre-shock pause ≤ 5 s (`pre_shock_pause`, mistake label "Pre-Shock Pause") | `audio_rules.py` | applicable matrix rows | — |
| 24 | Full scenario test matrix (brief section 8 × all rules × coverage policies) | `tests/test_rule_engine_scenarios.py`, fixtures | full matrix | — |
| 25 | Checklist renderer skeleton + feedback handover | `render.py`, `checklist.yaml` | many-to-one mapping | Checklist format |
| 26 | Documentation: how to add a rule / label / source; config reference | `docs/rule_engine/*.md` | — | — |

---

## D. Engineering placeholders

All live in `configs/rule_engine/engine.yaml`, each marked `placeholder: true`:

- Confidence threshold per source: annotation 1.0 (human), video 0.5, audio 0.5.
- Simultaneous window: 0.5 s.
- Gel minimum gap between two applications: 1.0 s.
- R8 placement-match window (`placement_match_window_seconds`): 0.5 s.
- R8 fallback `assume_first_taken_is_apical`: `false` (off).
- Header duration tolerance (`duration_tolerance_seconds`): 0.5 s.
- Coverage policy for `unknown`: interim Unable to Verify, `undecided: true`.
- Inferred Fail outcome (`inferred_fail_outcome`): interim Unable to Verify, `undecided: true`.
- Unable to Verify overall outcome: `undecided`.
- Expected counts per canonical event (`expected_counts`, Increment 9a): exactly 1 for both paddles
  taken, first placement, apical and sternal placements, removal and shock on screen; unlimited
  for commands; `undecided: true` (not checked) for gel, buttons pressed and paddles firmly on
  chest (OQ-021–023).
- Annotation audit (Step 9b, accepted 2026-10-14, D-074): a zone moving more than 5% of the
  frame diagonal; repeated tags within 15 frames marked "possibly the same incident tagged
  twice".
- Derived placements (Step 9c, accepted placeholders, D-081, D-086): overlap ≥ 0.5 of the paddle
  box, steady for 5 frames with the centre moving < 2% of the diagonal, `exit_frames` 5,
  agreement with the tags within 15 frames; the parallel window is `simultaneous_window_seconds`.
- `review_anomalies` (decided, not a placeholder): the D-069 list plus `count_violation` and
  `paddle_identity_conflict` (D-072).

---

## E. Open questions

Open questions are kept in a single register: **[open_questions.md](open_questions.md)**
(OQ-001 onwards), grouped by owner with a "For the supervisor" section first. The register keeps
each question's former number from this section (`E-1` to `E-19`, including the lettered
sub-items) in its "Old no." column, so earlier references in [progress.md](progress.md) can still
be followed. Answered questions stay in the register, linked to their decision in
[decisions.md](decisions.md).

Other registers: [decisions.md](decisions.md) (D), [assumptions.md](assumptions.md) (A),
[decision_flow.yaml](decision_flow.yaml) and [pathways.md](pathways.md) (decision points, P),
[rules_status.md](rules_status.md), [methods.md](methods.md), [diagrams.md](diagrams.md).

---

## F. Verification

For every increment:

```powershell
.venv\Scripts\python -m unittest discover -s tests
.venv\Scripts\python -m pipeline.run --events tests/fixtures/sample_timeline.json
```

Both must pass. From Increment 9, `.venv\Scripts\python -m rules.run --events <fixture>` prints
the full engine report.
