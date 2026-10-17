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
| OQ-057 | new (2026-10-17) | supervisor | Arnikan | open | No shock time without the screen (supersedes the proposal's A6 clause) |
| OQ-059 | new (2026-10-17) | supervisor | Arnikan, Sanjeevan | open | Does a parallel placement count as one mistake or two? |
| OQ-060 | new (2026-10-17) | supervisor | Arnikan | open | Should paddle removal still support an inferred Pass for R3 and R4? |
| OQ-061 | new (2026-10-17) | supervisor | Arnikan | open | Should either inference source apply when the direct evidence was visible but absent? |
| OQ-001 | E-1 | team | supervisor | open | Final policy when coverage is unknown |
| OQ-006 | E-3b | team | supervisor | open | R8 placement-match window; is the apical-first fallback clinically acceptable? |
| OQ-036 | Brief §9 | team | supervisor | open | Evaluator checklist format and its mapping to rules |
| OQ-014 | E-8 | supervisor | Arnikan | answered | Approval of the A8 5-second limit |
| OQ-004 | E-3 | Ananth | Arnikan | open | Who produces per-paddle placement events? |
| OQ-017 | E-10 | Ananth | Arnikan | open | Pipeline to call the full rule-engine assessment |
| OQ-020 | E-13 | Ananth | Sanjeevan, Arnikan | open | Timeline header: can it be provided, in what format? |
| OQ-053 | new (2026-10-16) | Ananth | Arnikan, Sanjeevan | open | Are the converted videos constant frame rate? |
| OQ-054 | new (2026-10-16) | Ananth | Arnikan | open | When will the final export be available? |
| OQ-055 | new (2026-10-16) | Ananth | Arnikan | open | Does anything take the camera view from the backup file name? |
| OQ-009 | E-4 | Sanjeevan | Arnikan | open | Missing audio command events |
| OQ-045 | new (2026-10-14) | Sanjeevan | Arnikan | open | Confirm the output contract's versioning rule |
| OQ-015 | E-8 | team | supervisor | open | Final IDs for R8 and A8 |
| OQ-018 | E-11 | team | Ananth, Sanjeevan, Arnikan | open | Engineering placeholder values |
| OQ-019 | E-12 | team | Ananth, Sanjeevan, Arnikan | open | Which side applies confidence thresholds? |
| OQ-037 | Brief §9 | team | Ananth, Sanjeevan | open | Model output formats and the meaning of confidence |
| OQ-038 | Brief §9 | team | Ananth | open | Final camera angle |
| OQ-007 | E-3c | Arnikan | — | answered | Zone visibility for annotation timelines |
| OQ-008 | E-3d | Arnikan | — | answered | Annotation label lists that drop the first-placement tag |
| OQ-046 | new (2026-10-14) | Arnikan | — | answered | Do count anomalies block an overall Pass? Zero found = missing? |
| OQ-047 | new (2026-10-14) | Arnikan | — | answered | Where does the exporter get each video's fps? |
| OQ-048 | new (2026-10-14) | Arnikan | — | answered | Usual zone pattern: computed or configured? |
| OQ-049 | new (2026-10-14) | Arnikan | — | answered | Output folders of the exporter and the audit |
| OQ-050 | new (2026-10-14) | Arnikan | — | answered | Reuse the existing scripts by import, or copy their helpers? |
| OQ-051 | new (2026-10-14) | Arnikan | — | answered | A zone track that is never visible |
| OQ-052 | new (2026-10-14) | Arnikan | — | answered | Derived placements: settings, evidence type, disagreement with tags |
| OQ-056 | new (2026-10-16) | Arnikan | — | answered | Is possible_parallel_placement alone enough for a Fail? |
| OQ-058 | new (2026-10-17) | Arnikan | — | answered | R2 in a parallel placement before the gate is approved |
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
- **Affects:** R3; P-016, P-035.
- **Why it matters:** Without approved regions, R3 cannot judge where a paddle was placed. It
  can only judge whether it was placed.
- **Interim behaviour:** R3 cannot produce `not_in_zone` until the regions are approved and an
  event exists. R3 (built in Increment 15) checks placement timing and presence only (D-106).

### OQ-013 Which steps must come before the shock indication (R5)?
- **Old no.:** E-7 · **Owner:** supervisor · **Also involves:** Arnikan · **Raised:**
  2026-10-10 · **Status:** open
- **Question:** R5 passes when a new shock indication appears "after the preceding steps".
  Which steps: paddle placement only, or placement and pressing both buttons?
- **Affects:** R5.
- **Why it matters:** It defines when R5 reports `wrong_order`.
- **Interim behaviour:** The answer goes into `configs/rules.yaml` R5
  `parameters.preceding_steps` (D-100), which is unset for now. R5 (built in Increment 13)
  checks the shock's presence only and flags `order_not_checked`, so the overall result cannot be
  Pass. Once set, a shock before an observed step is `wrong_order`.

### OQ-016 Missing clinical time limits
- **Old no.:** E-9 · **Owner:** supervisor · **Also involves:** Arnikan (records them in config)
  · **Raised:** 2026-10-10 · **Status:** open
- **Question:** Please give the maximum times (in seconds) for:
  - **R1:** the period within which the two gel applications (one per zone, D-110) must happen;
  - **R7/A6:** shock → start/resume compressions command;
  - **A4:** stop-compressions command → shock;
  - **A5:** how long before the shock the verbal shock command may be given;
  - **R6:** shock → paddles removed (if any limit applies);
  - **A1, A3:** whether the oxygen-away and stand-clear commands must come within some time
    before the shock.
- **The answer may be "no limit".** That is recorded as a decision too (`no_limit: true`, with
  the approver), and the rule then checks presence and order and passes fully (D-103).
- **Affects:** R1, R6, R7/A6, A4, A5, A1, A3.
- **Why it matters:** Without a limit, these rules can check presence and order but not
  timing.
- **Interim behaviour:** Each limit is empty. The rule checks presence and order only, and says
  "timing not checked" (D-005), which keeps the overall result from being Pass (D-062).

### OQ-021 Gel applied more than twice
- **Old no.:** E-14a · **Owner:** supervisor · **Also involves:** Ananth (detects each
  application), Arnikan · **Raised:** 2026-10-10 · **Status:** open
- **Question:** If gel is applied three or more times, is that a Fail, or does "at least twice"
  pass?
- **Affects:** R1.
- **Interim behaviour:** R1 (built in Increment 17) passes with more than two applications; 9d
  counts separate visits to a zone separately (D-111, D-113). Every application is kept (D-012).
  The counts of `gel_applied`, `apical_gel_applied` and `sternal_gel_applied` are undecided, so
  repeated gel is not checked as a count (D-071).

### OQ-022 Paddles lifted and placed again before the shock
- **Old no.:** E-14b · **Owner:** supervisor · **Also involves:** Ananth (detects re-placement),
  Arnikan · **Raised:** 2026-10-10 · **Status:** open
- **Question:** If a paddle is lifted and placed again before the shock, is that acceptable or a
  mistake? Which placement counts for R2, R3 and R8?
- **Affects:** R2, R3, R8; P-012.
- **Interim behaviour:** The earliest placement is used as the key time, and all placements are
  recorded and flagged `multiple_candidates` (D-040). The placement events are expected exactly
  once (placeholder), so a second placement also raises `count_violation`, never a Fail by itself;
  `paddles_firmly_on_chest` is undecided and not checked (D-071).

### OQ-023 Discharge buttons pressed more than once
- **Old no.:** E-14c · **Owner:** supervisor · **Also involves:** Ananth (detects each press),
  Arnikan · **Raised:** 2026-10-10 · **Status:** open
- **Question:** If both buttons are pressed more than once, is that acceptable or a mistake?
  Which press counts for R4?
- **Affects:** R4.
- **Interim behaviour:** R4 (built in Increment 16) accepts any valid press (D-012, D-108). Every press is kept.
  `expected_counts.both_paddle_buttons_pressed` is undecided, so repeated presses are not checked
  as a count (D-071).

### OQ-057 No shock time without the screen (supersedes the proposal's A6 clause)
- **Old no.:** new (2026-10-17) · **Owner:** supervisor · **Also involves:** Arnikan (to mention
  it) · **Raised:** 2026-10-17 · **Status:** open
- **Question:** The rule engine now takes the shock time only from the shock seen on the
  defibrillator screen, and never infers it from paddle removal (D-093). This supersedes the A6
  clause of the proposal. In a view without the screen, every shock-dependent rule is therefore
  Not evaluable. Is the supervisor content with this?
- **Affects:** R6, R7/A6, A1–A8; the choice of camera angle (OQ-038).
- **Interim behaviour:** `shock_time_fallback: none`. The removal fallback is kept behind the
  setting `removal`.
- **Supporting observation (2026-10-17):** in the videos, the paddles are sometimes removed
  without a successful shock. A removal therefore doesn't show when, or whether, a shock happened,
  which supports D-093 (no shock time from removal). D-093 stays.

### OQ-060 Should paddle removal still support an inferred Pass for R3 and R4?
- **Old no.:** new (2026-10-17) · **Owner:** supervisor · **Also involves:** Arnikan ·
  **Raised:** 2026-10-17 · **Status:** open
- **Question:** The proposal lets a confirmed paddle removal (`paddles_removed_after_shock`)
  support **Pass – Inferred** for R3 (paddles firmly on the chest) and R4 (both buttons pressed),
  as well as the shock on the screen. In the videos, paddles are sometimes removed **without a
  successful shock**. Should removal still count as evidence for the inference, or only the
  shock on the screen?
- **Affects:** R3, R4 (P-016).
- **Why it matters:** with removal as evidence, R3/R4 can pass (inferred) when no successful
  shock happened (A-021). The overall result still can't be Pass then, because R5 is Fail (screen
  visible) or Unable to Verify (screen not visible).
