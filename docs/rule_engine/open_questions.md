# Rule engine: open questions register

The **single register** of questions about the rule engine. **For the supervisor** comes
first, so that section can be printed for supervisor meetings.

- **Owner:** who must give the answer. **Also involves:** others who must contribute (for
  example, detection work for a clinically decided rule).
- **Grouping:** a question with a **clinical part** appears in the supervisor section, even
  when someone else owns its technical part. Every other question is grouped by owner.
- **Status:** `open`, `answered` (an answer exists and has become a decision), or `closed` (no
  longer relevant).
- **Answered questions stay here**, marked answered, so the history is kept.
- **"Old no."** is the number the question had before this register: `E-n` for
  implementation plan section E item n, `IncN-Qn` for an increment report in
  [progress.md](progress.md), `Brief §9` for the brief's open-decisions list.
- **Interim behaviour** is what the system does until the question is answered.
- **Links:** decisions are in [decisions.md](decisions.md) (D), assumptions in
  [assumptions.md](assumptions.md) (A), decision points in
  [decision_flow.yaml](decision_flow.yaml) and [pathways.md](pathways.md) (P).

## Summary

| ID | Old no. | Owner | Also involves | Status | Question (short) |
|---|---|---|---|---|---|
| OQ-002 | E-2 | supervisor | Arnikan | open | Overall result when some rules are Unable to Verify |
| OQ-005 | E-3a | supervisor | Arnikan | open | Does an inferred Fail count as Fail? |
| OQ-010 | E-4a | supervisor | Sanjeevan, Arnikan | open | Confirm the command names, accepted phrases and order |
| OQ-012 | E-6 | supervisor | Ananth | open | Approve the chest regions; evidence of a paddle outside its zone (R3) |
| OQ-013 | E-7 | supervisor | Arnikan | open | Which steps must precede the shock indication (R5)? |
| OQ-016 | E-9 | supervisor | Arnikan | open | Missing clinical time limits |
| OQ-021 | E-14a | supervisor | Ananth, Arnikan | open | Gel applied more than twice |
| OQ-022 | E-14b | supervisor | Ananth, Arnikan | open | Paddles lifted and placed again before the shock |
| OQ-023 | E-14c | supervisor | Ananth, Arnikan | open | Discharge buttons pressed more than once |
| OQ-001 | E-1 | team | supervisor | open | Final policy when coverage is unknown |
| OQ-006 | E-3b | team | supervisor | open | R8 placement-match window; is the apical-first fallback clinically acceptable? |
| OQ-036 | Brief §9 | team | supervisor | open | Evaluator checklist format and its mapping to rules |
| OQ-014 | E-8 | supervisor | Arnikan | answered | Approval of the A8 5-second limit |
| OQ-004 | E-3 | Ananth | Arnikan | open | Who produces per-paddle placement events? |
| OQ-017 | E-10 | Ananth | Arnikan | open | Pipeline to call the full rule-engine assessment |
| OQ-020 | E-13 | Ananth | Sanjeevan, Arnikan | open | Timeline header: can it be provided, in what format? |
| OQ-009 | E-4 | Sanjeevan | Arnikan | open | Missing audio command events |
| OQ-045 | new (2026-10-14) | Sanjeevan | Arnikan | open | Confirm the output contract's versioning rule |
| OQ-015 | E-8 | team | supervisor | open | Final IDs for R8 and A8 |
| OQ-018 | E-11 | team | Ananth, Sanjeevan, Arnikan | open | Engineering placeholder values |
| OQ-019 | E-12 | team | Ananth, Sanjeevan, Arnikan | open | Which side applies confidence thresholds? |
| OQ-037 | Brief §9 | team | Ananth, Sanjeevan | open | Model output formats and the meaning of confidence |
| OQ-038 | Brief §9 | team | Ananth | open | Final camera angle |
| OQ-007 | E-3c | Arnikan | — | open | Zone visibility for annotation timelines |
| OQ-008 | E-3d | Arnikan | — | open | Annotation label lists that drop the first-placement tag |
| OQ-044 | new (2026-10-14) | Arnikan | — | answered | Which timeline anomalies block an overall Pass, and where in the order? |
| OQ-043 | new (2026-10-14) | Arnikan | Ananth, Sanjeevan | answered | Registry check versus minimal test configs |
| OQ-042 | new (2026-10-13) | Arnikan | — | answered | Is a provided but unapproved time limit ignored or used? |
| OQ-040 | new (2026-10-13) | Arnikan | — | answered | R8 when a placement event is missing |
| OQ-041 | new (2026-10-13) | Arnikan | — | answered | R7/A6 and A8 under the removal fallback |
| OQ-003 | E-3 | Arnikan | — | answered | Real CVAT tag for "first paddle placed" |
| OQ-011 | E-5 | Arnikan | — | answered | A7/A4 overlap |
| OQ-024 | E-15 / Inc3-Q1 | Arnikan | — | answered | Merge duplicate shocks? |
| OQ-025 | E-15 / Inc3-Q2 | Arnikan | — | answered | Reject mixed human/model evidence? |
| OQ-026 | E-15 / Inc3-Q3 | Arnikan | — | answered | One camera and one recording as a hard error? |
| OQ-027 | E-16 | Arnikan | — | answered | Time-windowed coverage |
| OQ-028 | E-17 | Arnikan | — | answered | `analyses_run` for annotation timelines |
| OQ-029 | E-18 | Arnikan | — | answered | Commands between the real shock and removal |
| OQ-030 | E-19 | Arnikan | — | answered | Which start command counts as the restart |
| OQ-031 | Inc0-Q1 | Arnikan | — | answered | Install charging-sound packages locally? |
| OQ-032 | Inc1-Q3 | Arnikan | — | answered | Canonical names, one "compressions command" |
| OQ-033 | Inc2-Q1 | Arnikan | — | answered | Use a provided but unapproved clinical value? |
| OQ-034 | Inc2-Q2 | Arnikan | — | answered | New time-limit names |
| OQ-035 | Inc2-Q3 | Arnikan | — | answered | Keep the unused `charge_to_shock_seconds`? |
| OQ-039 | new (2026-10-13) | Arnikan | — | answered | Start command before removal under the fallback |

