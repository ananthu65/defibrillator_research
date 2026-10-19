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
  **Answered (Arnikan):** no; CI covers that test.

### Next increment
**Increment 1: event vocabulary.** Add `configs/rule_engine/vocabulary.yaml`, which maps every
source label to one canonical name, for example `Gel applied` → `gel_applied`. It includes
placeholders for the missing placement tags and audio commands. Add `rules/vocabulary.py` with
`map_events()`: it renames events to canonical names, keeps the original label in metadata,
keeps event IDs, and flags unknown labels instead of dropping them. Tests go in
`tests/test_rule_engine_vocabulary.py`.

---

## Increment 1: Event vocabulary (2026-10-10)

### What was done
There is now one config file that says which canonical event name every source label means,
plus a module that renames timeline events to those names. Rules will only ever see canonical
names, so a new or renamed CVAT label or model output means editing one line of YAML, not a
rule. The engine does not call the vocabulary yet (that wiring is Increment 7), so the
pipeline output is unchanged.

### How it was done
- **`configs/rule_engine/vocabulary.yaml`** (new) has three sections:
  - `events`: the 15 canonical names rules use, each with a `modality` (video or audio). The
    modality belongs to the *event*, not the source, so a CVAT annotation of a video action
    is still `video` for the coverage policy in Increment 4.
  - `labels`: per source (`annotation`, `video`, `audio`), a list of
    `{label, event, placeholder?}`. Matching is exact; `gel applied` is not `Gel applied`.
  - `unused`: labels we know about but no rule uses (`object_visible:*` from the detector and
    `charging_sound`). They stay in the timeline but are not reported as unknown.
- **`rules/errors.py`** (new): `ConfigError(ValueError)`, the single error type for invalid
  rule-engine config. It subclasses `ValueError`, so existing code that catches `ValueError`
  still works.
- **`rules/vocabulary.py`** (new):
  - `Vocabulary.from_dict()` validates the YAML. Every error names the exact entry, for
    example `labels.annotation[0]: unknown canonical event 'gel_aplied'`.
  - `map_events()` does the renaming:

```python
def map_events(self, events):
    mapped, unknown, unused = [], [], []
    for event in events:
        if SOURCE_LABEL_KEY in event.metadata and event.event_name in self.events:
            mapped.append(event)  # already mapped, so mapping twice changes nothing
            continue
        name = self.canonical(event.source, event.event_name)
        if name is not None:
            metadata = {**event.metadata, SOURCE_LABEL_KEY: event.event_name}
            mapped.append(replace(event, event_name=name, metadata=metadata))
            continue
        issue = LabelIssue(event.event_id, event.source, event.event_name)
        (unused if self.is_unused(event.source, event.event_name) else unknown).append(issue)
        mapped.append(event)
    return MappingResult(mapped, unknown, unused)
```

  How it works:
  - The lookup key is `(source, label)`, so the same text from two sources can mean different
    things.
  - `Event` is a frozen (read-only) dataclass, so `dataclasses.replace` builds a new event
    with the new name. `{**event.metadata, ...}` copies the metadata and adds
    `source_label: "Gel applied"`, so the original CVAT name stays visible. The input events
    are never modified, and the ID, times, confidence and camera are all kept.
  - The first `if` makes the function *idempotent* (running it twice gives the same result
    as running it once), in case the engine receives events that were already mapped.
  - Unknown and unused events are **kept**, never dropped, and listed in `MappingResult`, so
    later increments can report them (the brief says to flag anomalies, not hide them).