- **Interim behaviour:** the proposal is followed (D-102). The list is the setting
  `configs/rules.yaml` R3/R4 `parameters.inference_sources`; removing
  `paddles_removed_after_shock` from it is the only change needed. Inferences from the removal
  are flagged `inferred_from_removal` (D-107). See also OQ-061.

### OQ-061 Should either inference source apply when the direct evidence was visible but absent?
- **Old no.:** new (2026-10-17) · **Owner:** supervisor · **Also involves:** Arnikan ·
  **Raised:** 2026-10-17 · **Status:** open
- **Question:** With both inference sources (D-102, D-107), R3 and R4 pass (Pass – Inferred)
  whenever the shock is on the screen or the paddles are removed. That holds even when the zones
  (R3) or the paddles (R4) were visible throughout and the firm placement or the button press
  wasn't tagged, which may mean it didn't happen properly.
  1. Can the training defibrillator deliver a shock **without firm contact** with the chest?
  2. Since paddles are removed even without a successful shock (A-021), should **either** source
     still apply when the direct evidence was **visible but absent**?
- **Affects:** R3 (P-035), R4 (P-036); P-016.
- **Why it matters:** while either source is listed, R3's `missing` and R4's `not_pressed` can
  never be produced (D-106, D-107, D-108). If the answer is "no inference when the evidence was
  visible", the rules would check coverage before the inference.