---

## For the supervisor

Questions the supervisor owns, then questions owned by others that have a clinical part.

### OQ-002 Overall result when some rules are "Unable to Verify"
- **Old no.:** E-2 · **Owner:** supervisor · **Also involves:** Arnikan (implements the policy)
  · **Raised:** 2026-10-10 · **Status:** open
- **Question:** If no rule fails, but the system could not verify one or more steps, should
  the overall result be **Fail** or **"faculty review"** (a faculty member checks the
  recording)?
- **Affects:** overall result (all rules); P-017.
- **Why it matters:** It decides whether gaps in the evidence ever fail a learner. It is a
  study-method decision.
- **Interim behaviour:** The overall policy is built (Increment 8). While
  `unable_to_verify_outcome` is undecided (D-042), such a case is reported as
  **`unable_to_verify`**, flagged `overall_policy_undecided`, and the explanation names the
  undecided setting. It is never reported as Pass.

### OQ-005 Does an inferred Fail count as Fail?
- **Old no.:** E-3a · **Owner:** supervisor · **Also involves:** Arnikan · **Raised:**
  2026-10-10 · **Status:** open
- **Question:** When only one placement zone is visible, R8 infers which paddle was placed
  first. If that inference says sternal came first (a mistake), should it fail the learner, or
  be reported as "Unable to Verify"?
- **Affects:** R8; P-015.
- **Why it matters:** An inferred mistake is less certain than an observed one.
- **Interim behaviour:** Reported as Unable to Verify, flagged
  `inferred_fail_policy_undecided` (D-015).

### OQ-010 Confirm the command names, accepted phrases and order
- **Old no.:** E-4a · **Owner:** supervisor · **Also involves:** Sanjeevan (phrase matching),
  Arnikan (vocabulary) · **Raised:** 2026-10-10 · **Status:** open
- **Question:** Please confirm the six commands (oxygen away, continue compressions, all stand
  clear, stop compressions, shock, start/resume compressions), their accepted wordings, and
  their required order.
- **Affects:** A1–A8, R7; P-003, P-011.
- **Why it matters:** Audio rules cannot give a reliable Pass or Fail until the accepted
  wording is approved.
