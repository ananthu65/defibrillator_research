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
stops until Arnikan says "continue". **Commits (updated 2026-10-10):** the agent may commit on
`feature/rule-engine`, but shows the commit message first, and never includes a Co-Authored-By
line or any other Claude attribution. AI use is disclosed in `docs/rule_engine/ai_usage_log.md`
instead. Each increment also adds a short row to the coding-agent table of that log: what the
agent produced, and what Arnikan decided, changed or rejected.
Rule-engine tests go in flat files `tests/test_rule_engine_*.py` (matching the existing layout);
fixtures go in `tests/fixtures/rule_engine/`.

| # | Increment | Files | Tests | Needs from Arnikan |
|---|---|---|---|---|
| 0 | Environment + branch: create `.venv` (Python 3.11), install `requirements.txt`, confirm the existing tests and the pipeline pass, create `feature/rule-engine`, commit brief/plan/progress | docs only | baseline run | — |
| 1 | Event vocabulary: YAML mapping + `map_events()`; unknown labels kept and flagged; placeholders for missing tags/commands | `vocabulary.yaml`, `rules/vocabulary.py` | mapping, original label kept, unknown label, IDs preserved | Real apical/sternal/first-placed tag names; command names |
| 2 | Config format + validation: `rules.yaml` in display order, add R8/A8, `same_as: R7` on A6, approval records `{value, approved_by, approved_on, source}` (plain `null` still accepted), `engine.yaml` placeholders; loader errors on bad config; **test 14 → 16** | `rules.yaml`, `engine.yaml`, `rules/config.py`, `test_pipeline_contracts.py` | each invalid config → clear error; circular rule-result dependency → error naming the cycle; unknown dependency ID → error; null limit allowed | — (A8 record: provided by Arnikan 2026-10-10, team discussion; approved by Dr. Senani Samarasinghe) |
| 3 | Validation + preparation: confidence threshold per source (below → excluded, logged), anomalies (shock count ≠ 1, contradictory events), malformed input errors | `rules/prepare.py` | below-threshold logged; >1 shock flagged; malformed → error, no report | — |
| 4 | Coverage model + policy: coverage records from timeline/adapter for modalities (video, audio) **and regions** (`apical_zone`, `sternal_zone`); event → region mapping in config; policy lookup (explicit timeline coverage > region > source > modality); `undecided` handling; **timeline header** (`recording_id`, `camera_angle`, `duration_seconds`, `analyses_run`) used when present: an analysis that did not run means its modality is `not_covered`, and a missing header means `unknown`; **low confidence is not absence**: a missing event with an excluded event of the same name gives Unable to Verify (`low_confidence_evidence`), never Fail | `rules/coverage.py`, `engine.yaml` | every policy value × every coverage status; region visible / not visible / unknown; header present / absent / analysis not run; low-confidence event present | Unknown-coverage policy; header format |
| 5 | Procedure context: shock time (R5, R6 fallback, anomaly), phases, **first placement time** (`first_paddle_placed`), **per-paddle placement times** (apical, sternal), **zone visibility** (apical, sternal), stop/start times, `resume_compressions_command` resolved into `continue_compressions_command` (before shock) or `start_compressions_command` (after shock), coverage | `rules/context.py` | one/zero/two shocks, fallback, classification | — |
| 6 | `RuleOutcome` + shared checks; the presence check consults `excluded_named` so that "missing but low-confidence evidence exists" becomes Unable to Verify (`low_confidence_evidence`), never Fail; all comparisons use start time | `rules/outcome.py`, `rules/checks.py` | each helper incl. simultaneous window, null limit → "timing not checked", repeated event satisfies, low-confidence evidence → Unable to Verify | — |
| 7 | Registry + base rule + engine wiring: discovery, evaluation order from rule-result dependencies (topological sort, display-order tie-break), results reported in display order, dependency → "not evaluable because of X", pending → not counted, `same_as` reporting, all rules always run; `evaluate()` unchanged for the pipeline | `rules/registry.py`, `rules/base.py`, `rules/engine.py` | dummy rules; existing contract tests still pass | — |
| 8 | Overall result policy: any Fail → Fail; else any Unable → `engine.yaml: unable_to_verify_outcome` (`fail` / `faculty_review`, currently undecided); else Pass | `rules/policy.py` | all branches incl. pending not counted | Unable-to-Verify policy |
| 9 | JSON report renderer + `python -m rules.run` CLI | `rules/render.py`, `rules/run.py` | report shape, round-trip | — |
| 10 | Annotation input adapter (reuses `annotation.to_timeline.convert`); derives zone visibility from whether each placement zone (`apical_placement_zone`, `sternal_placement_zone`) is annotated in the recording; no zone information → coverage `unknown` | `rules/adapters/annotation.py` | CVAT record → mapped events + coverage; one zone / both zones / no zone info | Where the per-recording zone annotation comes from (`events.jsonl` has none today) |
| 11 | R2 second paddle after first placed (`simultaneous`, `taken_before_first_placed`, `first_missing`) | `video_rules.py` | applicable matrix rows | First-placed evidence |
| 12 | R8 apical before sternal: direct comparison when both zones are visible; one-visible-zone inference against `first_paddle_placed` with `placement_match_window_seconds`; Unable to Verify when not determinable; `assume_first_taken_is_apical` fallback (off by default, not counted); `inferred_fail_outcome` setting (`wrong_order`, `simultaneous`) | `video_rules.py` | every row of the R8 logic table; fallback on/off; inferred-fail setting × values | Per-paddle placement source labels |
| 13 | R5 shock on screen (`missing`, `wrong_order`) | `video_rules.py` | applicable matrix rows | Which "preceding steps" |
| 14 | R6 paddles removed after shock (`removed_before_shock`, `missing`) | `video_rules.py` | applicable matrix rows | — |
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
- Coverage policy for `unknown`: interim Unable to Verify, `undecided: true`.
- Inferred Fail outcome (`inferred_fail_outcome`): interim Unable to Verify, `undecided: true`.
- Unable to Verify overall outcome: `undecided`.

