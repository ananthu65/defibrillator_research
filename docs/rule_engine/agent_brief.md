# Rule Engine Build Brief (for the coding agent)

Read this whole file before doing anything. It is the source of truth for how the rule
engine should be designed and how you should work with me. If anything here conflicts with
what you find in the repo, stop and tell me rather than choosing for yourself.

I am Arnikan, owner of the `rules/` module in this repo. I want to understand every part of
what you build, so the way you report your work matters as much as the code.

---

## 1. What we are building

ARTS assesses a recorded defibrillation procedure on a training manikin. One video (from one
chosen camera angle) is processed separately by a video model and audio models. Their events
are merged by the pipeline into one timeline, the "procedure transcript". The **rule engine**
takes that timeline and evaluates it the way a human evaluator would: it checks every rule in
a set order and produces a result and reason for each rule, an evaluator-style checklist, and
one overall Pass or Fail.

**In scope (rule engine):** everything from receiving the merged timeline to producing rule
results, the overall result and the checklist.

**Out of scope (do not build or change):** audio extraction, transcription, command detection
(`audio/`), video models and event postprocessing (`video/`), timeline merging and
orchestration (`pipeline/`), feedback wording (`feedback/`), the app, and everything in
`legacy/`.

---

## 2. Things that are NOT fixed yet (design for change)

These three will change after the engine is built. The code must absorb each change in one
place, without rewriting rules:

1. **Input format.** The video and audio models are still being trained; their output format
   is undefined. During development we use timelines built from CVAT annotations.
2. **Output format.** The evaluator checklist format is undefined. It will resemble the rule
   list, but checklist items may not map one-to-one onto rules.
3. **Rule set.** New rules have already been added and more may come. Clinical values (time
   limits, accepted phrases) are still being approved by the supervisor.

---

## 3. Required architecture

A stable core between two adaptable edges, with every changeable value in config.

- **Input adapters (edge):** one adapter per source (annotation timeline now; video and audio
  model outputs later) that converts that source into the repo's shared event format
  (`schemas/event.py`). The core never sees source-specific formats.