- **Interim behaviour:** the proposal is followed. Inference comes first, from either source;
  inferences from the removal are flagged `inferred_from_removal`.
- **Related:** D-102, D-106, D-107, D-108, OQ-060.

### OQ-059 Does a parallel placement count as one mistake or two?
- **Old no.:** new (2026-10-17) · **Owner:** supervisor · **Also involves:** Arnikan, Sanjeevan
  (the feedback wording) · **Raised:** 2026-10-17 · **Status:** open
- **Question:** When a learner places both paddles at the same time, R2 (second paddle taken
  after the first is placed) and R8 (apical before sternal) both fail with `simultaneous`. They
  are separate checklist criteria, and one action caused both (D-098). Should the assessment
  count this as **two mistakes** (R2 and R8) or **one**?
- **Affects:** R2, R8; the overall result's list of mistakes; the feedback.
- **Interim behaviour:** Two mistakes, both flagged `possible_parallel_placement`, so the
  feedback module can explain that one action caused both.

### OQ-001 Final policy when coverage is unknown
- **Old no.:** E-1 · **Owner:** team · **Also involves:** supervisor (whether unverifiable
  evidence may count against a learner is an assessment-policy question) · **Raised:**
  2026-10-10 · **Status:** open
- **Question:** When it is unknown whether an event could have been observed (for example, no
  information on whether the audio was analysed), should a missing event be a Fail or Unable
  to Verify?
