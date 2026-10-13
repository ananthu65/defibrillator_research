# AI Usage Log: Rule Engine (Arnikan)

This log records how AI was used in my part of the ARTS project, what the AI produced, what I
decided, and how I evaluated and changed the AI's outputs. The project allows AI use up to
**Level 3 (AI Collaboration)** of the AI Assessment Scale (AIAS 2.1,
https://aiassessmentscale.com/): AI may help with idea generation, drafting, feedback and
refinement, and assessment covers both the work and how AI outputs are evaluated, modified and
integrated.

**Declared level for this work: Level 3 (AI Collaboration).**
*To confirm with the supervisor: that AI-drafted code, reviewed, directed and corrected by me,
falls within Level 3 for this project.*

## Tools used

| Tool | Where | Used for |
|---|---|---|
| Claude (Anthropic), claude.ai chat | Browser, with read access to the team Google Drive | Understanding the project, research, design discussion, drafting documents, reviewing the coding agent's plans and reports |
| Claude Code (Anthropic), coding agent | Local clone of the project repo | Repo inspection, implementation plan, environment setup, writing code, tests and docs for the rule engine |

## Data and privacy

- No video or audio recordings, frames or transcripts were shared with any AI tool. The
  recordings are medical data and are not uploaded to any cloud service.
- I chose not to use Google Colab for the Whisper work for the same reason; the department
  servers are the planned alternative.
- The AI read project documents in the team Google Drive (work allocation, annotation tracker,
  rule proposal, notes) and inspected the public GitHub repo. It first checked the repo history
  for recordings without downloading file contents; none were found.

## What AI did, and what I did

### Project understanding and research (chat)

| AI | Me |
|---|---|
| Summarised the project from the Drive documents: architecture, rules, team roles, my week 1 tasks | Directed which documents to read; corrected that I am responsible only for work under my name |
| Explained Whisper models, sizes and hardware requirements | Provided my laptop specs; raised the medical-data restriction that ruled out cloud GPUs |
| Researched the department GPU servers (CE FAQ pages) | Identified that I have Tesla access; decided to use department servers |
| Drafted Whisper transcription and comparison scripts | Not used yet; Whisper work paused until server access is confirmed. The repo already has a Whisper benchmark, which the team will align with |

### Repo inspection and design (chat)

| AI | Me |
|---|---|
| Inspected the repo: found the July rule engine in `legacy/`, the new `rules/` module assigned to me, and gaps against the rule proposal | Decided to continue in the restructured repo |
| Polished the wording of four additional rules | Supplied the rules; later refined gel (twice within an appropriate time period, order versus paddle placement not checked) and confirmed that any verbal command failure fails the procedure |
| Drafted the rule engine design plan (Claude Doc and Google Doc "ARTS Rule Engine: Design Plan") | Set the core principles: any mistake fails overall with no severity levels; every rule is always checked for feedback; rules are written by developers in Python; input, output and rule set must stay adaptable; Unable to Verify and unknown coverage stay undecided and configurable |
| Proposed severity levels and "Critical Error" in an early plan | Rejected: life-critical procedure, any mistake is a fail |
| Asked about multiple shocks, overall policy, per-paddle tags | Answered: always one shock; any Fail fails overall; explained the CVAT label set |
| Initially suggested assuming annotation timelines are fully covered | Rejected: coverage handling is not decided yet, so the design must not assume it |
| Discussed how to determine which paddle was placed first | **Originated the one-visible-zone inference for R8** (compare the visible zone's placement with the first placement), raised that placement order must come from video postprocessing, and asked who should own the inference (decided: rule engine, with observations from Ananth) |
| Drafted the coding agent brief (`agent_brief.md`) | Set the working method: small increments, a full explanation after each, no breaking of existing code, adaptability for input, output and rules |
| Drafted a message to Ananth and created the team message log (Google Sheet) | Added the request for placement order; decided to keep a message log |

### Coding agent: Step 0, Increment 0 and Increment 1

| AI (coding agent) | Me |
|---|---|
| Step 0: read the repo and wrote `implementation_plan.md` (27 increments) | Reviewed the plan with help from the chat; required separating display order from evaluation order (the plan would have rejected valid configs), approved the A7/A4 overlap handling, kept `configs/pipeline.yaml` untouched |
| Asked whether to generalise the shared 14-rule contract test | Decided against the AI's recommendation: update the count (14 → 16) whenever rules change, and log it |
| Increment 0: created `.venv`, installed requirements, created branch `feature/rule-engine` | Chose a virtual environment over installing into system Python; declined installing unrelated charging-sound packages |
| Increment 1: wrote `vocabulary.yaml`, `rules/vocabulary.py`, `rules/errors.py` and 30 tests | Rejected the name `compressions_command` (doesn't say which action); required action-specific command names following the proposal document, all provisional until the medical-faculty supervisor confirms them; supplied the real CVAT label `first_paddle_firmly_on_the_chest` |
| Updated the plan and brief for the R8 inference and wrote `upstream_requirements.md` | Approved: contradictory placement → Unable to Verify; inferred Fail → Unable to Verify until the policy is decided |
| Committed early increments itself | Changed the workflow: the agent no longer commits; I review and commit |
| Wrote the consolidated Increment 1 entry in `progress.md`, switched off Claude commit attribution in its user settings, and reported that `feature/rule-engine` is unpushed, with 3 commits carrying a Co-Authored-By line | Allowed the agent to commit again, with no Claude attribution and only after showing me the message; decided to disclose AI use in this log instead of in commits |
| Removed the Co-Authored-By trailer from the three earlier commits with `git filter-branch`, and verified that only the trailer changed | Decided to reword the unpushed commits; required a backup branch first and kept it for my own check |
| Increment 2: wrote `rules/config.py`, `engine.yaml`, the extended `rules.yaml` (R8, A8, A6 `same_as` R7, A7 dependencies, provenance records) and 43 tests; changed the shared contract test from 14 to 16 | Supplied the A8 record (5 s, provided by me, supervisor approval pending); the 14 → 16 change was my earlier decision; the agent's open questions are awaiting my review |
| Recorded the A8 approval, added "not used by any rule yet" notes to the unused limits, relaxed validation so an approver can be recorded without a date, and updated the tests | Reported the supervisor's (Dr. Senani Samarasinghe) approval of the A8 5 s limit, with the date unknown; kept the new limit names; decided to keep every unused parameter as null with a note rather than remove it |
| Increment 3: wrote `rules/prepare.py` (timeline validation, canonical mapping, per-source confidence filtering recorded as excluded events, anomalies for multiple shocks and mixed human/model evidence), `TimelineError`, and 22 tests | Asked for the next increment with a full what/how/why report; the agent's open questions (duplicate shock detections, mixed evidence, one camera per timeline) are awaiting my review |
| Increment 3 review: marked possible duplicate shocks, added rejection codes, a missing-threshold error, the `unknown_labels_present` warning, `excluded_named`, tests (31 total), `anomalies.md`, and the ownership and timeline-header sections in `upstream_requirements.md` | Held the Increment 3 commit until my review; decided: don't merge duplicate shocks (just mark them), keep mixed evidence as a flag, keep one camera and one task ID as a hard error, upstream owns duplicate merging and thresholds (the engine check is a safety net, 0 disables it); added the rules "low confidence is not absence" (Unable to Verify, never Fail), "unknown labels warn", "event time = start time", and "repeated events are kept"; requested the timeline header; raised supervisor questions on repeated gel, re-placed paddles and repeated button presses; asked for `anomalies.md` |
| Answered that the approval-date rule had been relaxed in `ddfa846`, and implemented the new rule with tests | Noticed the relaxed validation and set the rule: `approved_on` may be null only if the note says the date is to be confirmed |
| Increment 4: wrote `rules/coverage.py` (timeline header, coverage status per region, source and modality, missing-event outcomes), extended `engine.yaml` and `rules/config.py` with overrides and regions, 33 tests, and updates to `anomalies.md` and the plan | Specified what the increment must cover: region coverage, the header's `analyses_run` to tell "no audio events" from "audio not analysed", header-less timelines as unknown, low confidence → Unable to Verify (never Fail), every outcome configurable with unknown still undecided; the agent's open questions (time-windowed coverage, `analyses_run` for annotation timelines) are awaiting my review |
| Increment 4 review: replaced the note-text check with a `date_pending` field, added `duration_tolerance_seconds` (end-time check) and an optional `window` argument on `status()` and `missing()`, with tests (198 total) and doc updates; pointed out that `status()` had received only the event name, not a time | Held the commit until my review; rejected interpreting note text and required a structured `date_pending` flag; asked for a duration tolerance; decided annotation timelines declare `analyses_run: {video: true, audio: false}`, with `video: true` as a development assumption flagged `annotation_coverage_assumed`; decided no time windows now, but the interface must allow them later without rule changes |
| Increment 5: wrote `rules/context.py` (shock time with removal fallback, anchors, phases, zone visibility, command resolution, `elapsed()` carrying anchor flags), and found and closed a gap where low-confidence ambiguous commands were not treated as evidence; 29 tests, `anomalies.md` and plan updates | Specified four edge cases with tests: flag every timing result based on the removal fallback (`shock_time_from_removal`); leave commands near the shock or with no shock unresolved and flagged; use the earliest of several candidates and record them all; with multiple shocks, no shock time, nothing guessed. Asked to see the commit message first and not to push yet; the agent's open questions 18 and 19 are awaiting my review |
| Applied my answers to questions 18 and 19 in the context (with 10 tests); backfilled the documentation set (decisions, assumptions, open-questions register, `decision_flow.yaml`, pathways, rule status, methods, diagrams) from progress.md, the plan and the brief; wrote a consistency test between the docs and the code; proposed A-014 / OQ-039 | Answered question 18 (commands before removal stay unresolved under the fallback) and question 19 (the restart is the earliest start after the shock; earlier ones are an A7 sequence problem); specified the documentation set, its stable ID scheme (D/A/OQ/P), the audience (supervisor), the consistency test, and the new definition of done; review of the documentation is pending |
| Implemented D-053 in the context (an `ambiguous` list separate from `ineligible`, 3 new tests) and extended it to the no-shock-time case for consistency; added the "Also involves" column and regrouped the open questions by their clinical part; updated the decision flow, pathways (W-14) and diagrams (new e2) | Reviewed the documentation; rejected the agent's A-014 proposal (a start before the removal counted as a mistake) and decided D-053 (timing-ambiguous, not a mistake: Unable to Verify, not reported by A7); reassigned OQ-012 to the supervisor (approving the chest regions) with Ananth involved; set the rule that questions with a clinical part go in the supervisor section, and asked for every multi-stakeholder question to be checked |

## How I evaluated the AI's work

- Every plan and increment report was read before approval; the agent stops after each
  increment and explains what it did, how, the methods used, assumptions and open questions.
- File edits are approved manually rather than in automatic mode.
- I checked AI proposals against the project's rules and the team's decisions, and changed or
  rejected them where they didn't fit (examples in the tables above).
- The test suite and the pipeline command are run after every increment: baseline 48 tests,
  78 after Increment 1, all passing (1 test in another team member's area skipped locally).

## Limitations

- The rule engine code so far was written by the coding agent under my direction; my
  contribution is the clinical rules, the design decisions, the review and the corrections.
- Clinical values, command names and phrases are not decided by AI; they wait for the
  medical-faculty supervisor.
