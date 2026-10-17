# Rule engine: methods

How the rule engine is built and why. This is the technical companion to the plain-language
documents ([decisions](decisions.md), [pathways](pathways.md), [rules status](rules_status.md)).

## 1. Architecture

A stable core between two adaptable edges, with every changeable value in config (brief §3).

```
 source data ──► ADAPTERS ──► PREPARATION ──► COVERAGE ──► CONTEXT ──► RULES ──► OVERALL POLICY ──► RENDERERS
 (CVAT, models)   (edge)       (core)          (core)       (core)      (core)     (core)              (edge)
```

| Stage | Module | Decision points | What it does | Status |
|---|---|---|---|---|
| Annotation export and audit | `annotation/export_rule_engine_records.py`, `annotation/derive_paddle_placements.py`, `annotation/audit_rule_engine_checks.py`, `configs/rule_engine/annotation_export.yaml` | P-028, P-029, P-031 (Step 9c: derived per-paddle placements, validation report, gate) | Read the CVAT backups directly into rule-engine records (every tag, frame range, duration, zone visibility identical to the training boxes, D-079) and a separate annotation review list. Never touches the training pipeline (D-074). Reads only `task.json` and `annotations.json` (D-085). Ananth runs it on the final backups ([how-to](../annotation/rule_engine_export_howto.md), D-083) | built (Step 9b) |
| Adapters | `rules/adapters/annotation.py` | P-001, P-030 | Convert one source (exporter records now, model outputs later) into shared `Event`s plus a `TimelineHeader`: zone coverage and visible intervals (windowed coverage in `coverage.py`, D-092), the `annotation_coverage_assumed` header flag (carried onto every result by the engine), and the gate for derived placements (D-088). It imports from `annotation/` (an edge module), never from `video/`, `audio/`, `legacy/` or `pipeline/` | built (Increment 10) |
| Preparation | `rules/prepare.py`, `rules/vocabulary.py` | P-002 to P-005 | Validate, map names, set aside low-confidence events, flag anomalies, including confident-event counts against `expected_counts` and paddle identity (Increment 9a, D-071) → `PreparedTimeline` | built |
| Coverage | `rules/coverage.py` | P-006 to P-008 | Validate the header; decide whether each event was observable and what "missing" means | built |
| Context | `rules/context.py` | P-009 to P-013 | Shock time, phases, command resolution, key times (anchors), computed once → `ProcedureContext` | built |
| Rule outcome | `rules/outcome.py` | (all rule results) | `RuleOutcome`: kind, reason, failure code, evidence, flags, `blocked_by`, `timing_checked`; maps onto the shared `RuleResult` | built (Increment 6) |
| Shared checks | `rules/checks.py` | P-019 to P-025 | The ladder steps every rule uses: dependency, required facts, restart ambiguity, occurrences, weak or missing evidence (inference before coverage), time limits, order | built (Increment 6) |
| Registry and runner | `rules/registry.py`, `rules/engine.py` | P-026 | `@rule` registration and discovery of `*_rules` modules; `assess()` runs every rule in evaluation order (pending, same_as, dependencies, engine errors) and reports in display order; `evaluate()` keeps the pipeline contract | built (Increment 7) |
| Rules | `rules/video_rules.py`, `rules/audio_rules.py` | P-014 to P-016, P-032 | One small registered function per rule, built from the shared checks | R2 built (Increment 11, P-032; pending until approved); the others planned (Increments 12–23) |
| Overall policy | `rules/policy.py` | P-017 | `decide()`: Fail → Incomplete → the Unable-to-Verify setting → Pass, with its explanation (deciding rules, named mistakes, R7/A6 once, the deciding setting), timeline-review and development-data marks; `Assessment.overall` | built (Increment 8) |
| JSON report and command | `rules/render.py`, `rules/run.py` | P-027 | `report()`: the whole `Assessment` as plain JSON (overall result and explanation, every rule in display order, timeline, context, configuration), versioned by `REPORT_VERSION` and documented in [output_contract.md](output_contract.md) (D-070). `python -m rules.run --events <file>` writes it; no assessment → exit code 2 | built (Increment 9) |
| Checklist and feedback handover | `rules/render.py` | P-018 | Evaluator checklist (many rules to one item) and the feedback module's input | planned (Increment 25) |

Config files: `configs/rules.yaml` (rules in display order, clinical values with provenance),
`configs/rule_engine/vocabulary.yaml` (agreed names), `configs/rule_engine/engine.yaml`
(engineering placeholders and policies). They are loaded and validated by `rules/config.py`.

Boundaries: `rules/` never imports from `video/`, `audio/`, `legacy/` or `pipeline/`. The shared
schemas (`schemas/`) are not changed (D-038). `rules.engine.evaluate()` keeps its signature for
`pipeline/run.py`.

## 2. Techniques and why

