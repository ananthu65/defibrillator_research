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

- CVAT tags (`annotation/audit_cvat_backups.py:24`): `Gel applied`, `first_paddle_taken`,
  `second_paddle_taken`, `paddles_firmly_on_chest`, `both_paddle_buttons_pressed`,
  `shock_delivered_on_screen`, `paddles_removed_after_shock`.
- CVAT tracks/boxes: `paddle_sternal`, `paddle_apical`, `defibrillator_screen`, `learner_hand`,
  `sternal_placement_zone`, `apical_placement_zone`, `shock_symbol`.
- **No separate apical / sternal placement tags and no "first paddle placed" tag exist.**
  Placeholders: `apical_paddle_placed`, `sternal_paddle_placed`, `first_paddle_placed`
  (Arnikan is checking the current CVAT labels).
- Audio command events (`configs/pipeline.yaml:34`): only `oxygen_away_command`,
  `stand_clear_command` and `resume_compressions_command` (which also matches "continue
  compressions"). **Missing:** continue, stop, shock and a distinct start command, so these are
  placeholders. `configs/pipeline.yaml` is not changed by the rule engine.
- Video model events are `object_visible:<class>`; rules cannot use them until semantic
  postprocessing exists.

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

---

## C. Increments

Every increment adds tests, runs the full suite and
`python -m pipeline.run --events tests/fixtures/sample_timeline.json` in `.venv`, makes one
commit on `feature/rule-engine`, and ends with a report that is shown to Arnikan **and appended
to `docs/rule_engine/progress.md`**. Then work stops until Arnikan says "continue".
Rule-engine tests go in flat files `tests/test_rule_engine_*.py` (matching the existing layout);
fixtures go in `tests/fixtures/rule_engine/`.

| # | Increment | Files | Tests | Needs from Arnikan |
|---|---|---|---|---|
| 0 | Environment + branch: create `.venv` (Python 3.11), install `requirements.txt`, confirm the existing tests and the pipeline pass, create `feature/rule-engine`, commit brief/plan/progress | docs only | baseline run | — |
| 1 | Event vocabulary: YAML mapping + `map_events()`; unknown labels kept and flagged; placeholders for missing tags/commands | `vocabulary.yaml`, `rules/vocabulary.py` | mapping, original label kept, unknown label, IDs preserved | Real apical/sternal/first-placed tag names; command names |
| 2 | Config format + validation: `rules.yaml` in display order, add R8/A8, `same_as: R7` on A6, approval records `{value, approved_by, approved_on, source}` (plain `null` still accepted), `engine.yaml` placeholders; loader errors on bad config; **test 14 → 16** | `rules.yaml`, `engine.yaml`, `rules/config.py`, `test_pipeline_contracts.py` | each invalid config → clear error; circular rule-result dependency → error naming the cycle; unknown dependency ID → error; null limit allowed | A8 approver name/date |
| 3 | Validation + preparation: confidence threshold per source (below → excluded, logged), anomalies (shock count ≠ 1, contradictory events), malformed input errors | `rules/prepare.py` | below-threshold logged; >1 shock flagged; malformed → error, no report | — |
| 4 | Coverage model + policy: coverage records from timeline/adapter, policy lookup (override > source > modality), `undecided` handling | `rules/coverage.py`, `engine.yaml` | every policy value × every coverage status | Unknown-coverage policy |
| 5 | Procedure context: shock time (R5, R6 fallback, anomaly), phases, first paddle placement, stop/start times, "continue CPR" classified by position vs shock, coverage | `rules/context.py` | one/zero/two shocks, fallback, classification | — |
| 6 | `RuleOutcome` + shared checks | `rules/outcome.py`, `rules/checks.py` | each helper incl. simultaneous window, null limit → "timing not checked", repeated event satisfies | — |
| 7 | Registry + base rule + engine wiring: discovery, evaluation order from rule-result dependencies (topological sort, display-order tie-break), results reported in display order, dependency → "not evaluable because of X", pending → not counted, `same_as` reporting, all rules always run; `evaluate()` unchanged for the pipeline | `rules/registry.py`, `rules/base.py`, `rules/engine.py` | dummy rules; existing contract tests still pass | — |
| 8 | Overall result policy: any Fail → Fail; else any Unable → `engine.yaml: unable_to_verify_outcome` (`fail` / `faculty_review`, currently undecided); else Pass | `rules/policy.py` | all branches incl. pending not counted | Unable-to-Verify policy |
| 9 | JSON report renderer + `python -m rules.run` CLI | `rules/render.py`, `rules/run.py` | report shape, round-trip | — |
| 10 | Annotation input adapter (reuses `annotation.to_timeline.convert`) | `rules/adapters/annotation.py` | CVAT record → mapped events + coverage | — |
| 11 | R2 second paddle after first placed (`simultaneous`, `taken_before_first_placed`, `first_missing`) | `video_rules.py` | applicable matrix rows | First-placed evidence |
| 12 | R8 apical before sternal (`wrong_order`, `simultaneous`; no inferred pass) | `video_rules.py` | applicable matrix rows | Placement tag names |
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
- Coverage policy for `unknown`: interim Unable to Verify, `undecided: true`.
- Unable to Verify overall outcome: `undecided`.

---

## E. Open questions

1. Final coverage policy for `unknown` (interim: Unable to Verify, flagged
   `coverage_policy_undecided`, kept as a config value).
2. Unable to Verify overall: Fail or faculty review.
3. Names of the apical/sternal placement tags and of the "first paddle placed" event. Arnikan is
   checking the current CVAT labels; placeholders stay until then.
4. Missing audio command events (continue, stop, shock, start). `pipeline.yaml` maps "continue
   compressions" to `resume_compressions_command`. We do not change `configs/pipeline.yaml`;
   Arnikan raises this with Sanjeevan.
5. *(Resolved)* A7 checks order only; A4 owns stop-before-continue.
6. R3 `not_in_zone`: no event currently signals wrong placement. Which evidence should be used?
7. R5 "after the preceding steps": which steps (placement only, or placement + buttons)?
8. A8 5 s limit: approver name and date for the config record. Final IDs for R8 and A8.
9. Clinical limits still null: R1 period, R7/A6, A4, A5 tolerance, R6 removal limit.
10. The pipeline report will not show the overall result or checklist unless `pipeline/run.py`
    calls `rules.engine.assess()`. This needs Ananth.
11. Engineering placeholder values (section D).

---

## F. Verification

For every increment:

```powershell
.venv\Scripts\python -m unittest discover -s tests
.venv\Scripts\python -m pipeline.run --events tests/fixtures/sample_timeline.json
```

Both must pass. From Increment 9, `.venv\Scripts\python -m rules.run --events <fixture>` prints
the full engine report.