- **Event vocabulary (config):** a mapping from every source label to one canonical event
  name (for example CVAT's `Gel applied` → `gel_applied`). A new label means one line here.
- **Validation and preparation (core):** check the timeline is valid, map names, flag
  anomalies (for example more than one shock).
- **Procedure context (core):** computed once and shared by all rules: shock time, procedure
  phases (before / after shock), stop and start command times, and evidence coverage (where
  audio was unclear or a region was not visible) when such information exists.
- **Rule registry and rules (core):** each rule is a small Python unit declaring its metadata
  (ID, evaluation order, checklist item, dependencies, required events) next to its logic.
  The engine discovers rules through a registry, so adding a rule needs no engine change.
  Rules share helper checks (presence, count, order, time limit, simultaneity, inference,
  dependency) instead of each reimplementing them.
- **Overall result policy (core, configurable):** see section 5.
- **Output renderers (edge):** turn the same results into the JSON report, the evaluator
  checklist (via a rule-to-checklist mapping in config) and the handover for `feedback/`.

Rules are written by developers in Python. Clinical values live in `configs/rules.yaml` with
who approved them and when. Unapproved values are `null`, and a rule with a `null` time limit
checks presence and order only, and says in its result that timing was not checked.

---

## 4. Rules to implement

Evaluation order follows the procedure and must be set in config, not hard-coded.
R8 and A8 are proposed IDs for the newly added rules. R7 and A6 are the same check: implement
once, report under both IDs.

| Order | Rule | Pass when | Depends on | Failure codes |
|---|---|---|---|---|
| 1 | R1 Gel applied twice | Two separate gel applications within the approved time period. Order relative to paddle placement is NOT checked. | Approved time period (null for now) | `missing`, `applied_once`, `outside_time_period` |
| 2 | R2 Second paddle after first is placed | First paddle taken → first paddle placed firmly → second paddle taken. "Taken" = first frame where it is clearly visible. | First paddle placement | `simultaneous`, `taken_before_first_placed`, `first_missing` |
| 3 | R8 Apical before sternal | Apical paddle placed before sternal paddle. Both zones visible: compare the two placement times (Pass – Direct or Fail). Only one zone visible: inferred from that zone's placement time vs `first_paddle_placed` (see `implementation_plan.md`, Increment 12) | Per-paddle placement events, first placement time, zone visibility | `wrong_order`, `simultaneous` |
| 4 | R3 Paddles firmly on chest | Both paddles stable in approved zones before shock; else Pass – Inferred if `shock_delivered_on_screen` OR `paddles_removed_after_shock` is confidently confirmed | Shock time | `not_in_zone`, `placed_after_shock` |
| 5 | R4 Both discharge buttons pressed | After placement, before shock; else Pass – Inferred as for R3 | Placement, shock time | `before_placement`, `not_pressed` |
| 6 | R5 Shock confirmed on screen | One new shock indication after the preceding steps | Preceding steps | `missing`, `wrong_order` |
| 7 | R6 Paddles removed after shock | Removal after the shock | Shock time | `removed_before_shock`, `missing` |
| 8 | A1 Oxygen away | Command before shock | Shock time | `missing`, `after_shock` |
| 9 | A2 Continue compressions | Command during preparation, before stop | Stop command | `missing`, `wrong_stage` |
| 10 | A3 All stand clear | Command before shock | Shock time | `missing`, `after_shock` |
| 11 | A4 Stop compressions | Command before shock, after continue | Shock time, continue command | `missing`, `after_shock`, `wrong_order` |
| 12 | A5 Shock command | Verbal shock command given before or at the shock | Shock time | `missing` |
| 13 | R7 / A6 Restart compressions promptly | Start/resume command after shock, within approved limit (null for now) | Shock time (R5, or R6 as fallback) | `missing`, `before_shock`, `too_late` |
| 14 | A7 Command sequence | O₂ away → continue → stand clear → stop → shock → start | All commands | `missing_command`, `wrong_order` |
| 15 | A8 Pre-shock pause | "Stop CPR" to "Start CPR" within **5 seconds** (approved) | Stop and start commands | `pre_shock_pause`, mistake label "Pre-Shock Pause" |

Notes:
- Shock-based inference (R5/R6 as used for R3/R4) never establishes order. R8 has its own
  one-visible-zone inference instead (updated 2026-10-10; see `implementation_plan.md`,
  Increment 12). The inference lives in the rule engine; upstream only reports what is visible.
- "Continue CPR" before the shock means continue compressions; after the shock it means
  restart. Classify by position relative to the shock.
- Every recording has exactly one shock. More than one is a data anomaly.

---

## 5. Decision policy

- **Any mistake fails the procedure.** No severity levels: a missed verbal command fails
  exactly like a missed gel application. Do not use `critical_error` to grade mistakes.
- **Every rule is always evaluated.** Never stop at the first failure; feedback needs all
  results.
- **One mistake is reported once.** If a rule cannot be judged because something it depends
  on is missing (for example, no confirmed shock), it reports "not evaluable because of X"
  rather than a second Fail.
- **Never blame the learner for missing data.** Fail only when evidence clearly shows the
  mistake. Missing or unclear evidence gives Unable to Verify.
- **Overall result:** any Fail → Fail. No Fail but at least one Unable to Verify → a
  configurable outcome (Fail or faculty review), **not decided yet**; make it one setting.
  All counted rules Pass (direct or inferred) → Pass.
- Prefer the existing statuses in `schemas/rule_result.py` (Unable to Verify can map to
  `unable_to_assess`). Propose a new status or field only if truly needed, and ask first.

---

## 6. Hard constraints

1. **Do not break existing code.** All existing tests must pass after every increment
   (`python -m unittest discover -s tests`), and `python -m pipeline.run --events
   tests/fixtures/sample_timeline.json` must still run.
2. **Stay in your lane.** Change only `rules/`, `configs/rules.yaml`, new config files for
   the rule engine, `tests/` (rule engine tests and fixtures) and rule engine docs. Do not
   touch `video/`, `audio/`, `pipeline/`, `feedback/`, `legacy/` or `annotation/` without
   asking me first.
3. **Shared schemas are shared.** `schemas/` belongs to the whole team and follows
   `docs/contracts.md`. Only optional, backward-compatible additions, and only after I
   approve each one, because Ananth and Sanjeevan depend on them.
4. **`rules/` must not import from `video/`, `audio/` or `legacy/`.**
5. **Never invent clinical values.** Anything not approved stays `null` and is listed as an
   open question.
6. **No new heavy dependencies.** Ask before adding any package.
7. **Git:** work on a feature branch (for example `feature/rule-engine`), one small commit
   per increment with a clear message. Never commit data, recordings or outputs.

---

## 7. How to work with me

### Step 0: inspect and plan (before writing any code)

1. Read `README.md`, `docs/team.md`, `docs/contracts.md`, `docs/reorganization.md`, and
   everything in `rules/`, `schemas/`, `configs/`, `annotation/to_timeline.py` and `tests/`.
2. Check the current event names: the CVAT labels (in `annotation/` code and reports), and
   the audio command names (in `audio/commands/`). In particular, find the names of the
   separate apical and sternal placement tags. If you cannot find them, put placeholders in
   the vocabulary and list them as open questions.
3. Write the implementation plan to `docs/rule_engine/implementation_plan.md`: a numbered
   list of small increments, each with its goal, the files it touches, the tests it adds,
   and anything it needs from me. Include where existing code already does part of the job
   and how you will extend it rather than replace it.
4. **Stop and wait for my approval.** Do not start coding until I say so.

A reasonable starting order (refine it after inspecting the repo):
event vocabulary → config format and validation → procedure context → shared checks →
rule registry and base rule → overall result policy → JSON report renderer → annotation
input adapter → rules one at a time (R2, R8, R5, R6, R3, R4, R1, A1–A5, R7/A6, A7, A8) →
full scenario test matrix → checklist renderer skeleton → documentation.

### Every increment

Keep each increment small enough that I can review it in one sitting. For each one:

1. Implement only that increment.
2. Add tests for it, including the edge cases that apply from section 8.
3. Run the full test suite and the pipeline command from section 6.
4. Commit.
5. **Stop and report** using the template below, then wait for me to say "continue". If I
   ask questions, answer them before moving on.

### Report template (use after every increment)

```
## Increment N: <name>

### What was done
Plain-language summary of what now exists that didn't before.

### How it was done
Each file added or changed, and what it does. Show the key code (short excerpts) and
explain it line by line where it isn't obvious.

### Methods and design choices
Patterns or techniques used (for example registry, adapter, dataclass) and why each
was chosen over the alternatives you considered.

### Assumptions
Every assumption made, and what would change if it turns out wrong.

### How it stays adaptable
Which future changes (input, output, rules, clinical values) this increment
prepares for, and where each change would be made.

### Tests
Tests added, what each checks, and the results of the full suite.

### Try it yourself
A command I can run to see it working.

### Open questions
Anything you need me or the team to decide.

### Next increment
What you propose to do next.
```

Write for someone who knows Python but did not write this code. If a concept may be new to
me, explain it briefly.

---

## 8. Situations every rule must handle (test matrix)

| Situation | Expected result |
|---|---|
| Event present, confident, correct order and timing | Pass – Direct |
| Event clearly absent while the area or audio is covered | Fail (`missing`) |
| Event absent while the area is hidden or audio unclear | Unable to Verify |
| Event below the confidence threshold | Not used as evidence; logged |
| Wrong order | Fail (`wrong_order`) |
| Two events inside the simultaneous window where order matters | Fail (`simultaneous`) |
| Approved time limit exceeded | Fail (`too_late` or the named mistake) |
| Time limit not yet approved (`null`) | Presence and order only; note timing not checked |
| Same event repeated | Any valid occurrence satisfies the rule |
| Required reference missing (no shock) | Not evaluable, pointing to the missing step |
| More than one shock | Data anomaly; shock-dependent rules Unable to Verify |
| No audio at all | All audio rules Unable to Verify |
| Contradictory evidence | Unable to Verify, flagged |
| Rule not approved | Reported as pending; not counted |
| Invalid config or malformed input | Clear error; no assessment produced |

Engineering values (confidence thresholds, simultaneous window, minimum gap between two gel
applications) are not decided. Make each one a config value with a clearly marked placeholder
default, and list it as an open question.

---

## 9. Open decisions (keep configurable, do not decide)

- Whether Unable to Verify means overall Fail or faculty review.
- Checklist format and its mapping to rules.
- The time period for the two gel applications (R1).
- Time limits for R7/A6, A4 and the other blanks.
- Final IDs for R8 and A8.
- Model output formats, confidence meaning, and coverage signals.
- Final camera angle.