### Methods and design choices
- **Config, not code, for names.** The alternative was a Python dict in `rules/`. YAML keeps
  name changes separate from rule logic, as the brief asks ("a new label means one line
  here").
- **Per-source lookup**, not one flat table: annotation labels and model labels are defined by
  different people and may collide.
- **One canonical `compressions_command`** for start / continue / resume compressions, not
  separate continue and restart names. The brief says the meaning depends on position relative
  to the shock, and `configs/pipeline.yaml` already sends both "continue compressions" and
  "resume compressions" as `resume_compressions_command`. The split into continue (before the
  shock) and restart (after it) happens once, in the procedure context (Increment 5).
- **`placeholder` is marked on the source label**, not the canonical event. We choose the
  canonical names; what is unknown is what CVAT or the audio model will call them.
- **Strict validation** rejects unknown keys, duplicates, and a label that is both mapped and
  unused. A YAML typo then fails loudly instead of silently making a rule Unable to Verify.

### Assumptions
- **CVAT event tags are exactly the seven in `annotation/audit_cvat_backups.py:24`.** A test
  enforces this; if CVAT gains a tag, the test fails until a line is added.
- **Canonical names reuse the CVAT tag names**, except `Gel applied` → `gel_applied` (the
  brief's example). If you prefer other names, only this YAML and the later rules change.
- **Placeholder names**, until the real names are known:
  - Annotation: `first_paddle_placed`, `apical_paddle_placed`, `sternal_paddle_placed`.
  - Audio: `stop_compressions_command`, `shock_command`.
- **Raw detector output `object_visible:*` is never rule evidence** (as `README.md` says). If
  semantic video events appear later, they get lines under `labels.video`.

### How it stays adaptable
- **New, renamed or real placeholder label:** edit one line in `labels`.
- **New source (for example the video model):** fill in `labels.video`.
- **New canonical event for a new rule:** add one line in `events`.
- **File location:** `load_vocabulary(path)` takes any path; Increment 2 makes `rules.yaml`
  point to it.

### Tests
`tests/test_rule_engine_vocabulary.py`, 21 tests:
- **Repository sync (5):**
  - Every CVAT event tag is mapped.
  - Every audio command in `configs/pipeline.yaml` is mapped.
  - The placeholders are listed.
  - Modality is looked up per event.
  - The sample timeline has no unknown labels.
- **Mapping (6):**
  - The rename keeps the ID, times, camera and existing metadata, adds `source_label`, and
    leaves the input unmodified.
  - Mapping is per source.
  - Unknown labels are kept and flagged, including the case variant `gel applied`.
  - Unused labels are kept and not flagged.
  - Mapping twice gives the same result as mapping once.
  - Order and missing (`None`) IDs from `annotation.to_timeline.convert` are preserved.
- **Invalid config (10), each a clear `ConfigError`:**
  - Wrong schema version.
  - No events.
  - Bad modality.
  - A label pointing to an undeclared event.
  - A duplicate label.
  - An unknown source.
  - A typo in an entry key.
  - An empty label.
  - A label both mapped and unused.
  - A malformed unused entry.

Full suite: **69 tests run, all pass, 1 skipped** (the charging-sound test, as before). The
pipeline command exits with 0 and its output is unchanged. `rules/` imports nothing from
`video/`, `audio/` or `legacy/`.

### Try it yourself
```powershell
.venv\Scripts\python -c "from rules.vocabulary import load_vocabulary; from schemas.event import Event; r = load_vocabulary().map_events([Event('Gel applied', 2, 2, 'annotation', 1.0, event_id='e1'), Event('gel applied', 3, 3, 'annotation', 1.0, event_id='e2')]); print(r.events[0]); print('unknown:', r.unknown)"
```

### Open questions
1. Real names for the three annotation placeholders (you are checking CVAT).
2. Audio command names for stop and shock, and whether the audio model will emit separate
   continue and restart names. They would all map to `compressions_command` anyway.
3. Are the canonical names OK, particularly `compressions_command` for all
   start/continue/resume commands?

### Next increment
**Increment 2: config format and validation.**
- **`configs/rules.yaml`:**
  - Rules in display order.
  - Add R8 and A8, and `same_as: R7` on A6.
  - Approval records `{value, approved_by, approved_on, source}`; a plain `null` is still
    accepted.
  - Links to `vocabulary.yaml` and to a new `engine.yaml` that holds the engineering
    placeholders.
- **`rules/config.py`:** loads and validates all of it, including rejecting circular
  rule-result dependencies.
- **Shared test:** `tests/test_pipeline_contracts.py` changes from 14 to 16 rules (logged).
- **Needed from you:** the approver name and date for the A8 5-second limit. Until then I will
  record `approved_by: null` and `source: agent_brief.md`.

---

## Increment 1 fix: Review changes to the vocabulary (2026-10-10)

### What was done
I applied Arnikan's review of Increment 1, before starting Increment 2:
1. **Real CVAT label:** CVAT `first_paddle_firmly_on_the_chest` (type "any") now maps to
   `first_paddle_placed`. This replaces the placeholder. `apical_paddle_placed` and
   `sternal_paddle_placed` stay placeholders, because CVAT has no separate tags for them.
2. **8 CVAT tag labels:** the current CVAT project has 8 tag labels, while the list in
   `annotation/audit_cvat_backups.py` still has 7. I did not change `annotation/` (Arnikan
   updates it). The vocabulary test checks the 7 listed labels plus
   `first_paddle_firmly_on_the_chest`, and it keeps passing once the audit list gains the
   eighth.
3. **Action-specific command names:** `compressions_command` is gone. The six canonical
   command names follow the A1–A6 wording in the supervisor's proposal:
   - `oxygen_away_command`
   - `continue_compressions_command`
   - `stand_clear_command`
   - `stop_compressions_command`
   - `shock_command`
   - `start_compressions_command`

   The pipeline's `resume_compressions_command` is ambiguous, so it stays a source label. It is
   marked `resolve_by_shock: {before: continue_compressions_command, after:
   start_compressions_command}`, and the procedure context (Increment 5) renames it.
4. **Provisional:** all six command names are marked `provisional: true`. Command names and
   phrases are provisional until the medical-faculty supervisor confirms them. This is now
   open question 4a in the plan.
5. **A8 approval record:** the 5-second limit is recorded as provided by Arnikan on
   2026-10-10, source: team discussion, supervisor approval pending. A8 itself enters
   `configs/rules.yaml` in Increment 2, together with the 14 → 16 shared-test change, so the
   record is written there in that increment. For now it is in the plan (section E, item 8,
   and the Increment 2 row).

### How it was done
- **`configs/rule_engine/vocabulary.yaml`:**
  - New label `first_paddle_firmly_on_the_chest` → `first_paddle_placed`.
  - The six command events, each with `provisional: true`.
  - A `resolve_by_shock` entry for `resume_compressions_command`.
  - Placeholder audio labels for continue and start, alongside the existing stop and shock
    placeholders, in case the audio model emits action-specific names.
- **`rules/vocabulary.py`:**
  - `CanonicalEvent.provisional` field, and a `Vocabulary.provisional_events` property.
  - Event entries are now strict: only `modality`, `description` and `provisional` are
    allowed.
  - A label entry needs exactly one of `event` or `resolve_by_shock`.
  - `resolve_by_shock` needs `before` and `after`, both declared events with the same
    modality.
  - `Vocabulary.resolution(source, label)` returns `(before, after)`.
  - `map_events()` keeps an ambiguous event's name, adds `source_label`, and lists the event
    in the new `MappingResult.unresolved`. It is not reported as unknown.

```python
if self.resolution(event.source, event.event_name) is not None:
    metadata = {**event.metadata, SOURCE_LABEL_KEY: event.event_name}
    mapped.append(replace(event, metadata=metadata))
    unresolved.append(LabelIssue(event.event_id, event.source, event.event_name))
    continue
```

  The vocabulary does not know the shock time, so it cannot choose. It records that a choice
  is needed and leaves the decision to the one place that does know the shock time.

### Methods and design choices
- **Resolution declared in config** (`resolve_by_shock`), not hard-coded in the context. If
  Sanjeevan later emits separate continue and start labels, they map directly and
  `resolve_by_shock` is simply not used. If another ambiguous label appears, it is one line.
- **Unresolved is a separate list from unknown.** An unknown label is a vocabulary gap. An
  unresolved one is expected and is handled in Increment 5.

### Assumptions
- `first_paddle_firmly_on_the_chest` is emitted with source `annotation` and that exact
  spelling. Annotation events are one point per tag (from `annotation.to_timeline.convert`),
  even though the CVAT label type is "any".

### How it stays adaptable
- **When the supervisor confirms command names:** drop `provisional: true`, or rename, in the
  vocabulary only.
- **When the audit list gains its eighth label:** the test still passes; the extra name in the
  test becomes a harmless duplicate.

### Tests
`tests/test_rule_engine_vocabulary.py`: 21 → **30 tests**.
- **Changed:**
  - The CVAT sync test checks 8 labels, including that
    `first_paddle_firmly_on_the_chest` maps to `first_paddle_placed`.
  - The audio sync test accepts resolvable labels.
  - The placeholder set is checked exactly.
- **Added:**
  - `resume_compressions_command` resolves to continue/start.
  - The six command names match the proposal and are all provisional.
  - An ambiguous label is kept, gets `source_label`, is listed as unresolved, and mapping it
    twice changes nothing.
  - Rejected configs:
    - An unknown event key.
    - Both `event` and `resolve_by_shock`.
    - Neither of them.
    - `resolve_by_shock` missing `after`.
    - `resolve_by_shock` pointing to an undeclared event.
    - `resolve_by_shock` targets with different modalities.

Full suite: **78 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0. `rules/` imports nothing from `video/`, `audio/` or `legacy/`. No stale
`compressions_command` remains.

### Try it yourself
```powershell
.venv\Scripts\python -c "from rules.vocabulary import load_vocabulary; v = load_vocabulary(); print(v.canonical('annotation', 'first_paddle_firmly_on_the_chest')); print(v.resolution('audio', 'resume_compressions_command')); print(v.provisional_events)"
```

### Open questions (new or changed)
- **R8:** what evidence will R8 use to tell which paddle was placed first? (Plan item 3.)
- **Commands:** all command names and phrases are provisional until the medical-faculty
  supervisor confirms them. (Plan item 4a.)
- **A8:** supervisor approval of the 5-second limit is still pending. (Plan item 8.)

### Next increment
**Increment 2: config format and validation**, as planned. It includes writing the A8 record
above into `configs/rules.yaml`.

---

## Plan update: R8 inference, upstream names, commit workflow (2026-10-10)

Documentation only; no code changed.

### Decisions recorded (Arnikan)
1. **Commits:** from now on the agent does not commit. Each increment ends with the
   `git add` commands and commit message for Arnikan to run.
2. **Canonical names:** these are mostly assigned upstream. Video postprocessing and audio
   command detection will emit the agreed names directly. `vocabulary.yaml` stays as a thin
   safety layer, mostly mapping names to themselves, and is the team's reference list of
   agreed names. No code change.
3. **R8 one-visible-zone inference:**
   - **Both zones visible:** compare placement times directly (Pass – Direct or Fail).
   - **Only one zone visible:** compare that zone's placement time with `first_paddle_placed`.
     - Within `placement_match_window_seconds` (placeholder): that paddle was first.
     - Clearly after: the other paddle was first.
     - Either way the result is recorded as inferred.
   - **Not determinable:** Unable to Verify.
   - **Fallback:** "first paddle taken is apical" is a configurable last resort, off by
     default. When used, R8 is not counted and says "assumed apical first, to be checked by the
     evaluator".
   - **Inferred Fail:** whether it counts as Fail is a config setting, currently undecided.
   - **Where it lives:** the inference is in the rule engine; upstream only reports what is
     visible.

### Files changed
- **`docs/rule_engine/agent_brief.md`:**
  - R8 row: now describes the direct and one-zone cases, and depends on per-paddle placement,
    first placement time and zone visibility.
  - The note "Inference never establishes order, so R8 has no inferred pass" is replaced:
    shock-based inference (R5/R6) still never establishes order, but R8 has its own one-zone
    inference.
- **`docs/rule_engine/implementation_plan.md`:**
  - New section "Where canonical names come from".
  - New section "Annotation data findings" (see below).
  - New section "R8 logic", with a table of every case, the inferred-Fail setting, and the
    status mapping.
  - Increments preamble: no agent commits; git commands are handed over instead.
  - Increment 4: coverage supports regions (`apical_zone`, `sternal_zone`), not only modality
    and source.
  - Increment 5: the context computes the first placement time, per-paddle placement times and
    zone visibility.
  - Increment 10: the annotation adapter derives zone visibility from the zone annotations;
    with no zone information, coverage is `unknown`.
  - Increment 12: the full R8 logic.
  - Section D: new placeholders `placement_match_window_seconds` (0.5 s),
    `assume_first_taken_is_apical` (off) and `inferred_fail_outcome` (undecided).
  - Section E: question 3 updated, and new questions 3a–3d.
- **`docs/rule_engine/upstream_requirements.md`** (new): the reference for Ananth and
  Sanjeevan.
  - From video: the action events, including per-paddle placement and first placement time;
    zone visibility as proposed interval events `apical_zone_visible` / `sternal_zone_visible`
    (no schema change); and per-paddle taken events if feasible.
  - From audio: the six command names, and how ambiguous phrases are handled.
- **Memory:** saved the "no commits" instruction so it holds in later sessions.

### Findings while doing this (affect Increment 10)
- **`EVENT_LABELS` is defined in three `annotation/` scripts**, not one:
  `audit_cvat_backups.py:24`, `build_yolo_video_dataset.py:39` and
  `create_grouped_video_split.py:26`. `events.jsonl` keeps only tags in
  `build_yolo_video_dataset.py`'s list, so `first_paddle_firmly_on_the_chest` will be dropped
  from timelines unless that list is updated too. (Plan item 3d.)
- **`events.jsonl` has no zone tracks**, only tag events. The annotation adapter therefore
  cannot derive zone visibility until zone information is added to the records, or supplied
  separately. (Plan item 3c.)

### Choices I made that you should check
- **Contradictory case:** the visible zone's paddle placed clearly *before*
  `first_paddle_placed` is treated as Unable to Verify, flagged contradictory.
- **Interim inferred Fail:** Unable to Verify, flagged `inferred_fail_policy_undecided`. This
  matches the coverage interim.
- **Fallback status:** when the apical fallback is used, R8 is `unable_to_assess` with
  `kind = assumed` and `counted = false`.
- **Brief sections 6.7 and 7:** these still say "one small commit per increment" and "4.
  Commit." I did not edit them, because you asked only for the R8 changes in the brief. The
  plan records the new workflow.

### Tests
None added (docs only). Full suite: 78 tests run, all pass, 1 skipped (charging sound). The
pipeline command exits with 0.

### Open questions (new)
- 3a: Does an inferred Fail count as Fail?
- 3b: The placement-match window value, and whether the apical fallback should ever be on.
- 3c: Where zone visibility comes from for annotation timelines.
- 3d: The `EVENT_LABELS` lists in `build_yolo_video_dataset.py` and
  `create_grouped_video_split.py`.

### Next increment
**Increment 2: config format and validation** (unchanged). The new R8 settings go into
`engine.yaml` there, as placeholders.

---

## Increment 1 (consolidated): Event vocabulary, review fix, R8 and upstream docs (2026-10-10)

This entry summarises all Increment 1 work in one place. The three entries above ("Increment
1", "Increment 1 fix", "Plan update") keep the step-by-step detail.

### What was done
1. **Original work** (commit `bbebf1b`):
   - `configs/rule_engine/vocabulary.yaml` maps every source label to one canonical event name.
   - `rules/vocabulary.py` validates the YAML and renames timeline events. It keeps event IDs
     and the original label (`metadata.source_label`), and never drops an event. Unknown and
     unused labels are listed separately.
   - `rules/errors.py` adds `ConfigError`.
2. **Review fix** (commit `5868e79`):
   - The real CVAT label `first_paddle_firmly_on_the_chest` now maps to `first_paddle_placed`.
   - Action-specific command names follow the A1–A6 wording in the supervisor's proposal:
     `oxygen_away_command`, `continue_compressions_command`, `stand_clear_command`,
     `stop_compressions_command`, `shock_command`, `start_compressions_command`. All are marked
     `provisional: true`.
   - The ambiguous pipeline label `resume_compressions_command` is declared with
     `resolve_by_shock` and listed as unresolved. The procedure context will resolve it in
     Increment 5.
   - `apical_paddle_placed` and `sternal_paddle_placed` stay placeholders.
3. **R8 and upstream documentation:**
   - **R8 one-visible-zone inference:** added to the brief (R8 row and the inference note) and
     to the plan (section "R8 logic", and Increments 4, 5, 10 and 12).
   - **Canonical names:** these are emitted upstream, and `vocabulary.yaml` is the team's
     reference list of agreed names.
   - **`upstream_requirements.md` (new):** written for Ananth and Sanjeevan.
   - **Workflow:** the commit workflow changes are recorded.
4. **This entry, plus workflow updates:**
   - This consolidated entry.
   - A row in `ai_usage_log.md`.
   - Claude commit attribution switched off in Claude Code user settings
     (`attribution.commit = ""`, `attribution.pr = ""`, `sessionUrl = false`).

### Tests
`tests/test_rule_engine_vocabulary.py`, 30 tests. Full suite: **78 tests run, all pass, 1
skipped** (the charging-sound test, which CI runs). The pipeline command exits with 0. `rules/`
imports nothing from `video/`, `audio/` or `legacy/`.

### Decisions by Arnikan during Increment 1
- **Command names:** replace `compressions_command` with action-specific names from the
  proposal, all provisional until the medical-faculty supervisor confirms them.
- **Shared test:** the 8th CVAT tag label is mapped, but `annotation/` is not changed.
- **A8 record:** 5 s, provided by Arnikan on 2026-10-10, source: team discussion, supervisor
  approval pending. It is written into `rules.yaml` in Increment 2.
- **R8:** use the one-visible-zone inference. The inferred-Fail policy is undecided. The
  apical fallback is off by default and not counted when used.
- **Accepted interims:** contradictory placement gives Unable to Verify, and an inferred Fail
  gives Unable to Verify until the policy is decided.
- **Commits:** the agent may commit again, but with no Co-Authored-By line or other Claude
  attribution, and must show the message first. AI use is disclosed in `ai_usage_log.md`.

### Current open questions (plan section E, as of this entry)
1. Final coverage policy for `unknown` (interim: Unable to Verify, flagged
   `coverage_policy_undecided`, kept as a config value).
2. Unable to Verify overall: Fail or faculty review.
3. *(Partly resolved)* "First paddle placed" is CVAT `first_paddle_firmly_on_the_chest`. CVAT
   has no separate apical or sternal placement tags, so `apical_paddle_placed` and
   `sternal_paddle_placed` stay placeholders. R8 uses direct comparison or the one-visible-zone
   inference. Still open: which source emits per-paddle placement events.
   - 3a. Does an inferred Fail count as Fail? One setting, `inferred_fail_outcome`, currently
     undecided (interim: Unable to Verify, flagged `inferred_fail_policy_undecided`).
   - 3b. The R8 placement-match window value (placeholder 0.5 s), and whether the "first
     paddle taken is apical" fallback should ever be switched on.
   - 3c. Where per-recording zone visibility comes from for annotation timelines.
   - 3d. The `EVENT_LABELS` lists in `build_yolo_video_dataset.py` and
     `create_grouped_video_split.py` must include `first_paddle_firmly_on_the_chest`.
4. Missing audio command events (continue, stop, shock, start). `pipeline.yaml` maps
   "continue compressions" to `resume_compressions_command`. We do not change
   `configs/pipeline.yaml`; Arnikan raises this with Sanjeevan.
   - 4a. All command names and phrases are provisional until the medical-faculty supervisor
     confirms them.
5. *(Resolved)* A7 checks order only; A4 owns stop-before-continue.
6. R3 `not_in_zone`: no event currently signals wrong placement. Which evidence should be
   used?
7. R5 "after the preceding steps": which steps (placement only, or placement + buttons)?
8. A8 5 s limit: recorded as provided by Arnikan, supervisor approval pending. Still open:
   supervisor approval, and final IDs for R8 and A8.
9. Clinical limits still null: R1 period, R7/A6, A4, A5 tolerance, R6 removal limit.
10. The pipeline report will not show the overall result or checklist unless
    `pipeline/run.py` calls `rules.engine.assess()`. This needs Ananth.
11. Engineering placeholder values (plan section D).

### Annotation findings (affect Increment 10)
1. **Tag lists that would drop `first_paddle_firmly_on_the_chest`:**
   - `EVENT_LABELS` is defined separately in `annotation/audit_cvat_backups.py:24`,
     `annotation/build_yolo_video_dataset.py:39` and
     `annotation/create_grouped_video_split.py:26`.
   - `events.jsonl` keeps only the tags in `build_yolo_video_dataset.py`'s list (line 811), so
     `first_paddle_firmly_on_the_chest` is dropped from annotation timelines until that list
     is updated, not only the audit list.
2. **No zone tracks in `events.jsonl`:**
   - The records contain only tag events (label, frame, timestamp). There is no information on
     whether `apical_placement_zone` or `sternal_placement_zone` was annotated.
   - The annotation adapter therefore cannot derive zone visibility until that information is
     added to the records or supplied separately. Until then, zone coverage is `unknown`.

### Next increment
**Increment 2: config format and validation.**

---

## History rewrite: Claude trailer removed (2026-10-10)

Arnikan approved removing the `Co-Authored-By: Claude` trailer from the three earlier commits.
`feature/rule-engine` was not pushed.

- **Backup:** first created `backup/rule-engine-before-reword` at `b172f68`.
- **Rewrite:** ran
  `git filter-branch -f --msg-filter "sed '/^Co-Authored-By: Claude/d'" main..feature/rule-engine`.
- **Old → new hashes:** `4f1c944` → `fdbdba3`, `bbebf1b` → `7ad706e`, `5868e79` → `a58ac2b`,
  `b172f68` → `977ab11`.
- **Checks:**
  - No Claude or Co-Authored-By line remains.
  - Each message differs from the backup only by the removed trailer line.
  - The final tree is identical to the backup, and authors and dates are unchanged.
  - 78 tests pass (1 skipped) and the pipeline command exits with 0.
- **Kept:** `filter-branch` also keeps `refs/original/refs/heads/feature/rule-engine`. The backup
  branch was not deleted; Arnikan deletes it after checking.

---

## Increment 2: Config format and validation (2026-10-10)

### What was done
All rule-engine configuration now has one loader, `rules/config.py`, that checks every file
before any assessment runs. Each problem gives a clear `ConfigError` naming the file and entry.
- **`configs/rules.yaml`:**
  - Lists all 16 rule IDs (R8 and A8 added) in display order, with titles.
  - Records clinical values with their provenance, including the A8 5-second limit.
  - Links to the vocabulary and to a new `configs/rule_engine/engine.yaml`, which holds every
    engineering placeholder and undecided policy.
- **Evaluation order:** worked out from rule-result dependencies, and circular dependencies are
  rejected with the cycle named.
- **Engine unchanged:** `rules/engine.py` is not touched, so the pipeline still sees every rule
  as pending. The new loader is wired into the engine in Increment 7.

### How it was done
- **`configs/rules.yaml`** (changed; `schema_version` stays 1, and the existing keys keep their
  meaning):
  - New `vocabulary:` and `engine:` paths, both relative to the repo root.
  - `timing_limits`:
    - The two existing keys stay.
    - New keys, all `null`: `gel_application_period_seconds` (R1), `stop_to_shock_seconds`
      (A4), `shock_command_tolerance_seconds` (A5), `shock_to_removal_seconds` (R6).
      `shock_to_compressions_seconds` (R7/A6) was already there.
    - `pre_shock_pause_seconds` (A8) is the record:
      `{value: 5, approved_by: null, approved_on: null, provided_by: Arnikan,
      provided_on: "2026-10-10", source: team discussion, note: supervisor approval pending}`.
  - `rules`: 16 entries in brief order, each with a `title`. A6 is `same_as: R7`; A7 is
    `depends_on: [A1, A2, A3, A4, A5]`. All rules are `status: pending`.
- **`configs/rule_engine/engine.yaml`** (new):
  - Confidence thresholds per source.
  - `simultaneous_window_seconds`, `gel_minimum_gap_seconds`,
    `placement_match_window_seconds`, and `assume_first_taken_is_apical` (false). All are marked
    `placeholder: true`.
  - `coverage_policy.outcomes`: `covered → fail`, `not_covered → unable_to_verify`, and
    `unknown → unable_to_verify` marked `undecided: true`.
  - `inferred_fail_outcome` (interim `unable_to_verify`, undecided).
  - `unable_to_verify_outcome` (`null`, undecided).
  - **Every key is required**, so a missing setting is an error, not a silent default.
- **`rules/config.py`** (new):
  - Dataclasses: `ClinicalValue` (value plus provenance, and `.approved`), `Setting` (value,
    `placeholder`, `undecided`), `RuleDefinition`, `EngineSettings`, and `RuleEngineConfig`
    (which holds rules, limits, engine settings and the vocabulary).
  - `load_rules_config(path)` is the entry point.

  The evaluation order (a *topological sort*: order items so that each comes after the items
  it depends on):

```python
def _topological(order, dependencies, where="rules"):
    remaining, done, result = list(order), set(), []
    while remaining:
        ready = next((r for r in remaining if set(dependencies[r]) <= done), None)
        if ready is None:
            raise ConfigError(f"{where}: circular rule-result dependency: {_cycle(remaining, dependencies)}")
        remaining.remove(ready)
        done.add(ready)
        result.append(ready)
    return result
```

  How it works:
  - `order` is the display order. On each pass the loop takes the **first** rule in display
    order whose dependencies are all done (`<=` means "is a subset of"). So rules only move as
    far as their dependencies require, and the result is the same every run.
  - If no rule is ready, the remaining rules depend on each other. `_cycle` then walks the
    dependencies until a rule repeats and reports the loop, for example
    `A1 -> A2 -> A3 -> A1`.
  - `RuleDefinition.result_dependencies` is `depends_on` plus `same_as`, because A6 needs R7's
    result. Event dependencies (shock time and so on) are not listed and impose no order.
- **Clinical value rules:**
  - A value is either `null` or a record; a plain number is rejected because it has no
    provenance.
  - A non-null value needs a `source`.
  - `approved_by` and `approved_on` must be given together, and an approval needs a value.
  - Dates must be quoted `"YYYY-MM-DD"`. `pipeline/run.py:44` copies the raw `rules.yaml` into
    the JSON report, and an unquoted YAML date would become a Python `date` and crash
    `json.dumps`.
- **`tests/test_pipeline_contracts.py`** (shared): 14 → 16 in both assertions, with a comment to
  update it when rules change. **This is the only shared-file change. Ananth and Sanjeevan:
  please note.**

### Methods and design choices
- **Frozen dataclasses:** used rather than passing raw dicts around. Rules will receive typed,
  already-validated values, and a typo becomes an attribute error, not a silent `None`.
- **Two kinds of "unset":** `ClinicalValue` (clinical, needs provenance and approval) and
  `Setting` (engineering or policy, flagged `placeholder` or `undecided`) are kept separate. The
  brief treats them differently: clinical values are never invented, while engineering values
  get placeholder defaults.
- **Validate everything at load time:** a bad config stops the run with a clear error before
  any assessment (brief section 8, last row).
- **`yaml` read directly:** not via `pipeline.config`, so `rules/` does not depend on the
  pipeline package, which itself imports `rules`.

### Assumptions
- **The A8 value is used, flagged as not approved.** A provided but not-yet-approved value (A8)
  will be used by the rule, with its result saying "limit not yet approved by the supervisor".
  It is recorded, not invented. The A8 rule itself stays `pending`, so it is not counted. If
  you want unapproved values ignored instead, the rule would check `limit.approved`, a
  one-line change in A8.
- **New key names are mine:** `gel_application_period_seconds`, `stop_to_shock_seconds`,
  `shock_command_tolerance_seconds`, `shock_to_removal_seconds` and `pre_shock_pause_seconds`.
- **Only A7 has rule-result dependencies** (plus A6's `same_as`). Others will be added when the
  rules are implemented, if any need another rule's result.

### How it stays adaptable
- **Supervisor approves a value:** fill `approved_by` and `approved_on` in `rules.yaml`.
- **Rule approved:** change `status` to `approved` and set `implementation`.
- **New rule:** add one line in `rules`; its position is its display position.
- **New dependency:** `depends_on`; the evaluation order follows automatically.
- **Policy decided:** change the value in `engine.yaml` and drop `undecided`.
- **Pilot thresholds chosen:** change the value in `engine.yaml` and drop `placeholder`.

### Tests
`tests/test_rule_engine_config.py`, 43 tests:
- **Repository config (8):**
  - Display order.
  - All rules pending.
  - A6 `same_as` R7, and A7's dependencies.
  - The A8 record: provided, not approved.
  - The other limits are null.
  - Placeholders and undecided settings are listed.
  - The linked vocabulary loads.
  - The raw config is JSON-serialisable.
- **Evaluation order (2):**
  - A shuffled list moves only the rules with dependencies, and keeps the display order.
  - Event dependencies impose no order.
- **Invalid `rules.yaml` (23):**
  - Wrong schema version.
  - No rules.
  - A duplicate ID.
  - An unknown rule key.
  - A bad status.
  - A bad implementation path.
  - `same_as` together with an implementation.
  - A `same_as` chain.
  - An unknown dependency.
  - A self dependency.
  - A three-rule cycle, named exactly.
  - A cycle through `same_as`.
  - A plain-number limit.
  - An unknown limit key.
  - A value without a source.
  - A negative value.
  - An unquoted date.
  - An approval without a date.
  - An approval without a value.
  - A missing linked file.
  - Invalid YAML.
  - Allowed cases: a null limit for an approved rule, and an approved limit.
- **Invalid `engine.yaml` (10):**
  - A missing setting.
  - An unknown setting.
  - Confidence out of range.
  - A missing source threshold.
  - A negative window.
  - A non-boolean fallback.
  - A bad coverage outcome.
  - A bad overall outcome.
  - Null while not undecided.
  - Allowed: every permitted value of both policy settings is accepted.

Full suite: **121 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0. Its report lists 16 rules, all `unable_to_assess`, and includes the A8 record. `rules/`
imports nothing from `video/`, `audio/` or `legacy/`.

### Try it yourself
```powershell
.venv\Scripts\python -c "from rules.config import load_rules_config; c = load_rules_config(); print(c.evaluation_order()); print(c.limit('pre_shock_pause_seconds')); print(c.engine.undecided)"
```
To see an error, change `status: pending` to `status: draft` on any rule and run the command
again. You get `ConfigError: ...rules.yaml rules.R1: status must be one of ('pending',
'approved')`.

### Open questions
1. Should a provided but unapproved clinical value (A8's 5 s) be used, with a flag, or ignored
   until approved? I assumed used with a flag.
2. Are the five new `timing_limits` key names OK?
3. `charge_to_shock_seconds` is a pre-existing key that no rule uses. Keep it or remove it?

### Next increment
**Increment 3: validation and preparation** (`rules/prepare.py`):
- Map names through the vocabulary.
- Drop events below the per-source confidence threshold, and log them.
- Flag anomalies: shock count ≠ 1, unknown labels, contradictory events.
- Reject malformed timelines with a clear error.

---

## Increment 2 decisions: A8 approved, limit names, unused parameters (2026-10-10)

### Decisions (Arnikan)
1. **A8 approved:** the supervisor, Dr. Senani Samarasinghe, approved the 5-second limit between
   "Stop CPR" and "Start CPR". The approval date is not known and is left unrecorded.
2. **Limit names kept:** `gel_application_period_seconds`, `stop_to_shock_seconds`,
   `shock_command_tolerance_seconds`, `shock_to_removal_seconds` and `pre_shock_pause_seconds`.
   They may be used in future rules.
3. **Unused parameters kept:** `charge_to_shock_seconds` and every other unused parameter stay
   `null`, each with a short note saying it is not used by any rule yet. None are removed.

### What changed
- **`configs/rules.yaml`, A8 record:**
  - `approved_by: Dr. Senani Samarasinghe`.
  - `approved_on: null`, with the comment "approval date not recorded".
  - `provided_by`, `provided_on` and `source` are unchanged.
  - The "supervisor approval pending" note is removed.
- **`configs/rules.yaml`, unused limits:** the six null limits are now
  `{value: null, note: "...; not used by any rule yet"}`. The note names the planned rule where
  there is one. The header comment says unused keys are kept on purpose.
- **`rules/config.py`:** one validation rule relaxed, because the approval date is unknown.
  - **Before:** `approved_by` and `approved_on` had to be given together.
  - **Now:** an approver may be recorded without a date, but `approved_on` without
    `approved_by` is still rejected.
  - `ClinicalValue.approved` is true when there is a value and `approved_by` is set, so A8 now
    counts as approved, and its result will not call the limit unapproved.
- **`tests/test_rule_engine_config.py`:**
  - The A8 test now checks the approver, the null date, that no note remains, and
    `approved is True`.
  - The unused-limits test checks the notes.
  - The "approval without date" rejection test is replaced by two tests: a date without an
    approver is rejected, and an approver without a date is allowed.
- **`implementation_plan.md`:** open question 8 is marked resolved (only the final R8/A8 IDs
  remain open), and the Increment 2 row is updated.

### Tests
Full suite: **122 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0, and its report carries the approved A8 record.

### Note
Only the timing limits in `rules.yaml` got "not used by any rule yet" notes. The engineering
settings in `engine.yaml` are also unused until the rules exist, but they already carry
`placeholder` or `undecided` flags, so I left them as they are.

---

## Increment 3: Validation and preparation (2026-10-10)

### What was done
There is now a single preparation step, `prepare_timeline(events, config)`, that every timeline
will pass through before any rule runs. It does four things:
1. **Rejects malformed input** with a `TimelineError`, so no assessment is produced. Rejected
   input is: not a list of `Event`s, a missing or duplicate `event_id`, more than one camera
   angle, or more than one recording.
2. **Maps names** to canonical names through the vocabulary (Increment 1).
3. **Sets aside events below the confidence threshold** for their source. They are never used
   as evidence, and each one is recorded with its confidence and the threshold it missed.
4. **Flags data anomalies:** more than one confident shock, and the same event coming from
   both human annotation and a model.

The result is a `PreparedTimeline` that later steps (procedure context, rules, report) read.
It is not called by the engine yet (Increment 7), so the pipeline output is unchanged.

### How it was done
- **`rules/errors.py`:** new `TimelineError(ValueError)`. It is separate from `ConfigError`, so
  the report and tests can tell "your config is wrong" from "this recording's data is wrong".
- **`rules/prepare.py`** (new):
  - `ExcludedEvent`: an event set aside, with `event_id`, name, source, confidence, threshold
    and reason.
  - `Anomaly`: `code`, a plain-language `message`, and the `event_ids` involved.
  - `PreparedTimeline`: `events` (usable, canonical, in time order), `excluded`,
    `unknown_labels`, `unused_labels`, `unresolved_labels`, `anomalies`, and `sources` (which
    sources appeared at all). It has two helpers, `named(event_name)` and `has_anomaly(code)`.

The core of `prepare_timeline`:

```python
events = _validated(events)                                   # 1. stop on malformed input
mapping = config.vocabulary.map_events(events)                # 2. canonical names
thresholds = {source: setting.value for source, setting in config.engine.confidence_thresholds.items()}
kept, excluded = [], []
for event in mapping.events:                                  # 3. confidence filter
    threshold = thresholds[event.source]
    if event.confidence >= threshold:
        kept.append(event)
    else:
        excluded.append(ExcludedEvent(event.event_id, event.event_name, event.source, event.confidence, threshold))
kept.sort(key=lambda e: (e.start, e.end, e.event_id))
return PreparedTimeline(tuple(kept), tuple(excluded), ..., tuple(_anomalies(kept, config)), ...)  # 4. anomalies
```

How it works:
- **Thresholds come from config:** the threshold for each source comes from
  `engine.yaml: confidence_thresholds` (placeholders: annotation 1.0, video 0.5, audio 0.5).
  `>=` means an event exactly at the threshold is kept.
- **Anomalies use only kept events.** A shock the model was unsure about is not evidence, so it
  cannot create a "two shocks" anomaly either.
- **Sorting makes the order deterministic:** by start, then end, then ID, so the same input
  always gives the same output. The pipeline merger already sorts; this also covers timelines
  that do not come through the pipeline.
- **Everything is a tuple** (an immutable list), so a rule cannot accidentally change the
  evidence that other rules see.

`_validated` checks, in order:
1. The input is iterable.
2. Every item is a `schemas.event.Event`, not a raw dict. The core never sees source formats;
   adapters convert first.
3. Every event has an `event_id`, and the IDs are unique. Rule results cite evidence by ID, and
   the engine refuses citations of unknown IDs.
4. At most one non-null `camera_angle`, and at most one `metadata.task_id`. The contract says
   one recording and one camera per assessment.

Value checks (times, confidence range, source) are already done by `Event.__post_init__` in the
shared schema, so they are not repeated.

### Methods and design choices
- **Fail fast for malformed input; record everything else.** The brief says "Invalid config or
  malformed input → clear error; no assessment produced", but also "Event below the confidence
  threshold → not used as evidence; logged". So structural problems raise, while data problems
  become `excluded` or `anomalies` entries that the report will show.
- **"Logged" means recorded in the result**, not just printed or written to a log file. The
  record reaches the JSON report (Increment 9), so an evaluator can see exactly which evidence
  was ignored and why. The alternative, Python `logging`, would be lost unless someone captured
  the console.
- **Zero shocks is not an anomaly.** The brief lists "no shock" as a missing reference (rules
  report "not evaluable because of R5") and "more than one shock" as a data anomaly. Treating
  zero as an anomaly would report the same problem twice.
- **`mixed_evidence_sources`:** an assessment should use either human annotation or model
  output, not both for the same event. Mixing would let a human tag "fill in" a model miss
  without anyone noticing. It is flagged, not rejected, because the brief does not define this
  case.
- **Contradictory evidence is left to the rules and the context.** What counts as a
  contradiction is rule-specific (for example R8's "visible paddle placed before the first
  placement"). I did not invent generic contradiction rules here. `Anomaly` is the mechanism
  later steps use to flag them.

### Assumptions
- **The confidence thresholds are placeholders.** The shared contract says the ASR confidence
  is an `exp(log-probability)` proxy, not a calibrated probability, so the audio 0.5 especially
  needs pilot validation.
- **One camera angle and one task ID per timeline is a hard rule.** If calibrated multi-camera
  fusion is added later (the contract calls it a later extension), this check would move into
  config.
- **A shock is counted per event.** Two shock events are an anomaly even if they are a few
  frames apart. Merging detections into one event is upstream's job (video postprocessing
  persistence and smoothing). If upstream cannot guarantee that, the rule could treat shocks
  within `simultaneous_window_seconds` as one. I did not add that silently.

### How it stays adaptable
- **New source:** add its threshold to `engine.yaml`. The validator already requires one per
  source.
- **New anomaly type:** add a check in `_anomalies`, or flag it later in the procedure context
  or a rule using the same `Anomaly` type. The report will show it without other changes.
- **Changed input format:** handled in the adapters (Increment 10). `prepare_timeline` only
  accepts the shared `Event` schema.

### Tests
`tests/test_rule_engine_prepare.py`, 22 tests:
- **Mapping (4):**
  - Canonical name plus original label.
  - Unknown, unused and unresolved labels are reported and not dropped.
  - Time order.
  - The input is not modified.
- **Confidence threshold (4)** (brief section 8: "below the confidence threshold"):
  - An event below the threshold is excluded and recorded with its threshold.
  - An event exactly at the threshold is kept.
  - Thresholds are per source.
  - Excluded events do not create anomalies.
- **Anomalies (6)** (brief section 8: "more than one shock"):
  - One shock: no anomaly.
  - Two shocks: flagged with both IDs.
  - No shock: not an anomaly.
  - Human plus model evidence for one event: flagged.
  - An empty timeline is valid.
  - Sources present are recorded.
- **Malformed input (7)** (brief section 8: "malformed input → clear error"):
  - Not a list.
  - A raw dict.
  - A missing ID.
  - A duplicate ID.
  - Two camera angles.
  - Two recordings.
  - Invalid times rejected by the shared schema.
- **Pipeline (1):** the sample fixture, after `merge_timeline`, prepares with no unknown labels
  and no anomalies.

Full suite: **144 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0, and its output is unchanged. `rules/` imports nothing from `video/`, `audio/`,
`legacy/` or `pipeline/`.

### Try it yourself
```powershell
.venv\Scripts\python -c "from rules.config import load_rules_config; from rules.prepare import prepare_timeline; from schemas.event import Event as E; p = prepare_timeline([E('Gel applied', 2, 2, 'annotation', 1.0, event_id='g1'), E('stand_clear_command', 4, 4.5, 'audio', 0.3, event_id='a1'), E('shock_delivered_on_screen', 9, 9, 'annotation', 1.0, event_id='s1'), E('shock_delivered_on_screen', 40, 40, 'annotation', 1.0, event_id='s2')], load_rules_config()); print([e.event_name for e in p.events]); print(p.excluded); print(p.anomalies)"
```
Expected output:
- The gel event and both shocks are kept.
- The stand-clear command is excluded (0.3 < 0.5).
- A `multiple_shocks` anomaly cites `s1` and `s2`.

### Open questions
1. Should shock events within `simultaneous_window_seconds` count as one shock (a defence
   against duplicated detections), or is that strictly upstream's job? Currently each event
   counts.
2. Should `mixed_evidence_sources` reject the timeline instead of flagging it?
3. Is "one camera angle, one task ID" right as a hard error for now?

### Next increment
**Increment 4: coverage model and policy** (`rules/coverage.py`):
- Coverage statuses (`covered`, `not_covered`, `unknown`) for each modality (video, audio) and
  region (`apical_zone`, `sternal_zone`).
- An event → region mapping in config.
- Lookup order: explicit timeline coverage, then region, then source, then modality.
- The single function that turns "missing + coverage status" into Fail or Unable to Verify,
  tested under every policy setting.

---

## Increment 3 review: changes before Increment 4 (2026-10-10)

Arnikan reviewed Increment 3. Each item below is what was asked and what was done.

### Earlier items (confirmed)
1. **A8 update:** already done in commit `ddfa846` and pushed.
   - `approved_by: Dr. Senani Samarasinghe`.
   - `approved_on: null`, because Arnikan said the date is not known.
   - Provenance fields kept, and the pending note removed.
   - The new limit names are kept.
   - `charge_to_shock_seconds` and the other unused limits stay null, each with a "not used by
     any rule yet" note.

   No change was needed.
2. **Duplicate shocks are not merged.** `multiple_shocks` now records whether consecutive shocks
   fall within `simultaneous_window_seconds`. The message then adds "(possibly the same shock
   detected twice)". `details` holds `within_simultaneous_window`, `smallest_gap_seconds` and
   the window used.
3. **`mixed_evidence_sources` stays a flag.** No change.
4. **One camera angle and one task ID** stays a hard error. Events with no angle were already
   ignored by the check. A new test proves that video events from one angle plus audio events
   with no angle are accepted.
5. **Ownership:**
   - `upstream_requirements.md` has a new section, "Upstream owns detection quality": merging
     duplicate detections and choosing confidence thresholds belong upstream.
   - The engine's confidence step stays as a configurable safety check. A threshold of 0
     disables it cleanly: confidence is always ≥ 0, so every event is kept and `excluded` is
     empty (new test).
   - New open question 12 (plan) and open item 6 (upstream): which side applies the thresholds?
6. **Source with no threshold** now raises `TimelineError` `no_confidence_threshold`, with a
   clear message (new test). **An empty timeline is not rejected** (existing test).

### New items
7. **Low confidence is not absence.**
   - Recorded in the plan ("Evidence rules", Increments 4 and 6): when a rule finds an event
     missing but an excluded low-confidence event of the same canonical name exists, the outcome
     is Unable to Verify, flagged `low_confidence_evidence`, never Fail.
   - `PreparedTimeline.excluded_named(name)` returns those events in time order.
   - `ExcludedEvent` now also stores `start` and `end`, so a rule can check whether the
     low-confidence event falls in the relevant period.
8. **Unknown labels warn.** Any unknown label raises an `unknown_labels_present` anomaly, with
   the event IDs and `details.labels` (`source:label`). This shows a possible naming mismatch
   instead of silently treating the event as missing (new tests: present and absent).
9. **Event time rule:** order and timing comparisons use each event's `start` time.
   - Documented in the `prepare.py` docstring, the plan ("Evidence rules") and the
     introduction of `anomalies.md`.
   - `prepare_timeline` already sorts by start time.
   - The `multiple_shocks` gap is a difference of start times.
   - A new test checks that a long event starting earlier comes first.
10. **Repeated events are kept.** A new test has three `gel_applied`, two `first_paddle_taken`
    and a command said twice. All are kept, in time order, with none merged or dropped. No code
    change: the step never merged anything.
11. **Timeline header request:**
    - `upstream_requirements.md` requests `recording_id`, `camera_angle`, `duration_seconds` and
      `analyses_run` with each timeline.
    - Why: without it, "no audio events" cannot be told apart from "audio analysis didn't run",
      so the engine would have to treat a likely learner mistake as unknown.
    - Its use is added to Increment 4 in the plan: an analysis that did not run gives
      `not_covered`, and a missing header gives `unknown`.
    - Listed as open question 13, and upstream open item 7.
12. **Supervisor questions on repeated actions:** added as open question 14.
    - 14a: gel applied more than twice — Fail, or "at least twice"?
    - 14b: paddles lifted and placed again before the shock.
    - 14c: discharge buttons pressed more than once.
13. **Anomaly list:** new `docs/rule_engine/anomalies.md`. It lists every rejection code (7) and
    anomaly code (3), which step raises it and why, plus the flags planned for later
    increments. It is to be extended in every increment.

### How the code changed
- **`rules/errors.py`:** `TimelineError(code, message)` now carries a stable `.code`. The code
  is also appended to the message (`... [duplicate_event_id]`), so it shows in tracebacks.
- **`rules/prepare.py`:**
  - Every rejection has a code.
  - A dict or string is rejected as `not_a_list`. (A dict is iterable, so before this change it
    would have been read as a list of its keys.)
  - There is a check for a missing threshold.
  - `ExcludedEvent` gains `start` and `end`, and the excluded list is sorted by time.
  - `Anomaly` gains `details` (a dict).
  - New `PreparedTimeline` helpers: `excluded_named(name)` and `anomaly(code)`.
  - The `multiple_shocks` window check, and the `unknown_labels_present` anomaly.

The shock check (start times; consecutive gaps):

```python
window = config.engine.value("simultaneous_window_seconds")
gaps = [later.start - earlier.start for earlier, later in zip(shocks, shocks[1:])]
duplicate = min(gaps) <= window
```

`shocks` is already in time order, so `zip(shocks, shocks[1:])` pairs each shock with the next
one. The smallest gap decides whether any two may be the same shock.

### Tests
`tests/test_rule_engine_prepare.py`: 22 → **31 tests**.
- **New:**
  - Repeated events are kept.
  - Start-time order.
  - A threshold of 0 disables the check.
  - A missing threshold gives `TimelineError`.
  - `excluded_named` lookup.
  - Close shocks are kept but marked.
  - Unknown labels warn, and known labels don't.
  - Audio without an angle is not a second angle.
- **Changed:** every rejection test now also checks `.code`, and a dict input is rejected.

Full suite: **153 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0. `rules/` imports nothing from `video/`, `audio/`, `legacy/` or `pipeline/`.

### Open questions added (plan section E)
- 12: Which side applies the confidence thresholds?
- 13: The timeline header.
- 14a–c: The supervisor questions on repeated actions.
- 15: The Increment 3 decisions, recorded as decided.

### Next increment
**Increment 4: coverage model and policy.**

---

## Approval-date rule (2026-10-13)

**Question from Arnikan:** in Increment 2, `approved_by` and `approved_on` had to be set
together, yet A8 now has `approved_on: null`. Was the rule relaxed?

**Answer: yes, in commit `ddfa846`**, when the A8 approval was recorded with an unknown date.
That change was noted in its commit message and in the "Increment 2 decisions" entry. Exactly
what changed in `rules/config.py`:

| | Rule |
|---|---|
| Increment 2 | `(approved_by is None) != (approved_on is None)` → error "approved_by and approved_on must be given together" |
| `ddfa846` | Only `approved_on` set without `approved_by` → error "approved_on needs approved_by". An approver with no date was accepted with no further condition |
| **Now (decided 2026-10-13)** | `approved_on` without `approved_by` → error (unchanged). `approved_by` with `approved_on: null` is allowed **only if `note` says the date is to be confirmed**: the note must contain both "date" and "to be confirmed", in any case. Otherwise: error "approved_on may be null only if note says the date is to be confirmed" |

- **A8 record:** now has `note: approval date to be confirmed`. This replaces the earlier
  "supervisor approval pending" note, and the record still counts as approved.
- **Tests:**
  - The A8 test now checks the note.
  - "Approver without date is allowed" is replaced by two tests. With no note, an unrelated
    note, or "to be confirmed" without the word "date" → rejected. With "approval date to be
    confirmed" or "Date to be confirmed by the supervisor" → accepted.

---

## Increment 4: Coverage model and policy (2026-10-13)

### What was done
The rule engine can now say whether the evidence for an event could have been observed
(**coverage**), and what a missing event then means. Rules will never decide this themselves:
they will call `Coverage.missing(event_name)` and get one answer from one configurable policy.

It covers four things:
1. **Coverage per region** (`apical_zone`, `sternal_zone`), **per source** (annotation, video,
   audio) and **per modality** (video, audio).
2. **The timeline header**, so that "no audio events" can be told apart from "audio not
   analysed". `analyses_run: {audio: true}` with no audio events means the audio was covered
   and nothing was said, so a missing command is a Fail. `{audio: false}` means not covered,
   so Unable to Verify. **No header at all means unknown.**
3. **Low confidence is not absence:** if a low-confidence event of the same name was excluded,
   the outcome is Unable to Verify, flagged `low_confidence_evidence`. It is never Fail, under
   every policy setting, and this is not configurable.
4. **Every outcome is configurable:**
   - Defaults per status.
   - Overrides per modality, source and region.
   - `unknown` is still marked undecided (interim: Unable to Verify, flagged
     `coverage_policy_undecided`).

It is not yet called by rules or the engine (Increments 5–7), so the pipeline output is
unchanged.

### How it was done
- **`configs/rule_engine/engine.yaml`:** `coverage_policy` now has `outcomes` (defaults,
  unchanged values), `by_modality`, `by_source` and `by_region` (overrides, all empty for now),
  and `regions` (`apical_zone: [apical_paddle_placed]`, `sternal_zone: [sternal_paddle_placed]`).
  All five keys are required.
- **`rules/config.py`:**
  - `EngineSettings` gains `coverage_overrides` (keyed `"region:apical_zone"` and so on), a
    `regions` mapping, and `region_of(event)`.
  - Validation: overrides may only name known modalities, sources and defined regions; only
    the three statuses; only `fail` / `unable_to_verify`.
  - A region's events must be canonical *video* events from the vocabulary, and no event may be
    in two regions.
  - `placeholders` and `undecided` now include overrides.
- **`rules/coverage.py`** (new):
  - **`TimelineHeader`:** `recording_id`, `camera_angle`, `duration_seconds`, `analyses_run`
    (modality → ran?) and `coverage` (explicit scope → status, for example
    `"region:sternal_zone": "not_covered"`). `from_dict` validates it (`invalid_header`).
  - **`Coverage(prepared, config, header=None)`:** checks the header against the events
    (`header_mismatch`), then answers two questions:
    - `status(event)` → `CoverageStatus(status, scope, basis)`;
    - `missing(event)` → `MissingOutcome(outcome, coverage, decided_by, flags,
      low_confidence_event_ids)`.

The two lookups:

```python
def status(self, event_name):
    if self.header is None:
        return CoverageStatus(UNKNOWN, None, "no timeline header")
    for scope in self.scopes(event_name):             # region, source, modality: most specific first
        if scope in self.header.coverage:
            return CoverageStatus(self.header.coverage[scope], scope, "header.coverage")
        kind, name = scope.split(":", 1)
        if kind == "modality" and name in self.header.analyses_run:
            ran = self.header.analyses_run[name]
            return CoverageStatus(COVERED if ran else NOT_COVERED, scope, "header.analyses_run")
    return CoverageStatus(UNKNOWN, None, "not stated in timeline header")

def missing(self, event_name):
    coverage = self.status(event_name)
    low = tuple(e.event_id for e in self.prepared.excluded_named(event_name))
    if low:                                            # low confidence is not absence: never Fail
        return MissingOutcome(event_name, "unable_to_verify", coverage, "low confidence is not absence",
                              (LOW_CONFIDENCE_FLAG,), low)
    setting = self._policy(event_name, coverage.status)  # by_region > by_source > by_modality > outcomes
    flags = (UNDECIDED_FLAG,) if setting.undecided else ()
    return MissingOutcome(event_name, setting.value, coverage, setting.name, flags)
```

How it works:
- **`scopes(event)`** lists the scopes that apply, most specific first. For
  `apical_paddle_placed` in an annotation timeline that is `region:apical_zone`, then
  `source:annotation`, then `modality:video`. A source scope is used only when exactly one
  source produced events of that modality. With two sources, no single source "owns" the
  coverage.
- **The first scope with stated coverage decides the status.** `basis` records where it came
  from, so the report can say why.
- **`decided_by`** names the exact policy setting used, for example
  `coverage_policy.by_region.apical_zone.covered`. Every Fail or Unable to Verify can then be
  traced to one line of config.
- **The header check** rejects a header that contradicts its events: a different camera or
  recording, events after `duration_seconds`, or "audio did not run" while audio events exist.
  Trusting such a header could turn a learner's actual commands into "not covered".

### Methods and design choices
- **Two separate questions:** "was it observable?" (status, from the data) and "what does
  missing mean?" (outcome, from the team's policy). Status depends on the recording; the outcome
  is a team decision. Keeping them apart means a decision is one config change, as you
  required, and the report can show both.
- **Most-specific-wins** for both status and policy. Region knowledge (for example "the
  sternal zone is not in this camera view") is more precise than "video ran", so it should win.
- **No header means unknown, not covered.** This follows "never blame the learner for missing
  data". The header is the only way the engine can know an analysis ran. Until upstream sends
  it, missing events are not Fails.
- **The low-confidence rule is hard-coded, not configurable.** You defined it as "never Fail".
  Putting it in config would make it changeable by accident.
- **Whole-recording coverage only, for now.** Per-interval coverage ("audio unclear 40–55 s")
  needs upstream to send intervals; it is open question 16.
- **Header passed separately.** The header is not part of the `Event` schema; it is passed to
  `Coverage` separately, so the shared schema is unchanged. How it travels with the timeline is
  decided with upstream (open question 13).

### Assumptions
- **`analyses_run: true` means the analysis covered the whole recording.** If upstream can only
  say "it ran" but not "it was usable", unusable stretches will need explicit `coverage`
  entries.
- **Regions apply to video events only,** and only the two per-paddle placement events belong
  to a region for now. Other events (for example `paddles_firmly_on_chest`) may need a region
  later.
- **Annotation timelines:** I propose the Increment 10 adapter declares
  `analyses_run: {video: true, audio: false}` (open question 17).

### How it stays adaptable
- **The team decides `unknown`:** change `coverage_policy.outcomes.unknown` and drop
  `undecided`.
- **A different policy for one modality, source or region:** add one line under `by_modality`,
  `by_source` or `by_region`.
- **A new camera region:** add it under `regions` with its events.
- **Upstream sends coverage:** use the header's `coverage` map. New scope kinds would need a
  code change in `scopes()`.

### Tests
**`tests/test_rule_engine_coverage.py`, 33 tests:**
- **Header (5):**
  - A full header and an empty header are accepted.
  - 9 invalid headers are rejected with `invalid_header`.
  - 4 contradictions are rejected with `header_mismatch`.
  - A matching header is accepted.
- **Status (7):**
  - No header → unknown.
  - A header without the modality → unknown.
  - `analyses_run` → covered / not covered.
  - Explicit coverage beats `analyses_run`.
  - Region coverage applies only to its own events.
  - Region beats source beats modality.
  - Source scope only when there is a single source.
- **No audio vs audio not analysed (3):** the same timeline gives Fail (audio ran),
  Unable to Verify (audio did not run), and Unable to Verify plus `coverage_policy_undecided`
  (no header).
- **Low confidence (3):**
  - Unable to Verify even when covered.
  - Never Fail, even with every outcome configured as `fail`.
  - Only the same canonical name counts.
- **Every policy setting (5):**
  - Each status × each outcome gives the configured outcome, with no undecided flag.
  - Override precedence, region > source > modality.
  - A modality override.
  - An override for another status falls back to the default.
  - An undecided override is flagged.
- **Repository policy (1):** the shipped values, `unknown` undecided, no overrides, the two
  regions.
- **Invalid config (9):**
  - A missing policy section.
  - Unknown modality, source, region or status.
  - A bad outcome.
  - An event in two regions.
  - An empty region.
  - A region event that is not a video event in the vocabulary.

**`tests/test_rule_engine_config.py`:** 43 → 44 tests (approval-date rule above).

Full suite: **187 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0, and its output is unchanged. `rules/` imports nothing from `video/`, `audio/`,
`legacy/` or `pipeline/`.

### Try it yourself
```powershell
.venv\Scripts\python -c "from rules.config import load_rules_config; from rules.prepare import prepare_timeline; from rules.coverage import Coverage, TimelineHeader; from schemas.event import Event as E; c = load_rules_config(); p = prepare_timeline([E('Gel applied', 1, 1, 'annotation', 1.0, event_id='g1'), E('oxygen_away_command', 5, 6, 'audio', 0.2, event_id='o1')], c); [print(h, '->', Coverage(p, c, h and TimelineHeader.from_dict(h)).missing(n)) for h in (None, {'analyses_run': {'video': True, 'audio': True}}) for n in ('stand_clear_command', 'oxygen_away_command')]"
```
Expected output:
- **No header:** a missing `stand_clear_command` is Unable to Verify (`unknown`,
  `coverage_policy_undecided`).
- **Header saying audio ran:** the same missing command is `fail` (`covered`).
- **Either header:** `oxygen_away_command` is Unable to Verify with `low_confidence_evidence`,
  because its only evidence was excluded at 0.2.

### Open questions
- 16: Time-windowed coverage.
- 17: Should the annotation adapter declare `analyses_run: {video: true, audio: false}`?
- Still open: 1 (final `unknown` policy) and 13 (timeline header format).

### Next increment
**Increment 5: procedure context** (`rules/context.py`). Computed once and shared by all rules:
- The shock time (R5, with R6 as fallback; Unable to Verify when there are multiple shocks).
- Phases before and after the shock.
- The first placement time, and the per-paddle placement times.
- Zone visibility, from coverage.
- Stop and start command times.
- `resume_compressions_command` resolved into continue (before the shock) or start (after it).

---

## Increment 4 review: changes before committing (2026-10-13)

Arnikan reviewed Increment 4 before it was committed. This supersedes the note-text rule in the
"Approval-date rule" entry above.

### 1. Approval date: structured `date_pending` field
- **Decision:** replace the note-text check with a structured field. `approved_on` may be null
  only when `date_pending: true` is set; the note is a human-readable explanation only.
- **`rules/config.py`:**
  - `date_pending` added to the allowed record keys, and `ClinicalValue.date_pending` (default
    `false`).
  - The note-text helper `_date_to_be_confirmed` is removed; the engine never reads `note`.
  - Rules now enforced:

| Record | Result |
|---|---|
| `approved_on` set, no `approved_by` | error "approved_on needs approved_by" (unchanged) |
| `approved_by` set, `approved_on: null`, `date_pending` missing or `false` | error "approved_on may be null only when date_pending: true is set" |
| `date_pending` not a boolean (`"yes"`, `1`, `null`) | error "date_pending must be true or false" |
| `date_pending: true` with a date, or without an approver | error "date_pending: true needs approved_by and approved_on: null" |
| `approved_by` set, `approved_on: null`, `date_pending: true` | accepted; counts as approved |

- **A8 record:** now `approved_by: Dr. Senani Samarasinghe`, `approved_on: null`,
  `date_pending: true`, and `note: approval date to be confirmed` (explanation only).
- **Tests:**
  - The note-text tests are replaced by five tests.
  - A missing flag, `false`, and wrong types are rejected.
  - Note text alone is never interpreted.
  - `date_pending: true` is accepted.
  - `date_pending` with a date, or without an approver, is rejected.
  - A dated approval needs no flag.

### 2. Duration tolerance
- **`engine.yaml`:** new `duration_tolerance_seconds: {value: 0.5, placeholder: true}`.
  It is required, and must be a nonnegative number.
- **`rules/coverage.py`:** the header check now uses each event's **end** time. An event (kept
  or excluded) may end up to the tolerance after `duration_seconds`, with the boundary
  inclusive. Beyond that it is still `header_mismatch`, and the message names both values.
  - **Why end, not start:** the event-time rule (start) is for order and timing between
    events. This check asks "does the event fit inside the recording?", and that depends on
    where the event ends.
- **Tests:**
  - Ending exactly at the duration: accepted.
  - Ending within the tolerance (60.4 s and 60.5 s against 60 s): accepted.
  - Ending beyond it (60.6 s): `header_mismatch`.
  - Low-confidence events are checked too.
  - The tolerance is configurable (2.0 s).
  - A negative tolerance is rejected.

### 3. Question 17: annotation `analyses_run` (decided)
- **Decision:** the annotation adapter declares `analyses_run: {video: true, audio: false}`.
  `video: true` is recorded as a **development assumption**: annotators tag only what is
  visible from that angle, so a missing tag may mean "not visible".
- **Report flag:** the report for annotation timelines, and every result built on one, carries
  the flag `annotation_coverage_assumed`, so these results are never mistaken for real
  assessments.
- **Where recorded:** planned in Increment 10 in the plan, added to `anomalies.md`, and question
  17 marked decided.

### 4. Question 16: no time windows (decided)
- **Correction:** when I reported Increment 4, `status()` and `missing()` received only the event
  *name*, with no time. A rule therefore had no way to say *when* it expected the event, so
  adding windows later would have meant changing every rule call.
- **Fix:** both methods now take an optional `window=(start, end)`.
  - It is validated (a malformed window raises `ValueError`, because it is a programming error,
    not bad data), and otherwise ignored for now.
  - Time-windowed coverage can later be added inside `rules/coverage.py` without changing any
    rule.
- **Where recorded:** in the module docstring and the plan, which also says rules should pass
  `window` whenever they know it. Question 16 is marked decided.
- **Tests:** passing a window does not change today's results, and malformed windows are
  rejected.

### Docs
- **`anomalies.md`:** `header_mismatch` now describes the end-time tolerance, and
  `annotation_coverage_assumed` is added as a planned flag (Increment 10).
- **Plan:** coverage notes (granularity, duration tolerance, approval date), the Increment 10
  row, placeholder list (D), and questions 16 and 17.

### Tests
- `tests/test_rule_engine_config.py`: 44 → 48.
- `tests/test_rule_engine_coverage.py`: 33 → 41.

Full suite: **198 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0. `rules/` imports nothing from `video/`, `audio/`, `legacy/` or `pipeline/`.

---

## Increment 5: Procedure context (2026-10-13)

### What was done
`build_context(prepared, config, header=None)` computes, once per timeline, the facts every rule
needs:
- **The shock time:** from `shock_delivered_on_screen`, with `paddles_removed_after_shock` as
  the fallback.
- **The phase of any time:** before, at, or after the shock.
- **Anchors:** the first placement, the apical and sternal placements, and the continue, stop
  and start commands.
- **Zone visibility** for the apical and sternal zones (from Increment 4 coverage).
- **Resolved commands:** each ambiguous `resume_compressions_command` is classified as continue
  (before the shock) or start (after it).

The context never judges and never guesses. When a fact cannot be established, it is absent
and flagged, and each rule decides what that means for its result. It is not yet used by rules
or the engine (Increments 6–7), so the pipeline output is unchanged.

Arnikan's four edge cases:
1. **Shock time from removal:** recorded on the shock anchor, which names the event and gives
   the reason. It is flagged `shock_time_from_removal`, and that flag appears on every elapsed
   time using the shock, and on every command resolved against it. Removal happens after the
   shock, so delays measured from it look shorter.
2. **Ambiguous command near the shock:** a `resume_compressions_command` within
   `simultaneous_window_seconds` (0.5 s) of the shock time stays unresolved, flagged
   `command_near_shock`. With no shock time at all it also stays unresolved, flagged
   `no_shock_time`.
3. **Multiple candidates:** an anchor with several events (for example two
   `first_paddle_placed`) uses the earliest, flags `multiple_candidates`, and records every
   candidate ID in `Anchor.candidates`.
4. **Multiple shocks:** no shock time is chosen, not even from a removal. The shock anchor is
   absent and flagged `multiple_shocks`, with both shock IDs as candidates. Phases, elapsed times
   from the shock, and command resolution are absent or unresolved, and flagged.

### How it was done
- **`rules/context.py`** (new):
  - **`Anchor`:** `name`, `time` (None when absent), `event_id`, `event_name`, `candidates`,
    `flags`, `reason`, and a `present` property.
  - **`CommandResolution`:** `event_id`, `label`, `time`, `resolved_to` (None when unresolved),
    `flags`.
  - **`Elapsed`:** the two anchors, `seconds` (None if either anchor is absent), and the union
    of both anchors' flags.
  - **`ProcedureContext`:**
    - `events`: prepared events with commands resolved, in time order.
    - `anchors`, `resolutions`, `zone_visibility`, `coverage`.
    - Methods `named()`, `anchor()`, `phase_of()`, `elapsed()` and `missing()`.

Command resolution, the core decision:

```python
def _resolve(resolution, time, shock, window):
    if not shock.present:
        return None, (NO_SHOCK_TIME,)
    carried = (SHOCK_FROM_REMOVAL,) if SHOCK_FROM_REMOVAL in shock.flags else ()
    if abs(time - shock.time) <= window:
        return None, (COMMAND_NEAR_SHOCK,) + carried
    before, after = resolution          # from vocabulary.yaml: resolve_by_shock
    return (before if time < shock.time else after), carried
```

How it works:
- **Which names to use** comes from `vocabulary.yaml` (`resolve_by_shock`), not from code, so
  another ambiguous command is one line of config.
- **A resolved event** is a copy with the canonical name. Its metadata keeps
  `source_label: resume_compressions_command` and records `resolved_by` and `shock_time`, so
  the report can explain the classification.
- **An unresolved event** keeps its ambiguous name, so no rule can count it as a continue or a
  start command. The continue and start anchors are then flagged `unresolved_commands`, because
  the command they missed might have been theirs.

**Shock time:** the multiple-shocks check comes **first**, so a removal event can never be used
to guess a shock time when the recording has two shocks.

**`ProcedureContext.missing(name)`** closes a gap found while building this. Low-confidence
`resume_compressions_command` events keep their ambiguous name, so `Coverage.missing
("start_compressions_command")` could not see them. A weak "resume compressions" after the shock
would then have made R7 a Fail. The context's `missing()` also treats a low-confidence ambiguous
command as evidence for `name` when it would resolve to `name`, or cannot be resolved at all. The
outcome is then Unable to Verify (`low_confidence_evidence`). A test shows `Coverage.missing`
alone would return `fail` in that case.

### Methods and design choices
- **Absent, not guessed.** An `Anchor` with `time=None` plus a `reason` and flags is used rather
  than a default value or an exception. Every rule must handle "no shock time" explicitly, and
  the report can say why. A default (for example the removal time when there are two shocks)
  would hide a data problem. An exception would stop the other rules, and the brief says every
  rule is always evaluated.
- **Flags travel with values.** `elapsed()` merges the flags of both anchors, so a timing result
  cannot use the removal-based shock time without carrying `shock_time_from_removal`.
  Increment 6's shared checks will copy these flags onto rule results.
- **Earliest candidate.** The earliest is used for every anchor, and all candidates are kept.
  Which occurrence a specific rule should use (for example the first start command *after* the
  shock for R7) stays with the rule (open question 19).
- **Rules use `ctx.named()`, not `prepared.named()`**, so they see resolved commands. Explicit
  names are never reclassified: a `start_compressions_command` said before the shock stays a
  start command, and R7 reports it as `before_shock`.

### Assumptions
- **Window** for "near the shock" is `simultaneous_window_seconds` (placeholder 0.5 s), measured
  from command start to shock start, inclusive.
- **Zone visibility** for a region is the coverage status of the region's first event, the
  per-paddle placement event.
- **Fallback misclassification:** under the removal fallback, a command between the real shock
  and the removal is classified as *continue*. It is flagged, but not left unresolved (open
  question 18).

### How it stays adaptable
- **New anchor:** one line in `ANCHOR_EVENTS`.
- **New ambiguous label:** one line in `vocabulary.yaml` (`resolve_by_shock`).
- **Window value:** change `simultaneous_window_seconds` in `engine.yaml`.
- **Time-windowed coverage:** `ctx.missing(name, window)` already passes the window through.

### Tests
`tests/test_rule_engine_context.py`, 29 tests:
- **Shock time (8):**
  - Shock on screen.
  - Removal fallback, recorded and flagged.
  - Every elapsed time using the fallback is flagged, and one not using it is not.
  - Several removals: the earliest is used, and all are recorded.
  - No shock.
  - Multiple shocks: no shock time, not guessed even with a removal, and elapsed times flagged.
  - A low-confidence shock is not used.
  - Phases.
- **Command resolution (8):**
  - Before → continue, after → start, with the original label and shock time recorded.
  - Within the window (29.5 s, 30.0 s and 30.4 s against a 30 s shock) → unresolved,
    `command_near_shock`.
  - At 30.6 s → resolved.
  - No shock → `no_shock_time`.
  - Multiple shocks → `no_shock_time`.
  - Unresolved commands flag the continue and start anchors, but not the stop anchor.
  - Resolution against a removal time carries `shock_time_from_removal`.
  - Explicit names are not reclassified.
- **Anchors (6):**
  - Multiple candidates: the earliest is used, all are recorded, and it is flagged.
  - A single candidate has no flag.
  - Per-paddle placement anchors.
  - An absent anchor gives its reason.
  - An absent anchor with low-confidence evidence is flagged.
  - Stop → start elapsed time.
- **Zone visibility (2):** no header → unknown; header region coverage.
- **Low-confidence resume commands (4):**
  - A weak resume after the shock makes a missing start command Unable to Verify (Coverage
    alone would say Fail).
  - A weak resume before the shock does not count for start, but does for continue.
  - A weak resume near the shock could be either.
  - Unrelated events are unaffected.
- **Order (1):** every event kept, in time order, after resolution.

Full suite: **227 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0, and its output is unchanged. `rules/` imports nothing from `video/`, `audio/`,
`legacy/` or `pipeline/`.

### Try it yourself
```powershell
.venv\Scripts\python -c "from rules.config import load_rules_config as L; from rules.prepare import prepare_timeline as P; from rules.context import build_context as B; from schemas.event import Event as E; c = L(); x = B(P([E('first_paddle_firmly_on_the_chest', 14, 14, 'annotation', 1.0, event_id='p2'), E('first_paddle_firmly_on_the_chest', 12, 12, 'annotation', 1.0, event_id='p1'), E('paddles_removed_after_shock', 33, 33, 'annotation', 1.0, event_id='rm'), E('resume_compressions_command', 33.2, 34, 'audio', 0.9, event_id='r1'), E('resume_compressions_command', 36, 37, 'audio', 0.9, event_id='r2')], c), c); print(x.shock); print(x.anchor('first_placement')); [print(r) for r in x.resolutions]; print(x.elapsed('shock', 'start_compressions'))"
```
Expected output:
- **Shock:** 33 s from the removal, flagged `shock_time_from_removal`.
- **First placement:** 12 s (`p1`), with candidates `p1` and `p2`, flagged
  `multiple_candidates`.
- **`r1` at 33.2 s:** unresolved, flagged `command_near_shock` and `shock_time_from_removal`.
- **`r2` at 36 s:** resolved to start.
- **Elapsed shock → start:** 3 s, flagged `shock_time_from_removal` and `unresolved_commands`.

### Open questions
- 18: Under the removal fallback, should a command between the real shock and the removal stay
  unresolved instead of being classified as continue?
- 19: Which start command counts for R7/A8 (for example, the first after the shock)? To be
  confirmed when those rules are built.

### Next increment
**Increment 6: `RuleOutcome` and shared checks** (`rules/outcome.py`, `rules/checks.py`):
presence, count, order, time limit, simultaneity, inference and dependency helpers. These use
`ctx.missing()`, copy anchor and `Elapsed` flags onto results, and report "timing not checked"
for null limits.

---

## Answers to OQ-029/OQ-030, and the project documentation set (2026-10-13)

From this entry on, progress.md is the chronological log. It links to register IDs (D, A, OQ, P)
instead of repeating their content.

### A. Context changes (answers to plan questions 18 and 19)
- **OQ-029 (was E-18) → D-024:** when the shock time comes from removal, every "resume
  compressions" before the removal stays unresolved, flagged `command_before_removal` (P-011).
  `rules/context.py` `_resolve` now checks this before the near-shock window.
- **OQ-030 (was E-19) → D-025:** the start anchor is the earliest start command **after** the
  shock (P-012, new `_start_anchor`).
  - **At or before the shock:** a start command does not count. It is listed in the new
    `Anchor.ineligible`, and the anchor is flagged `start_command_before_shock`, for A7 to
    report.
  - **No shock time:** the start anchor is absent (`no_shock_time`, plus the shock flags).
  - **Under the removal fallback:** the start anchor carries `shock_time_from_removal`.
- **Consequence:** under the removal fallback, the stop → start interval (A8) is now flagged
  `shock_time_from_removal` too, because which start counts depends on the shock time. One
  Increment 5 test asserted the opposite, and was updated with that reason.
- **Agent choice to confirm (A-014, new OQ-039):** under the fallback, an explicit start
  command before the removal is treated as before the shock, so it does not count. It is
  flagged.
- **Code:** `context.FLAGS` and `coverage.FLAGS` now list every flag, for the documentation
  test.
- **Tests:** `tests/test_rule_engine_context.py` 29 → 39.
  - 3 tests for D-024: before removal → unresolved; just after removal → near shock; a real
    shock is unaffected.
  - 7 tests for D-025: the earliest after the shock; a start before the shock doesn't count; a
    start only before the shock; a start exactly at the shock; no shock time (no shock, and
    multiple shocks); the fallback flag; a weak start.

### B. Documentation set (backfilled from Step 0 to Increment 5)

| Document | Contents |
|---|---|
| [decisions.md](decisions.md) | D-001 to D-052: every decision so far, with date, decider, status, reason, alternatives, what it affects, and the question it resolved |
| [assumptions.md](assumptions.md) | A-001 to A-016, including A-001 (annotation covers video, development only), A-002 (placeholder values), A-003 (provisional command names) |
| [open_questions.md](open_questions.md) | OQ-001 to OQ-039: the single register, migrated from plan section E (`E-1`…`E-19`), the increment reports (`IncN-Qn`) and the brief's §9. It has a summary table, owner sections with **For the supervisor** first, and answered questions kept with their decision |
| [decision_flow.yaml](decision_flow.yaml) | P-001 to P-018: 13 built decision points (P-002 to P-013) and 5 planned (P-001, P-014 to P-018) |
| [pathways.md](pathways.md) | The readable version of every decision point, plus 13 worked pathways (W-1 to W-13) |
| [rules_status.md](rules_status.md) | All 16 rules: logic, events, decision points, failure codes, increment, status (all pending), and the questions each is waiting on |
| [methods.md](methods.md) | Architecture, techniques and why, how-tos, and the definition of done |
| [diagrams.md](diagrams.md) | Seven Mermaid diagrams (a) to (g), labelled with P-IDs, with planned parts dashed |

- **New test:** `tests/test_rule_engine_docs.py`, 11 tests.
  - Every flag, anomaly and rejection code raised in code is in `decision_flow.yaml`, and the
    reverse (planned points excepted).
  - Every listed code is in `anomalies.md`.
  - Every D/A/OQ/P ID referenced in the docs, `rules/` or the rule-engine tests exists exactly
    once.
  - The summary table matches the entries, and every answered question names its decision.
  - **Checked by breaking it on purpose:** dropping a code from the YAML, or referencing an
    unknown OQ, makes it fail.
- **`implementation_plan.md`:**
  - Section E now points to `open_questions.md`; the old numbers survive in its "Old no."
    column.
  - Section C has the new definition of done (full text in `methods.md` §4).
- **`anomalies.md`:** the new flags `command_before_removal` and `start_command_before_shock`;
  the updated `no_shock_time`; a new section of planned rule failure codes (from the brief); and
  links to the P-IDs.

### Open questions in this step
- **New:** OQ-039 (start command before the removal under the fallback). Newly registered from
  the brief §9 list, which was not in plan section E: OQ-036 (checklist format), OQ-037 (model
  output formats), OQ-038 (final camera angle).
- **Answered:** OQ-029 → D-024, OQ-030 → D-025.

### Documents updated
`rules/context.py`, `rules/coverage.py`, `tests/test_rule_engine_context.py`,
`tests/test_rule_engine_docs.py` (new); `decisions.md`, `assumptions.md`,
`open_questions.md`, `decision_flow.yaml`, `pathways.md`, `rules_status.md`, `methods.md`,
`diagrams.md` (all new); `anomalies.md`, `implementation_plan.md`, `progress.md`,
`ai_usage_log.md`.

### Tests
Full suite: **248 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0.

---

## Documentation review: D-053 and question ownership (2026-10-13)

### 1. A start command before the removal is timing-ambiguous (D-053, closes OQ-039)
- **Decision:** Arnikan rejected the agent's A-014 proposal and decided D-053.
  - Under the removal fallback, an explicit start command at or before the removal is
    timing-ambiguous, the same as D-024: not counted as the restart, and not a mistake, flagged
    `command_before_removal`.
  - R7/A6 and A8 give Unable to Verify, not Fail.
  - A7 does not report it.
- **Code** (`rules/context.py`, P-012):
  - New field `Anchor.ambiguous`, kept separate from `Anchor.ineligible` (start commands before
    a confirmed on-screen shock, which A7 reports).
  - Under the fallback, earlier start commands go to `ambiguous`, flagged
    `command_before_removal`. A later start is still used as the restart time, but the anchor
    keeps the flag, so a delay measured to it is not trusted (W-14).
- **Consistency fix (agent):** with no shock time at all, start commands were listed as
  `ineligible`, which A7 would report. They are now `ambiguous` too: the timing is just as
  unknown. This is included in D-053.
- **Tests:** `tests/test_rule_engine_context.py` 39 → 42.
  - A start before the removal is ambiguous and not a mistake (at 20 s, 32 s and 33 s against a
    33 s removal).
  - A later start is used, but the ambiguity flag is kept and reaches the stop → start elapsed
    time.
  - With a shock on screen, a start before it is still a mistake.
  - The no-shock-time test now expects `ambiguous`.
- **Registers:**
  - D-053 is added; D-025 is marked "refined by D-053".
  - A-014 is rewritten: the real shock time is unknown but before the removal.
  - OQ-039 is answered → D-053.
- **Flow, pathways, diagrams and anomalies:**
  - `decision_flow.yaml`: P-012 has a new branch, and P-014 a planned branch ("restart
    ambiguous → Unable to Verify").
  - `pathways.md`: P-012 and P-014 rows, a new worked pathway W-14, and W-10 now says its shock
    was confirmed on screen.
  - `diagrams.md`: (c) has an ambiguity step, and there is a new diagram (e2), "Which start
    command is the restart".
  - `anomalies.md`: `command_before_removal` and `start_command_before_shock` rows.
  - `rules_status.md`: R7/A6, A7 and A8.

### 2. Question ownership
- **"Also involves":** `open_questions.md` now has an "Also involves" column, and each entry has
  an "Also involves" field.
- **Grouping rule:** a question with a clinical part appears in the supervisor section, even
  when someone else owns the technical part.
- **Changes:**

| Question | Change |
|---|---|
| OQ-012 | Owner **Ananth → supervisor** (approving the chest regions); also involves Ananth (detection). Moved to the supervisor section and retitled |
| OQ-001 | Owner stays team; also involves supervisor (whether unverifiable evidence may count against a learner). **Moved** to the supervisor section |
| OQ-006 | Owner stays team (the window value); also involves supervisor (is the apical-first fallback clinically acceptable?). **Moved** to the supervisor section |
| OQ-036 | Owner stays team; also involves supervisor (the checklist mirrors the faculty rubric). **Moved** to the supervisor section |
| OQ-021, OQ-022, OQ-023 | Also involves Ananth (detecting each repeated action), Arnikan |
| OQ-010 | Also involves Sanjeevan (phrase matching), Arnikan |
| OQ-009 | Also involves Arnikan; notes that its clinical part is OQ-010 |
| OQ-020 | Also involves Sanjeevan (whether audio analysis ran), Arnikan |
| OQ-015 | Also involves supervisor (rubric naming); stays in the team section, because it is not clinical |
| OQ-018, OQ-019 | Also involves Ananth, Sanjeevan, Arnikan (by part) |
| OQ-037 | Also involves Ananth, Sanjeevan |
| OQ-038 | Also involves Ananth |
| OQ-002, OQ-005, OQ-013, OQ-016, OQ-004, OQ-017, OQ-014 | "Also involves" filled in (Arnikan); no move |

### Documents updated
`rules/context.py`, `tests/test_rule_engine_context.py`, `decisions.md`, `assumptions.md`,
`open_questions.md`, `decision_flow.yaml`, `pathways.md`, `diagrams.md`, `anomalies.md`,
`rules_status.md`, `progress.md`, `ai_usage_log.md`.

### Open questions in this step
- **Answered:** OQ-039 → D-053.
- **New:** none.

### Tests
Full suite: **251 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0.

---

## Diagram review: logic fixes (2026-10-13)

Arnikan checked that the diagrams render on GitHub, and found logic issues.

### Decisions recorded
- **D-055:** the overall result can be Pass only if every rule was evaluated. Any pending rule
  makes it "incomplete: rules not yet approved", never Pass. It refines D-043.
- **D-056:** "not evaluable" counts like Unable to Verify in the overall policy.
- **D-054:** with no shock time, start commands are timing-ambiguous. This was split out of
  D-053, and cross-references in the code, tests, decision flow, anomalies, pathways and rule
  status are updated.
- **D-057:** an approved inference (R3/R4) applies when direct evidence is missing as well as
  when it is weak, checked before the coverage step.

### Open questions added (for Arnikan)
- **OQ-040:** R8 when a placement event is missing. The proposed outcome for both (a) the
  visible zone's paddle has no placement event and (b) both zones visible but one placement
  missing: Unable to Verify, flagged `placement_missing`, with no inference and not
  `wrong_order`. R3 reports the missing placement (D-003).
- **OQ-041:** R7/A6 and A8 under the removal fallback with no ambiguous start. Planned in P-014:
  - The start after the removal is definitely the restart.
  - A8's stop → restart is measured without the fallback flag.
  - R7/A6: a delay from the removal that is already over the limit is a confident Fail
    `too_late`; one within the limit is Unable to Verify (`shock_time_from_removal`).
  - **Agent's addition:** should an unresolved "resume" before the removal make the restart
    ambiguous too (proposed: yes)?

### Code change (interim, under OQ-041)
`rules/context.py` `_start_anchor`: under the fallback, the start time now carries
`shock_time_from_removal` (with `command_before_removal`) **only** when a start command before
the removal is ambiguous. When the restart is certain it is unflagged, so A8's stop → restart
elapsed time is unflagged; R7/A6's shock → restart is still flagged through the shock time.
This reverses the "consequence" noted on 2026-10-13 (stop → start flagged), on Arnikan's
reasoning that the interval does not depend on the shock time.

### Logic fixes in the documentation
- **P-017** (`decision_flow.yaml`, `pathways.md`, diagram g): Fail first (even with pending
  rules), then any pending → incomplete, then Unable to Verify or Not evaluable → the undecided
  policy, else Pass.
- **P-014 / P-016** (diagram c): "weak **or missing**" direct evidence goes to the inference
  check **before** the coverage step. P-014 also has the planned R7/A6 and A8 fallback branches
  and a separate route to P-015 for R8.
- **P-015** (diagram f): the two missing-placement branches (OQ-040), plus the planned flag
  `placement_missing` (in `anomalies.md`).
- **Diagram (e2):** each start command is checked on its own, and the restart is the earliest
  remaining candidate.
- **Diagram (e):** the window is labelled as configurable, `simultaneous_window_seconds`
  (placeholder 0.5 s).
- **Diagram (b):** P-013 added.
- **New worked pathways:** W-15 to W-22.
  - R7/A6 under the fallback: Fail, and Unable to Verify.
  - R8 missing placements: two cases.
  - A8 under the fallback.
  - R3 inference with missing evidence.
  - Overall result with a pending rule, and with a "not evaluable" rule.
- **W-5** rewritten.

### Tests
- **Changed:** "stop → start flagged under the fallback" now asserts the opposite (OQ-041).
- **Replaced:** "start anchor carries the fallback flag" is now "an unambiguous restart carries
  no fallback flag (but shock → restart does)".
- **Added:** each start command is checked on its own.
- `tests/test_rule_engine_context.py`: 42 → 43.
- The documentation consistency test caught the undocumented `placement_missing` before it was
  added to `anomalies.md`.

### Documents updated
`rules/context.py`, `tests/test_rule_engine_context.py`, `decisions.md`, `open_questions.md`,
`decision_flow.yaml`, `pathways.md`, `diagrams.md`, `anomalies.md`, `rules_status.md`,
`progress.md`, `ai_usage_log.md`.

### Open questions in this step
- **New:** OQ-040, OQ-041.
- **Answered:** none.

### Tests
Full suite: **252 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0.

---

## Answers to OQ-040/OQ-041, and the assumed-result rule (2026-10-13)

- **D-057 kept** as a decision (Arnikan).
- **OQ-040 → D-058:** R8 with a missing placement event (visible zone without a placement, or
  one of two visible placements missing) gives Unable to Verify, flagged `placement_missing`,
  with no inference; R3 reports the missing placement.
- **OQ-041 → D-059:** R7/A6 and A8 under the removal fallback, as specified. It also makes an
  unresolved "resume" before the removal leave the restart ambiguous.
  - **Context:** `_start_anchor` now also lists unresolved resume commands before the removal
    (`command_before_removal`) in `Anchor.ambiguous`.
  - **Tests:** 3 new context tests (43 → 46).
- **D-060:** an assumed result (R8's apical-first fallback) prevents an overall Pass, like a
  pending rule (D-055).
- **Docs:**
  - `decision_flow.yaml`: P-012, P-014, P-015, P-017.
  - `pathways.md`: the matching rows, plus W-23 (R8 assumed → incomplete) and W-24 (resume before
    the removal → restart ambiguous).
  - `diagrams.md`: (e2), (f), (g).
  - `anomalies.md` and `rules_status.md`.

---

## Increment 6: RuleOutcome and shared checks (2026-10-13)

### What was done
Every rule will now be built from two new modules:
- **`rules/outcome.py`:** `RuleOutcome`, the rule engine's own result for one rule. It holds the
  kind, reason, failure code, evidence, flags, `blocked_by` and `timing_checked`, and converts to
  the shared `RuleResult`.
- **`rules/checks.py`:** the ladder steps of diagram (c), as shared checks with the decision points
  P-019 to P-025. Each check returns either an outcome or "go on" (`None`).

No individual rule is built yet. The engine that runs the ladder for each rule is Increment 7,
so the pipeline output is unchanged.

The five properties you asked for:

| Requirement | Where | How |
|---|---|---|
| Inference **before** coverage for weak or missing evidence | `missing()` (P-023) | If the rule passes `inference=` event names and one is confirmed → Pass – Inferred. Only otherwise is `ctx.missing()` asked (D-057) |
| `ctx.missing()` for **every** missing event, so low confidence is never Fail | `missing()`, `occurrences()` | No check builds a missing Fail itself. When confident occurrences exist but none is valid, a low-confidence occurrence still gives Unable to Verify (P-022) |
| A null limit means "timing not checked" | `time_limit()`, `timed()` (P-024) | A null, unapproved or unmeasurable limit → `checked=False` and the flag `timing_not_checked`. `timed()` then passes on presence and order, with `timing_checked=False` and "timing not checked" in the reason |
| Repeated events: any valid occurrence satisfies the rule | `first_valid()`, `occurrences()` (P-022) | The earliest **valid** occurrence is cited; invalid ones elsewhere don't matter (D-012) |
| Anchor and elapsed-time flags carried onto every result | `outcome.flags_of`, `uses=` on every builder | Every builder takes `uses=(anchor, elapsed, check, missing_outcome…)` and merges their flags in order, without duplicates |

### How it was done
`RuleOutcome` checks its own consistency:
- a Fail needs a failure code, and only a Fail has one;
- a Pass must cite evidence;
- `blocked_by` exists only for "not evaluable";
- flags and evidence are de-duplicated in order.

`to_rule_result()` maps the kinds onto the existing statuses (D-045): passes and Fail keep
theirs, and everything else becomes `unable_to_assess`. The reason text spells out what the
status can't, for example `"7 s against a limit of 5 s [failure code: pre_shock_pause; flags:
shock_time_from_removal]"`. `as_rule("A6")` reports R7's outcome under A6 (D-044).

A rule will read as a chain in diagram (c) order (illustration of Increment 18's A3):

```python
return (checks.requires("A3", ctx.shock, "R5")
        or checks.occurrences("A3", ctx, "stand_clear_command",
                              valid=lambda e: e.start < ctx.shock.time,
                              invalid_code="after_shock", what="stand clear", uses=(ctx.shock,)))
```

How it works: `requires` returns "not evaluable because of R5" if there is no shock time,
otherwise `None`, so `or` moves to the next step. `occurrences` returns:
- Pass – Direct for the earliest command before the shock;
- Fail `after_shock` if every command was after it, unless a weak one may have been before it;
- the missing-event outcome if none was said.

`uses=(ctx.shock,)` carries, for example, `shock_time_from_removal` onto whichever result comes
out.

### Methods and design choices
- **Return an outcome or `None`.** The ladder becomes a readable `or` chain, and the order of the
  steps is the same in every rule. The alternative, a class hierarchy with a fixed template
  method, would hide the order and make rule-specific steps (such as R8's inference) awkward.
- **`uses=` instead of copying flags by hand.** A rule cannot forget a flag, because flags come
  from the objects the result was built from.
- **`occurrences()` checks low confidence even when confident evidence exists.** "Stand clear"
  confidently after the shock plus a weak one before it is Unable to Verify, not Fail, because
  the weak one may have been the valid one. This is the same principle as D-010, applied to
  invalid evidence.
- **Unapproved limits are ignored** (A-017, OQ-042). This follows D-005 and "never invent
  clinical values".

### Assumptions
- **A-017 (new):** a limit with a value but no approver is not used. It is open as OQ-042.
- **Confirmed means confident:** "confidently confirmed" for an inference means the event
  survived the confidence step (P-004). No higher bar is applied.

### How it stays adaptable
- **New rules** are short chains of these checks. New ladder steps become new checks with a
  P-ID.
- **Limits:** when the supervisor approves a limit, the same rule starts checking timing, with
  no code change.
- **Overall policy:** it reads `kind`, `passed` and `evaluated` (Increment 8).

### Tests
`tests/test_rule_engine_checks.py`, 37 tests:
- **Outcome (7):** validation, de-duplication, mapping of all 7 kinds, reason text, evaluated
  and passed, same_as, `flags_of`.
- **Dependencies (3):** passed → go on; each non-passing kind → not evaluable; evaluation-order
  mistakes are loud.
- **Required facts (2).**
- **Restart ambiguity (2).**
- **Occurrences (6):**
  - A valid occurrence passes.
  - **Repeated events: any valid one** satisfies the rule.
  - Only invalid occurrences → Fail with the rule's code.
  - Invalid but weak-valid → Unable to Verify.
  - No occurrence → the missing ladder.
  - **Anchor flags are carried.**
- **Missing ladder (7):**
  - **Inference before coverage**, which would otherwise have said Fail.
  - The earliest supporting event is cited.
  - With no inference, it falls through to coverage.
  - All three coverage outcomes.
  - **Low confidence is never Fail, even when covered.**
  - A low-confidence ambiguous command is never Fail.
  - A custom failure code.
- **Timing (8):**
  - **A null limit means timing not checked.**
  - An unapproved limit is not used.
  - An unmeasurable interval.
  - Within, at and over the limit.
  - The repository's A8 limit is usable.
  - `timed` passes without a limit but says so.
  - `timed` fails over the limit and **carries the elapsed time's flags**.
  - Within the limit.
- **Order (2).**

`tests/test_rule_engine_docs.py` now also reads `checks.FLAGS`. It failed until
`timing_not_checked` and `limit_not_approved` were documented and P-019 to P-025 existed.

Full suite: **292 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0. `rules/` imports nothing from `video/`, `audio/`, `legacy/` or `pipeline/`.

### Try it yourself
```powershell
.venv\Scripts\python -m unittest tests.test_rule_engine_checks -v
```

### Documents updated
- **Code and tests:** `rules/outcome.py` (new), `rules/checks.py` (new), `rules/context.py`,
  `tests/test_rule_engine_checks.py` (new), `tests/test_rule_engine_context.py`,
  `tests/test_rule_engine_docs.py`.
- **`decision_flow.yaml`:** P-019 to P-025 built; P-012, P-014, P-015 and P-017 updated.
- **`pathways.md`:** a shared-checks section, and W-23 to W-26.
- **`diagrams.md`:** (b), (c) (P-IDs; the built steps are no longer dashed), (e2), (f), (g).
- **Registers:** `decisions.md` (D-058, D-059, D-060), `assumptions.md` (A-017),
  `open_questions.md` (OQ-040 and OQ-041 answered, OQ-042 new).
- **Other docs:** `anomalies.md`, `methods.md`, `rules_status.md`, `progress.md`,
  `ai_usage_log.md`.

### Open questions
- **New:** **OQ-042**, whether a provided but unapproved time limit is ignored (current) or
  used with a flag.
- **Answered:** OQ-040 → D-058, OQ-041 → D-059.

### Next increment
**Increment 7: rule registry and engine wiring.**
- Discover the rules.
- Run the ladder in evaluation order, so pending rules become `pending` and A6 reuses R7.
- Keep `evaluate()` unchanged for the pipeline.

---

## Answers: OQ-042 and unchecked timing (2026-10-14)

- **OQ-042 → D-061:** a time limit with a value but no approver is ignored and flagged
  `limit_not_approved` (as built in Increment 6). A-017 is marked confirmed.
- **D-062:** a rule result flagged `timing_not_checked` or `limit_not_approved` stays a Pass at
  rule level, but the overall result is **incomplete** ("timing not checked for R7"), never Pass,
  like a pending rule (D-055).
- **Updated:**
  - `decision_flow.yaml`: P-017 (incomplete branch), P-024.
  - `pathways.md`: the P-017 and P-024 rows, and new worked pathway W-27.
  - `diagrams.md`: (g).
  - `anomalies.md`, `assumptions.md`, `open_questions.md`, `decisions.md`.
- **Open questions:** OQ-042 answered; no new questions.

---

## Increment 7: Rule registry and engine wiring (2026-10-14)

### What was done
The engine now runs every rule through the new pieces, instead of the Increment 0 scaffold.
`assess(events, config, header=None)` does the following:
1. Prepares the timeline (P-002 to P-005).
2. Builds the procedure context (P-006 to P-013).
3. Evaluates **every** rule in evaluation order (dependencies first), and reports in display order
   (P-026).

Each rule's result is one of:
- **pending**, if the rule is not approved;
- **the reused outcome**, under its own ID, if it is `same_as` another rule (A6 = R7);
- **not evaluable**, if a rule it depends on did not pass;
- **its own outcome**, from its registered function;
- **`engine_error`**, if that function crashes (D-063).

`evaluate(events, config)` keeps its signature and returns the shared `RuleResult` list for
`pipeline/run.py`.

**Your two additions:**
1. **A crashing rule is recorded (D-063).**
   - A registered rule that raises, or returns something invalid (not an outcome, the wrong rule
     ID, or evidence outside the timeline), gets `engine_error`, with the message in its reason
     (for example "ZeroDivisionError: division by zero in R2").
   - Every other rule still runs, and dependents are "not evaluable because of R2". A6 reusing
     an errored R7 reports the error too.
   - `engine_error` counts as not evaluated, so the overall result will be incomplete (P-017,
     Increment 8).
2. **The pipeline output is unchanged while all rules are pending.**
   - Before changing the engine, I saved the pipeline's output for the sample timeline to
     `tests/fixtures/rule_engine/pipeline_all_pending.json` (the events, the 16 rule results with
     their exact pending text, and the feedback).
   - A test compares the current pipeline report with it, field by field. It passes, so the new
     engine produces identical output.

### How it was done
- **`rules/registry.py`** (new): `@rule("A3", requires=(...), description=...)` registers a rule
  function `(ctx, definition, results) -> RuleOutcome` next to its logic. `discover()` imports
  every `*_rules` module in `rules/`, so a new rule module needs no engine change (D-064).
  Registering two different functions under one ID is an error.
- **`rules/engine.py`** (rewritten): `assess()` and `Assessment` (outcomes, prepared timeline,
  context, config). `_evaluate()` follows P-026:

```python
if not definition.enabled:            return pending(rule_id, DISABLED_REASON)   # not reported
if definition.status != "approved":   return pending(rule_id)
if definition.same_as:                return results[definition.same_as].as_rule(rule_id)
blocked = checks.depends(rule_id, definition.depends_on, results)
if blocked is not None:               return blocked
...
try:
    outcome = function(context, definition, results)
    _check_outcome(outcome, rule_id, event_ids)
except Exception as error:            # D-063: recorded, never stops the assessment
    return engine_error(rule_id, error)
```

  How it works:
  - **Order:** rules are visited in `config.evaluation_order()`, the topological order from
    Increment 2, so a dependency's result always exists when needed. `results` collects them, and
    the final tuple is rebuilt in display order.
  - **Errors:** the `try` covers the rule's own code and the validation of what it returned, so a
    wrong return is caught as an engine error too.
- **The `implementation: module:function` path** (the shared contract test) still works, in two
  ways:
  - If it points at a registered function, that function is run like any registered rule.
  - Otherwise it is called the old way, `(timeline, settings) -> RuleResult`, and its
    `RuleResult` is reported **exactly as returned** (new `RuleOutcome.original`).
  - Its contract violations still stop the run, as `test_rule_cannot_cite_nonexistent_evidence`
    requires. This is noted in D-063.
- **`rules/outcome.py`:** a new kind, `ENGINE_ERROR` (not evaluated, so the overall result
  cannot be Pass), and `engine_error()`. `pending()` now uses the original pending text, and its
  RuleResult reason gets no "[pending]" suffix, which keeps the pipeline output identical.
- **`rules/base.py`:** documents both rule kinds.
- **Startup check:** the events a rule declares in `requires=` must exist in the vocabulary,
  otherwise `ConfigError` stops the run, so a typo cannot silently make a rule Unable to Verify.

### Methods and design choices
- **Decorator registry over listing implementations in YAML.** The rule's ID and the events it
  needs sit next to its code (brief §3). The YAML keeps what the team and the supervisor
  decide: order, status, dependencies and limits.
- **Catch at the boundary of each rule, not inside the checks.** One `try` per rule is the only
  place an error can be turned into a result. Errors inside a rule are never swallowed elsewhere.
- **Malformed input and invalid config still stop the run.** Those mean no assessment can be
  trusted at all (P-002, D-049), while a crashing rule affects only itself and its dependents.

### Assumptions
- **Disabled rules:** a rule disabled in config is still recorded internally as pending (so its
  dependents are not evaluable) but is not reported, as before.

### How it stays adaptable
- **New rule:** a decorated function in a `*_rules` module, plus a line in `rules.yaml`.
- **New rule module:** name it `*_rules.py`.
- **Report and overall policy:** they read `Assessment` (Increments 8 and 9). `pipeline/run.py`
  can switch from `evaluate()` to `assess()` when Ananth is ready (OQ-017).

### Tests
`tests/test_rule_engine_engine.py`, 25 tests:
- **Ordering (2):** dependencies are evaluated first and reported in display order; every rule
  is evaluated after a failure.
- **Status and reuse (5):**
  - Pending rules are not called, and keep the original reason.
  - Approved but unregistered → pending.
  - Disabled rules are not reported.
  - same_as copies the outcome.
  - same_as a pending rule is pending.
- **Dependencies (2):** failed or unable dependency → not evaluable; pending dependency →
  blocks.
- **Engine errors (5):**
  - The exception is recorded with its message, the others still run, and it is not evaluated.
  - Dependents are not evaluable.
  - same_as reports the error.
  - Invalid returns (None, the wrong ID, evidence outside the timeline) are engine errors.
  - Malformed input still stops the run.
- **Rules use the context (3):**
  - A rule built from the shared checks passes.
  - Required events are checked against the vocabulary.
  - The header reaches coverage.
- **Registry (4):** the decorator registers; two functions for one ID are rejected; discovery
  imports the rule modules; an implementation path can point at a registered rule.
- **Shared contract (2):** a path rule's result is reported exactly as returned; it receives
  the settings.
- **Pipeline (2):** the output matches the pre-Increment 7 reference; the real config gives 16
  pending rules.

The existing shared contract tests (`tests/test_pipeline_contracts.py`) pass unchanged.

Full suite: **317 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0. `rules/` imports nothing from `video/`, `audio/`, `legacy/` or `pipeline/`.

### Try it yourself
```powershell
.venv\Scripts\python -m unittest tests.test_rule_engine_engine -v
.venv\Scripts\python -c "from rules.engine import assess; import json, yaml; from schemas.event import Event; from pipeline.merge_timeline import merge_timeline; ev = merge_timeline([Event.from_dict(e) for e in json.load(open('tests/fixtures/sample_timeline.json'))]); a = assess(ev, yaml.safe_load(open('configs/rules.yaml'))); print([(o.rule_id, o.kind) for o in a.outcomes][:4])"
```

### Documents updated
- **Code and tests:** `rules/engine.py`, `rules/registry.py` (new), `rules/outcome.py`,
  `rules/base.py`, `tests/test_rule_engine_engine.py` (new),
  `tests/fixtures/rule_engine/pipeline_all_pending.json` (new).
- **`decision_flow.yaml`:** P-026 is new and built; P-017 now includes engine errors.
- **`pathways.md`:** a P-026 table, the P-017 rows, and W-28.
- **`diagrams.md`:** (b), (c) (P-026, with an engine-error branch), (g).
- **Other docs:** `decisions.md` (D-063, D-064), `anomalies.md`, `methods.md`,
  `rules_status.md`, `progress.md`, `ai_usage_log.md`.

### Open questions
- **New:** none.
- **Answered:** none.

### Next increment
**Increment 8: overall result policy** (`rules/policy.py`, P-017):
- Fail if any evaluated rule failed.
- Otherwise incomplete if anything is pending, assumed, errored or timing-unchecked
  (D-055, D-060, D-062, D-063).
- Otherwise the undecided Unable-to-Verify setting if anything is unverified or not evaluable
  (D-042, D-056).
- Otherwise Pass.

### Increment 7 review: registry checks at load (2026-10-14)

Arnikan agreed with the D-063 exception for the shared-contract path, and asked for three
load-time checks before committing. All are recorded under D-064.

- **New `RegistryError(ConfigError)`** in `rules/errors.py`, with a stable `.code`. When the
  engine loads, before any timeline is read, `rules/engine.py` `_check_registry` raises:
  - **`approved_rule_not_registered`:** a rule approved (and enabled, without `same_as`) in
    `rules.yaml` with no `@rule` function and no `implementation` path. This is now an error,
    not a pending result; the `NOT_REGISTERED_REASON` path is removed.
  - **`registered_rule_not_in_config`:** a `@rule` registered under an ID that is not in
    `rules.yaml` (probably a typo). The message names the function's module, name, file and
    line.
  - **`unknown_required_event`:** the existing `requires=` check, now with a code.
- **In `rules/registry.py`:** `duplicate_rule_registration` is raised when two different
  functions are registered under one ID. The message names **both** locations (module.function,
  file:line). The same function imported twice is not a duplicate.
- **Docs:**
  - `anomalies.md`: a new section for the four codes.
  - `decision_flow.yaml`: P-026 gains four load-time branches; the old "pending if not
    registered" branch is removed.
  - `pathways.md`: the P-026 table.
  - `decisions.md`: D-064 extended.
  - `tests/test_rule_engine_docs.py`: now also reads `RegistryError` codes. It failed until the
    four were documented.
- **New question, OQ-043 (for Arnikan):** once the real rules are registered (Increment 11), the
  "not in config" check would fail every test that assesses with a small custom config,
  including the shared contract tests. The proposal is to apply that one check only when the
  config **is** `configs/rules.yaml`. Nothing fails today, because no real rule is registered.
- **Tests:** `tests/test_rule_engine_engine.py` 25 → 30.
  - **New:** approved but unregistered → error, not pending; registered but not in
    `rules.yaml` → error naming the location; allowed without a registration (pending, disabled,
    same_as); a shared-contract path rule needs no registration; the repository's rule modules
    match `rules.yaml`; the same function registered twice is fine.
  - **Changed:** a duplicate registration names both locations (checked to the file); unknown
    required event carries its code.
  - **Removed:** "approved without registration is pending".
- **Documents updated:** `rules/errors.py`, `rules/registry.py`, `rules/engine.py`,
  `tests/test_rule_engine_engine.py`, `tests/test_rule_engine_docs.py`, `anomalies.md`,
  `decision_flow.yaml`, `pathways.md`, `decisions.md`, `open_questions.md`, `progress.md`,
  `ai_usage_log.md`.
- **Result:** full suite **322 tests run, all pass, 1 skipped**. The pipeline command exits
  with 0, and its output still matches the pre-Increment 7 reference.

- **OQ-043 answered (2026-10-14) → D-064:**
  - **The answer:** registered rule IDs are always checked against the full catalogue in
    `configs/rules.yaml`, whatever config is being assessed. A smaller config only decides which
    rules are evaluated; registered rules outside it are simply not run.
  - **Code:** `_check_registry` loads the catalogue itself.
  - **Tests (30 → 32):**
    - A one-rule config works with other rules registered (only that rule runs).
    - A copied config at a different path, even one listing the unknown ID, still fails with
      `registered_rule_not_in_config`.
  - **Docs:** D-064, OQ-043, `anomalies.md`, P-026, `pathways.md`.
  - **Result:** full suite **324 tests, all pass, 1 skipped**.

---

## Increment 8: Overall result policy (2026-10-14)

### What was done
`rules/policy.py` `decide(outcomes, config, anomalies)` gives one overall result per assessment
(P-017, now built). `assess()` attaches it as `Assessment.overall`. The rules are applied in
this order:
1. **Fail**, if any evaluated rule fails (D-001). On a timeline with a review anomaly, the Fail
   stays Fail but is flagged `timeline_needs_review`, with the anomalies listed.
2. Otherwise **Incomplete**, if:
   - no rule was evaluated (D-068);
   - a rule is pending (D-055), assumed (D-060), has timing not checked or limit not approved
     (D-062), or hit an engine error (D-063);
   - or the timeline has a review anomaly (D-065, proposed list OQ-044).
3. Otherwise, if any rule is Unable to Verify or Not evaluable (D-056), the
   **`unable_to_verify_outcome` setting**: Fail or faculty review. While it is undecided, the
   result is **`unable_to_verify`**, flagged `overall_policy_undecided` (OQ-002).
4. Otherwise **Pass**.

On top of the steps:
- **Development data:** any result carrying `annotation_coverage_assumed` marks the overall
  result as development data (D-066).
- **Explanation (D-067):**
  - `deciding`: the rules that decided it;
  - `mistakes`: every Fail, with its failure code and rule title;
  - `incomplete`: each rule with why;
  - `unverified`;
  - `decided_by`: the step or setting, including any undecided setting;
  - `timeline_anomalies`;
  - a one-line `summary`.
- **R7 and A6 as one entry:** a `same_as` rule is merged into the rule it reuses.

With every rule pending today, the overall result is "Incomplete: rules not yet approved for
R1, R2, R8, R3, R4, R5, R6, A1, A2, A3, A4, A5, R7/A6, A7, A8". The pipeline's output is
unchanged, because it does not show the overall result yet (OQ-017).

### How it was done
- **Grouping and classification:** `_grouped()` builds one `Contribution` per outcome, folding
  a `same_as` rule into its target. `_incomplete()` classifies each group by kind (pending,
  assumed, engine error) or by its flags (`timing_not_checked`, `limit_not_approved`).
- **The four steps** are four `if` blocks in the order above. The first match returns, so the
  order in the code is the order of the decision.
- **Review list in config:** the list of review anomalies is `engine.yaml: review_anomalies`,
  validated against the anomaly codes that exist, and marked `undecided: true`. Changing the
  list is a config change.
- **Undecided case named after the setting:** the undecided result is named
  `unable_to_verify`, after the setting, rather than chosen silently. The explanation states
  `unable_to_verify_outcome = None (undecided, OQ-002; D-042, D-056)`.

### Methods and design choices
- **Overall result separate from rule results:** `OverallResult` is its own type. The shared
  `RuleResult` and the pipeline report are unchanged.
- **Every list is computed every time:** `incomplete` and `unverified` are filled in even when
  the result is Fail, so a reviewer sees everything that was not checked, not only what
  decided the result.

### Assumptions
- **Anomaly placement:** a review anomaly with no Fail is handled in the Incomplete step, so it
  wins over the undecided Unable-to-Verify setting. This is part of OQ-044.

### How it stays adaptable
- **Policy decided (OQ-002):** set `unable_to_verify_outcome` in `engine.yaml`.
- **Review list confirmed (OQ-044):** edit `review_anomalies`.
- **Report:** the JSON report (Increment 9) renders `OverallResult` as is.

### Tests
`tests/test_rule_engine_policy.py`, 24 tests:
- **Fail row (3):**
  - Every Fail is listed with its code and title.
  - Fail beats pending, engine error, unable and assumed (those are still listed).
  - A Fail with a timeline anomaly stays Fail, flagged.
- **Incomplete row (10):**
  - Pending.
  - Assumed R8.
  - Timing not checked (R7/A6 once).
  - Limit not approved.
  - An engine error keeps its message.
  - A timeline anomaly alone.
  - Incomplete beats Unable to Verify.
  - No rules.
  - Every rule disabled, through the engine.
  - An anomaly outside a configured list is ignored.
- **Unverified row (3):** the undecided setting; each decided setting (fail, faculty_review);
  Not evaluable counts like Unable to Verify, and is not a named mistake.
- **Pass row (1).**
- **R7/A6 reported once (1).**
- **Development data (2):** on a Pass and on a Fail; model results are not marked.
- **Through the engine (2):** the real catalogue gives Incomplete with 15 entries and R7/A6
  once; timeline anomalies reach the policy.
- **Setting validation (2).**

The consistency test now also reads `policy.FLAGS`, and caught the four new flags before they
were documented.

Full suite: **348 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0, and its output still matches the reference. `rules/` imports nothing from `video/`,
`audio/`, `legacy/` or `pipeline/`.

### Try it yourself
```powershell
.venv\Scripts\python -m unittest tests.test_rule_engine_policy -v
.venv\Scripts\python -c "import json, yaml; from rules.engine import assess; from schemas.event import Event; from pipeline.merge_timeline import merge_timeline; ev = merge_timeline([Event.from_dict(e) for e in json.load(open('tests/fixtures/sample_timeline.json'))]); o = assess(ev, yaml.safe_load(open('configs/rules.yaml'))).overall; print(o.result); print(o.summary); print(o.decided_by)"
```

### Documents updated
- **Code and tests:** `rules/policy.py` (new), `rules/engine.py`, `rules/config.py`,
  `rules/prepare.py` (`ANOMALY_CODES`), `configs/rule_engine/engine.yaml` (`review_anomalies`),
  `tests/test_rule_engine_policy.py` (new), `tests/test_rule_engine_config.py`,
  `tests/test_rule_engine_docs.py`.
- **`decision_flow.yaml`:** P-017 is now built.
- **`pathways.md`:** the P-017 table, and W-29 to W-33.
- **`diagrams.md`:** (g).
- **Registers:** `decisions.md` (D-065 to D-068); `open_questions.md` (OQ-044 new, and OQ-002's
  interim behaviour updated).
- **Other docs:** `anomalies.md`, `methods.md`, `rules_status.md`, `progress.md`,
  `ai_usage_log.md`.

### Open questions
- **New:** **OQ-044**. Which timeline anomalies block an overall Pass? The proposal is all
  three: `unknown_labels_present`, `multiple_shocks`, `mixed_evidence_sources`. And is placing
  the anomaly in the Incomplete step right?
- **Answered:** none.

### Next increment
**Increment 9: JSON report renderer and `python -m rules.run`.** The report will contain:
- the timeline, with excluded events and anomalies;
- the context (shock time and key times);
- every rule outcome, with its flags;
- the overall result and its explanation.

---

## OQ-044 answered → D-069 (2026-10-14)

- **(a)** `review_anomalies` contains all three timeline anomalies. **(b)** The anomaly step stays
  before the Unable-to-Verify setting. The reason, recorded in D-069: otherwise, if that setting
  is later decided as Fail, a data problem such as two shocks could fail a learner.
- **Config:** `engine.yaml: review_anomalies` is no longer marked undecided.
- **Tests (348 → 349):**
  - New: with `unable_to_verify_outcome: fail` and `multiple_shocks`, the overall result is
    Incomplete, not Fail.
  - Updated: the config and policy tests that checked "undecided".
- **Docs:** D-065, D-069, OQ-044, P-017, `anomalies.md`, `pathways.md`.

---

## Increment 9: JSON report, command line and output contract (2026-10-14)

### What was done
- **JSON report (P-027):** `rules/render.py` `report(assessment)` turns a whole `Assessment` into
  plain JSON:
  - `report_version` (1), `kind`, `development_data`;
  - `overall`: the result, summary, `decided_by`, flags, timeline anomalies, and the deciding,
    mistake, incomplete and unverified lists (R7/A6 once);
  - `rules`: every enabled rule in display order, with title, kind, shared status, reason,
    failure code, evidence, timestamps, flags, `blocked_by` and `timing_checked`;
  - `timeline`: events used, excluded low-confidence events, anomalies, and unknown, unused and
    unresolved labels;
  - `context`: header, key times (anchors with candidates and flags), command resolutions, zone
    visibility;
  - `configuration`: placeholder and undecided settings, time limits with their approval, rule
    statuses.
- **Command line:** `python -m rules.run --events <file> [--header file] [--config path]
  [--output path]`:
  - Writes the report (default `data/outputs/rule_engine_report.json`) and prints the overall
    result and one line per rule.
  - The file can be a list of events or `{"header": ..., "events": [...]}`. Events without an
    ID get `event_000001`, … in file order.
  - A rejected configuration or timeline, or an unreadable file: the error is printed, no report
    is written, and the exit code is 2.
- **Output contract for Sanjeevan:** [output_contract.md](output_contract.md), version 1. It
  covers:
  - the structure, with an example from a real engine run;
  - every overall result and rule result kind;
  - every flag, anomaly, failure code and rejection, each with its meaning and status (built,
    planned, interim, undecided);
  - a changelog.

  Changes to the output raise the version together with the document (D-070, interim until
  you review it).
- **Vocabulary fix (found while building the example):** the 10 canonical video events were not
  accepted under their own names from source `video`, so a model timeline using the agreed names
  (D-020) would have shown them as unknown labels. `vocabulary.yaml` now maps them to
  themselves, and a test checks that every canonical event is accepted from its own modality's
  source.
- **`unspecified` failure code made explicit:** a Fail from a shared-contract path rule
  (`implementation: module:function`) has no failure code. This code already existed inline in
  the engine. It is now a named constant (`engine.FAILURE_CODES`), listed in P-026 and
  `anomalies.md`, and checked like the other codes.

### How it was done
- **Rendering:** the renderer only reads the `Assessment`. It converts dataclasses with
  `asdict`, and tuples to lists, so the report equals its own JSON round trip. Nothing is
  recomputed, so the report cannot disagree with the engine.
- **The command line** reuses `assess()` and `report()`. It applies no source offsets
  (`pipeline.run` does that); timelines are expected to be already aligned.

### Methods and design choices
- **One report, the whole assessment:** the report includes context and configuration, not only
  results. A reviewer or Sanjeevan can then see why, for example, a time was flagged, and which
  settings were still undecided when the report was produced.
- **Version number plus a contract checked by tests:** the alternative, a JSON Schema file, was
  rejected because it adds a dependency or a hand-maintained schema. It would also not explain
  what each code means. The test keeps the document honest instead.

### Assumptions
- No new register entries. Two behaviours belong to the command line only: IDs are assigned in
  file order, and no offsets are applied.

### How it stays adaptable
- **New code (flag, failure code):** add it to `decision_flow.yaml`, `anomalies.md` and
  `output_contract.md`. The tests fail until all three agree with the code.
- **New field or changed meaning:** raise `REPORT_VERSION` and add a changelog line. The test
  fails if the version and the document disagree.
- **Checklist and feedback handover (P-018, Increment 25):** they will be built from the same
  `Assessment`.

### Tests
- **`tests/test_rule_engine_render.py`, 19 tests:**
  - **Report (8):** keys and version; JSON round trip; every enabled rule in display order with
    its title; pending → shared status `unable_to_assess`; mistake listed with its title, and A6
    reusing R7; context and configuration; development data at the top; header.
  - **Command line (11):** the sample timeline writes the same report as `assess()` +
    `report()`; ID assignment, including no clash with given IDs; header inside the file;
    `--header` overriding it; and no report with exit code 2 for each of: a duplicate ID, not a
    list, not an event, a header contradicting the events, a bad config, and invalid or missing
    JSON.
- **`tests/test_rule_engine_docs.py`, +11 tests (output contract):**
  - The version equals `REPORT_VERSION` and the changelog.
  - The structure table and the example match a real report's keys.
  - The overall results equal `policy.RESULTS`.
  - The rule kinds equal `outcome.KINDS`, with their shared status computed by the code.
  - Every code has a status.
  - Every code in `decision_flow.yaml` and every code raised in code is in the contract.
  - Every failure code in `anomalies.md` is in the contract.
  - Every contract code is in `anomalies.md`.
  - "built" matches what the code raises.
  - A guard that the tables are found.

  The existing flow test now also compares built failure codes with the code.
- **`tests/test_rule_engine_vocabulary.py`, +1 test:** canonical names are accepted from their
  own source.

Full suite: **380 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0, and its output still matches the reference. `python -m rules.run` on the sample
timeline exits with 0: Incomplete, every rule pending.

### Try it yourself
```powershell
.venv\Scripts\python -m rules.run --events tests/fixtures/sample_timeline.json
.venv\Scripts\python -m unittest tests.test_rule_engine_render tests.test_rule_engine_docs -v
```

### Documents updated
- **Code and tests:** `rules/render.py` and `rules/run.py` (new); `rules/engine.py`
  (`FAILURE_CODES`); `configs/rule_engine/vocabulary.yaml`; `tests/test_rule_engine_render.py`
  (new); `tests/test_rule_engine_docs.py`; `tests/test_rule_engine_vocabulary.py`.
- **`output_contract.md`** (new).
- **`decision_flow.yaml`:** P-027 new (built); P-018 renamed to checklist and feedback handover
  (still planned); P-026 gained the `unspecified` branch.
- **`pathways.md`:** P-027, and W-34.
- **`diagrams.md`:** (a) and (b). P-017 and P-027 are shown as built; (b) also marked P-017 as
  planned before this fix.
- **Registers:** `decisions.md` (D-070); `open_questions.md` (OQ-045 new; OQ-017 update: the
  function the pipeline should call now exists).
- **Other docs:** `anomalies.md`, `methods.md`, `rules_status.md`, `implementation_plan.md`
  (row 9), `progress.md`, `ai_usage_log.md`.

### Open questions
- **New:** **OQ-045** (owner Sanjeevan). Confirm the versioning rule, since the contract is for
  his module.
- **Still open:** OQ-017 (the pipeline calling `assess()`) is still Ananth's. Until then,
  `rules.run` produces the report.

### Review (Arnikan, 2026-10-14)
- **Approved,** with the commit prefix `feat(rules):`.
- **D-070 now states the version triggers:** the version goes up whenever a report field or
  code is added, removed or renamed, or its meaning changes. A planned code becoming built
  does not change it. Updated in D-070, `output_contract.md`, P-027 and `pathways.md`.
- **D-070 stays interim** until Sanjeevan confirms it (OQ-045, new).

### Next increment
**Increment 10: annotation input adapter.** It turns a CVAT record into mapped events and a
header, with `analyses_run: {video: true, audio: false}`, and marks every result
`annotation_coverage_assumed`, so the report shows `development_data: true`.

### Status of the separate annotation task (2026-10-14)
Not done. None of the three `annotation/` tag lists contains `first_paddle_firmly_on_the_chest`,
and nothing writes zone-visibility events. A plan was shown to Arnikan. It is now **Step 9b** in
the plan, together with the audit extensions from Increment 9a. `annotation/` is unchanged until
Arnikan approves and Ananth has been told.

---

## Increment 9a: Event count and consistency checks (2026-10-14)

Inserted before Increment 10 at Arnikan's request. It is numbered 9a, and the annotation task is
9b, so Increments 10 to 26 keep their numbers and every existing reference stays valid.

### What was done
- **Expected counts (P-005, D-071):** `engine.yaml` `expected_counts` gives every canonical
  event an expected number of **confident** events:
  - Exactly 1: `first_paddle_taken`, `second_paddle_taken`, `first_paddle_placed`,
    `apical_paddle_placed`, `sternal_paddle_placed`, `paddles_removed_after_shock`,
    `shock_delivered_on_screen`.
  - Unlimited: the six commands.
  - Undecided, so not checked: `gel_applied`, `both_paddle_buttons_pressed`,
    `paddles_firmly_on_chest`. These are linked to the repeated-actions questions OQ-021,
    OQ-022 and OQ-023.
  - Every value is marked `placeholder: true`.
- **`count_violation`:** one anomaly per event whose count is outside its range. It names the
  event, the expected and found counts (`details.event`, `expected`, `found`) and lists the
  event IDs.
- **Possible duplicates:** for an event limited to one (`exactly: 1` or `at_most: 1`), each pair
  within `simultaneous_window_seconds` is listed in `details.possible_duplicates`. The message
  says "possibly the same incident detected twice". Nothing is merged.
- **`paddle_identity_conflict`:** two or more apical placements and no sternal placement, or the
  reverse. The details give both counts.
- **Effect:** never a Fail by itself; no event is removed or changed. Both codes are added to
  `review_anomalies` as a proposal (the setting is marked undecided, OQ-046). With them, a
  timeline with a count problem is **Incomplete**, never Pass, and a Fail stays Fail, flagged
  `timeline_needs_review`. A rule may fail on a repeated action only once the supervisor decides
  that the repetition is a mistake.
- **Upstream:** `upstream_requirements.md` lists the sanity checks needed from video
  postprocessing:
  - placement zones never move while the paddles do;
  - at most one apical and one sternal paddle per frame;
  - paddle identity kept over time.
- **Annotation audit (plan only, Step 9b):** extend `audit_cvat_backups.py` to report:
  - frames with two boxes of the same paddle label;
  - zone tracks that move like a paddle;
  - incidents tagged more than once (the existing repeated-tag checks, plus marking near
    duplicates).
- **Output contract version 2:** two codes were added, a version trigger under D-070. The
  changelog says what changed; no field was added, removed or renamed.

### How it was done
- **Config:**
  - `rules/config.py` validates every count (`unlimited`, or one of `exactly` / `at_least` /
    `at_most` with a positive whole number). Null is allowed only while undecided.
  - The list must name every canonical event in the vocabulary and nothing else, so adding an
    event forces a decision on its count.
  - `count_allows()` is the single place where a count is compared with its range.
- **Preparation:** `_count_anomalies()` in `rules/prepare.py` runs after the existing anomaly
  checks, on confident events only. Excluded low-confidence events are never counted.

### Methods and design choices
- **Counts are an engineering check, not a clinical rule.** They live in `engine.yaml`, as
  placeholders, and raise anomalies, not rule results. Whether a repeated action is a learner's
  mistake is the supervisor's decision; once it is made, the rule concerned will apply it.
- **Two shocks raise both `multiple_shocks` and `count_violation`.** `multiple_shocks` is the
  shock-specific anomaly that the procedure context uses to refuse a shock time. The count check
  is general, so it is raised as well. The overall result lists each code once.

### Assumptions
- **New: A-018.** No confident event at all is a **missing event**, decided by the coverage step
  and the rules, not a count violation. Otherwise every skipped step would be marked "timeline
  needs review", and every Unable to Verify would become Incomplete. This is open as OQ-046 (b).

### How it stays adaptable
- **Supervisor answers on repetition:** set the value in `expected_counts` (for example
  `gel_applied: {value: {at_least: 2}}`).
- **OQ-046:** keep or remove the two codes in `review_anomalies`.
- **A new canonical event:** loading fails until it has an expected count.

### Tests (380 → 406)
- **`tests/test_rule_engine_prepare.py`, +21:**
  - **Expected counts (11):**
    - exactly 1 met;
    - exactly 1 found twice: event, counts and IDs, and the events kept;
    - zero found is not a violation;
    - only confident events counted;
    - unlimited;
    - undecided not checked;
    - `at_least` met and violated;
    - `at_most` met and violated;
    - `exactly: 2` with one and with three found;
    - several violations reported separately in name order;
    - two shocks give both codes.
  - **Possible duplicates (4):**
    - a close pair is marked;
    - only the close pair of three events;
    - exactly at the window counts as close;
    - `at_most: 1` is also limited to one.
  - **Paddle identity (6):**
    - two apical and no sternal;
    - three sternal and no apical;
    - one of each, one alone and none are not conflicts;
    - two apical and one sternal is a count problem only;
    - low-confidence placements are not counted;
    - nothing is removed or judged.
- **`tests/test_rule_engine_config.py`, +4:**
  - invalid counts rejected (7 forms);
  - null only while undecided;
  - every count form accepted;
  - the list must match the vocabulary exactly (missing and unknown event).
- **`tests/test_rule_engine_policy.py`, +1 and 2 updated:**
  - New: a count violation alone makes the result Incomplete, flagged.
  - Updated: two shocks now list both codes; the review list contains the proposed codes and is
    marked undecided.
- **Updated:** the config test's list of undecided settings.

Full suite: **406 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0, and its output still matches the reference. `python -m rules.run` on the sample timeline
still gives Incomplete with no anomalies.

### Try it yourself
```powershell
.venv\Scripts\python -m unittest tests.test_rule_engine_prepare -v
```

### Documents updated
- **Code and config:** `rules/prepare.py`, `rules/config.py`, `rules/render.py`
  (`REPORT_VERSION` 2), `configs/rule_engine/engine.yaml`.
- **Tests:** `tests/test_rule_engine_prepare.py`, `tests/test_rule_engine_config.py`,
  `tests/test_rule_engine_policy.py`.
- **`decision_flow.yaml`:** P-005 branches.
- **`pathways.md`:** P-005 table, W-35 to W-38.
- **`diagrams.md`:** (b).
- **`anomalies.md`:** the two codes.
- **`output_contract.md`:** version 2.
- **`upstream_requirements.md`:** the video sanity checks.
- **`implementation_plan.md`:** rows 9a and 9b, section D.
- **Registers:** `decisions.md` (D-071); `assumptions.md` (A-018); `open_questions.md` (OQ-046
  new; interim notes on OQ-021, OQ-022, OQ-023).
- **Other docs:** `methods.md`, `rules_status.md`, `progress.md`, `ai_usage_log.md`.

### Open questions
- **New: OQ-046** (Arnikan):
  - (a) Should `count_violation` and `paddle_identity_conflict` block an overall Pass (the
    proposal)?
  - (b) Is A-018 right that zero found is a missing event, not a count violation?
- **Linked, for the supervisor:** OQ-021 (gel), OQ-022 (re-placed paddles), OQ-023 (buttons)
  decide the undecided counts, and whether a repeat can ever be a Fail.

### Next
**Step 9b** (annotation task, awaiting approval), then **Increment 10** (annotation input
adapter).

---

## OQ-046 answered → D-072 (2026-10-14)

- **(a)** `count_violation` and `paddle_identity_conflict` block an overall Pass. **(b)** A-018 is
  right: no confident event at all is a missing event, not a count violation.
- **Config:** `engine.yaml: review_anomalies` is no longer marked undecided.
- **Tests (406, unchanged count):** the policy test now checks that the review list is decided;
  the config test's list of undecided settings no longer contains `review_anomalies`.
- **Docs:**
  - registers: D-072, A-018 (confirmed), OQ-046 (answered);
  - P-005, P-017, `anomalies.md`, `pathways.md` (P-005 note, W-35, W-36);
  - `output_contract.md`: wording only, the version stays 2;
  - `implementation_plan.md` section D.

---

## CVAT frozen, separate exporter, commit rule; Steps 9b and 9c revised (2026-10-14, plan only)

### Decisions recorded (Arnikan)
- **D-073:** CVAT is frozen. Tags and component names never change; names are mapped in
  `vocabulary.yaml` only.
- **D-074:** Ananth's dataset files are not modified. A **separate exporter** reads the CVAT
  backups and writes rule-engine records to a separate output. A **separate audit script** holds
  the new checks. Also decided:
  - a missing zone track means unknown;
  - off-pattern videos are listed for annotation review;
  - learner order is information only;
  - the thresholds are 5% of the frame diagonal and 15 frames.

  Closes OQ-007 and OQ-008.
- **D-075:** commit only on an explicit instruction, and push only on an explicit instruction,
  including documentation-only commits. It replaces every earlier rule. Recorded in the brief, the
  plan and the agent's memory.

### Findings used by the plan
- **The new tag isn't in the backups:** the current CVAT backups (phase 1 inventory, 144 videos,
  14 declared labels each) don't contain `first_paddle_firmly_on_the_chest`. It appears once the
  final backups are exported.
- **The tag lists matter for training:** `build_yolo_video_dataset.py` uses its tag list to
  choose training frames, and Ananth's training view reads `sample_manifest.csv`. That is why the
  dataset files stay untouched.
- **fps must be read per video:** it varies (25, 29.71, 29.98, 30, 30.01, 24.91), and every video
  starts at frame 0.
- **Zone tracks by camera view (current backups):**

  | View | Usual pattern | Off-pattern videos |
  |---|---|---|
  | LL | apical only (44 of 48) | 1 sternal only, 3 none |
  | LS | both (44 of 48) | 2 apical only, 2 sternal only |
  | T | both (38 of 48) | 7 sternal only, 3 none |

  That is 18 off-pattern videos, 6 of them with no zone track.

### Plan
Rows 9b, 9c and 10 of `implementation_plan.md` are revised. The full plan, with its open points,
was shown to Arnikan; no code was changed.

---

## Step 9b: rule-engine annotation exporter and audit (2026-10-16)

Arnikan told Ananth before the work started. No file of the training pipeline was changed (see
"Verification").

### Decisions recorded (Arnikan's answers to the 9b/9c questions)
- **D-076:** fps, width and height come from `video_conversion.csv` only. A missing video is an
  export issue.
- **D-077:** the usual zone pattern per view is fixed in config, with the actual distribution
  printed beside it.
- **D-078:** the output folders.
- **D-079:** the training code is reused by import, pinned by tests.
- **D-080:** a zone track that is never visible means not covered (information in the audit).
- **D-081:** Step 9c's settings, evidence type, no event on disagreement, and the validation
  gate (final backups; R8 waits for Arnikan's review).
- **D-082:** the zone pattern is used for the review list only; reviewed exceptions remove a
  video from it and make the zone not covered.
- **Registers:** OQ-047 to OQ-052 are recorded as answered by these decisions. **OQ-053 (new,
  Ananth):** are the converted videos constant frame rate?

### What was done
- **`annotation/export_rule_engine_records.py` (P-028):** reads the CVAT backup ZIPs directly and
  writes `data/rule_engine/annotation_export/<run>/`:
  - `records.jsonl`: one record per task, with:
    - every tag under its CVAT name, with frame and seconds;
    - `fps`, `width`, `height`;
    - `start_frame`, `stop_frame`, `duration_seconds`;
    - `zone_tracks`, `zone_visibility` intervals;
    - an empty `derived_events` (9c).
  - `export_issues.csv`;
  - `export_manifest.json`: a SHA-256 per backup ZIP, counts, the config and report checksums.

  It refuses `data/video/` and non-empty folders.
- **`annotation/audit_rule_engine_checks.py` (P-029):** writes the review list (`issues.csv`),
  information (`info.csv`), `zone_patterns.csv`, `audit_manifest.json`, and a README. The README
  shows the usual pattern beside the actual distribution per view and the off-pattern videos.
- **`configs/rule_engine/annotation_export.yaml`:** zone and paddle labels (CVAT names), the
  usual pattern, `reviewed_zone_exceptions` (empty), and the two accepted thresholds.

### How it was done
- **Reuse by import:** task discovery comes from `audit_cvat_backups.py` (`canonicalize_task_id`,
  `normalize_jobs`, `read_json_entry`, `Issue`). Geometry comes from
  `build_yolo_video_dataset.py` (`collect_annotations`, `track_box_at`, `clip_box`,
  `shape_box`).
- **Zone visibility:** a zone is visible on a frame when any of its tracks gives a box there that
  survives `clip_box`. This is exactly how `frame_boxes` builds the training labels, and a test
  compares the two frame by frame. Visible frames become runs, merged across tracks and jobs.
- **Times:** `frame / fps`, the training data's convention. Every current video starts at frame
  0.

### Methods and design choices
- **The exporter writes facts only.** Coverage policy stays in the rule engine (P-030,
  Increment 10): exception → not covered; visible → covered; never visible → not covered;
  no track → unknown.
- **Exporter and audit tests share one file** with a synthetic CVAT backup builder (`tests/` is
  not a package).

### Smoke run on real backups (read-only)
Both scripts ran on one annotator's corrected backups, 39 ZIPs in
`D:\FYP\Annotation - correction\Kartheepan\Complete sets (…)`. Output went to the gitignored
`data/rule_engine/`.
- **Export:** 38 records, 270 tags, 65 zone intervals. P01_LL agrees with the conversion report:
  fps 24.91, frames 0 to 472, duration 18.988 s.
- **These corrected backups already contain `first_paddle_firmly_on_the_chest`** (P01_LL, frame
  323). Only the older backups behind the phase 1 reports lack it.
- **Findings:**
  - `P14_LL.zip` contains task P14_LS (`duplicate_task`);
  - 8 zone tracks moved 5.7% to 13.2% of the diagonal;
  - 2 near-duplicate gel tags (1 and 15 frames apart);
  - no off-pattern videos in this set.
- **Not run on the full set:** the phase 1 backup layout (`defibliration2.zip`,
  `kartheepan/P01_LL.zip`, …) is not on this machine, so the "current" folder needs Arnikan's
  confirmation.

### Tests (406 → 437)
`tests/test_rule_engine_annotation_export.py`, 31 tests:
- **Visibility matches training (3):**
  - the `track_box_at` behaviour pinned;
  - visible frames equal the frames with a training box;
  - a box outside the image is not visible.
- **Records (10):**
  - every tag kept and timed;
  - outside keyframes and merging across tracks and jobs;
  - missing and never-visible tracks (facts only);
  - a single-frame shape reported, not converted;
  - `fps_missing`;
  - frame-count mismatch;
  - a tag outside the frames;
  - a project backup with duplicates;
  - an unrecognised name;
  - deterministic output.
- **Separation from training (3):** writing inside `data/video` refused; a non-empty folder
  refused; the command line writes three files.
- **Configuration (5):**
  - the repository config;
  - an exception loaded;
  - invalid exceptions;
  - invalid patterns and settings;
  - the real conversion report (144 videos; P01_LL is 24.91 fps).
- **Audit checks (9):**
  - duplicate paddle boxes;
  - one box per paddle, and a standalone shape counted;
  - a moving zone, and one overlapping a paddle;
  - the 15-frame window;
  - learner order is information only;
  - zone patterns for 5 view cases;
  - a never-visible track;
  - an exception removes a video from the list;
  - a contradicted exception.
- **Audit output (1):** five files, the README table and the review-only `issues.csv`.

Full suite: **437 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0, and its output matches the reference.

### Verification: Ananth's files unchanged
`git diff --stat` lists only `docs/rule_engine/` files. `git status` shows no change to
`annotation/build_yolo_video_dataset.py`, `create_grouped_video_split.py`,
`validate_yolo_dataset.py`, `audit_cvat_backups.py`, `to_timeline.py`, `annotation/reports/`,
`annotation/splits/`, `annotation/docs/`, `video/`, `configs/video/` or `configs/pipeline.yaml`.
New files: the two scripts, the config and the test file.

### Try it yourself
```powershell
.venv\Scripts\python -m annotation.export_rule_engine_records --backup-root "<CVAT backup folder>" --output data/rule_engine/annotation_export/2026-10-16
.venv\Scripts\python -m annotation.audit_rule_engine_checks --backup-root "<CVAT backup folder>" --output annotation/reports/rule_engine_audit/2026-10-16
```

### Documents updated
- **`decision_flow.yaml`:** new stage `annotation_export`, P-028 to P-031, and P-001 revised.
- **`pathways.md`:** P-028 to P-031 and P-001, and W-39 to W-44.
- **`diagrams.md`:** (h) and (i), with (a) and (b) linked.
- **Registers:** `decisions.md` (D-076 to D-082); `open_questions.md` (OQ-047 to OQ-052
  answered, OQ-053 new).
- **Other docs:** `anomalies.md` (export and audit codes), `implementation_plan.md` (rows 9b,
  9c, 10), `methods.md`, `rules_status.md`, `progress.md`, `ai_usage_log.md`.

### Open questions
- **New:** OQ-053 (Ananth), constant frame rate.
- **Needed for the real run:** which backup folder is the current set.

### Next
Increment 10 (annotation adapter, P-001 and P-030). Step 9c is planned and not built. Nothing is
committed; commit only when Arnikan says so (D-075).

---

## Step 9b handover: Ananth runs the exporter; privacy rule (2026-10-16)

### Decisions recorded (Arnikan)
- **D-083:** the corrected backups go to Ananth, and Arnikan no longer works with them. **Ananth
  runs the exporter and the audit on the final backups.** He sends only `records.jsonl`,
  `export_manifest.json` and the audit outputs, never media. How-to:
  [docs/annotation/rule_engine_export_howto.md](../annotation/rule_engine_export_howto.md).
- **D-084:** until then, the smoke-run export of the 39 corrected backups is the development
  data for Increment 10:
  - records: `data/rule_engine/annotation_export/smoke-kartheepan/`;
  - audit: `data/rule_engine/audit_smoke/kartheepan/`.

  Both are gitignored. Exported records are never committed. P14_LS in that set is unreliable.
- **D-085, privacy:** media in the backups is never opened, listed in detail or printed. Only
  `task.json` and `annotations.json` are read. Recorded in the brief (section 6, rule 8) and the
  agent's memory.

### Code change for D-085
- **The manifest no longer hashes the whole ZIP:** reading the whole file would read the video
  bytes. It now records each ZIP's size and a SHA-256 over its `task.json` and
  `annotations.json` entries only (`annotation_sha256`).
- **New tests (2):**
  - a spy on `ZipFile.open` shows that the export and the audit open only those two entries;
  - the digest stays the same when only the media changes, and changes when an annotation
    changes.
- **Disclosure:** the earlier smoke run hashed the whole ZIPs for its manifest. No media was
  opened, listed in detail or printed.

### Annotation findings for Ananth to fix in the backups (smoke run, 39 corrected backups)
1. **`P14_LL.zip` contains a task named `P14_LS`.** It clashes with `P14_LS.zip`
   (`duplicate_task`), so the P14_LL video seems to be missing from that set.
2. **8 moving zone tracks** (centre moving > 5% of the frame diagonal; none overlapped a paddle at
   its end frame):

   | Video | Zone | Moved |
   |---|---|---|
   | P06_T | sternal | 5.8% |
   | P07_T | sternal | 6.8% |
   | P07_T | apical | 8.1% |
   | P14_LS (in `P14_LL.zip`) | apical | 7.6% |
   | P14_LS (in `P14_LL.zip`) | sternal | 6.8% |
   | P31_LL | apical | 5.7% |
   | P31_T | sternal | 13.2% |
   | P31_T | apical | 11.2% |

3. **2 near-duplicate gel tags:**
   - P06_LS, frames 259 and 260;
   - P12_LS, frames 164 and 179.

The same list, with frames, is in the how-to.

### Registers
- **New open questions, both Ananth's:**
  - **OQ-054:** when the final export will be available;
  - **OQ-055:** does anything in his pipeline take the camera view from the backup file name?
- **Plan:** rows 9b, 9c and 10 updated.
- **`diagrams.md` (h):** shows Ananth running the exporter and sending records back, and the
  interim smoke data.
- **Also updated:** `decision_flow.yaml` (P-028, P-029), `methods.md`,
  `upstream_requirements.md`.

### Tests
437 → 439, all pass, 1 skipped (charging sound). The pipeline output is unchanged. None of
Ananth's files changed.

---

## Step 9c: derived per-paddle placements (2026-10-16)

### Decisions and assumptions recorded (Arnikan's answers)
- **A-019, the annotators' convention:** a correct, fully visible procedure is tagged first
  paddle taken → first paddle firmly on the chest (T1) → second paddle taken → paddles firmly on
  chest (T2). T1 is not tagged when both paddles go on together, and T2 is not tagged when only
  one paddle is visible as both are placed.
- **D-086, the tag rules:**
  - two-zone disagreement with T1 → no event for either paddle;
  - one-zone videos → not earlier than T1 − 15;
  - T1 missing and both placements within `simultaneous_window_seconds` → both kept, flagged
    `possible_parallel_placement`; T1 missing otherwise → no events;
  - T2 only when present;
  - re-placement after `exit_frames`, a separate setting.
- **D-087:** placements are derived per paddle label across all its tracks. A split track is not a
  re-placement. Overlapping tracks of one paddle give no event, and Ananth fixes them.
- **D-088, the gate:** a review record with `export_id` and `placement_settings_sha256`, enforced
  by the Increment 10 adapter. An approval doesn't carry over to another export or other
  settings. The engine flag `derived_placement` enters the contract with R8 (Increment 12).
- **D-089, the validation report for tuning:**
  - highest overlap, steady frames achieved and centre motion for each video and paddle;
  - their distributions;
  - the parallel-placement count.
- **A-020 (mine, for your review):** a frame whose zone isn't visible counts as out of the zone.
  The report gives `frames_zone_not_visible` to check this.
- **OQ-056 (new, Arnikan):** is `possible_parallel_placement` alone enough for a Fail, or does it
  need review?

### What was done
- **`annotation/derive_paddle_placements.py`** (new, called by the exporter):
  - frame states per paddle label (in, out, blocked);
  - placement episodes (steady start, exit after `exit_frames`);
  - the tag rules;
  - the events;
  - the validation rows, summary and Markdown;
  - the settings loader;
  - the gate check `derived_placements_approved()`.
- **Exporter:**
  - fills `derived_events`;
  - writes `placement_validation.csv` and `placement_validation.md`;
  - adds `export_id`, `placement_settings_sha256` and the validation summary to the manifest;
  - reads `simultaneous_window_seconds` from `engine.yaml` (`--engine-config`).
- **Config:** `annotation_export.yaml` `derived_placements` holds the paddle → zone → event
  mapping, the five placeholder settings, T1 and T2, and the empty `reviewed_for_r8` record.
- **Vocabulary:** the annotation entries `apical_paddle_placed` / `sternal_paddle_placed` are no
  longer placeholders. They are now the exporter's derived names (D-073).
- **Bug found by a test and fixed:** on Windows, `records.jsonl` was written with CRLF line
  endings while the export ID hashed the LF text, so the ID wouldn't match the file sent. The
  file is now written as bytes (LF on every OS), and `export_id` is the SHA-256 of the file
  exactly as sent.

### Limits of this step
- **No geometry in the interim data:** the smoke-run records (D-084) were exported before 9c and
  hold no box geometry. Real derived placements, and the validation report, therefore first
  appear when Ananth runs the final export.
- **Placeholders not tuned yet:** they couldn't be tuned on real data before then. The report's
  distributions are there for that.

### Tests (439 → 465)
- **`tests/test_rule_engine_derived_placements.py`, 24 tests:**
  - **placement:** both paddles in order, with the event's fields; the overlap boundary (0.5 vs
    0.49); the steady-frames boundary (5 vs 4); the motion boundary (43 vs 45 px moves the start
    from frame 20 to 21); zone not visible;
  - **re-placement:** after 6 frames out; a 4-frame dip; `exit_frames` as its own setting;
  - **tracks:** a split track (one placement); overlapping tracks (no event, review issue, the
    other paddle unaffected);
  - **tag rules:** the T1 window (15 vs 16); one zone (before T1 − 15 rejected, second paddle
    accepted); parallel (0.4 s, flagged); T1 missing otherwise (0.52 s apart, or one paddle); T2
    only when present; a parallel placement failing T2 drops both;
  - **validation:** rows for tuning; summary counts and the Markdown;
  - **gate:** approved only for the reviewed export and settings; the digest ignores the review
    record; a partial review record is rejected;
  - **configuration:** the repository settings; the parallel window comes from `engine.yaml`;
    invalid settings.
- **Exporter (+1):** derived events reach the record. `export_id` equals the SHA-256 of
  `records.jsonl` as written, with no CRLF. The settings hash and validation files are present.
- **Vocabulary (+1, 1 updated):** the derived labels map to the canonical events; the
  placeholder list no longer has them.

Full suite: **465 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0, and its output matches the reference.

### Documents updated
- **`decision_flow.yaml`:** P-031 now built, with every branch.
- **`pathways.md`:** the P-031 table, and W-45 to W-49 (correct placement, parallel placement,
  T1 missing otherwise, split track, disagreement and the one-zone case).
- **`diagrams.md`:** (j).
- **Registers:** `decisions.md` (D-086 to D-089); `assumptions.md` (A-019, A-020);
  `open_questions.md` (OQ-056).
- **`anomalies.md`:** placement export issues and event flags.
- **`docs/annotation/rule_engine_export_howto.md`:** send the validation files; keep
  `records.jsonl` and the manifest from the same run; fix overlapping tracks; the new messages.
- **Other docs:** `implementation_plan.md` (rows 9c, 10, 11, 12, section D), `rules_status.md`,
  `methods.md`, `progress.md`, `ai_usage_log.md`.

### Next
Increment 10, the annotation adapter, with the gate check. Nothing is committed; commit only when
Arnikan says so.

### Review changes before the commit (Arnikan, 2026-10-16)
- **A-020 changed → D-090:** a frame where the zone isn't visible is **unknown**, neither in nor
  out of the zone.
  - It doesn't start or end a placement, and in on both sides of the gap is the same placement.
  - Only out frames count towards `exit_frames`.
  - Code: a new `unknown` frame state in `derive_paddle_placements.py`.
  - The validation report still counts the not-visible frames per paddle.
  - **Tests (+4):**
    - a 6-frame occlusion during a placement is one placement (the old rule would have invented
      a re-placement at frame 47);
    - a real 6-frame exit with the zone visible is two placements;
    - unknown frames don't start a placement;
    - out frames on both sides of an occlusion add up to an exit.
- **OQ-056 closed → D-091:** `possible_parallel_placement` is enough for R2 and R8 to Fail with
  `simultaneous`, but only once the gate is approved, as for every derived placement.
- **Docs:** P-031 (new branch), pathways (P-031 table, W-46 updated, W-50 new), diagram (j)
  (unknown state, D-091), anomalies, rules status, plan rows 9c/11/12, registers.
- **Tests:** 465 → 469.

---

## Increment 10: annotation adapter, with partial zone visibility (2026-10-17)

### Decisions recorded (Arnikan)
- **D-092 (replaces D-036 for zones with intervals):** partial zone visibility uses the exporter's
  zone intervals, through the existing `window` parameter:
  - in a time window, a zone is covered only if visible throughout it; unknown if visible for
    part of it; not covered if never visible in it;
  - without a window, partial visibility is unknown.

  OQ-027 stays answered, with an update line.
- **Already decided and now built:** header from the record; `analyses_run` video true and audio
  false, flagged `annotation_coverage_assumed`; reviewed exceptions and never-visible tracks →
  not covered; no track → unknown (D-035, D-066, D-074, D-080, D-082); the gate (D-088).

### What was done
- **`rules/adapters/annotation.py` (new; P-001, P-030):**
  - reads `records.jsonl`, never `events.jsonl`;
  - events from every tag under its CVAT name, with the vocabulary mapping them (D-073);
  - a header with `recording_id`, `camera_angle`, `duration_seconds`, `analyses_run`, the region
    coverage per P-030, the visible intervals (`visibility`) and the flag
    `annotation_coverage_assumed`;
  - derived placements pass only when `derived_placements_approved()` holds for the export's ID
    and settings hash, and every derived event carries that settings hash; otherwise they are
    withheld and counted;
  - command `python -m rules.adapters.annotation --records … --output … [--task] [--exclude]`
    writes one timeline per video and `adapter_summary.json`, and refuses `data/video/` and
    non-empty folders.
- **`rules/coverage.py`:**
  - `TimelineHeader` gains `visibility` (sorted, non-overlapping intervals per region scope) and
    `flags` (header flags, now `annotation_coverage_assumed`);
  - `status(event, window)` applies D-092;
  - visibility ending after the duration is a `header_mismatch`.
- **`rules/engine.py`:** header flags are copied onto every rule result, so
  `annotation_coverage_assumed` makes the overall result `development_data` (D-066). The constant
  moved to `coverage.py`, and `policy.py` imports it.
- **Output contract version 3:** `context.header` gains `visibility` and `flags`; the flag
  `annotation_coverage_assumed` is now built.

### Methods and design choices
- **Two header fields, one per purpose:** the header keeps the whole-recording status
  (`coverage`) and adds the intervals (`visibility`). A rule asking without a window gets the
  recording status; with a window, the window's status. No rule changes (the window parameter
  existed since Increment 4).
- **Zone → region mapping without new names:** each CVAT zone maps to the engine region of the
  placement event it governs (from the 9c settings and `engine.yaml` regions).
- **One flag mechanism:** header flags reach every result through the engine, so adapters never
  touch rule outcomes.

### Tests (469 → 486)
`tests/test_rule_engine_annotation_adapter.py`, 17 tests:
- **Events and header (3):** tags become annotation events, which the vocabulary maps; the header
  comes from the record and is flagged; a non-record is rejected.
- **P-030 (2):**
  - covered;
  - unknown (no track);
  - partial, with the intervals in the header;
  - never visible (empty intervals);
  - a reviewed exception is not covered, even if a track shows the zone.
- **Windowed coverage (6):**
  - visible throughout the window → covered, including a window exactly on the interval;
  - visible for part of it → unknown;
  - never visible in it → not covered;
  - no window → unknown;
  - a placement expected while the zone was out of view → Unable to Verify, never Fail (through
    `Coverage` and `ProcedureContext`), and Fail when the zone was visible throughout;
  - events outside regions ignore the window.
- **Gate (2):** an approved export passes derived placements on. Not approved in four cases: no
  review, another export, no manifest, an event made with other settings.
- **Through the engine (2):** every result flagged, development data, Incomplete, zone statuses,
  and the header surviving the trip to the timeline file and back; header validation (non-region
  scope, overlapping intervals, unknown flag, visibility after the duration).
- **Command line (2):** adapter then `rules.run` (excluding P14_LS); non-empty output refused.

Full suite: **486 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0, and its output matches the reference.

### Interim data: adapter and `rules.run` on 6 smoke-run records (D-084; P14_LS excluded)
Output (gitignored): `data/rule_engine/timelines/interim-2026-10-17/` and
`data/rule_engine/reports/interim-2026-10-17/`.

| Video | Events | Apical zone | Sternal zone | Shock time | Result |
|---|---|---|---|---|---|
| P01_LL | 5 | covered (0–18.95 s) | unknown (no track) | from removal, 15.94 s | Incomplete, development data |
| P01_LS | 9 | covered | covered | on screen, 16.8 s | Incomplete, development data |
| P01_T | 9 | covered | covered | on screen, 15.91 s | Incomplete, development data |
| P06_T | 6 | **unknown** (visible only from 10.1 s) | covered | from removal, 21.57 s | Incomplete, development data |
| P07_T | 9 | covered | covered | on screen, 19.6 s | Incomplete, development data |
| P12_LS | 9 | covered | covered | on screen, 13.57 s | Incomplete, development data |

**What was checked:**
- **Headers:** duration and camera from the record; `analyses_run` video true and audio false;
  flagged.
- **Labels:** every CVAT label was recognised; `first_paddle_firmly_on_the_chest` maps to
  `first_paddle_placed`, and its key time is set.
- **Results:** no timeline anomalies; every rule result carries `annotation_coverage_assumed`.
- **Per-paddle placements are absent:** this export predates 9c, so P-012's apical and sternal
  placement anchors are empty.
- **P06_T:** its first placement (14.03 s) lies inside the apical zone's visible interval, so a
  rule asking about that time gets covered. This is D-092 at work on real data.
- **Two LL/T videos have no shock-on-screen tag:** the shock time comes from paddle removal and
  is flagged. Expected for P01_LL: the screen isn't in that view.

### Documents updated
- **`decision_flow.yaml`:** P-001 and P-030 built; P-007 window branch.
- **`pathways.md`:** P-001, P-030 and P-007 tables; W-51 (zone out of view), W-52 (gate), W-53
  (interim P06_T).
- **`diagrams.md`:** (b), (h), (i).
- **Registers:** `decisions.md` (D-092); `open_questions.md` (OQ-027 update).
- **Other docs:**
  - `anomalies.md` (header flags);
  - `output_contract.md` (version 3);
  - `upstream_requirements.md` (optional header fields);
  - `implementation_plan.md` (row 10);
  - `rules_status.md`, `methods.md`, `progress.md`, `ai_usage_log.md`.

### Open questions
None new. Still open and relevant: OQ-053 (constant frame rate), OQ-054 (final export date),
OQ-055 (camera view from the file name).

### Next
Increment 11 (R2). Nothing is committed; commit only when Arnikan says so.

**Committed 2026-10-17** as `946ebf7` and pushed (on Arnikan's instruction).

---

## Increment 11 (R2), with the shock-time, screen and camera-angle changes (2026-10-17)

### Decisions recorded (Arnikan)
- **D-093, shock time only from the screen:**
  - the shock time comes only from `shock_delivered_on_screen`, and is never inferred;
  - `engine.yaml` `shock_time_fallback: none`; the removal fallback is kept behind `removal`;
  - D-023 is replaced as the default; D-024, D-053, D-054 and D-059 apply only with `removal`;
  - this supersedes the proposal's A6 clause, to be mentioned to the supervisor (**OQ-057**,
    new).
- **D-094, screen coverage for R5:** the screen's visibility is derived exactly like the zones'.
  A missing shock on screen while the screen is out of view is Unable to Verify, never Fail.
- **D-095, R2:** when the first placement is missing, R2 asks coverage of both placement zones
  over the window from first paddle taken to second paddle taken. Visible throughout →
  `first_missing`; otherwise Unable to Verify. A possible parallel placement past the gate →
  `simultaneous` (D-091).
- **OQ-058 (new, Arnikan):** in a parallel placement before the gate is approved, R2 names the
  wrong mistake (`first_missing`).

### What was done
- **Shock time** (`rules/context.py`, `rules/config.py`, `engine.yaml`): the new setting
  `shock_time_fallback` (`none` | `removal`, validated). With `none`, no shock on screen → no
  shock time (`no_shock`, "never inferred"), resume commands unresolved, and shock-dependent
  rules Not evaluable because of R5. R3/R4's removal inference is untouched.
- **Screen** (exporter, adapter, `engine.yaml`):
  - the exporter writes `screen_tracks` and `screen_visibility` (the training box rule, as for
    the zones);
  - `engine.yaml` has a region `screen` governing `shock_delivered_on_screen`;
  - the adapter applies the P-030 rules to the screen; an export without screen fields →
    unknown.
- **R2** (`rules/video_rules.py`, P-032): the first registered rule. It runs only when approved
  in `rules.yaml`, so the catalogue still reports it as pending.
- **Camera-angle evidence** (`docs/rule_engine/camera_angle_evidence.md`, interim, 37 of 38
  videos): zone and screen visibility and tag frequencies per view, and which rules each view
  can check. It is linked from OQ-038.
- **Output contract version 4:**
  - `no_shock` changed meaning;
  - the `screen` region was added;
  - R2's failure codes are now built.
- **How-to for Ananth:** records now include the screen. Item 4 is new: P05_LL has the object
  label `apical_placement_zone` as a tag at frame 287.

### Tests (486 → 511)
- **Shock time (6, context):**
  - the decided setting is `none`;
  - no shock on screen → no shock time, even with a removal;
  - the screen shock is still used;
  - resume commands unresolved and start commands ambiguous, with no removal flags;
  - a low-confidence screen shock doesn't become the removal;
  - an invalid setting is rejected.

  The existing removal-fallback tests in `test_rule_engine_context.py` and
  `test_rule_engine_checks.py` now run with `shock_time_fallback: removal`, as each module's
  docstring says.
- **Screen (6):**
  - the exporter writes screen intervals like the zones;
  - an LL video with no screen visible → unknown → Unable to Verify;
  - a never-visible screen → not covered;
  - a screen visible throughout → a missing shock is a Fail;
  - a shock expected while the screen was out of view → Unable to Verify;
  - an export without screen fields → unknown.
- **R2 (13):**
  - pass, `taken_before_first_placed`, `simultaneous`;
  - no second paddle taken;
  - pending in the catalogue;
  - first placement missing with the zones visible throughout (`first_missing`), out of view,
    partly visible, with no header, with a low-confidence placement, and with no first paddle
    taken;
  - a parallel placement with an approved gate (`simultaneous`) and without one (placements
    withheld → `first_missing`, OQ-058).
- **Updated:** five assertions now include the `screen` region; the docs test also reads the
  failure codes raised by rule modules.

Full suite: **511 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0, and its output matches the reference.

### Interim data
- **Adapter and engine on 4 records** (`data/rule_engine/reports/interim-2026-10-17b/`, not
  committed):
  - P01_LL and P06_T now have **no shock time** (`no_shock`); before D-093 it came from removal;
  - P01_LS still uses the screen shock (16.8 s);
  - the screen is unknown everywhere, because this export predates the screen fields;
  - P05_LL raises `unknown_labels_present` (the mislabelled tag);
  - all are Incomplete; R2 is pending.
- **R2 dry run** (R2 approved in a scratch config, not committed; 37 videos):

  | View | Pass | `simultaneous` | `taken_before_first_placed` | `first_missing` | Unable to Verify |
  |---|---|---|---|---|---|
  | LL (12) | 2 | 3 | 2 | 0 | 5 (no second paddle taken) |
  | LS (12) | 9 | 1 | 1 | 1 | 0 |
  | T (13) | 10 | 1 | 2 | 0 | 0 |

  - **The views of one learner often disagree.** P04: LL and T `simultaneous`, LS pass. P13: LL
    `simultaneous`, LS `first_missing`, T pass. P31: LS `simultaneous`, T pass. Only P33 agrees
    in all three views (`taken_before_first_placed`).
  - **The `simultaneous` Fails** come from gaps of 0.04 to 0.37 s, all inside the placeholder
    0.5 s window (OQ-018). The window may be too wide for the "taken" and "placed" tags, which
    are annotated per view.
  - **P13_LS** is the OQ-058 case on real data.
  - R2 should not be approved until these are reviewed.

### Documents updated
- **`decision_flow.yaml`:** P-009, P-011, P-012 (the fallback is removal-only), P-030 (screen),
  P-032 (R2, new).
- **`pathways.md`:** the P-009, P-011, P-030 and P-032 tables. W-5, W-6, W-14 to W-16, W-19 and
  W-24 are marked removal-only. W-53 is updated; W-54 (LL, no screen), W-55 (R2, first
  placement missing) and W-56 (R2, parallel) are new.
- **`diagrams.md`:** (e), (e2), (i).
- **Registers:** `decisions.md` (D-093 to D-095, and a D-023 note); `open_questions.md`
  (OQ-057 and OQ-058 new; OQ-038 evidence link).
- **Other docs:**
  - `anomalies.md`, `output_contract.md` (v4), `rules_status.md`, `methods.md`;
  - `implementation_plan.md` (rows 11, 13, 14), `upstream_requirements.md`;
  - `docs/annotation/rule_engine_export_howto.md`, `camera_angle_evidence.md` (new);
  - `progress.md`, `ai_usage_log.md`.

### Open questions
- **New:** OQ-057 (supervisor: no shock time without the screen); OQ-058 (Arnikan: R2 in a
  parallel placement before the gate).
- **Worth revisiting with the R2 dry run:** OQ-018 (the simultaneous window).

### Next
Increment 12 (R8). Nothing is committed; commit only when Arnikan says so.

### Review changes (Arnikan, 2026-10-17)
- **R2 stays pending** until the supervisor confirms its definition.
- **D-096, angles are separate videos:** each camera angle is a separate video. Results are
  never compared or cross-checked across angles, and no cross-view comparison is built. The
  per-participant comparison in the R2 dry run above is **not used** for anything.
- **D-097, closes OQ-058:** a missing first placement while both zones were visible throughout
  the window → **Fail `first_placement_not_observed`**: "either the paddles were placed in
  parallel, or the second paddle was taken before the first was placed" (A-019).
  - The old "first missing" code is not used for this case. R2 no longer produces it, so it is
    removed from the output contract (still v4, which wasn't pushed yet).
  - Past the gate, derived parallel placements refine the result to `simultaneous` (D-091).
  - Tests: 2 updated, and they assert the old code is never used.
- **OQ-001 note:** if unknown coverage were set to Fail, a missing screen track would fail R5, and
  any rule leaving a missing placement to the coverage policy (R3 and R8 as planned) would fail
  where a zone has no track. **Correction to the request:** R2 as built would not be affected.
  D-095 fails only when both zones are actually visible throughout the window, never on unknown.

### Items to share with the team
- **For the team and the supervisor (camera angle, OQ-038):** **LS is the strongest view for the
  rule engine.** In the interim evidence ([camera_angle_evidence.md](camera_angle_evidence.md)),
  LS shows both placement zones throughout in every video and the shock on screen in 10 of 12.
  Every rule can then be checked directly. Without a shock-time fallback (D-093), LL leaves every
  shock-dependent rule unverifiable (shock seen in 0 of 12). T is partly usable (shock seen in 9
  of 13; apical zone often only partly in view).
- **For Ananth (backups):** **P05_LL uses the track label `apical_placement_zone` as a tag**
  (frame 287). It should be removed or replaced by the intended event tag. Listed in the how-to,
  item 4, with the other items to fix.
- **For the supervisor:** OQ-057 (no shock time without the screen, superseding the proposal's
  A6 clause); and confirming R2's definition, including `first_placement_not_observed` (D-097).

**Tests:** 511 run, all pass, 1 skipped (charging sound).

**Committed 2026-10-17** as `d428628` and pushed (on Arnikan's instruction).

---

## Increment 12: R8, apical before sternal (2026-10-17)

### Decisions recorded
- **D-098 (Arnikan), a parallel placement fails both R2 and R8:**
  - R2 and R8 are separate checklist criteria, so a parallel placement fails both, each with
    `simultaneous`;
  - it is not a dependency cascade: R8 has no dependency on R2 and is evaluated on its own
    evidence (the apical paddle was not placed first);
  - both results carry the cause flag **`possible_parallel_placement`**, so the feedback module
    can explain that one action caused both.
- **OQ-059 (new, supervisor):** does a parallel placement count as two mistakes or one?
- **D-099 (my proposal, interim, for your review):** R8 judges zone visibility over the
  **placement phase**. It runs from the first paddle taken to paddles firmly on chest; when a tag
  is missing, it starts at the earliest placement and ends at the second paddle taken or the
  latest placement. A zone visible for only part of the phase, or with no track, doesn't count as
  visible. LL views (no sternal track) therefore use the one-zone inference.

### What was done
- **R8 in `rules/video_rules.py` (P-015),** following diagram (f):
  1. a parallel placement → `simultaneous`, with the cause flag;
  2. both placements → direct comparison (`wrong_order`, `simultaneous`);
  3. a zone in view during the phase with its placement missing → Unable to Verify,
     `placement_missing` (D-058);
  4. the one-zone inference against the first placement (`placement_match_window_seconds`):
     - apical first → Pass – Inferred;
     - sternal first → the inferred-fail setting (undecided → Unable to Verify,
       `inferred_fail_policy_undecided`);
     - clearly before the first placement → `contradictory`;
  5. not determinable → Unable to Verify, or **assumed** when `assume_first_taken_is_apical` is
     on (off by default; blocks an overall Pass, D-060).

  Derived placements reach R8 only past the gate (the adapter). Results resting on them carry
  `derived_placement`.
- **R2:** its parallel Fail now carries the same flags, through a shared helper.
- **Rule-result flags** are listed in `video_rules.FLAGS`, and the docs test reads them.
- **Output contract version 5:**
  - two flags added: `possible_parallel_placement`, the shared cause flag, and `derived_placement`;
  - `placement_missing`, `contradictory`, `inferred_fail_policy_undecided` and `wrong_order` (R8)
    are now built.
- **R8 stays pending** in `rules.yaml`.

### Tests (511 → 533; `tests/test_rule_engine_r8.py`, 22)
- **Both zones visible:** apical first passes; `wrong_order`; `simultaneous`; one placement
  missing → `placement_missing`; both missing → `placement_missing`; pending in the catalogue.
- **One zone (LL-like):**
  - at the first placement time → Pass – Inferred;
  - clearly later → inferred mistake (undecided → Unable to Verify, flagged);
  - the setting decided as fail → `wrong_order`, and as unable → Unable to Verify;
  - clearly before → `contradictory`;
  - no placement in the visible zone → `placement_missing`;
  - sternal zone only;
  - no first placement → not determinable.
- **Zone windows:** a zone in view only after the placement phase, or for only part of it, does
  not count as visible.
- **Fallback:** off by default → Unable to Verify; on → assumed, and the overall result is
  Incomplete; it never overrides evidence.
- **Gate:** approved → derived placements used, flagged `derived_placement`; not approved →
  withheld, so `placement_missing` (zones in view).
- **Parallel placement:**
  - approved gate → **R2 and R8 both Fail `simultaneous`**, both flagged
    `possible_parallel_placement` and `derived_placement`, overall Fail with two mistakes;
  - not approved → R2 `first_placement_not_observed`, R8 `placement_missing`, no parallel flag.

Full suite: **533 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0, and its output matches the reference.

### Documents updated
- **`decision_flow.yaml`:** P-015 built; P-032's parallel branch flags.
- **`pathways.md`:** the P-015 table; W-17, W-18 and W-23 marked built; W-57 (parallel fails
  both), W-58 (LL one-zone inference), W-59 (zone windows).
- **`diagrams.md`:** (f).
- **Registers:** `decisions.md` (D-098, D-099); `open_questions.md` (OQ-059).
- **Other docs:** `anomalies.md` (rule-result flags), `output_contract.md` (v5),
  `rules_status.md`, `methods.md`, `implementation_plan.md` (row 12), `progress.md`,
  `ai_usage_log.md`.

### Open questions
- **New:** OQ-059 (supervisor: one mistake or two).
- **Still open for R8:** OQ-005 (inferred Fail), OQ-006 (match window; the fallback), OQ-015
  (final IDs).
- **For your review:** D-099 (the placement-phase window).

### Next
Increment 13 (R5). Nothing is committed; commit only when Arnikan says so.

**Review (Arnikan, 2026-10-17):** D-099 approved as interim. The final export's validation report
will show whether it discards real placements (as P06_T might), and it will be refined then.
**Committed** with the proposed message and pushed (on Arnikan's instruction).

---

## Increment 13: R5, shock confirmed on screen (2026-10-17)

### Decisions recorded (Arnikan)
- **D-100, preceding steps:**
  - the steps that must come before the shock are a setting, `configs/rules.yaml` R5
    `parameters.preceding_steps`, unset until the supervisor answers **OQ-013** (updated);
  - while unset, R5 checks presence only and flags **`order_not_checked`**, which, like
    `timing_not_checked` (D-062), keeps the overall result from being Pass;
  - once set, a shock before an observed step → `wrong_order`; a step not observed →
    `order_not_checked` for it.
- **D-101, screen window:**
  - a missing shock fails only if the screen was visible throughout the window from paddles
    firmly on chest to paddles removed; otherwise Unable to Verify;
  - if either tag is missing, the whole recording is used;
  - two or more shocks remain the preparation anomaly, and R5 gives Unable to Verify.

### What was done
- **R5 in `rules/video_rules.py` (P-033).** Multiple shocks → Unable to Verify. A shock seen → the
  preceding-step logic above. No shock → low confidence → Unable to Verify; the screen visible
  throughout the window → Fail `missing`; otherwise Unable to Verify. An invalid
  `preceding_steps` value is a configuration error, recorded as `engine_error` (D-063).
- **`order_not_checked`** is in `checks.FLAGS`. The overall policy lists it as "order not
  checked" among the Incomplete reasons.
- **Output contract version 6:** `order_not_checked` added; `missing` and `wrong_order` built
  for R5.
- **R5 stays pending** in `rules.yaml`.

### Tests (533 → 546; `tests/test_rule_engine_r5.py`, 13)
- **Shock seen:**
  - steps unset → presence only, `order_not_checked`, overall Incomplete ("order not checked");
  - steps set and met → Pass, overall Pass;
  - a shock before a step → `wrong_order`;
  - a step not observed → `order_not_checked`;
  - an invalid setting → `engine_error`;
  - multiple shocks → Unable to Verify;
  - pending in the catalogue.
- **Shock missing:**
  - screen visible throughout the window → `missing`;
  - out of view in the window → Unable to Verify;
  - visible for part of it → Unable to Verify;
  - no screen track → Unable to Verify;
  - window tags missing → whole recording (throughout → Fail; partly → Unable to Verify);
  - low-confidence shock → Unable to Verify.

Full suite: **546 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0, and its output matches the reference.

### Documents updated
- **`decision_flow.yaml`:** P-033 (new); P-017's Incomplete branch includes `order_not_checked`.
- **`pathways.md`:** the P-033 table; W-60 (steps unset), W-61 (screen window), W-62 (two
  shocks).
- **Registers:** `decisions.md` (D-100, D-101); `open_questions.md` (OQ-013 interim behaviour).
- **Other docs:** `anomalies.md`, `output_contract.md` (v6), `rules_status.md`, `methods.md`,
  `implementation_plan.md` (row 13), `configs/rules.yaml` (R5 parameter), `progress.md`,
  `ai_usage_log.md`.

### Open questions
None new. OQ-013 (supervisor: which steps must precede the shock) now feeds the setting.

### Next
Increment 14 (R6). Nothing is committed; commit only when Arnikan says so.

## Increment 14: R6, paddles removed after the shock; "no limit"; R3/R4 inference sources (2026-10-17)

Increment 13 was committed and pushed on instruction (eaa9a3c) before this work.

### Decisions recorded (Arnikan)
- **D-102, R3/R4 inference from removal:** the proposal is followed despite an observed
  contradiction. Paddles are sometimes removed without a successful shock, but both sources are
  kept.
  - The list is the setting R3/R4 `parameters.inference_sources` in `configs/rules.yaml`.
  - **Risk:** R3/R4 may be Pass – Inferred without a successful shock (A-021). The overall result
    can't be Pass then, because R5 is Fail (screen visible) or Unable to Verify (not visible).
  - **OQ-060** asks the supervisor whether removal should still count.
- **OQ-057 note:** the same observation (removal without a successful shock) supports D-093,
  which stays.
- **D-103, "no limit":** a clinical value can state `no_limit: true` with the same provenance and
  approval fields as an approved value.
  - Approved → the rule checks presence and order and passes fully, without
    `timing_not_checked`.
  - Unapproved → not used (`timing_not_checked`, `limit_not_approved`).
  - `null` still means "not decided" (D-062).
  - The R6, A1 and A3 records and OQ-016 note that the answer may be "no limit".
- **D-104, R6:** a removal means only that the paddles were removed; it doesn't prove a shock.
  - No shock time → Not evaluable because of R5, even with a removal.
  - A removal clearly before the shock → `removed_before_shock`; within the simultaneous window
    before it → treated as at the shock.
  - Past the gate, a derived placement ending (by a real exit) before the shock →
    `removed_before_shock`.
  - Missing removal → `missing` only if both placement zones were visible from the shock to the
    end of the recording; otherwise Unable to Verify.
  - `shock_to_removal_seconds` stays unset, so a Pass is flagged `timing_not_checked`.

### What was done
- **R6 in `rules/video_rules.py` (P-034)**, in this order:
  1. no shock time → Not evaluable because of R5;
  2. a shock time taken from the removal itself (only with `shock_time_fallback: removal`) →
     Unable to Verify, because a removal can't be judged against its own time (an agent proposal,
     in D-104);
  3. the earliest removal clearly before the shock → `removed_before_shock`;
  4. derived placements: a paddle whose placements all ended by a real exit clearly before the
     shock (none on at the shock) → `removed_before_shock`, flagged `derived_placement`;
  5. a removal at or after the shock → Pass, through the time-limit check (P-024): unset →
     `timing_not_checked`; approved no limit → fully checked; approved value exceeded →
     `too_late`;
  6. no removal → low confidence → Unable to Verify; both zones covered from the shock to the end
     (header duration, else the last event) → `missing`; otherwise Unable to Verify.
- **Derived placements (9c):** each event now records `end_frame`, `end_seconds` and
  `ended_by_exit` (a real exit of `exit_frames`, not the end of the video). `events.jsonl` and
  Ananth's files are untouched; the change is in the rule engine's own exporter only.
- **"No limit":** `ClinicalValue.no_limit`; validation (must be true/false; not with a value; an
  approval needs a value or no limit; either needs a source); `checks.time_limit` handles it.
- **R3/R4 `inference_sources`** in `rules.yaml` (read by R3/R4 in Increments 15-16).
- **Output contract version 7:** `configuration.timing_limits` entries gain `no_limit`;
  `removed_before_shock`, `missing` (R6) and `too_late` (R6) are built.
- **R6 stays pending** in `rules.yaml`.
- **A-022 (new):** both placement zones in view means a removal would have been seen.

### Tests (546 → 570)
- **`tests/test_rule_engine_r6.py` (18):**
  - with a shock time: removal after → Pass, `timing_not_checked`, overall Incomplete; just
    before, within the window → Pass at 0 s; clearly before → `removed_before_shock`; approved
    limit exceeded → `too_late`, within → full Pass; approved no limit → full Pass, overall Pass;
    unapproved no limit → not used; pending in the catalogue;
  - without a shock time: removal only → Not evaluable (R5); two shocks → Not evaluable (R5);
    fallback removal → Unable to Verify;
  - missing removal: zones visible to the end → `missing`; out of view before the end → Unable to
    Verify; no zone tracks → Unable to Verify; low-confidence removal → Unable to Verify;
  - derived placements: gate approved, episode ended before the shock → `removed_before_shock`;
    gate not approved → withheld, Pass from the tag; the paddle placed again before the shock →
    Pass; an episode ending within the window of the shock → Pass.
- **Config (3):** the inference-sources setting; approved no limit; no-limit validation. The
  unused-limits test now checks `shock_to_removal_seconds` stays unset and notes "may be no
  limit".
- **Checks (2):** approved no limit → checked and passed; unapproved no limit → not used.
- **Derived placements (1):** episode end and `ended_by_exit` recorded.

Full suite: **570 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0.

### Documents updated
- **`decision_flow.yaml`:** P-034 (new); P-024 (no-limit branches); P-016 (inference sources,
  D-102); P-031 (episode end metadata).
- **`pathways.md`:** the P-034 table, P-024 and P-016 rows; W-20 step 4; W-63 to W-66.
- **`diagrams.md`:** (k) R6 (new); (j) end metadata and R6 as a user of derived placements.
- **Registers:** `decisions.md` (D-102, D-103, D-104); `assumptions.md` (A-021, A-022);
  `open_questions.md` (OQ-060 new; OQ-057 note; OQ-016 "no limit" and A1/A3).
- **Other docs:** `anomalies.md`, `output_contract.md` (v7), `rules_status.md`, `methods.md`,
  `implementation_plan.md` (row 14), `configs/rules.yaml`, `progress.md`, `ai_usage_log.md`.

### Open questions
- **OQ-060 (supervisor, new):** should paddle removal still support an inferred Pass for R3/R4?

### Next
Increment 15 (R3). Nothing is committed; commit only when Arnikan says so.

## Increment 15: R3, paddles firmly on chest; R6's screen-delay tolerance (2026-10-17)

Increment 14 was committed and pushed on instruction (e7cdc8b) before this work.

### Screen delay for R6 (D-105)
The screen may show the shock slightly after the discharge, so a correct learner can remove the
paddles before the screen updates. R6 now uses its own setting,
`removal_before_screen_tolerance_seconds` (`engine.yaml`, placeholder 0.5 s), instead of
`simultaneous_window_seconds`. It applies to the removal tag and to the end of a derived
placement.

**Measurement.** Source: the interim export of 2026-10-16 (`smoke-kartheepan`, tags only). Videos:
LS and T videos with both `shock_delivered_on_screen` and `paddles_removed_after_shock`. Measured:
the removal tag time minus the shock-on-screen time.
- **Videos:** 20 of 26 LS/T videos (11 LS, 9 T). The other 6 have a removal but no shock tag:
  P06_LS, P06_T, P31_T, P32_T, P33_LS, P33_T.
- **Each tag was present once**, and the videos are about 30 fps (one frame ≈ 0.033 s).

| Screen → removal (s) | Videos |
|---|---|
| below 0 (removal before the screen) | **0** |
| 0 – 0.5 | 2 (0.133, 0.267) |
| 0.5 – 1.0 | 10 (0.600, 0.767, 0.800, 0.800, 0.800, 0.833, 0.833, 0.867, 0.900, 0.900) |
| 1.0 – 1.5 | 8 (1.000, 1.066, 1.067, 1.167, 1.233, 1.267, 1.267, 1.401) |

Summary:
- **Range:** minimum 0.133 s, median 0.884 s, maximum 1.401 s.
- **By view:** LS median 0.800 s (n = 11); T median 1.000 s (n = 9).

**What it shows:** in this data the removal always came after the screen showed the shock, so a
screen delay longer than the learner's removal time was never observed. The data doesn't bound
the tolerance from below. The placeholder stays 0.5 s (the value it replaces, so no result
changes). The value is part of OQ-018. Videos where the removal comes before the screen would be
needed to measure the delay itself.

### Decisions recorded (Arnikan)
- **D-105:** R6's separate screen-delay tolerance (above).
- **D-106, R3:**
  - **Direct evidence:** the firm-placement tag at or before the shock, or past the gate both
    derived placements before it → Pass – Direct. Only after the shock → `placed_after_shock`.
  - **Missing direct evidence:** first the inference from `inference_sources`, then (no shock
    time) Not evaluable because of R5, then coverage. A missing tag fails `missing` only if both
    placement zones were visible from first paddle taken to the shock; otherwise Unable to Verify.
  - **`not_in_zone`** is not produced until the chest regions are approved (OQ-012). R3 checks
    placement timing and presence only until then.

### What was done
- **R3 in `rules/video_rules.py` (P-035):**
  - `inference_sources` is validated (a list of canonical events, else `engine_error`).
  - A tag within `simultaneous_window_seconds` after the shock counts as at it (annotation timing,
    as in R2 and R8).
  - Without a shock time the tag can't be judged against the shock (D-093: R3's direct check needs
    the shock time), so the inference decides, else Not evaluable because of R5.
  - Without `first_paddle_taken`, the placement phase starts at the recording's start.
  - A new code for R3, `missing`; the brief's R3 codes had none for a placement that never
    happened.
- **Finding:** with the proposal's sources, a shock time always means a shock on the screen,
  which is itself an inference source. R3's coverage step (and `missing`) is reached only if
  `inference_sources` drops the shock on screen.
- **R6:** uses the new tolerance. `engine.yaml` and `config.py` gained the required setting.
- **R3 stays pending** in `rules.yaml`.
- **Output contract:** still version 7. `placed_after_shock` and `missing` (R3) became built, and
  the meanings of `removed_before_shock` and `not_in_zone` were clarified. No field or code was
  added, removed or renamed.

### Tests (570 → 594)
- **`tests/test_rule_engine_r3.py` (23):**
  - **direct evidence:** tag before the shock → Pass, overall Pass; within the window after →
    Pass; only after → `placed_after_shock`; before and after → Pass with the earliest;
    `placed_after_shock` beats the inference; `not_in_zone` never produced; pending in the
    catalogue; invalid `inference_sources` → `engine_error`;
  - **inference:** from the shock; from the removal without a shock; a tag without a shock time
    (with removal → inferred, alone → Not evaluable); sources are a setting; nothing → Not
    evaluable (R5);
  - **coverage (no inference sources):** both zones visible → `missing`; one paddle visible →
    Unable to Verify; a zone partly visible → Unable to Verify; no first paddle taken → from the
    recording's start; low confidence → Unable to Verify; with the proposal's sources the shock
    always infers;
  - **derived placements:** gate approved → Pass – Direct, `derived_placement`; gate not approved
    → withheld, inferred from the shock; one derived placement, or one after the shock → not
    direct evidence.
- **R6 (1):** the screen-delay tolerance is its own setting.

Full suite: **594 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0.

### Documents updated
- **`decision_flow.yaml`:** P-035 (new); P-016 (R3 built there, R4 planned); P-034 (tolerance).
- **`pathways.md`:** the P-035 table; P-034 and P-016 rows; W-20 built; W-64 (tolerance); W-67
  to W-70.
- **`diagrams.md`:** (l) R3 (new); (k) the tolerance.
- **Registers:** `decisions.md` (D-105, D-106); `assumptions.md` (A-002: new placeholder);
  `open_questions.md` (OQ-018 R6 screen delay; OQ-012 interim behaviour).
- **Other docs:** `anomalies.md`, `output_contract.md`, `rules_status.md`, `methods.md`,
  `implementation_plan.md` (row 15), `configs/rules.yaml`, `configs/rule_engine/engine.yaml`,
  `progress.md`, `ai_usage_log.md`.

### Open questions
None new. The tolerance value is part of OQ-018; R3's zone check waits on OQ-012.

### Next
Increment 16 (R4). Nothing is committed; commit only when Arnikan says so.

## Increment 16: R4, both buttons pressed; R3/R4 inference; paddle visibility (2026-10-17)

Increment 15 was committed and pushed on instruction (bb34dfb) before this work.

### Decisions recorded (Arnikan)
- **D-107, R3/R4 inference, following the proposal:**
  - each rule is Pass – Inferred when either `shock_delivered_on_screen` or
    `paddles_removed_after_shock` is confidently confirmed; one is enough;
  - `inference_sources` lists both for R3 and R4 (confirmed by a config test). The first listed
    source that is confirmed is cited, so the shock is cited whenever it is there;
  - a removal alone gives Pass – Inferred even without a shock time (views without the screen);
  - the contradiction is linked on those results: the flag `inferred_from_removal`, and a reason
    naming A-021 and D-102.
- **OQ-061 (supervisor, new; linked to D-102, D-106, OQ-060):** with both sources, R3 and R4 pass
  whenever the shock is on the screen or the paddles are removed, even when the zones or paddles
  were visible and the firm placement or press wasn't tagged. Can the training defibrillator
  deliver a shock without firm contact? Since removal happens without a successful shock, should
  either source still apply when the direct evidence was visible but absent?
- **D-108, R4:**
  - **direct evidence:** a press after the placement and at or before the shock, with the same
    annotation-lag tolerance as R3. A press clearly before the placement → `before_placement`;
  - **missing evidence:** first the inference from either source, then without a shock time Not
    evaluable because of R5, then coverage;
  - **paddle visibility:** exported and adapted like the zones and the screen. `not_pressed`
    fails only if both paddles were visible throughout from the placement to the shock;
    otherwise Unable to Verify;
  - **repeated presses:** stay the supervisor's question (OQ-023); the count stays undecided.
- **Unreachable for now (D-107):** R3's `missing` and R4's `not_pressed` can't be produced while
  either source is in `inference_sources`. With a shock time there is a shock on the screen; without
  one a removal infers, and otherwise the rule is Not evaluable.

### What was done
- **Shared inference (`_inferred` in `rules/video_rules.py`)**, used by R3 and R4. R3 now uses it, so
  its inferences from the removal carry the new flag.
- **R4 (`both_buttons_pressed`, P-036):**
  - **The placement:** the firm-placement tag, or, past the gate, the later of the two derived
    placements.
  - **Choices of mine, recorded in D-108:**
    - no placement observed → Pass – Direct, `order_not_checked` (blocks an overall Pass);
    - presses only clearly after the shock → Unable to Verify, `contradictory`;
    - without a shock time, `before_placement` only if no press came after the placement;
    - no placement known → the coverage window starts at the recording's start.
- **Paddle visibility:**
  - **Exporter (version 2):** `paddle_tracks` and `paddle_visibility`, derived like the zones; the
    manifest counts `paddle_intervals`.
  - **Export config:** `paddle_regions` maps `paddle_apical` → `apical_paddle` and
    `paddle_sternal` → `sternal_paddle`.
  - **Engine config:** these are visibility-only regions in `engine.yaml` (an empty event list, now
    allowed).
  - **Coverage:** `region_status` and `region_missing` ask a region by name.
  - **Context and adapter:** the context reports the new regions, and the adapter turns the paddle
    fields into header coverage and intervals. An older export gives unknown.
  - Ananth's files and `events.jsonl` are untouched.
- **Output contract version 8:**
  - new flag `inferred_from_removal`;
  - new regions `apical_paddle` and `sternal_paddle`;
  - `before_placement` and `not_pressed` built;
  - `contradictory` and `order_not_checked` can also come from R4.
- **R4 stays pending** in `rules.yaml`.

### Tests (594 → 628)
- **`tests/test_rule_engine_r4.py` (28):**
  - **direct evidence:**
    - a valid press → Pass, overall Pass;
    - within the window after the shock, or before the placement → Pass;
    - before the placement → `before_placement`, which beats the inference;
    - an early press followed by a valid one → Pass;
    - only after the shock → `contradictory`;
    - no placement → `order_not_checked`, overall Incomplete;
    - the count stays undecided;
    - pending in the catalogue;
    - invalid sources → `engine_error`;
  - **inference:**
    - the shock on its own;
    - the removal on its own and with both listed, without a shock time, flagged and naming A-021;
    - a press without a shock time;
    - an early press without a shock time (fails only with no later press);
    - the shock not listed → coverage;
    - nothing → Not evaluable (R5);
    - `not_pressed` unreachable with the proposal's sources;
  - **coverage (no inference):**
    - both paddles visible → `not_pressed`;
    - a paddle partly visible, out of view, or no tracks → Unable to Verify;
    - no placement → from the recording's start;
    - low confidence → Unable to Verify;
  - **derived placements and exported paddle visibility:**
    - gate approved: a press after the later placement → Pass, `derived_placement`; a press between
      the placements → `before_placement`;
    - gate not approved → `order_not_checked`;
    - exported paddle visibility through the adapter: throughout → `not_pressed`; partly → Unable to
      Verify; an older export → Unable to Verify.
- **R3 (2):** each source on its own; with both confirmed the shock is cited. The removal test
  checks the flag and A-021.
- **Exporter (1):** paddle visibility exported like the zones.
- **Adapter (2):** paddle regions with windowed status; an older export → unknown.
- **Coverage (net 1):** region events must be a list; an empty region is visibility-only.
- **Updated for the new regions:** the region list, the zone-visibility maps and the manifest
  counts.

Full suite: **628 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0.

### Documents updated
- **`decision_flow.yaml`:** P-036 (new); P-016 (built, both sources, the flag, unreachability);
  P-035 (the flag); P-030 and P-007 (paddle regions).
- **`pathways.md`:** the P-036 and P-016 tables; P-030 and P-007 rows; W-71 to W-74.
- **`diagrams.md`:** (m) R4 (new); (l) the flag; (i) the paddles.
- **Registers:** `decisions.md` (D-107, D-108); `open_questions.md` (OQ-061 new; OQ-060 and OQ-023
  notes); `assumptions.md` (A-021 linked on results).
- **Other docs:** `anomalies.md`, `output_contract.md` (v8), `rules_status.md`, `methods.md`,
  `implementation_plan.md` (row 16), `upstream_requirements.md` (paddle visibility),
  `configs/rules.yaml`, `configs/rule_engine/engine.yaml`, `configs/rule_engine/annotation_export.yaml`,
  `progress.md`, `ai_usage_log.md`.

### Open questions
- **OQ-061 (supervisor, new):** should either inference source apply when the direct evidence was
  visible but absent? Can the training defibrillator shock without firm contact?

### Next
Increment 17 (R1). Nothing is committed; commit only when Arnikan says so.

## Step 9d and Increment 17: derived gel applications and R1 (2026-10-17)

Increment 16 was committed and pushed on instruction (c309b92). The how-to update for exporter
version 2 was not committed; it is superseded here by version 3.

### Decisions recorded (Arnikan)
- **D-109:** gel must be applied before the paddles are placed (a shock without gel harms the
  patient). Gel only after the first placement → `after_placement` (new code). Replaces D-018's
  "order versus placement not checked".
- **D-110:** gel twice means once on each placement zone (sternal on the chest, apical on the left
  side of the ribs), in either order. Replaces D-018's "two separate applications".
- **D-111 (Step 9d):** per-zone gel applications derived in the rule engine's exporter from the
  `learner_hand` and zone boxes: gel phase, proximity (not overlap), nearest-zone matching, visits
  and dips, per-zone status (gelled, not gelled, unknown), `gel_hand_not_tracked`, cross-check with
  the tags in `gel_validation.csv`/`.md`.
- **D-112:** the 9d gate (`derived_gel.reviewed_for_r1`, export ID and 9d settings hash). R1 uses
  derived gel only past it.
- **D-113 (R1):** per zone past the gate, the tag-count proxy before it, and the time period
  unset (`timing_not_checked`).
- **Assumptions:** A-023 (`Gel applied` tagged when the nozzle is on or near a zone), A-024 (the
  `learner_hand` box is only the bottle hand, tracked during gel in every video), A-025 (the hand
  is near the zone, sometimes overlapping, rarely further), A-026 (the proxy's risk: an arm can
  hide the nozzle while the zone is visible).

### What was done
- **`annotation/derive_gel_applications.py` (new, P-037):**
  - **Settings:** the `derived_gel` section of `annotation_export.yaml` (placeholders: gap 0.05 of
    the diagonal, dwell 10 frames, nearer ratio 2.0, exit 5 frames, tag window 30 frames), with the
    `reviewed_for_r1` gate.
  - **Settings hash:** includes the 9c settings hash, because the gel phase may end at a 9c
    placement. The exporter can't check the 9c gate itself: the export ID is the hash of its own
    output.
- **Exporter (version 3):**
  - **Records:** `derived_gel_events` and `gel` (the phase, bottle period and each zone's status).
  - **New files:** `gel_validation.csv`/`.md`.
  - **Manifest:** `gel_settings_sha256`, the `derived_gel_events` count and the `gel_validation`
    summary.
  - **Issues:** `gel_hand_not_tracked` in the export issues.
- **Audit:** `gel_hand_not_tracked` on the review list. The audit has no derived placements, so
  its gel phase ends at the first-placement tag, else `first_paddle_taken`.
- **Engine and adapter:**
  - **Vocabulary:** new canonical events `apical_gel_applied` and `sternal_gel_applied`, with
    undecided counts (OQ-021).
  - **Regions:** visibility-only `apical_gel` and `sternal_gel`.
  - **Adapter:** passes the gel events, and each zone's status as region coverage, only past the 9d
    gate.
- **R1 (`gel_applied_twice`, P-038):**
  - `after_placement` first;
  - then per zone when the gel regions are in the header;
  - otherwise the tag-count proxy;
  - a pass goes through the period check.
  - The first placement is `first_paddle_placed` or the earliest per-paddle placement. A gel tag
    within the simultaneous window after it still counts. Without a placement time,
    `after_placement` isn't judged and the phase ends at `first_paddle_taken`.
- **Output contract version 9:** new failure code `after_placement`, new flag
  `derived_gel_application`, new regions `apical_gel` and `sternal_gel`. R1's `applied_once` and
  `missing` are now per zone; `applied_once`, `outside_time_period` and `missing` (R1) are built.
- **R1 stays pending** in `rules.yaml`.
- **Re-export needed:** the interim export has no hand geometry, so derived gel needs a re-export
  with exporter version 3. The how-to now asks for version 3 and the gel validation files.
  Ananth's files are untouched.

### Proxy check on the interim export (item 12)
Source: the interim export of 2026-10-16 (38 videos), tags and zone visibility only. Gel phase:
start → `first_paddle_firmly_on_the_chest` (37 videos), else `first_paddle_taken` (1). Separate
applications: `Gel applied` tags in the gel phase, merged when closer than
`gel_minimum_gap_seconds`.

**17 videos** have both zones visible throughout the gel phase (13 LS, 4 T). The other 21 are the
12 LL videos (no sternal zone) and 9 T videos. No gel tag came after the first placement in any
video.

**First run, with the 1.0 s placeholder:** 0 videos with no application, 10 with one, 7 with two
or more. Six of the ten (P03_LS, P03_T, P04_LS, P12_LS, P13_LS, P14_LS) had two tags 0.5–0.97 s
apart, merged by the 1.0 s gap.

**Rerun with 0.4 s (set by Arnikan on 2026-10-17, still a placeholder, OQ-018):**

| Separate applications | Videos |
|---|---|
| 0 | 0 |
| 1 | **4** (P15_LS, P31_LS, P33_LS, P33_T) |
| 2 or more | 13 |

Per video (the `Gel applied` tags in the gel phase, frame and seconds):

| Video | Tags | Separate applications |
|---|---|---|
| P01_LS | 288 (9.60), 323 (10.77) | 2 |
| P01_T | 260 (8.67), 296 (9.87) | 2 |
| P03_LS | 198 (6.60), 226 (7.53) | 2 (0.93 s apart; for Arnikan's review) |
| P03_T | 166 (5.53), 193 (6.43) | 2 |
| P04_LS | 101 (3.37), 126 (4.20) | 2 |
| P05_LS | 223 (7.43), 261 (8.70) | 2 |
| P06_LS | 226 (7.53), 259 (8.63), 260 (8.67) | 2 (259 and 260 are 0.03 s apart, the audit's near-duplicate, merged) |
| P07_LS | 259 (8.63), 303 (10.10) | 2 |
| P07_T | 197 (6.57), 250 (8.33) | 2 |
| P12_LS | 164 (5.47), 179 (5.97) | 2 (0.50 s apart, also on the audit's list as a possible duplicate; for Arnikan's review) |
| P13_LS | 170 (5.67), 199 (6.63) | 2 |
| P14_LS | 186 (6.20), 211 (7.03) | 2 |
| P15_LS | 236 (7.87) | **1** (for Arnikan's review) |
| P31_LS | 194 (6.46) | **1** (for Arnikan's review) |
| P32_LS | 179 (5.96), 210 (7.00) | 2 |
| P33_LS | 466 (15.53) | **1** (for Arnikan's review) |
| P33_T | 427 (14.24) | **1** (for Arnikan's review) |

**What it shows:**
- **The four single-tag videos:** under the proxy, R1 would fail them `applied_once`. Either the
  second application wasn't visible (A-026's risk), or the learner gelled one zone.
- **P12_LS:** its pair, 0.5 s apart, now counts as two applications. Arnikan reviews whether it is
  one zone each or the same application tagged twice.

### Tests (628 → 679)
- **`tests/test_rule_engine_derived_gel.py` (24):**
  - **proximity:** touching; at the threshold and just beyond; near without overlap;
  - **nearest zone:** clearly nearer; ambiguous; the ratio deciding; the other zone not visible;
  - **visits:** a short dip stays one visit; a longer dip makes two; too short a visit; both zones
    in either order;
  - **missed applications:** hidden hand frames → unknown; zone not visible → unknown; no hand
    track → unknown and the review issue;
  - **gel phase:** T1, else derived placement, else `first_paddle_taken`, else the end; no
    application after the phase;
  - **tag agreement:** a tag in the window agrees; disagreements both ways, the event kept;
  - **settings and gate:** repository values; the digest (the settings and 9c's, not the review);
    the gate; invalid settings;
  - **validation report:** the summary and markdown.
- **`tests/test_rule_engine_r1.py` (26):**
  - **proxy:** both zones visible with 2, 1 and 0 applications; the minimum gap; one zone visible;
    no zone visible; a zone partly visible; `after_placement`; no placement time; gel before and
    after the placement; no placement → `first_paddle_taken`; low confidence; more than two;
    pending in the catalogue;
  - **time period:** unset, set (exceeded and within), approved no limit, derived applications;
  - **per zone:** both gelled (either order); one gelled; neither; a zone unknown;
    `after_placement`;
  - **gate through the adapter:** approved → per zone; unknown status → unknown coverage; not
    approved → proxy; an export before version 3 → proxy.
- **Audit (1):** the bottle hand must be tracked in the gel phase.
- **Updated:** the exporter tests (the `gel_hand_not_tracked` review issue on synthetic tasks
  without a hand, the seven output files, the new counts), the region lists, the undecided counts,
  and the R1 period no longer "unused".

Full suite: **679 tests run, all pass, 1 skipped** (charging sound). The pipeline command exits
with 0.

### Documents updated
- **`decision_flow.yaml`:** P-037 (new, 9d); P-038 (new, R1); P-001 (the 9d gate); P-030 (gel
  regions).
- **`pathways.md`:** the P-037 and P-038 tables; P-001 rows; W-75 to W-80.
- **`diagrams.md`:** (n) Step 9d and (o) R1 (new).
- **Registers:** `decisions.md` (D-109 to D-113; D-018 marked replaced); `assumptions.md` (A-023
  to A-026); `open_questions.md` (OQ-016, OQ-018 and OQ-021 notes).
- **Other docs:** `anomalies.md`, `output_contract.md` (v9), `rules_status.md`, `agent_brief.md`
  (R1), `implementation_plan.md` (rows 9d and 17), `methods.md`, `upstream_requirements.md`
  (per-zone gel events from production), the how-to for Ananth (exporter version 3, gel
  validation files), `configs/rules.yaml`, the engine config, the vocabulary and
  `annotation_export.yaml`, `progress.md`, `ai_usage_log.md`.

### Open questions
None new. OQ-016 (the period, possibly no limit), OQ-018 (the 9d settings and the gel gap, now 0.4 s) and
OQ-021 (more than two applications) apply.

### Next
The audio rules (Increment 18, A1 and A3). Nothing is committed; commit only when Arnikan says so.

## Demo of the rule engine as it stands (2026-10-17)

Step 9d and Increment 17 were committed and pushed on instruction (6f43000), with
`gel_minimum_gap_seconds` at 0.4 s. The supervisor briefing (`supervisor_briefing.md`) is not
committed yet.

### Decision recorded (Arnikan)
- **D-114:** the demo uses its own config, `configs/rule_engine/demo/rules_demo.yaml`. It is a copy
  of `rules.yaml` with the built rules (R1–R6, R8) approved and the unbuilt ones disabled, and it
  states `demo: true`. Every report from it carries `demo_notice`, "DEMO ONLY: rules not approved
  by the supervisor", and the overall flag `demo_only`. The real `rules.yaml` is unchanged.

### What was done
- **Engine:**
  - `RuleEngineConfig.demo` (validated true/false);
  - the overall flag `demo_only` (`rules/policy.py`);
  - the report field `demo_notice` (`rules/render.py`);
  - `rules.run` prints the notice.
  - **Output contract version 10.**
- **Demo config:** generated from `rules.yaml`. The audio rules are disabled rather than left
  pending, so a correct procedure shows the built rules alone; it is then Incomplete only because
  of undecided settings.
- **Scenarios (synthetic, no participant data):** seven, in `docs/rule_engine/demo/scenarios/`,
  with expected results in `scenarios.yaml`:
  - a correct procedure (Incomplete: timing and order not checked);
  - a parallel placement (R2 and R8 `simultaneous`);
  - gel after placement (`after_placement`);
  - the screen not in view (R5 Unable to Verify, R6 Not evaluable because of R5, R3/R4 inferred
    from the removal);
  - a low-confidence removal (R6 Unable to Verify);
  - removed before the shock (`removed_before_shock`);
  - the correct procedure with the real catalogue (every rule pending → Incomplete).
- **`python -m rules.demo`:**
  - **Per scenario:** a table (rule, result, failure code, flags, short reason), the overall result
    and why, and a check against the expected result.
  - **Options:** `--scenario`; `--full` for whole reasons; `--records` to run real interim
    annotation records with the demo config.
  - **`--records` output:** reports written only under the gitignored `data/rule_engine/`, labelled
    development data. Any other path is refused.
- **`docs/rule_engine/demo_walkthrough.md`:** a 15–20 minute presentation guide with two diagrams,
  linking the detailed documents.

### Interim data through the demo (development data)
On the interim export of 2026-10-16 (38 videos):
- **R8** is Unable to Verify everywhere: the derived placements are held back by the 9c gate.
- **R6** is Not evaluable in the views without the screen.
- **R1** fails `missing` in four videos (P12_LL, P12_T, P31_LL, P31_T) that have **no `Gel applied`
  tag at all** while a zone was in view. That is worth checking against the videos: possibly
  untagged gel rather than a learner mistake (A-026).

### Tests (679 → 690)
- **`tests/test_rule_engine_demo.py` (11):**
  - every scenario gives its expected results;
  - the key pathways are covered;
  - the scenarios hold no participant data;
  - the demo config approves the built rules, disables the rest, and is otherwise a copy of
    `rules.yaml`;
  - the real catalogue is not a demo;
  - every demo report says DEMO ONLY (the catalogue's doesn't);
  - the command prints the tables and returns 0, and refuses an unknown scenario;
  - interim records are written only under `data/rule_engine/` and marked development data.
- **Render (updated):** the new `demo_notice` field.

### Documents updated
- `decisions.md` (D-114);
- `decision_flow.yaml` (P-017 and P-027);
- `anomalies.md` (`demo_only`);
- `output_contract.md` (v10);
- `demo_walkthrough.md` (new);
- `progress.md`, `ai_usage_log.md`.

### Next
Wait for Arnikan before committing and before Increment 18.

## Removing every "paddle removal implies a shock" inference (2026-10-19)

The demo and the supervisor briefing were committed and pushed on instruction (6a5845b).

### Why
Arnikan checked the original documents and found **no inference rule** stating that a paddle
removal implies a shock was delivered. The engine had two such uses, both from the rule engine
brief rather than the proposal:
- R7/A6's "Shock time (R5, or R6 as fallback)": the shock time taken from the removal (D-023);
- R3's "Pass – Inferred if `shock_delivered_on_screen` OR `paddles_removed_after_shock`" (D-102,
  D-107).

Earlier documents credited these to the proposal (D-093's "A6 clause", D-102's "follows the
proposal") without that being verified.

### Decision recorded (Arnikan)
- **D-115:** a paddle removal is never evidence that a shock was delivered, or of when it was. It
  withdraws D-023, D-024, D-053, D-059, D-102 and D-107, retires A-014 and A-021, and answers
  OQ-060.

### What was removed or changed
- **Shock time:**
  - the `shock_time_fallback` setting is removed from `engine.yaml` and `config.py`; an engine
    file that still has it is rejected;
  - its code paths are removed from `rules/context.py` (shock anchor, command resolution, start
    anchor) and R6's fallback guard;
  - the flags `shock_time_from_removal` and `command_before_removal` are gone.
- **R3/R4:**
  - `inference_sources` is `[shock_delivered_on_screen]` in `rules.yaml` and the demo config;
  - the rules refuse the removal as a source (`engine_error`, D-063);
  - the flag `inferred_from_removal` is gone.
  - Without a shock on the screen, R3 and R4 are Not evaluable because of R5.
- **Unchanged:**
  - R6 still judges the removal against the shock on the screen (D-104, D-105);
  - R5 still uses the removal tag only as the end of its screen window (D-101), which is not an
    inference.
- **Output contract version 11:** the three flags removed.
- **Demo:** the "screen not visible" scenario now expects R3, R4 and R6 Not evaluable because of
  R5.
- **Interim data:** in views without the screen (LL, and T videos without a shock tag), R3 and
  R4 are now Not evaluable instead of Pass – Inferred.

### Tests (690 → 677)
- **Removed:** the fallback tests in `test_rule_engine_context.py`, and R6's fallback guard test.
- **Rewritten:**
  - the R3/R4 inference tests: the shock infers; a removal infers nothing; the removal is refused
    as a source; the catalogue lists only the shock;
  - the shared-check tests, to use flags that still exist;
  - the config test (only the shock as a source).
- **New:** a test that there is no fallback setting.

Full suite: **677 tests run, all pass, 1 skipped** (charging sound). The demo matches all seven
expected results. The pipeline command exits with 0.

### Documents updated
- **Registers:**
  - `decisions.md`: D-115 new; D-023, D-024, D-053, D-059, D-102 and D-107 marked withdrawn; D-093
    and D-104 notes;
  - `assumptions.md`: A-014 and A-021 retired;
  - `open_questions.md`: OQ-060 answered; OQ-057 and OQ-061 corrected.
- **`decision_flow.yaml`:** P-009, P-011, P-012, P-014, P-016, P-021, P-034, P-035, P-036.
- **`pathways.md`:**
  - the tables;
  - W-5, W-6, W-14, W-15, W-16, W-19, W-24, W-20, W-69 and W-71 marked withdrawn;
  - W-54.
- **`diagrams.md`:** (e), (e2), (k), (l), (m).
- **The rest:**
  - `anomalies.md`, `output_contract.md` (v11), `rules_status.md`, `methods.md`,
    `implementation_plan.md` and `camera_angle_evidence.md`;
  - `upstream_requirements.md` and `agent_brief.md` (the R3 and R7/A6 rows, with change notes);
  - `supervisor_briefing.md`: the shock-time row is no longer a departure, and OQ-060 is removed;
  - `demo_walkthrough.md`, `configs/rules.yaml` and the demo config.
- `progress.md` and `ai_usage_log.md` keep their history unchanged.

### Next
Wait for Arnikan before committing.

## Team assumption on the first/second paddle tags; R8's one-zone inference removed (2026-10-19)

Not committed (on instruction).

### Decisions recorded
- **A-027 (the team: Ananth, Sanjeevan, Arnikan, 2026-10-19):** `first_paddle_taken` and
  `first_paddle_firmly_on_the_chest` mean the **apical** paddle, and `second_paddle_taken` the
  **sternal** paddle.
  - In every annotated video the apical paddle went first, and the models are trained on these
    labels.
  - The vocabulary and the CVAT mapping are unchanged.
  - **Untested risk:** it is unknown whether the models learned the paddle's appearance or its
    order. Only a reversed-order recording can tell.
- **D-116 (Arnikan):** R8 has no one-zone inference. One placement seen with the other zone out of
  view → Unable to Verify, `one_zone_in_view`. The number D-115 was already taken (the removal
  decision), so this is D-116.
  - It supersedes the inference part of D-013. D-015 and OQ-005 no longer apply.
  - The settings `inferred_fail_outcome` and `placement_match_window_seconds`, and the flag
    `inferred_fail_policy_undecided`, are removed. R8 no longer raises `contradictory`.

### Who reads the four tags, and how
"Time order" means the reader treats the tag as "whichever came first"; "identity" means it
treats it as the apical or sternal paddle.

| Reader | Tags read | Treated as | With a sternal-first learner (labels per A-027) |
|---|---|---|---|
| Context anchor `first_placement` (`rules/context.py`) | `first_paddle_placed` | time order ("the first placement") | the anchor is the **apical** placement, later than the real first one |
| R1 `_first_placement`, gel phase (`video_rules.py`) | `first_paddle_placed` (or the earliest per-paddle placement), else `first_paddle_taken` | time order | with tags only, the gel phase ends at the apical placement: gel put on between the sternal and apical placements counts as "before placement", so `after_placement` can be missed. With per-paddle placements it ends correctly at the sternal one |
| **R2** (`video_rules.py`) | `first_paddle_placed` vs `second_paddle_taken`; window `first_paddle_taken` → `second_paddle_taken` | time order | **Fail `taken_before_first_placed`**, even when the learner placed the sternal paddle before taking the apical (R2's own step done right). Run: sternal taken 3 s, apical taken 6 s, apical firm 9 s → "second paddle taken at 3 s, before the first was placed at 9 s". The mistake is really R8's, so it is double-counted. With no first-placement tag, the window is empty (the "first" was taken after the "second") → Unable to Verify |
| R3 (`video_rules.py`) | `paddles_firmly_on_chest`; `first_paddle_taken` as the start of the placement phase | both paddles (neither); time order for the window | the coverage window starts at the apical taken, later than the real start (only reached if the shock isn't an inference source) |
| R4, R5 | `paddles_firmly_on_chest` | both paddles (neither) | unaffected |
| R8 `_placement_phase` | starts at `first_paddle_taken`; ends at `paddles_firmly_on_chest`, else `second_paddle_taken` | time order | the phase starts at the apical taken (late) and may end at the sternal taken (early, even before it starts → whole recording) |
| R8 one-zone inference (**removed**, D-116) | `first_paddle_placed` | time order | apical zone only: the apical placement always matched the tag → **false Pass – Inferred** |
| R8 fallback `assume_first_taken_is_apical` (off) | `first_paddle_taken` | identity | consistent with A-027, but then it always says "apical first" (circular); stays off |
| Preparation counts (`prepare.py`, `engine.yaml`) | each tag counted (exactly 1; `paddles_firmly_on_chest` undecided) | neither | unaffected |
| **Step 9c** (`derive_paddle_placements.py`) | T1 = `first_paddle_firmly_on_the_chest` as "the earlier placement"; T2 = `paddles_firmly_on_chest` as an upper bound | time order (T1); both (T2) | **both zones in view:** the earlier (sternal) placement is far from T1 (the apical placement) → **no event for either paddle**, review issue `placement_disagrees_with_tag` (run: sternal frame 30, apical and T1 frame 60 → "the earlier placement (frame 30) is 30 frames from first_paddle_firmly_on_the_chest (frame 60)"). R8 then can't see the reversal: with both zones visible and no placement it is `placement_missing`. **Apical zone only:** the apical placement is kept (not earlier than T1 − 15); R8 now gives `one_zone_in_view` instead of the old false Pass – Inferred. **No T1:** no events unless the two are within the parallel window |
| Step 9d gel phase (`derive_gel_applications.py`) | T1, else the earliest 9c placement, else `first_paddle_taken` | time order | ends at the apical placement (late), as for R1 |
| Rule-engine audit (`audit_rule_engine_checks.py`) | `first_paddle_firmly_on_the_chest` (presence, `first_placement_tag_missing`); the gel-phase end | presence; time order | the information line is unaffected; the gel-hand check uses a late phase end |
| Ananth's scripts (`build_yolo_video_dataset.py`, `create_grouped_video_split.py`, `audit_cvat_backups.py`) | the tag labels as training events | identity (the models' labels, A-027) | not changed (not ours) |

**What this shows:** apart from R8's removed inference, the readers that matter are R2, R1 and
Steps 9c and 9d. They read "first" as time order, which A-027 says it isn't. For a sternal-first
learner:
- **R2** fails, double-counting R8's mistake;
- **9c** drops both derived placements (with a review issue), so R8 can't see the reversal;
- **R1 and 9d** may end the gel phase late.

None of these was changed; they need a decision.

### What was done
- **R8 (`rules/video_rules.py`):**
  - `_one_zone` now returns Unable to Verify with `one_zone_in_view`;
  - `_not_determinable` no longer depends on a first-placement time;
  - the both-zones path, `placement_missing`, the parallel placement and the fallback are
    unchanged.
- **Settings removed:** `inferred_fail_outcome` and `placement_match_window_seconds`, from
  `engine.yaml` and `rules/config.py`.
- **Output contract version 12:**
  - flag `inferred_fail_policy_undecided` removed and `one_zone_in_view` added;
  - `contradictory` comes from R4 only;
  - R8's `wrong_order` comes only from two observed placements.
- **Demo:** no scenario relied on the inference; all seven still match.

### Tests (677 → 676)
- **R8, the old one-zone inference tests replaced:**
  - apical zone only → Unable to Verify, `one_zone_in_view`, whatever the timing (before, at,
    after the tag);
  - **the circular case:** a sternal-first timeline (sternal taken 3 s, apical taken 6 s, apical
    firm and apical placed 9 s) with the apical zone only, which used to give Pass – Inferred, is
    now Unable to Verify;
  - sternal zone only;
  - no first-placement tag;
  - the inference settings are gone.
  - The zone-window tests now expect `one_zone_in_view`.
- **Config tests:** the undecided list, the policy values and the negative-window check updated
  for the removed settings.

Full suite: **676 tests run, all pass, 1 skipped** (charging sound). The demo matches all seven
expected results. The pipeline command exits with 0.

### Documents updated
- **Registers:** `assumptions.md` (A-027; the A-002 placeholder list); `decisions.md` (D-116; D-013
  and D-015 status lines); `open_questions.md` (OQ-005 closed; OQ-006 narrowed; OQ-018 note).
- **`decision_flow.yaml`:** P-015.
- **`pathways.md`:** the P-015 table; W-58 rewritten; W-59.
- **`diagrams.md`:** (f).
- **The rest:**
  - `anomalies.md`, `output_contract.md` (v12), `rules_status.md`, `camera_angle_evidence.md` (LL:
    R8 unverifiable);
  - `supervisor_briefing.md` (the R8 paragraph, the departures row, OQ-005 and OQ-006);
  - `demo_walkthrough.md` (limitations);
  - `agent_brief.md` (the R8 row and note, with change notes);
  - `implementation_plan.md` (the R8 logic section and placeholders), `upstream_requirements.md`;
  - `progress.md`, `ai_usage_log.md`.
- The vocabulary, the CVAT mapping and Ananth's files are unchanged.

### Open items for Arnikan
*All three resolved on 2026-10-19 by D-118 (see the next entry).*
- **R2 under A-027:** keep the time-order reading (a sternal-first learner also fails R2), or
  change R2?
- **Step 9c:** T1 is checked as "the earlier placement". Under A-027 it is the apical placement,
  so sternal-first videos lose both derived placements.
- **R1 and 9d:** the gel phase ends at the first-placement tag, which is the apical placement.

### Next
Wait for Arnikan. Nothing is committed.

## Paddle time order from event times: R2, Step 9c, R1/9d (2026-10-19)

The R8 and exporter-role changes were committed and pushed on instruction (3329e63). This change is
not committed.

### Decision recorded (Arnikan)
- **D-118:** tag names give paddle identity, never time order (A-027). It resolves the three open
  items of the previous entry.

### What was done
- **`paddle_order` in the procedure context (`rules/context.py`):** each paddle's take and firm
  placement, which paddle was taken first, the earliest firm placement, and whether it is certain.
  - **Apical placement:** the annotators' tag wins over the per-paddle placement. The sternal paddle
    has no tag.
  - **First taken:** a paddle placed before the other was taken counts as first even without its own
    take (as in P05_LL, whose apical take tag is missing). An exact tie counts as apical.
- **R2:**
  - the paddle taken first must be placed before the other is taken, whichever it is;
  - sternal taken first with no placement event → Unable to Verify, new flag
    **`placement_time_unknown`**;
  - apical taken first with its placement unseen keeps D-097;
  - a parallel placement fails R2 and R8 as before.
- **R1:**
  - the gel phase ends at the earliest firm placement of either paddle, else the earliest take;
  - if the other paddle's placement is unknown and could have been earlier, a Pass with gel after
    the earliest time that placement could be → Unable to Verify, `placement_time_unknown`.
- **Step 9c (`derive_paddle_placements.py`):**
  - T1 cross-checks only the apical placement (new setting `first_placement_tag_paddle`), never the
    order; an apical placement that disagrees with T1 is dropped alone;
  - method `paddle_in_zone_v2`;
  - the gate is unchanged, but the settings hash changes, so a review must name the new hash;
  - the validation report's T1 gap is now the apical paddle's.
- **Step 9d (`derive_gel_applications.py`):**
  - the gel phase ends at the earliest firm placement of either paddle (the T1 tag wins over the
    derived apical placement), else the earliest take of either paddle;
  - new setting `second_paddle_taken_tag`; the audit uses the same phase.
- **Output contract version 13:** the flag `placement_time_unknown`; the R2 and R1 meanings are
  order-neutral.

### Why Step 9c dropped both placements in a sternal-first video
In `_check_tags` (before), with T1 tagged and both paddles derived:
`earliest = min(p["first"] for p in derived)`; if `abs(earliest - t1) > window`, both paddles were
rejected with `placement_disagrees_with_tag`. T1 was taken as "the earlier placement". Under A-027
it is the apical placement, while the earliest placement of a sternal-first learner is the sternal
one, so the two always disagreed. The one-paddle branch had the same assumption: a placement
"earlier than T1 − 15" was rejected.

### Before/after comparison on the interim backups (data only under the gitignored data/rule_engine/d118/)
- **Source:** the "Complete sets" CVAT backups of the interim export (38 videos). Annotation JSON
  only; no media opened.
- **Runs:** the exporter and the audit before the change (HEAD 3329e63) and after it. The built
  rules were run with the demo config, with the gates closed and with both review gates simulated
  as approved (in memory only).

| Run | Rule results | Exporter (derived placements, gel phase, issues) | Audit |
|---|---|---|---|
| Real settings (`min_overlap_of_paddle` 0.5) | **identical** (0 differences, both gate states) | **identical** (0 derived placements before and after) | **identical** (issues and info) |
| Experimental `min_overlap_of_paddle` 0.1 (temporary config, not saved) | **identical** (0 differences, both gate states) | 20 → 27 derived placements (see below); 4 gel-phase ends moved | not run |

**What the experimental run shows:**
- **Placements now kept:** in 7 videos (P04_T, P05_T, P07_T, P14_LS, P14_T, P33_LS, P33_T) the
  apical placement disagreed with T1 by more than 15 frames. The old check dropped both paddles;
  now only the apical is dropped, and the sternal placement is kept. That is the intended fix.
- **Earlier gel-phase ends:** in 4 of them (P14_LS, P14_T, P33_LS, P33_T) the kept sternal placement
  is earlier than the apical tag, so the 9d gel phase ends earlier (for example P14_LS: frame 432 →
  367). In apical-first videos this suggests the low threshold picks up a sternal paddle near its
  zone before it is really placed.
- **A caught side effect:** an earlier draft let a derived apical placement override the apical
  tag. That changed R2 in P04_LL and P13_LL in the experimental run. The tag now wins for the
  apical paddle, and those differences are gone.

**Separate finding:** at the placeholder `min_overlap_of_paddle` of 0.5, Step 9c derives **no
placement in any of the 38 videos**. The best paddle-zone overlap reached is 0.29 (median 0.11),
so 9c's evidence for R8 (and R2's parallel placement) can't exist until that setting is tuned
(OQ-018).

### Tests (676 → 687)
- **`tests/test_rule_engine_paddle_order.py` (9):** sternal-first timelines:
  - one paddle at a time with gel before both → R2 Pass, R8 `wrong_order`, R1 Pass;
  - gel after the sternal placement but before the apical → R1 `after_placement`;
  - sternal placement unknown → R2 and R1 Unable to Verify, `placement_time_unknown`;
  - gel before the sternal take → certain;
  - a parallel placement fails R2 and R8;
  - the helper: order from times, tie, placed-before-take, certainty.
- **Step 9c:**
  - T1 cross-checks only the apical placement;
  - a sternal-first video keeps both placements;
  - a one-zone apical placement must match T1;
  - method v2;
  - the validation summary.
- **Step 9d:** the earliest placement of either paddle ends the gel phase; the apical tag wins over
  the derived apical placement; the earliest take of either paddle ends it otherwise.
- **R1 fixtures:** an explicit sternal take after the first placement (apical-first, certain).
- **R2:** the message for a missing take.

Full suite: **687 tests run, all pass, 1 skipped** (charging sound). The demo matches all seven
expected results. The pipeline command exits with 0.

### Documents updated
- **Registers:** `decisions.md` (D-118; D-051 and D-086 notes); `assumptions.md` (A-027 linked).
  The open items in the previous entry are marked resolved.
- **Logic:**
  - `decision_flow.yaml` (P-032, P-031, P-037, P-038);
  - `pathways.md` (the P-032, P-031, P-037 and P-038 tables; W-81 to W-83);
  - `diagrams.md` ((j) 9c, (n) 9d, (o) R1).
- **The rest:**
  - `anomalies.md`, `output_contract.md` (v13), `rules_status.md` (R1, R2);
  - `supervisor_briefing.md` (R2), `agent_brief.md` (the R2 row);
  - `configs/rule_engine/annotation_export.yaml` (two settings);
  - `progress.md`, `ai_usage_log.md`.
- The vocabulary, the CVAT labels and Ananth's files are unchanged. No exported records are
  committed.

### Next
Wait for Arnikan. Nothing is committed.

## D-118 review additions (2026-10-19)

Arnikan approved D-118 with additions. Committed and pushed on instruction (this entry is part of
the commit).

### Decisions (Arnikan)
- The apical tie-break stays, but both paddles taken within `simultaneous_window_seconds` fail R2
  `simultaneous`, whichever is named first.
- The deduced first take stays, and the result shows it with a flag.
- D-097 is kept, and the output contract stays at v13 (not released yet).

### What was done
- **R2:**
  - Both takes within the window → Fail `simultaneous`, before any order is judged
    (`_taken_together`).
  - A first take deduced from a placement → the result carries the new flag
    **`take_order_from_placement`**, and the reason explains the deduction.
- **`paddle_order`:**
  - New field `take_deduced`.
  - New property `gel_phase_end` (the earliest firm placement, else the earliest take). R1 now
    uses it.
- **Step 9d and the helper:** a test checks that both give the same gel-phase end on six synthetic
  timelines:
  - apical first;
  - sternal first;
  - sternal placement unknown;
  - the apical tag beats its 9c placement;
  - takes only;
  - nothing.
- **Step 9c finding recorded:** at `min_overlap_of_paddle` 0.5, no placement is derived in any of
  the 38 interim videos (highest share of a paddle box inside its zone 0.29, median 0.11).
  - On the annotations, R8 has no direct evidence and R2 can't detect a parallel placement.
  - The LS "direct" claim for R8 in `camera_angle_evidence.md` is corrected.
  - Linked to OQ-018.

### Effect on the interim backups (the rules rerun on the same export)
- **R2 code change:** in P14_LS, P14_T, P33_LS and P33_T, R2's code changes from
  `taken_before_first_placed` to `simultaneous`. The two takes are 0.06–0.47 s apart, so both
  paddles were taken together. The result is still a Fail.
- **New flag:** P05_LL's R2 Pass now carries `take_order_from_placement`.
- **Unchanged:** no other result changes, and no overall result changes, with the gates closed and
  simulated as approved.
- **Test fixture:** the R2 parallel-placement test had its takes 0.2 s apart. They are now
  0.64 s apart, so that test still checks the gate-closed path (D-097).

### Tests (687 → 692)
- **Taken together:** apical named first, sternal named first, an exact tie, and no placement seen
  all give `simultaneous`. Takes just outside the window are ordered.
- **Deduced take:** R2 carries the flag; there is no flag when both takes are tagged; the helper's
  `take_deduced`.
- **Step 9d against the helper:** the six timelines above.

### Documents updated
- **Decisions and questions:** `decisions.md` (D-118 review additions), `open_questions.md`
  (OQ-018).
- **Logic:** `decision_flow.yaml`, `pathways.md` (P-032).
- **Flags and contract:** `anomalies.md`, `output_contract.md` (v13).
- **Status and briefing:** `rules_status.md`, `supervisor_briefing.md`,
  `camera_angle_evidence.md`.
- **Logs:** `progress.md`, `ai_usage_log.md`.

### Not in this commit
The investigation of the overlap setting (report only; Arnikan decides the value).
