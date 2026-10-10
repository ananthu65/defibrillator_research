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
