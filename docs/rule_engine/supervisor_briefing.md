# Rule engine: supervisor briefing

**For:** the supervisor meeting · **From:** Arnikan · **Date:** 2026-11-24 · **State:** the whole
engine is built: the video rules, the audio rules and the procedure order. Every rule stays
"pending" until you confirm its definition.

IDs in brackets point to the project registers: decisions (D-),
[decisions.md](decisions.md); open questions (OQ-), [open_questions.md](open_questions.md);
assumptions (A-), [assumptions.md](assumptions.md). The order of the steps is in
[procedure.md](procedure.md).

## 1. What the rule engine does

The rule engine is the part of ARTS that turns what was seen and heard in a defibrillation
recording into an assessment. It receives one timeline of events from the video (for example "gel
applied", "shock shown on the screen") and from the audio (for example "stand clear" said), and
checks each rule of the procedure against it.

- **One result per rule:** **Pass** (seen directly), **Pass – Inferred** (shown by an approved
  inference), **Fail** (with a named mistake), or **Unable to Verify** (the evidence can't settle
  it). A rule that depends on something missing says "not evaluable because of …".
- **Any mistake fails the procedure.** There are no severity levels: a missed verbal command fails
  exactly like a missed physical step (D-001, D-019).
- **A Pass must mean everything was checked.** The overall result is "Incomplete", never Pass,
  while a rule is pending, a clinical time limit hasn't been given, part of an order couldn't be
  checked, or the data needs review (D-055, D-062, D-100).

### The design policies
1. **The learner is never blamed for missing data.** A step fails only when the evidence clearly
   shows the mistake. If it couldn't be seen or heard, the result is Unable to Verify (D-004, D-007).
   Low-confidence evidence is never a Fail (D-010).
2. **A missing command fails only inside clear audio.** The audio detector states when the audio was
   clear; outside those intervals a missing command is Unable to Verify (D-122).
3. **A Fail needs its own evidence.** A mistake in one step is never used as evidence of a mistake in
   another step. If a step can't be judged because another is missing, it says "not evaluable because
   of X", and every other part of it is still checked (D-119, D-121).
4. **One owner per order relation.** Each "X before Y" in the procedure is judged by exactly one rule,
   so one mistake is reported once (D-123, D-126, D-131).
5. **A "wrong place" Fail needs clear evidence where the right place was (D-128).** A wrong-order or
   wrong-time Fail also claims the step was *not* done in the right place. That is an absence, so it
   needs the right place in view (video) or the audio clear there. Otherwise Unable to Verify.
6. **A tag that contradicts the shock is not a Fail (D-129).** With the shock confirmed on the screen,
   the paddles must have been on the chest and the buttons pressed. A tag saying otherwise (R3 placed
   after the shock, R4 pressed before the placement) gives Unable to Verify, "contradictory".
7. **A Pass that rests on an absence needs clear evidence too (D-130, D-132).** For example R6's Pass
   also claims the paddles were not removed before the shock. If that couldn't be seen, Unable to
   Verify. The exception is R5: a second shock is a data problem, not a learner action, so R5's Pass
   is only flagged ("second shock not ruled out").
8. **The shock time comes only from the screen.** A paddle removal is never evidence of a shock or of
   its time (D-093, D-115).
9. **Each camera angle is assessed on its own** (D-096).
10. **Clinical values are never invented.** Every time limit records who gave and who approved it.
    Until then it is empty, and the rule checks presence and order only. "No limit" can be recorded
    as an approved answer (D-103).

Overview diagrams: [the whole flow](diagrams.md#a-end-to-end-from-recording-to-report);
[the steps every rule follows](diagrams.md#c-the-decision-ladder-every-rule-follows-p-026-p-014);
[a wrong place needs clear evidence](diagrams.md#w-a-wrong-place-needs-clear-evidence-where-the-right-place-was-d-128-d-129);
[the overall result](diagrams.md#g-overall-result-p-017-built).

Today the rules are developed on the team's annotated videos and on synthetic timelines. Those
results are development data, not real assessments (D-066, D-117).

## 2. The built rules

All rules below are built and tested; each reports "pending" until you confirm it. Each rule's logic
in plain words is in [rules_status.md](rules_status.md).

**Video**
| Rule | Checks | Fails with |
|---|---|---|
| R1 Gel applied twice | Gel once on each placement zone, either order, before the paddles are placed | `after_placement`, `applied_once`, `missing` |
| R2 Second paddle taken after the first is placed | The paddle taken first is placed before the other is taken | `taken_before_first_placed`, `simultaneous`, `first_placement_not_observed` |
| R8 Apical before sternal | The apical paddle placed before the sternal one (both seen) | `wrong_order`, `simultaneous` |
| R3 Paddles firmly on the chest | Firmly placed before the shock (or inferred from the shock) | `placed_after_shock` (only if the shock is not an inference source), `missing` |
| R4 Both buttons pressed | After the placement and before the shock (or inferred from the shock) | `before_placement` (as R3), `not_pressed` |
| R5 Shock on the screen | One new shock indication | `missing` |
| R6 Paddles removed after the shock | The removal after the shock on the screen | `removed_before_shock`, `missing`, `too_late` (once a limit is given) |

**Audio** (Sanjeevan's command events; the shock time from the screen)
| Rule | Checks | Fails with |
|---|---|---|
| A1 Oxygen away, A3 All stand clear | Said before the shock | `after_shock`, `missing` |
| A2 Continue compressions | Said in the preparation, before the shock | `wrong_stage`, `missing` |
| A4 Stop compressions | After "continue", before the shock | `wrong_order`, `after_shock`, `missing` |
| A5 Shock command | Before or at the shock (held back: is it required? OQ-075) | `after_shock`, `missing` |
| R7/A6 Restart compressions | Start said after the shock (one check, two IDs) | `before_shock`, `missing`, `too_late` (once a limit is given) |
| A7 Command order | The commands heard in the expected order (its audio relations) | `wrong_order` |
| A8 Pre-shock pause | Stop to restart within 5 s (approved); the end event is a setting (OQ-076) | `pre_shock_pause` |

**Procedure order**
| Rule | Checks | Fails with |
|---|---|---|
| S1 Procedure order | The whole procedure in the expected order, on the relations no other rule judges (OQ-064: its own checklist item?) | `wrong_order` |

## 3. Where the system departs from the original proposal

| Change | Reason |
|---|---|
| **No severity levels:** any mistake fails the procedure (D-001, D-019) | A missed verbal safety command is as serious as a missed physical step |
| **R1:** gel **twice, once on each placement zone**, either order, **before placement** (D-109, D-110) | Twice, one per zone, is the procedure taught; a shock without gel harms the patient |
| **R2:** the second paddle is taken only after the first is **placed** (D-051) | The procedure taught |
| **New rule R8:** apical paddle before sternal (D-052) | A taught step |
| **New rule A8:** pre-shock pause at most **5 s**, approved by you (D-016) | A taught limit |
| **R7 and A6 are one check**, reported under both IDs (D-044) | The same step |
| **A7 checks the command order only;** a missing command is its own rule's mistake (D-027) | One mistake, one rule (D-119) |
| **New rule S1:** the order of the whole procedure, judged only where no other rule judges it (D-123, D-126) | The proposal's order has steps no single rule covers (OQ-064) |
| **R5 no longer checks the steps before the shock;** each step's own rule does (D-123) | One owner per relation |
| **R3 does not yet judge "paddle outside its zone"** (D-106) | The chest regions are not approved (OQ-012) |
| **The interim order is the lecturer's video,** not yet approved (D-127, OQ-062) | The best source until you confirm the order |

Not a departure: the shock time comes only from the screen, and a paddle removal is never evidence
of a shock (D-093, D-115).

## 4. Every open question, in one list

Each question shows what the system does until it is answered. Details:
[open_questions.md](open_questions.md).

### For you (the supervisor)
**The overall result and the checklist**
- **OQ-002:** no rule fails, but some steps couldn't be verified: Fail or "faculty review"? *Until
  then:* reported as Unable to Verify, never Pass.
- **OQ-001:** when it's unknown whether a step could have been seen, Fail or Unable to Verify?
  *Until then:* Unable to Verify. (Fail would fail learners for what a camera never showed.)
- **OQ-036:** the evaluator checklist and which rules feed each item. *Until then:* one item per rule.
- **OQ-064:** is the procedure order (S1) its own checklist item? *Until then:* built, held back.
- **OQ-015:** final IDs for R8 and A8. *Until then:* "R8" and "A8".

**The procedure order**
- **OQ-062:** the approved full order of the audio and video steps ([procedure.md](procedure.md)).
  *Until then:* the lecturer's interim order (D-127).
- **OQ-063:** which steps, if any, may swap? *Until then:* none, except the gel and "applying gel"
  (said while the gel is applied, D-127).
- **OQ-077:** must oxygen away, stand clear and continue be in exactly this order? *Until then:* strict.
- **OQ-075:** is the shock command (A5) required, and where does it go? The lecturer gave none.
  *Until then:* A5 built, held back.
- **OQ-072, OQ-073:** are the spoken "charging" and "applying gel" compulsory? *Until then:* optional:
  checked for position only if said.
- **OQ-074:** does the charging sound count as evidence for charging? *Until then:* only the spoken
  "charging" is the step.

**Time limits and repeats**
- **OQ-016:** the missing time limits: the two gel applications (R1), shock → removal (R6),
  shock → restart (R7/A6), stop → shock (A4), how early the shock command may come (A5), oxygen away
  and stand clear before the shock (A1, A3). "No limit" is a valid answer. *Until then:* not checked;
  the overall result stays Incomplete.
- **OQ-076:** the pre-shock pause (A8): stop → start, or stop → shock? In the lecturer's order the whole
  shocking process lies between stop and start; on a lecturer-like timeline stop → start is 6–8 s
  (Fail) and stop → shock 3–4 s (Pass). *Until then:* stop → start; A8 held back.
- **OQ-021:** gel applied more than twice: a mistake? *Until then:* passes.
- **OQ-022:** paddles lifted and placed again before the shock? *Until then:* the earliest counts.
- **OQ-023:** buttons pressed more than once? *Until then:* any valid press counts.

**Paddles and the shock**
- **OQ-059:** a parallel placement fails R2 and R8: one mistake or two? *Until then:* two, marked as one
  cause.
- **OQ-006:** may "the paddle taken first was also placed first" be assumed when no placement is seen?
  *Until then:* off.
- **OQ-012:** approve the chest regions (R3 "outside its zone"). *Until then:* timing and presence only.
- **OQ-061:** should the shock on the screen still infer R3 and R4 when the step was in view but not
  seen? *Until then:* it infers.
- **OQ-057:** are you content that the shock time comes only from the screen? *Until then:* never
  estimated.

**The commands**
- **OQ-010, OQ-065:** the command names, the accepted phrases per command, and their order. *Until
  then:* the proposal's names and the lecturer's phrases, marked provisional.

### For Sanjeevan (audio)
- **OQ-009:** the missing command events: stop compressions and the shock command, and a separate start
  command with word timestamps (top priority: without them a restart said at the shock stays
  unresolved, and R7/A6 give Unable to Verify even for a correct learner).
- **OQ-068:** clear-audio intervals, their signal and format (top priority: without them every missing
  command and every audio "wrong place" Fail is Unable to Verify).
- **OQ-066:** non-standard phrasing: strict or lenient matching?
- **OQ-045:** confirm the output contract's versioning rule.

### For Ananth (video)
- **Top priority:** visibility intervals for every region (both placement zones, the screen, the
  paddles, the learner's hand), in the annotation adapter's header format. Without them every video
  "wrong place" Fail is Unable to Verify (D-128; upstream_requirements.md).
- **OQ-004:** who produces the per-paddle placement events?
- **OQ-020:** the timeline header: can it be provided, in what format?
- **OQ-017:** the pipeline calling the full rule-engine assessment.
- **OQ-054:** when the final annotation export will be available; **OQ-053:** constant frame rate;
  **OQ-055:** does anything take the camera view from the backup file name?

### For the team (Ananth, Sanjeevan and Arnikan)
- **OQ-018:** the engineering placeholder values (windows, thresholds).
- **OQ-019:** which side applies confidence thresholds?
- **OQ-037:** the model output formats and the meaning of confidence.
- **OQ-038:** the final camera angle.