- **Affects:** all rules; P-008.
- **Interim behaviour:** Unable to Verify, flagged `coverage_policy_undecided` (D-008).
- **A consequence to weigh when deciding (noted 2026-10-17):** a recording with **no zone track
  or no screen track** has unknown coverage for that region (D-074, D-094). If unknown were set
  to Fail:
  - a missing shock on screen would **fail R5** in a view that never shows the screen (for
    example LL);
  - any rule that leaves a missing placement to the coverage policy would **fail** where a zone
    has no track: R3 and R8 are planned this way.

  The learner would then be failed for what the camera couldn't see. **R2 as built would not be
  affected:** D-095 fails only when both zones are actually visible throughout the window. It
  never relies on the unknown setting.

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
- **Update 2026-10-14:** CVAT is frozen (D-073), so no CVAT tag will provide these events. For
  **annotation** timelines, Step 9c plans to derive them from the annotated paddle and zone boxes
  in the rule engine's own exporter. For **model** timelines, the question stays open for Ananth.

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

### OQ-053 Are the converted videos constant frame rate?
- **Old no.:** new (2026-10-16) · **Owner:** Ananth · **Also involves:** Arnikan (exporter),
  Sanjeevan (audio times) · **Raised:** 2026-10-16 · **Status:** open
- **Question:** The exporter converts frames to seconds as `frame / fps`, with fps from
  `video_conversion.csv` (D-076). Are the converted videos constant frame rate? If not,
  `frame / fps` only approximates real time, and the error grows through the video.
- **Affects:** every annotation time; rules comparing video and audio times, such as R7/A6 (shock
  on screen to the restart command) and A8.
- **Interim behaviour:** Constant frame rate is assumed. fps values in the report vary by video
  (24.91 to 30.01), so it is read per video.

### OQ-054 When will the final export be available?
- **Old no.:** new (2026-10-16) · **Owner:** Ananth · **Also involves:** Arnikan · **Raised:**
  2026-10-16 · **Status:** open
- **Question:** When will the exporter and audit outputs for the final backup set (D-083) be
  available?
- **Affects:** Increment 10 onward (real annotation data), the Step 9c validation report.
- **Interim behaviour:** The smoke-run export of 39 corrected backups is used as development data
  (D-084).

### OQ-055 Does anything take the camera view from the backup file name?
- **Old no.:** new (2026-10-16) · **Owner:** Ananth · **Also involves:** Arnikan · **Raised:**
  2026-10-16 · **Status:** open
- **Question:** In the smoke run, `P14_LL.zip` contained a task named P14_LS. Does anything in the
  training pipeline take the camera view or task ID from the backup **file name**, instead of from
  inside the backup? If so, P14_LS could be trained or split under the wrong view.
- **Affects:** Ananth's split and dataset. The rule engine's exporter takes the ID from the task
  name and media name inside the backup, and reports the clash as `duplicate_task`.
- **Interim behaviour:** P14_LS in the interim data is treated as unreliable (D-084).

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
  placement-match window, duration tolerance and R6 removal-before-screen tolerance from pilot
  validation.
