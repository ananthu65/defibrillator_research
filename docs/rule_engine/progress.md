# Rule Engine Progress Log

One entry per increment, newest last. Each entry uses the report template from
`agent_brief.md` section 7.

---

## Step 0: Inspect the repo and plan (2026-10-10)

### What was done
I read the brief, the supervisor document, `README.md`, `docs/team.md`, `docs/contracts.md`,
`docs/reorganization.md`, everything in `rules/`, `schemas/`, `configs/`, and also
`annotation/to_timeline.py`, `audio/commands/detect.py`, the relevant `pipeline/` and
`feedback/` files, and `tests/`. Then I wrote `docs/rule_engine/implementation_plan.md` and
Arnikan approved it. No code was written.

### How it was done
Files added:
- `docs/rule_engine/implementation_plan.md`: the 27-step plan (Increments 0–26), the target
  file map, the decisions, the open questions and the verification commands.
- `docs/rule_engine/progress.md`: this log.

### Findings
- **Existing tests:** `python -m unittest discover -s tests` runs 32 tests: 1 import error and
  1 skipped. The error is `test_pipeline_contracts`, which cannot import because PyYAML is not
  installed in the system Python 3.11. The pipeline command fails for the same reason. Nothing
  in the repo needs to change; the environment just needs PyYAML.
- **Rule count:** `tests/test_pipeline_contracts.py:53-55` asserts exactly 14 rules, all
  `unable_to_assess`. Adding R8 and A8 makes that 16.
- **Pipeline:** `pipeline/run.py` calls `rules.engine.evaluate()` and expects a
  `list[RuleResult]`, so that function must keep its signature.
- **CVAT event tags:** `Gel applied`, `first_paddle_taken`, `second_paddle_taken`,
  `paddles_firmly_on_chest`, `both_paddle_buttons_pressed`, `shock_delivered_on_screen`,
  `paddles_removed_after_shock`.
- **Missing placement tags:** there are no separate apical or sternal placement tags and no
  "first paddle placed" tag. There are only the `paddle_apical`/`paddle_sternal` box tracks and
  the combined `paddles_firmly_on_chest` tag.
- **Audio commands:** only `oxygen_away_command`, `stand_clear_command` and
  `resume_compressions_command` exist. `resume_compressions_command` also matches "continue
  compressions". There are no continue, stop, shock or separate start commands.
- **Data:** `data/video/phase4_yolo/metadata/events.jsonl` is not present locally.
- **Ignore rules:** `.venv/` is already in `.gitignore`.

### Decisions recorded during review (Arnikan, 2026-10-10)
1. **Shared test change:** change the count in `tests/test_pipeline_contracts.py` from 14 to 16,
   and update it whenever rules are added or removed. Log every change in the increment report
   and here so the team can see it. *(Ananth and Sanjeevan: this is a shared contract test.)*
2. **Environment:** create `.venv` with Python 3.11 in the repo root, install
   `requirements.txt` into it and use it for every command. Confirm the existing tests and the
   pipeline command pass before Increment 1.
3. **Coverage:** rules record raw findings (`missing` plus `covered`/`not_covered`/`unknown`).
   One configurable coverage policy turns them into outcomes, set per source and per modality,
   and explicit timeline coverage overrides it. `covered → Fail` and `not_covered → Unable to
   Verify` are approved. `unknown → Unable to Verify` is an interim value flagged
   `coverage_policy_undecided` and marked undecided in config. Rules are tested under every
   policy setting.
4. **Order:** the order in `rules.yaml` is the display order only. The engine works out the
   evaluation order from rule-result dependencies and rejects only circular dependencies.
   Example: A7 depends on the results of A1–A5. R2's dependency on the first paddle placement
   is an event dependency from the procedure context, not a rule-result dependency.
5. **A7 and A4:** A7 checks command order only and reports "not evaluable because of Ax" when a
   command is missing. A4 owns the stop-before-continue mistake.
6. **Placeholders:** placeholder tag names stay until Arnikan sends the real CVAT names.
7. **`configs/pipeline.yaml`:** we do not change it. Arnikan raises the audio command gaps with
   Sanjeevan.

