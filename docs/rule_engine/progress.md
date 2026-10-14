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
