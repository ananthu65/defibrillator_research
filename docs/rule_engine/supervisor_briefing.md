# Rule engine: supervisor briefing

**For:** the supervisor meeting · **From:** Arnikan · **Date:** 2026-10-17 · **State:** the seven
video rules are built. All rules stay "pending" until you confirm their definitions.

IDs in brackets point to the project registers: decisions (D-),
[decisions.md](decisions.md); open questions (OQ-), [open_questions.md](open_questions.md);
assumptions (A-), [assumptions.md](assumptions.md).

## 1. What the rule engine does

The rule engine is the part of ARTS that turns what was seen and heard in a defibrillation
recording into an assessment. It receives a timeline of events (for example "gel applied", "shock
shown on the screen", "stand clear" said) and checks each rule of the procedure against it.

- **One result per rule:** each rule gives **Pass** (seen directly), **Pass – Inferred** (shown
  indirectly by an approved inference), **Fail** (with a named mistake), or **Unable to Verify**
  (the evidence can't settle it). A rule that depends on something missing says "not evaluable
  because of …" instead of repeating the same mistake.
- **Any mistake fails the procedure.** There are no severity levels: a missed verbal command
  fails exactly like a missed physical step (D-001, D-019).
- **The learner is never blamed for missing data.** A step fails only when the evidence clearly
  shows the mistake, for example when the area was in view and the step didn't happen. If the
  camera couldn't see it, the result is Unable to Verify (D-004, D-007). Low-confidence evidence
  is never a Fail (D-010).
- **A Pass must mean everything was checked.** The overall result is "Incomplete", never Pass,
  while any of these remains:
  - a rule is still pending;
  - a clinical time limit hasn't been given;
  - an order requirement isn't set;
  - the data itself needs review.
  (D-055, D-062, D-065, D-100.)
- **The shock time comes only from the screen.** A paddle removal is never taken as evidence of
  a shock or of its time, because paddles are sometimes removed without a successful shock. Without
  the screen in view, the rules that need the shock time are not evaluable (D-093, D-115).
- **Each camera angle is assessed on its own.** Results are never compared across angles (D-096).
- **Clinical values are never invented.** Every time limit records who gave it and who approved
  it. Until then it is empty, and the rule checks presence and order only. "No limit" can be
  recorded as an approved answer too (D-103).

Overview diagrams:
- [the whole flow](diagrams.md#a-end-to-end-from-recording-to-report);
- [the steps every rule follows](diagrams.md#c-the-decision-ladder-every-rule-follows-p-026-p-014);
- [what a missing event means](diagrams.md#d-what-a-missing-event-means-p-007-p-008-p-013);
- [the overall result](diagrams.md#g-overall-result-p-017-built).

Today the rules run on the team's annotated videos, through a development and evaluation tool
rather than the final input path; with perfect perception they also give a baseline for judging
the rules themselves (D-117). Those results are marked as development data,
not real assessments (D-066).

## 2. The built rules

All seven rules below are built and tested. They report "pending" until you confirm them. The
audio rules (A1–A8, R7) come next.

**R1 Gel applied twice** ([diagram](diagrams.md#o-r1-gel-twice-once-to-each-zone-before-placement-p-038-built-in-increment-17-pending-until-approved)).
Gel must be applied once to each placement zone (sternal on the chest, apical on the left side of
the ribs), in either order, **before** the paddles are placed. If gel was applied only after the
first paddle went on, R1 fails ("gel after placement"). One zone gelled and the other not is
"applied once"; no gel is "missing". These fail only when the missing gel could have been seen.
- **How gel is seen today:** by counting the annotators' "Gel applied" tags while both zones were
  in view. Tags under 0.4 s apart count as one application.
- **Planned:** a per-zone method from the tracked hand holding the gel bottle. It is used once its
  validation report has been reviewed.
- **Not checked:** the time between the two applications (no limit given yet), and more than two
  applications.

**R2 Second paddle taken after the first is placed** ([pathway table](pathways.md#p-032-r2-second-paddle-taken-after-the-first-is-placed-built-increment-11-pending-until-approved)).
The paddle taken first, whichever it is, must be placed firmly before the other is taken. "First"
is by time: under the team's working definition (A-027), `first_paddle_*` means the apical paddle and
`second_paddle_*` the sternal paddle, so the tag names say which paddle, never the order (D-118). A
learner who starts with the sternal paddle but handles one paddle at a time passes R2; R8 reports
the order.
- Taking the second paddle at the same moment as placing the first fails ("simultaneous");
  taking it before the first is placed fails.
- Taking both paddles together (within the simultaneous window) fails as "simultaneous",
  whichever paddle the tags name first.
- If the first placement wasn't seen although both zones were in view, it fails as "first
  placement not observed": either the paddles were placed together, or the second was taken
  first.
- Otherwise, if the order can't be seen, Unable to Verify.

**R8 Apical paddle placed before sternal** ([diagram](diagrams.md#f-r8-apical-before-sternal-p-015-built-in-increment-12-pending-until-approved)).
- **Both placements seen:** they are compared directly. Sternal first is "wrong order", and both
  together is "simultaneous".
- **Only one zone in view:** Unable to Verify. Which paddle went first can't be established from
  one zone. (An earlier version inferred it from the first-placement tag, but under the team's
  working definition that tag is the apical paddle's placement, so the inference could pass a
  learner who placed the sternal paddle first.)
- **Both paddles placed together:** both R2 and R8 fail, marked as one cause.
- **On the annotations so far:** R8 has no direct evidence yet. Its placements come from the
  paddle and zone boxes (Step 9c), whose settings are still placeholders to be set later (OQ-018),
  and they are used only after my review. For the same reason, R2 can't detect a parallel
  placement yet.

**R3 Paddles placed firmly on the chest** ([diagram](diagrams.md#l-r3-paddles-placed-firmly-on-the-chest-p-035-built-in-increment-15-pending-until-approved)).
- **Pass:** both paddles seen firmly on the chest before the shock shown on the screen.
- **Fail:** placed firmly only after the shock ("placed after shock").
- **Inferred:** if the firm placement wasn't seen, R3 passes by inference when the shock on the
  screen is confirmed. A paddle removal never infers it.
- **No shock on the screen:** R3 is not evaluable.
- **Not checked yet:** where the paddles were placed ("not in zone"), because the chest regions
  are not approved yet. Until then R3 checks timing and presence only.

**R4 Both discharge buttons pressed** ([diagram](diagrams.md#m-r4-both-discharge-buttons-pressed-p-036-built-in-increment-16-pending-until-approved)).
- **Pass:** both buttons pressed after the paddles were placed and at or before the shock.
- **Fail:** pressed before the paddles were placed ("before placement").
- **Inferred:** if no press was seen, R4 passes by inference from the shock on the screen, as R3
  does; never from the paddle removal. "Not pressed" would fail only if both paddles were in view
  throughout. While the shock infers, that case can't happen yet (see OQ-061).
- **No shock on the screen:** R4 is not evaluable.

**R5 Shock confirmed on screen** ([pathway table](pathways.md#p-033-r5-shock-confirmed-on-screen-built-increment-13-pending-until-approved)).
- **One shock seen:** R5 passes, but the order against the preceding steps isn't checked until
  you say which steps those are. The overall result stays Incomplete meanwhile.
- **Missing:** no shock shown fails only if the screen was in view throughout, from paddles
  firmly on the chest to paddles removed. Otherwise Unable to Verify.
- **Two shocks:** a data problem, so Unable to Verify.

**R6 Paddles removed after the shock** ([diagram](diagrams.md#k-r6-paddles-removed-after-the-shock-p-034-built-in-increment-14-pending-until-approved)).
- **Pass:** the removal is after the shock shown on the screen. A removal up to 0.5 s before it
  counts as at the shock, because the screen may update after the discharge.
- **Fail:** clearly before the shock ("removed before shock"). Removal is not counted as proof
  of a shock: paddles are sometimes removed without a successful shock.
- **No shock seen:** R6 is not evaluable.
- **No removal:** fails only if both placement zones were in view until the end.
- **Not checked:** the time from shock to removal, until you give a limit or say "no limit".

## 3. Where the system departs from the original proposal

| Change | Reason |
|---|---|
| **No severity levels:** any mistake fails the procedure, and there is no "critical error" class (D-001, D-019) | Defibrillation is life-critical: a missed verbal safety command is as serious as a missed physical step |
| **R1 redefined:** gel applied **twice, once on each placement zone**, in either order, and still **before placement** (D-109, D-110). An earlier version dropped "before placement" (D-018); it is restored | Twice, one per zone, is the procedure taught. A shock without gel harms the patient, so gel must come first |
| **R2 redefined:** the second paddle may be taken only after the first is **placed** (D-051) | This is the procedure taught |
| **New rule R8: apical paddle before sternal** (D-052). Judged only when both placements are seen; with one zone in view it is Unable to Verify (D-116) | It is a taught step |
| **New rule A8: pre-shock pause** from "stop CPR" to "start CPR" at most **5 s**, approved by you (D-016) | A taught limit on the pause in compressions |
| **R7 and A6 are one check**, reported under both IDs and counted as one mistake (D-044) | They describe the same step |
| **A7 checks the command order only.** A missing command is reported by its own rule, not again by A7. "Stop" before "continue" is A4's mistake only (D-027) | A mistake in one step is never used as evidence of a mistake in another step (D-119) |
| **R3 does not yet judge "paddle outside its zone"** (D-106) | The chest regions are not approved yet (OQ-012) |
| **A parallel placement fails both R2 and R8,** marked as one cause (D-098) | They are separate checklist items, but the feedback should say one action caused both (OQ-059) |

Not a departure: the shock time comes only from the screen, and a paddle removal is never taken
as evidence of a shock (D-093, D-115). The original documents have no rule inferring a shock from
the removal.

## 4. Your open questions, by rule

Each question shows what the system does until it is answered.

### The overall result
- **OQ-002: no rule fails, but some steps couldn't be verified.** Should the overall result be
  Fail or "faculty review"?
  - *Until then:* reported as "Unable to Verify", never Pass.
- **OQ-001: it's unknown whether a step could have been seen** (for example no information on
  whether the audio was analysed). Should a missing step then fail, or be Unable to Verify?
  - *Until then:* Unable to Verify.
  - *Note:* choosing Fail would fail learners for what a camera never showed, for example R5 in a
    view without the screen.
- **OQ-036: evaluator checklist.** What does the checklist look like, and which rules feed each
  item?
  - *Until then:* one item per rule (planned).
- **OQ-015: final IDs for the new rules** R8 and A8.
  - *Until then:* "R8" and "A8".

### R1 Gel
- **OQ-016: time period.** Within what time must the two gel applications happen? "No limit" is a
  valid answer.
  - *Until then:* not checked, and the overall result stays Incomplete.
- **OQ-021: three or more applications.** A mistake, or does "at least twice" pass?
  - *Until then:* passes.

### R2 and R8 Paddle order
- **OQ-059: parallel placement.** Both paddles placed together fails R2 and R8, each on its own
  evidence (D-119). One mistake or two?
  - *Until then:* two, marked as one cause.
- **OQ-006: fallback.** May "the paddle taken first was also placed first" ever be assumed as a
  last resort, when no placement can be seen at all? Since the tags say which paddle is which
  (A-027), it would apply only when the apical paddle was taken first (D-118).
  - *Until then:* off.
- **OQ-022: paddle lifted and placed again before the shock.** Acceptable or a mistake? Which
  placement counts?
  - *Until then:* the earliest counts; the repeat is flagged for review, never a Fail by itself.

### R3 Paddles firmly on the chest
- **OQ-012: chest regions.** Please approve the regions and what counts as a correct placement.
  - *Until then:* R3 checks timing and presence only, never "not in zone".
- **OQ-061: inference when the step was visible but not seen.** Can the training defibrillator
  deliver a shock without firm contact? Should the shock on the screen still infer R3 and R4 when
  the zones (R3) or paddles (R4) were in view and the step wasn't seen?
  - *Until then:* the inference applies, so R3's "missing" and R4's "not pressed" can't be
    produced.

### R4 Both buttons pressed
- **OQ-023: buttons pressed more than once.** Acceptable or a mistake? Which press counts?
  - *Until then:* any valid press counts.
- OQ-061 above also applies.

### R5 Shock on screen
- **OQ-013: preceding steps.** Which steps must come before the shock: paddle placement only, or
  placement and both buttons pressed?
  - *Until then:* presence only, and the overall result stays Incomplete.

### R6 and the shock time
- **OQ-016: removal time limit.** Is there a time limit from shock to removal? "No limit" is a
  valid answer.
  - *Until then:* not checked, and the overall result stays Incomplete.
- **OQ-057: shock time only from the screen.** Are you content that the shock time comes only from
  the screen, so that in a view without the screen every shock-dependent rule is not evaluable?
  - *Until then:* never estimated.

### Audio rules (A1–A8, R7; to be built next)
- **OQ-010: commands.** Please confirm the six commands (oxygen away, continue compressions, all
  stand clear, stop compressions, shock, start or resume compressions), their accepted wordings
  and their order.
  - *Until then:* the proposal's names, marked provisional.
- **OQ-016: time limits.**
  - Shock → restart compressions (R7/A6).
  - Stop command → shock (A4).
  - How early the verbal shock command may come (A5).
  - Whether oxygen away and stand clear (A1, A3) have a limit before the shock.
  - *Until then:* not checked.