| Technique | Where | Why (and the alternative rejected) |
|---|---|---|
| **Vocabulary mapping** keyed by (source, label) | `vocabulary.py` | A new or renamed label is one line of YAML, not a rule change. The per-source key avoids collisions between annotation and model labels. Ambiguous labels are declared with `resolve_by_shock` and resolved once, in the context (P-011) |
| **Validation with error codes** | `config.py`, `prepare.py`, `coverage.py` | Bad config or input stops the run with a message naming the entry (`ConfigError`) or a stable code (`TimelineError.code`), before any assessment. Missing settings are errors, not silent defaults (D-049). Codes are documented in `anomalies.md` and checked by a test (D-050) |
| **Topological evaluation order** (Kahn's algorithm, display-order tie-break) | `config.py` `_topological` | Rules are listed in report order. The engine moves a rule only as far as its rule-result dependencies require, so the result is deterministic. A cycle is reported with its path (D-006) |
| **Coverage lookup, most specific to most general** | `coverage.py` | Status: region → source → modality → unknown. Outcome: `by_region` → `by_source` → `by_modality` → defaults. More precise knowledge wins, and every outcome names the exact setting that decided it (`decided_by`) |
| **Separate status from policy** | `coverage.py` | "Was it observable?" is data; "what does missing mean?" is a team decision. A policy change is then one config edit (D-007, D-008) |
| **Hard-coded safety rule** | `coverage.py`, `context.py` | "Low confidence is never absence" is not configurable, so it cannot be switched off by accident (D-010) |
| **Absent, not guessed** | `context.py` `Anchor` | A key time that cannot be established has `time=None`, a reason and flags. Defaults would hide data problems; exceptions would stop the other rules (D-002, D-039) |
| **Flags travel with values** | `context.py` `Elapsed`, `outcome.py` `flags_of` | A time difference carries both anchors' flags, and every rule outcome carries the flags of everything it used (`uses=`), so no result can lose `shock_time_from_removal` (D-023) |
| **Errors become results** | `engine.py` | A rule that raises is recorded as `engine_error` with its message; the other rules still run (D-063). A silent skip would hide a bug, and stopping would lose every other result |
| **Checks return an outcome or "go on"** | `checks.py` | Each ladder step returns a `RuleOutcome` or `None`. A rule is then a short chain such as `depends(...) or requires(...) or occurrences(...)`, and the order of diagram (c) is the same in every rule |
| **Immutable data** | all stages (frozen dataclasses, tuples) | One rule cannot change the evidence another rule sees. Inputs are never modified |
| **Provenance records for clinical values** | `config.py` `ClinicalValue` | Every clinical number states who provided and who approved it. Unapproved values stay null (D-005, D-033) |
| **Documentation checked by tests** | `tests/test_rule_engine_docs.py` | `decision_flow.yaml` must match the codes raised in code, and every D/A/OQ/P reference must exist in its register |

Event time rule: comparisons use `start` (D-011). The header duration check uses `end` plus
a tolerance (D-034).

## 3. How to …

### Add a label (a new or renamed CVAT tag or model output)
1. Add one line under `labels.<source>` in `configs/rule_engine/vocabulary.yaml`. If it is a new
   canonical event, add it under `events` too, with its modality.
2. Run the tests. The vocabulary sync test fails if a CVAT tag is unmapped.
3. If the label is ambiguous, use `resolve_by_shock: {before, after}` instead of `event`.

### Add a source (for example the trained video model)
1. Write an adapter in `rules/adapters/` that produces shared `Event`s and a `TimelineHeader`.
2. Add its labels under `labels.<source>` in the vocabulary, and its threshold under
   `confidence_thresholds` in `engine.yaml`.
3. Add a decision point for the adapter to `decision_flow.yaml` and `pathways.md`.

### Add a rule
1. Add a line to `configs/rules.yaml` in its display position, with `status: pending` and any
   `depends_on` on other rules' results.
2. Implement it in `rules/video_rules.py` or `rules/audio_rules.py` as a function decorated with
   `@rule("A3", requires=("stand_clear_command",))` (D-064), with the shared checks in
   ladder order: `depends` → `requires` → (`restart_ambiguity`) → `occurrences` (which calls
   `missing`, with any approved `inference`), and `timed` for limits. Pass every anchor and elapsed
   time used as `uses=`, so their flags are carried. Never build a Fail for a missing event
   yourself: `missing()` goes through `ctx.missing()`.
3. Update the shared contract test count in `tests/test_pipeline_contracts.py` (D-022) and log
   it.
4. Add its failure codes to `anomalies.md`, its row to `rules_status.md`, and its decision
   points and worked pathways.

### Add a decision point
1. Add an entry to `docs/rule_engine/decision_flow.yaml`: id, stage, status, branches with
   conditions, outcomes, flags and codes, config, code location, and related D, A and OQ.
2. Add any new flag to the module's `FLAGS` tuple, and new codes to `anomalies.md`.
3. Add the readable table to `pathways.md`, and update `diagrams.md` if the logic changed.
4. Run `tests/test_rule_engine_docs.py`.

## 4. Definition of done for every increment

From 2026-10-13, an increment is done when:
- tests are added, and the full suite and the pipeline command pass;
- new and changed decision points are in `decision_flow.yaml` and `pathways.md`;
- new decisions are in `decisions.md`, and new assumptions in `assumptions.md`;
- new questions are in `open_questions.md`, and answered ones are marked answered with their
  decision ID;
- rule status changes are in `rules_status.md`;
- `diagrams.md` is updated when the logic changes;
- `anomalies.md` lists every new code;
- `progress.md` has the increment report, linking to the IDs instead of repeating them,
  listing the documents updated, and naming each new open question with its OQ-ID;
- `ai_usage_log.md` has a row for the increment;
- the commit message is shown first and carries no AI attribution (D-026).