- **Interim behaviour:** The names follow the proposal document and are marked provisional
  (D-017, A-003).

### OQ-012 Approve the chest regions; evidence of a paddle outside its zone (R3)
- **Old no.:** E-6 · **Owner:** supervisor (approving the chest regions) · **Also involves:**
  Ananth (detecting placement relative to the regions) · **Raised:** 2026-10-10 · **Status:**
  open
- **Question:** R3 fails with `not_in_zone` when a paddle is placed outside its approved zone.
  The supervisor approves the chest regions and what counts as a correct placement. Ananth then
  defines which video event shows a paddle outside its zone.
- **Affects:** R3; P-016.
- **Why it matters:** Without approved regions, R3 cannot judge where a paddle was placed. It
  can only judge whether it was placed.
- **Interim behaviour:** R3 cannot produce `not_in_zone` until the regions are approved and an
  event exists.

### OQ-013 Which steps must come before the shock indication (R5)?
- **Old no.:** E-7 · **Owner:** supervisor · **Also involves:** Arnikan · **Raised:**
  2026-10-10 · **Status:** open
- **Question:** R5 passes when a new shock indication appears "after the preceding steps".
  Which steps: paddle placement only, or placement and pressing both buttons?
- **Affects:** R5.
- **Why it matters:** It defines when R5 reports `wrong_order`.
- **Interim behaviour:** R5 is not built yet (Increment 13).

### OQ-016 Missing clinical time limits
- **Old no.:** E-9 · **Owner:** supervisor · **Also involves:** Arnikan (records them in config)
  · **Raised:** 2026-10-10 · **Status:** open
- **Question:** Please give the maximum times (in seconds) for:
  - **R1:** the period within which the two gel applications must happen;
  - **R7/A6:** shock → start/resume compressions command;
  - **A4:** stop-compressions command → shock;
  - **A5:** how long before the shock the verbal shock command may be given;
  - **R6:** shock → paddles removed (if any limit applies).
- **Affects:** R1, R6, R7/A6, A4, A5.
- **Why it matters:** Without a limit, these rules can check presence and order but not
  timing.
- **Interim behaviour:** Each limit is empty. The rule checks presence and order only, and says
  "timing not checked" (D-005).

### OQ-021 Gel applied more than twice
- **Old no.:** E-14a · **Owner:** supervisor · **Also involves:** Ananth (detects each
  application), Arnikan · **Raised:** 2026-10-10 · **Status:** open
- **Question:** If gel is applied three or more times, is that a Fail, or does "at least twice"
  pass?
- **Affects:** R1.
- **Interim behaviour:** R1 is not built yet (Increment 17). Every application is kept (D-012).

### OQ-022 Paddles lifted and placed again before the shock
- **Old no.:** E-14b · **Owner:** supervisor · **Also involves:** Ananth (detects re-placement),
  Arnikan · **Raised:** 2026-10-10 · **Status:** open
- **Question:** If a paddle is lifted and placed again before the shock, is that acceptable or a
  mistake? Which placement counts for R2, R3 and R8?
- **Affects:** R2, R3, R8; P-012.
- **Interim behaviour:** The earliest placement is used as the key time, and all placements are
  recorded and flagged `multiple_candidates` (D-040).

### OQ-023 Discharge buttons pressed more than once
- **Old no.:** E-14c · **Owner:** supervisor · **Also involves:** Ananth (detects each press),
  Arnikan · **Raised:** 2026-10-10 · **Status:** open
- **Question:** If both buttons are pressed more than once, is that acceptable or a mistake?
  Which press counts for R4?
- **Affects:** R4.
- **Interim behaviour:** R4 is not built yet (Increment 16). Every press is kept (D-012).

### OQ-001 Final policy when coverage is unknown
- **Old no.:** E-1 · **Owner:** team · **Also involves:** supervisor (whether unverifiable
  evidence may count against a learner is an assessment-policy question) · **Raised:**
  2026-10-10 · **Status:** open
- **Question:** When it is unknown whether an event could have been observed (for example, no
  information on whether the audio was analysed), should a missing event be a Fail or Unable
  to Verify?
- **Affects:** all rules; P-008.
- **Interim behaviour:** Unable to Verify, flagged `coverage_policy_undecided` (D-008).