- **Affects:** P-004, P-005, P-006, P-011, P-015, P-034; R1, R2, R3, R6, R8.
- **Interim behaviour:** The placeholder values in A-002.
- **9d gel settings (2026-10-17, D-111):** `gel_hand_zone_max_gap` (0.05), `gel_dwell_frames` (10),
  `gel_zone_nearer_ratio` (2.0), `gel_exit_frames` (5), `gel_tag_agreement_frames` (30), to be tuned
  from `gel_validation.md` of the final export.
- **`gel_minimum_gap_seconds`, set to 0.4 s (Arnikan, 2026-10-17; still a placeholder):**
  - **Why lower:** on the interim export, 6 of the 10 videos where the R1 proxy found one
    application had two gel tags 0.5–0.97 s apart, which the 1.0 s placeholder merged. They are
    probably one application per zone.
  - **Why not lower still:** the true duplicates found by the audit were within about 0.5 s
    (P06_LS: 0.03 s).
  - **Result:** with 0.4 s, 13 of the 17 videos with both zones visible have two separate
    applications, and 4 have one (P15_LS, P31_LS, P33_LS, P33_T).
  - **Still to review:** P12_LS's pair (exactly 0.5 s apart, on the audit's duplicate list) now
    counts as two; Arnikan reviews it with P03_LS and the four single-tag videos (progress.md,
    Increment 17).
- **R6 screen delay (2026-10-17, D-105):** on the interim export, the removal tag came after the
  shock on the screen in all 20 LS/T videos with both tags (0.13 to 1.40 s, median 0.88 s), so the
  data doesn't bound the tolerance. Placeholder 0.5 s for now.

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
- **Affects:** R8 (zone visibility), all video rules; with no shock-time fallback (D-093), every
  shock-dependent rule.
- **Interim behaviour:** Any single angle is accepted; mixing angles is rejected (D-032).
- **Evidence (interim, 38 videos):** [camera_angle_evidence.md](camera_angle_evidence.md). It
  covers how often each zone and the screen are visible per view, how often each tag appears,
  and which rules each view can check. It is to be rerun on the final export.

---

## For Arnikan (rule engine and annotation)



### OQ-058 R2 in a parallel placement before the gate is approved — *answered*
- **Old no.:** new (2026-10-17) · **Owner:** Arnikan · **Raised:** 2026-10-17 · **Status:**
  answered
- **Question:** In a parallel placement the annotators don't tag the first placement (A-019).
  Before the gate is approved, R2 saw "first placement missing" and, with the zones visible
  throughout, reported the code for "first paddle never placed". That names the wrong mistake.
  What should R2 report?
- **Answer:** A new code, `first_placement_not_observed`: "either the paddles were placed in
  parallel, or the second paddle was taken before the first was placed". The old code is not
  used for this case. Once the gate is approved, derived parallel placements refine it to
  `simultaneous`.
- **Answered:** 2026-10-17 → **D-097**.

### OQ-056 Is `possible_parallel_placement` alone enough for a Fail? — *answered*
- **Old no.:** new (2026-10-16) · **Owner:** Arnikan · **Raised:** 2026-10-16 · **Status:**
  answered
- **Question:** Derived placements of both paddles within `simultaneous_window_seconds`, with no
  `first_paddle_firmly_on_the_chest` tag, are flagged `possible_parallel_placement` (D-086). Is
  that enough for R2 and R8 to Fail with `simultaneous`, or should it go to review?
- **Answer:** It is enough for a Fail, but only once the gate is approved, as for every derived
  placement.
- **Answered:** 2026-10-16 → **D-091**.

### OQ-047 Where does the exporter get each video's fps? — *answered*
- **Old no.:** new (2026-10-14, Step 9b plan) · **Owner:** Arnikan · **Raised:** 2026-10-14 ·
  **Status:** answered
- **Question:** Use an MP4 header reader cross-checked with the conversion report, or the report
  only?
- **Answer:** The conversion report only; a missing video is an export issue.
- **Answered:** 2026-10-16 → **D-076**.

### OQ-048 Usual zone pattern: computed or configured? — *answered*
- **Old no.:** new (2026-10-14, Step 9b plan) · **Owner:** Arnikan · **Raised:** 2026-10-14 ·
  **Status:** answered