### Assumptions
- No shared schema changes are needed: the rule engine's extra detail lives in a rules-internal
  `RuleOutcome`. If the team later wants failure codes inside `RuleResult`, that would be an
  optional field proposed separately for approval.
- All rules stay `status: pending` in the real `configs/rules.yaml` until the supervisor
  approves them, so the fixture pipeline run still reports every rule as `unable_to_assess`.

### Tests
None added (planning only). Baseline before any change: 32 tests ran, with 1 import error
(PyYAML missing) and 1 skipped.

### Try it yourself
Read `docs/rule_engine/implementation_plan.md`.

### Open questions
See section E of the plan. The ones blocking specific increments:
- Placement and first-placed tag names (blocks Increments 11–12).
- Audio command names (Increments 18–23).
- A8 approver name and date (Increment 2).
- R3 evidence for `not_in_zone` (Increment 15).
- R5 "preceding steps" (Increment 13).

### Next increment
**Increment 0:** create `.venv`, install `requirements.txt`, confirm the existing tests and the
pipeline command pass, create the `feature/rule-engine` branch, and commit the brief, plan and
progress docs.

---

## Increment 0: Environment and branch (2026-10-10)

### What was done
A working Python environment now exists in the repo, and the existing tests and pipeline
command pass in it. Rule engine work now happens on its own branch, `feature/rule-engine`. The
brief, plan and this log are committed as its first commit. No code was changed.

### How it was done
- `python -m venv .venv` created a virtual environment with Python 3.11.2 in the repo root. A
  virtual environment is a private copy of Python with its own installed packages, so nothing
  touches the system Python.
- `.venv\Scripts\python -m pip install -r requirements.txt` installed PyYAML 6.0.3, the only
  core dependency.
- `.venv/` is already ignored by `.gitignore` (line 11), so the environment is never committed.
- `git switch -c feature/rule-engine` created the branch from `main` at `30deb1f`.
- Committed files: `docs/rule_engine/agent_brief.md`, `implementation_plan.md` and
  `progress.md`.

### Methods and design choices
- I used the standard-library `venv` rather than conda or another tool, because it matches the
  README ("activate the existing `.venv`") and needs nothing new installed.
- I installed only `requirements.txt`, the core dependencies the rule engine needs. The optional
  area requirements (video, audio, charging sound, app) belong to other team members and pull in
  heavy packages.

### Assumptions
- Using the same interpreter version as CI (Python 3.11) is enough for local results to match
  CI. If CI's Python changes, the venv should be recreated with that version.

### How it stays adaptable
Not applicable (environment only).

### Tests
No tests added. Full suite in `.venv`: **48 tests run, all pass, 1 skipped.** Before the venv,
only 32 ran, because `test_pipeline_contracts` could not import without PyYAML.
- The skipped test is `test_charging_sound.test_synthetic_training_prediction_and_test_holdout`
  (Sanjeevan's area). It is skipped on purpose when numpy/scipy/sklearn/joblib are absent. CI
  installs `requirements/charging-sound.txt`, so CI runs it. I did not install those packages.
- `python -m pipeline.run --events tests/fixtures/sample_timeline.json` writes
  `data/outputs/assessment.json` (gitignored) and exits with 0.

### Try it yourself
```powershell
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m pipeline.run --events tests/fixtures/sample_timeline.json
```

### Open questions
- Should I install `requirements/charging-sound.txt` into `.venv` so the local run has zero
  skips and matches CI? This adds numpy, scipy, scikit-learn and joblib (Sanjeevan's
  dependencies, already used by CI). Not needed for rule engine work.

### Next increment
**Increment 1: event vocabulary.** Add `configs/rule_engine/vocabulary.yaml`, which maps every
source label to one canonical name, for example `Gel applied` → `gel_applied`. It includes
placeholders for the missing placement tags and audio commands. Add `rules/vocabulary.py` with
`map_events()`: it renames events to canonical names, keeps the original label in metadata,
keeps event IDs, and flags unknown labels instead of dropping them. Tests go in
`tests/test_rule_engine_vocabulary.py`.