### OQ-006 R8 placement-match window; is the apical-first fallback clinically acceptable?
- **Old no.:** E-3b · **Owner:** team (the window value, from pilot validation) · **Also
  involves:** supervisor (whether "the first paddle taken is the apical one" is acceptable as a
  last-resort assumption) · **Raised:** 2026-10-10 · **Status:** open
- **Question:** How close (in seconds) must the visible paddle's placement be to the first
  placement to count as "the same time"? And should the "first paddle taken is apical"
  fallback ever be switched on?
- **Affects:** R8; P-015.
- **Interim behaviour:** 0.5 s (placeholder, A-002). The fallback is off (D-014).

### OQ-036 Evaluator checklist format and its mapping to rules
- **Old no.:** Brief §9 · **Owner:** team · **Also involves:** supervisor (the checklist mirrors
  the faculty's evaluation rubric) · **Raised:** 2026-10-10 · **Status:** open
- **Question:** What does the evaluator checklist look like, and which rules feed each item?
- **Affects:** P-018; Increment 25.
- **Interim behaviour:** A one-item-per-rule placeholder mapping (planned).

### OQ-014 Approval of the A8 5-second limit — *answered*
- **Old no.:** E-8 · **Owner:** supervisor · **Also involves:** Arnikan · **Raised:**
  2026-10-10 · **Status:** answered
- **Question:** Is the 5-second limit from "Stop CPR" to "Start CPR" approved?
- **Answer:** Yes, approved by Dr. Senani Samarasinghe. The approval date is to be confirmed.
- **Answered:** 2026-10-10 → **D-016**.

---

## For Ananth (video and pipeline)

### OQ-004 Who produces per-paddle placement events?
- **Old no.:** E-3 · **Owner:** Ananth · **Also involves:** Arnikan (vocabulary names) ·
  **Raised:** 2026-10-10 · **Status:** open
- **Question:** How will video postprocessing produce `apical_paddle_placed` and
  `sternal_paddle_placed`? CVAT has no per-paddle placement tags.
- **Affects:** R8, R3; P-003, P-015.
- **Interim behaviour:** These names are placeholders. Without them, R8 is Unable to Verify.

### OQ-017 Pipeline to call the full rule-engine assessment
- **Old no.:** E-10 · **Owner:** Ananth · **Also involves:** Arnikan (provides the function) ·
  **Raised:** 2026-10-10 · **Status:** open
- **Question:** The pipeline report shows the overall result and checklist only if
  `pipeline/run.py` calls the rule engine's full assessment function. Can this be added once
  that function exists (Increment 9)?
- **Affects:** all rules; P-017, P-018.
- **Interim behaviour:** The pipeline report lists the individual rule results only.
- **Update 2026-10-14:** The function exists (Increment 9). The call is
  `rules.render.report(rules.engine.assess(events, config))`, which returns the report described
  in [output_contract.md](output_contract.md) (P-027). Until the pipeline calls it,
  `python -m rules.run` produces the same report.

### OQ-020 Timeline header: can it be provided, and in what format?
- **Old no.:** E-13 · **Owner:** Ananth · **Also involves:** Sanjeevan (whether audio analysis
  ran), Arnikan · **Raised:** 2026-10-10 · **Status:** open
- **Question:** Can the pipeline send, with each timeline, the recording ID, camera angle,
  duration and which analyses ran? See [upstream_requirements.md](upstream_requirements.md).
- **Affects:** all rules; P-006, P-007, P-008.
- **Why it matters:** Without it, "no audio events" cannot be told apart from "audio analysis
  didn't run".
- **Interim behaviour:** No header means coverage is unknown, so missing events give Unable to
  Verify (D-008, D-009).

---

## For Sanjeevan (audio and feedback)

### OQ-009 Missing audio command events
- **Old no.:** E-4 · **Owner:** Sanjeevan · **Also involves:** Arnikan (vocabulary). The
  clinical part, the accepted wording, is OQ-010. · **Raised:** 2026-10-10 · **Status:** open
- **Question:** Audio command detection currently emits only oxygen away, stand clear and
  resume compressions. It needs continue, stop, shock and start too, and "continue
  compressions" is currently matched as "resume".
- **Affects:** A2, A4, A5, R7/A6, A7, A8; P-003, P-011.
- **Interim behaviour:** Placeholder names are ready in the vocabulary. Ambiguous "resume"
  commands are resolved by their position relative to the shock (P-011).

### OQ-045 Confirm the output contract's versioning rule
- **Old no.:** new (2026-10-14) · **Owner:** Sanjeevan · **Also involves:** Arnikan (rule
  engine) · **Raised:** 2026-10-14 · **Status:** open
- **Question:** The feedback module is built against [output_contract.md](output_contract.md).
  Is this versioning rule what Sanjeevan needs? The version goes up whenever a report field or
  code is added, removed or renamed, or its meaning changes. A code already listed as planned
  becoming built does not change the version.
- **Affects:** P-027; the feedback module and app.
- **Interim behaviour:** D-070 is applied as written and stays interim until Sanjeevan confirms.

---

## For the team

### OQ-015 Final IDs for R8 and A8
- **Old no.:** E-8 · **Owner:** team · **Also involves:** supervisor (naming in the faculty
  rubric; not a clinical question) · **Raised:** 2026-10-10 · **Status:** open
- **Question:** R8 and A8 are proposed IDs. What are the final ones?
- **Affects:** R8, A8.
- **Interim behaviour:** The proposed IDs are used.

### OQ-018 Engineering placeholder values
- **Old no.:** E-11 · **Owner:** team · **Also involves:** Ananth (video thresholds), Sanjeevan
  (audio thresholds), Arnikan (rule-engine windows and tolerances) · **Raised:** 2026-10-10 ·
  **Status:** open
- **Question:** Choose the confidence thresholds, simultaneous window, gel minimum gap, R8
  placement-match window and duration tolerance from pilot validation.
- **Affects:** P-004, P-005, P-006, P-011, P-015; R1, R2, R8.
- **Interim behaviour:** The placeholder values in A-002.

### OQ-019 Which side applies confidence thresholds?
- **Old no.:** E-12 · **Owner:** team · **Also involves:** Ananth, Sanjeevan, Arnikan ·
  **Raised:** 2026-10-10 · **Status:** open
- **Question:** Should thresholds be applied upstream, in the rule engine, or both with the same
  values, so they are not applied twice with different values?
- **Affects:** P-004.
- **Interim behaviour:** The rule engine applies its placeholder thresholds as a safety check;
  0 disables it (D-021).

### OQ-037 Model output formats and the meaning of confidence
- **Old no.:** Brief §9 · **Owner:** team · **Also involves:** Ananth (video), Sanjeevan
  (audio) · **Raised:** 2026-10-10 · **Status:** open
- **Question:** What exactly will the video and audio models send, what does their confidence
  mean, and what coverage signals will they provide?
- **Affects:** P-001, P-004, P-007.
- **Interim behaviour:** Development uses annotation timelines. Model adapters are added when
  the formats are known.

### OQ-038 Final camera angle
- **Old no.:** Brief §9 · **Owner:** team · **Also involves:** Ananth (models are trained per
  angle) · **Raised:** 2026-10-10 · **Status:** open
- **Question:** Which camera angle will the final system use?
- **Affects:** R8 (zone visibility), all video rules.
- **Interim behaviour:** Any single angle is accepted; mixing angles is rejected (D-032).

---

## For Arnikan (rule engine and annotation)

### OQ-007 Zone visibility for annotation timelines
- **Old no.:** E-3c · **Owner:** Arnikan · **Also involves:** — · **Raised:** 2026-10-10 ·
  **Status:** open
- **Question:** `events.jsonl` has no zone tracks. Should zone flags be added to it (in
  `annotation/build_yolo_video_dataset.py`), or supplied as a separate per-task file?
- **Affects:** R8; P-001, P-007.
- **Interim behaviour:** Zone coverage is unknown.

### OQ-008 Annotation label lists that drop the first-placement tag
- **Old no.:** E-3d · **Owner:** Arnikan · **Also involves:** — · **Raised:** 2026-10-10 ·
  **Status:** open
- **Question:** `first_paddle_firmly_on_the_chest` must be added to the label lists in
  `build_yolo_video_dataset.py` and `create_grouped_video_split.py`, not only the audit list.
  Otherwise `events.jsonl` drops it.
- **Affects:** R2, R8; P-003.
- **Interim behaviour:** The tag is missing from annotation timelines, so the first-placement
  key time is absent.

### OQ-044 Which timeline anomalies block an overall Pass, and where in the order? — *answered*
- **Old no.:** new (2026-10-14) · **Owner:** Arnikan · **Raised:** 2026-10-14 · **Status:**
  answered
- **Question:**
  - **(a)** Which timeline-level anomalies should prevent an overall Pass?
  - **(b)** Should the anomaly be checked in the Incomplete step, before the Unable-to-Verify
    setting, or only at the very end?
- **Answer:**
  - **(a)** All three: `unknown_labels_present`, `multiple_shocks`, `mixed_evidence_sources`.
  - **(b)** Keep it before the Unable-to-Verify setting. Otherwise, if that setting is later
    decided as Fail, a data problem such as two shocks could fail a learner.
- **Answered:** 2026-10-14 → **D-069**.

### OQ-043 Registry check versus minimal test configs — *answered*
- **Old no.:** new (2026-10-14) · **Owner:** Arnikan · **Also involves:** Ananth, Sanjeevan ·
  **Raised:** 2026-10-14 · **Status:** answered
- **Question:** Once the real rules are registered, the check "a registered rule ID must be in
  `rules.yaml`" would fail every test that assesses with a small custom config. How should it
  work?
- **Answer:** Always check registered rule IDs against the full catalogue in
  `configs/rules.yaml`, whatever config is being assessed. A smaller config only decides which
  rules are evaluated; registered rules outside it are simply not run, and that is not an error.
  (The agent's proposal, to check only when the config path is `configs/rules.yaml`, was
  replaced by this.)
- **Answered:** 2026-10-14 → **D-064**.

### OQ-042 Is a provided but unapproved time limit ignored or used? — *answered*
- **Old no.:** new (2026-10-13) · **Owner:** Arnikan · **Raised:** 2026-10-13 · **Status:**
  answered
- **Question:** If a time limit in `rules.yaml` has a value but no approver, should rules
  ignore it (timing not checked) or use it with a flag?
- **Answer:** Ignore it, flagged `limit_not_approved` (as built). Unchecked timing then makes
  the overall result incomplete (D-062).
- **Answered:** 2026-10-14 → **D-061**.

### OQ-040 R8 when a placement event is missing — *answered*
- **Old no.:** new (2026-10-13) · **Owner:** Arnikan · **Raised:** 2026-10-13 · **Status:**
  answered
- **Question:** What should R8 give when (a) the visible zone's paddle has no placement event,
  or (b) both zones are visible but one paddle's placement event is missing?
- **Answer:** The proposal was approved. In both cases: Unable to Verify, flagged
  `placement_missing`, with no inference, and R3 reports the missing placement.
- **Answered:** 2026-10-13 → **D-058**.

### OQ-041 R7/A6 and A8 under the removal fallback — *answered*
- **Old no.:** new (2026-10-13) · **Owner:** Arnikan · **Raised:** 2026-10-13 · **Status:**
  answered
- **Question:** Under the removal fallback with no ambiguous start, is a start after the removal
  definitely the restart? Is A8's stop → restart measured without the fallback flag? Is R7/A6 a
  Fail `too_late` when the delay from the removal already exceeds the limit, and Unable to
  Verify otherwise? Should an unresolved "resume" before the removal also make the restart
  ambiguous?
- **Answer:** Yes to all; the agent's addition (the unresolved resume) was approved too.
- **Answered:** 2026-10-13 → **D-059**.

### OQ-039 Start command before the removal under the fallback — *answered*
- **Old no.:** new (2026-10-13) · **Owner:** Arnikan · **Raised:** 2026-10-13 · **Status:**
  answered
- **Question:** When the shock time comes from paddle removal, should an explicit "start
  compressions" said before the removal be treated as before the shock (a mistake)?
- **Answer:** No. It is timing-ambiguous (the real shock was at an unknown earlier time). It is
  not counted as the restart and not treated as a mistake, and is flagged
  `command_before_removal`. R7/A6 and A8 give Unable to Verify, and A7 does not report it. The
  agent's proposal (A-014, as first written) was rejected.
- **Answered:** 2026-10-13 → **D-053**.

### OQ-003 Real CVAT tag for "first paddle placed" — *answered*
- **Old no.:** E-3 · **Raised:** 2026-10-10 · **Status:** answered
- **Answer:** `first_paddle_firmly_on_the_chest`. No separate apical or sternal tags exist.
- **Answered:** 2026-10-10 → **D-047**.

### OQ-011 A7/A4 overlap — *answered*
- **Old no.:** E-5 · **Raised:** 2026-10-10 · **Status:** answered
- **Answer:** A7 checks order only; A4 owns stop-before-continue.
- **Answered:** 2026-10-10 → **D-027**.

### OQ-024 Merge duplicate shocks? — *answered*
- **Old no.:** E-15 / Inc3-Q1 · **Raised:** 2026-10-10 · **Status:** answered
- **Answer:** No. Mark them as "possibly the same shock detected twice".
- **Answered:** 2026-10-10 → **D-030**.

### OQ-025 Reject mixed human/model evidence? — *answered*
- **Old no.:** E-15 / Inc3-Q2 · **Raised:** 2026-10-10 · **Status:** answered
- **Answer:** No; keep it as a flag.
- **Answered:** 2026-10-10 → **D-031**.

### OQ-026 One camera and one recording as a hard error? — *answered*
- **Old no.:** E-15 / Inc3-Q3 · **Raised:** 2026-10-10 · **Status:** answered
- **Answer:** Yes. Events with no angle do not count as a second angle.
- **Answered:** 2026-10-10 → **D-032**.

### OQ-027 Time-windowed coverage — *answered*
- **Old no.:** E-16 · **Raised:** 2026-10-13 · **Status:** answered
- **Answer:** No time windows now. The interface allows them later without rule changes.
- **Answered:** 2026-10-13 → **D-036**.

### OQ-028 `analyses_run` for annotation timelines — *answered*
- **Old no.:** E-17 · **Raised:** 2026-10-13 · **Status:** answered
- **Answer:** `{video: true, audio: false}`, with video as a development assumption, flagged
  `annotation_coverage_assumed`.
- **Answered:** 2026-10-13 → **D-035**.

### OQ-029 Commands between the real shock and removal — *answered*
- **Old no.:** E-18 · **Raised:** 2026-10-13 · **Status:** answered
- **Answer:** Under the removal fallback, every resume command before the removal stays
  unresolved, flagged.
- **Answered:** 2026-10-13 → **D-024**.

### OQ-030 Which start command counts as the restart — *answered*
- **Old no.:** E-19 · **Raised:** 2026-10-13 · **Status:** answered
- **Answer:** The earliest start command after the shock. Earlier ones don't count, and A7
  reports them, when the shock is confirmed on screen (refined by D-053).
- **Answered:** 2026-10-13 → **D-025**.

### OQ-031 Install charging-sound packages locally? — *answered*
- **Old no.:** Inc0-Q1 · **Raised:** 2026-10-10 · **Status:** answered
- **Answer:** No; CI runs that test.
- **Answered:** 2026-10-10 → **D-048**.

### OQ-032 Canonical names, one "compressions command" — *answered*
- **Old no.:** Inc1-Q3 · **Raised:** 2026-10-10 · **Status:** answered
- **Answer:** Use action-specific names following the proposal, all provisional.
- **Answered:** 2026-10-10 → **D-017**.

### OQ-033 Use a provided but unapproved clinical value? — *answered*
- **Old no.:** Inc2-Q1 · **Raised:** 2026-10-10 · **Status:** answered
- **Answer:** No longer relevant: the only such value (A8, 5 s) was approved.
- **Answered:** 2026-10-10 → **D-016**.

### OQ-034 New time-limit names — *answered*
- **Old no.:** Inc2-Q2 · **Raised:** 2026-10-10 · **Status:** answered
- **Answer:** Keep them.
- **Answered:** 2026-10-10 → **D-037**.

### OQ-035 Keep the unused `charge_to_shock_seconds`? — *answered*
- **Old no.:** Inc2-Q3 · **Raised:** 2026-10-10 · **Status:** answered
- **Answer:** Keep it, and every other unused limit, empty with a note.
- **Answered:** 2026-10-10 → **D-037**.