- **Answer:** Fixed in config, with the actual distribution per view printed beside it.
- **Answered:** 2026-10-16 → **D-077**.

### OQ-049 Output folders of the exporter and the audit — *answered*
- **Old no.:** new (2026-10-14, Step 9b plan) · **Owner:** Arnikan · **Raised:** 2026-10-14 ·
  **Status:** answered
- **Answer:** As proposed: `data/rule_engine/annotation_export/<run>/` and
  `annotation/reports/rule_engine_audit/<run>/`.
- **Answered:** 2026-10-16 → **D-078**.

### OQ-050 Reuse the existing scripts by import, or copy their helpers? — *answered*
- **Old no.:** new (2026-10-14, Step 9b plan) · **Owner:** Arnikan · **Raised:** 2026-10-14 ·
  **Status:** answered
- **Answer:** By import, with a test pinning the behaviour.
- **Answered:** 2026-10-16 → **D-079**.

### OQ-051 A zone track that is never visible — *answered*
- **Old no.:** new (2026-10-14, Step 9b plan) · **Owner:** Arnikan · **Raised:** 2026-10-14 ·
  **Status:** answered
- **Answer:** Not covered; the audit lists it as information.
- **Answered:** 2026-10-16 → **D-080**.

### OQ-052 Derived placements: settings, evidence type, disagreement with tags — *answered*
- **Old no.:** new (2026-10-14, Step 9c plan) · **Owner:** Arnikan · **Raised:** 2026-10-14 ·
  **Status:** answered
- **Answer:** The placeholders are accepted. Derived placements are direct evidence, flagged
  `derived_placement`. There is no event when they disagree with the tags. R8 waits for the
  validation report.
- **Answered:** 2026-10-16 → **D-081**.

### OQ-046 Do count anomalies block an overall Pass? — *answered*
- **Old no.:** new (2026-10-14) · **Owner:** Arnikan · **Raised:** 2026-10-14 · **Status:**
  answered
- **Question:**
  - **(a)** Should `count_violation` and `paddle_identity_conflict` be review anomalies, so the
    overall result is Incomplete instead of Pass (a Fail stays Fail, flagged
    `timeline_needs_review`)?
  - **(b)** Is A-018 right: zero confident events is a missing event, decided by the coverage
    step and the rules, and never a count violation?
- **Answer:** (a) Yes, both codes block an overall Pass. (b) A-018 is right.
- **Answered:** 2026-10-14 → **D-072**.

### OQ-007 Zone visibility for annotation timelines — *answered*
- **Old no.:** E-3c · **Owner:** Arnikan · **Also involves:** — · **Raised:** 2026-10-10 ·
  **Status:** answered
- **Question:** `events.jsonl` has no zone tracks. Should zone flags be added to it (in
  `annotation/build_yolo_video_dataset.py`), or supplied as a separate per-task file?
- **Answer:** Neither file of Ananth's changes. A separate rule-engine exporter reads the zone
  tracks from the CVAT backups and writes zone visibility to its own output. A missing zone
  track means visibility unknown.
- **Answered:** 2026-10-14 → **D-074**.

### OQ-008 Annotation label lists that drop the first-placement tag — *answered*
- **Old no.:** E-3d · **Owner:** Arnikan · **Also involves:** — · **Raised:** 2026-10-10 ·
  **Status:** answered
- **Question:** `first_paddle_firmly_on_the_chest` must be added to the label lists in
  `build_yolo_video_dataset.py` and `create_grouped_video_split.py`, not only the audit list.
  Otherwise `events.jsonl` drops it.
- **Answer:** The lists stay as they are. The separate exporter keeps every tag, including this
  one, so `events.jsonl` is not needed for rule-engine timelines.
- **Answered:** 2026-10-14 → **D-074**.

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
- **Update 2026-10-17:** time windows are now used for placement zones with visibility intervals
  (D-092, replacing D-036 there). This question stays answered.

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