---

## E. Open questions

1. Final coverage policy for `unknown` (interim: Unable to Verify, flagged
   `coverage_policy_undecided`, kept as a config value).
2. Unable to Verify overall: Fail or faculty review.
3. *(Partly resolved)* "First paddle placed" is CVAT `first_paddle_firmly_on_the_chest`. CVAT
   has no separate apical or sternal placement tags, so `apical_paddle_placed` and
   `sternal_paddle_placed` stay placeholders. *(Resolved: which paddle was first)* R8 uses
   direct comparison or the one-visible-zone inference (section B, R8 logic). Still open:
   which source emits per-paddle placement events (see `upstream_requirements.md`).
3a. **Does an inferred Fail count as Fail?** One setting, `inferred_fail_outcome`, currently
   undecided (interim: Unable to Verify, flagged `inferred_fail_policy_undecided`).
3b. Placement-match window value for R8 (placeholder 0.5 s), and whether the
   "first paddle taken is apical" fallback should ever be switched on.
3c. Where per-recording zone visibility comes from for annotation timelines: `events.jsonl`
   has no zone tracks. Options: add zone-annotated flags to `events.jsonl` in
   `annotation/build_yolo_video_dataset.py` (Arnikan's annotation area), or a separate
   per-task manifest. Until then, zone coverage is `unknown`.
3d. `EVENT_LABELS` must include `first_paddle_firmly_on_the_chest` in
   `build_yolo_video_dataset.py` (and `create_grouped_video_split.py`), not only the audit
   list, or `events.jsonl` drops it.
4. Missing audio command events (continue, stop, shock, start). `pipeline.yaml` maps "continue
   compressions" to `resume_compressions_command`. We do not change `configs/pipeline.yaml`;
   Arnikan raises this with Sanjeevan.
4a. All command names and phrases are provisional until the medical-faculty supervisor
   confirms them (marked `provisional: true` in `vocabulary.yaml`).
5. *(Resolved)* A7 checks order only; A4 owns stop-before-continue.
6. R3 `not_in_zone`: no event currently signals wrong placement. Which evidence should be used?
7. R5 "after the preceding steps": which steps (placement only, or placement + buttons)?
8. *(Resolved 2026-10-10)* A8 5 s limit ("Stop CPR" → "Start CPR") is **approved** by the
   supervisor, Dr. Senani Samarasinghe (approval date not recorded); provided by Arnikan on
   2026-10-10, source: team discussion. A8's result will not call the limit unapproved.
   Still open: final IDs for R8 and A8.
9. Clinical limits still null: R1 period, R7/A6, A4, A5 tolerance, R6 removal limit.
10. The pipeline report will not show the overall result or checklist unless `pipeline/run.py`
    calls `rules.engine.assess()`. This needs Ananth.
11. Engineering placeholder values (section D).
12. **Confidence thresholds:** which side applies them, upstream or the rule engine, so they
    are not applied twice with different values? (The rule engine's check is a safety net, and
    a threshold of 0 disables it.)
13. **Timeline header:** can upstream provide `recording_id`, `camera_angle`,
    `duration_seconds` and `analyses_run` with each timeline, and in what format? Without it,
    "no audio events" cannot be told apart from "audio analysis didn't run".
14. **Supervisor: repeated actions.**
    - 14a. Gel applied **more than twice**: Fail, or "at least twice" passes?
    - 14b. Paddles **lifted and placed again** before the shock: acceptable, or a mistake? Which
      placement counts for R2, R3 and R8?
    - 14c. Discharge buttons **pressed more than once**: acceptable, or a mistake? Which press
      counts for R4?
15. *(Decided, Increment 3)* Duplicate shocks are not merged; `multiple_shocks` records whether
    they fall within `simultaneous_window_seconds`. `mixed_evidence_sources` stays a flag. One
    camera angle and one task ID per timeline stays a hard error (events with no angle do not
    count as a second angle).

---

## F. Verification

For every increment:

```powershell
.venv\Scripts\python -m unittest discover -s tests
.venv\Scripts\python -m pipeline.run --events tests/fixtures/sample_timeline.json
```

Both must pass. From Increment 9, `.venv\Scripts\python -m rules.run --events <fixture>` prints
the full engine report.
