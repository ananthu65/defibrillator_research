# Rule engine: decision log

Every decision about how the rule engine assesses a recording, with its reason and status.
Written for readers who do not read code; technical detail is in [methods.md](methods.md).

- **Status:** `approved` (final), `interim` (in use until a final decision), `undecided`
  (the system uses a safe interim behaviour, and the question is open in
  [open_questions.md](open_questions.md)).
- **Decided by:** Arnikan, team, supervisor, or "agent proposal approved by Arnikan".
- **IDs are stable.** A decision that is changed gets a new entry that names the one it
  replaces; old entries are not edited.

Related registers: [open questions](open_questions.md) (OQ), [assumptions](assumptions.md) (A),
decision points (P) in [decision_flow.yaml](decision_flow.yaml) and [pathways.md](pathways.md).

---

## Assessment policy

### D-001 Any mistake fails the procedure; no severity levels
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** If any rule fails, the overall result is Fail. There are no severity levels, so
  "Critical Error" is never used to grade a mistake.
- **Reason:** Defibrillation is life-critical. A missed verbal safety command is as serious as a
  missed physical step.
- **Alternatives considered:** Severity levels and a "Critical Error" class (in an early AI
  proposal), rejected.
- **Affects:** all rules; overall policy P-017; Increment 8.

### D-002 Every rule is always evaluated
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** All rules are checked, even after one fails.
- **Reason:** Feedback needs a result for every step, not just the first mistake.
- **Alternatives considered:** Stop at the first failure (rejected).
- **Affects:** all rules; rule ladder P-014; Increment 7.

### D-003 One mistake is reported once
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** If a rule cannot be judged because something it depends on is missing (for
  example, no confirmed shock), it reports "not evaluable because of X" instead of a second
  Fail.
- **Reason:** Repeating one mistake as several failures would overstate it in the feedback.
- **Affects:** all shock-dependent rules, A7; P-014; Increments 6–7.

### D-004 Never blame the learner for missing data
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** A rule fails only when the evidence clearly shows the mistake. Missing or
  unclear evidence gives "Unable to Verify".
- **Reason:** A camera or microphone failure must not count against the learner.
- **Affects:** all rules; P-008; D-007, D-008, D-010.

### D-019 Verbal command failures fail the procedure
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** A missing or wrong verbal command (A1–A8, R7) fails the procedure exactly like a
  missed physical step.
- **Reason:** Follows from D-001; the commands are safety steps.
- **Affects:** A1–A8, R7; P-017.

### D-042 What "Unable to Verify" means overall is undecided
- **Date / by / status:** 2026-10-10 · Arnikan · undecided
- **Decision:** When no rule fails but at least one is Unable to Verify, the overall result is
  either Fail or "faculty review". This is one setting (`unable_to_verify_outcome`), currently
  unset.
- **Reason:** It is a study-method decision for the supervisor.
- **Affects:** P-017; Increment 8. **Open question:** OQ-002. **See also:** D-056 ("not
  evaluable" counts as Unable to Verify).

### D-043 Rules not yet approved are reported but not counted
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** A rule whose definition is not approved appears in the report as "pending". It
  has no Pass or Fail of its own.
- **Affects:** all rules; P-014, P-017. **Refined by:** D-055 (a pending rule prevents an
  overall Pass).

### D-055 The overall result can be Pass only if every rule was evaluated
- **Date / by / status:** 2026-10-13 · Arnikan · approved
- **Decision:** If any rule is pending (not yet approved), the overall result is **incomplete
  ("rules not yet approved")**, never Pass. A Fail in an evaluated rule still makes the overall
  result Fail, because any mistake fails (D-001).
- **Reason:** A Pass must mean every step was checked. Ignoring pending rules could make a
  procedure pass with steps that were never assessed.
- **Alternatives considered:** Pending rules not counted at all, so the overall result could
  be Pass (D-043 as first written), rejected.
- **Affects:** all rules; P-017; Increment 8.

### D-062 Unchecked timing prevents an overall Pass
- **Date / by / status:** 2026-10-14 · Arnikan · approved
- **Decision:** A rule result flagged `timing_not_checked` or `limit_not_approved` stays a Pass
  at rule level. The overall result, however, cannot be Pass: it is **incomplete** ("timing not
  checked for R7"), the same as a pending rule (D-055).
- **Reason:** A Pass must mean every step was fully checked. A missing clinical limit means one
  part of a step was never assessed.
- **Affects:** every timed rule (R1, R6, R7/A6, A4, A5, A8); P-017, P-024; Increment 8.

### D-065 Timeline anomalies prevent an overall Pass
- **Date / by / status:** 2026-10-14 · Arnikan · approved (the list and its place: D-069)
- **Decision:** When the timeline has a timeline-level anomaly from the review list
  (`review_anomalies` in `engine.yaml`), the overall result can never be Pass:
  - **a Fail stays Fail**, but is flagged `timeline_needs_review`, with the anomalies listed;
  - **otherwise the result is Incomplete**, "the timeline needs review (…)".
- **The list:** `unknown_labels_present`, `multiple_shocks` and `mixed_evidence_sources` (D-069).
- **Affects:** P-017; Increment 8. **See also:** D-069.

### D-069 Review anomalies: all three, checked before the Unable-to-Verify setting
- **Date / by / status:** 2026-10-14 · agent proposal approved by Arnikan · approved
- **Decision:**
  - **(a) The list:** `review_anomalies` contains all three timeline anomalies:
    `unknown_labels_present`, `multiple_shocks` and `mixed_evidence_sources`.
  - **(b) The order:** with no Fail, a review anomaly makes the overall result Incomplete. It is
    checked **before** the Unable-to-Verify setting.
- **Reason:** If `unable_to_verify_outcome` is later decided as Fail, and the anomaly were
  checked after it, a data problem such as two shocks could fail a learner. Placing it in the
  Incomplete step means a data problem never becomes the learner's Fail (D-004).
- **Affects:** P-017; `engine.yaml: review_anomalies` (no longer undecided). **Resolved:**
  OQ-044.

### D-071 Event counts and paddle identity are checked, never a Fail by themselves
- **Date / by / status:** 2026-10-14 · Arnikan · approved (the values are placeholders; the
  effect on the overall result is OQ-046)
- **Decision:** Preparation (P-005) checks two things.
  - **Expected counts:** the number of confident events of each canonical event is checked
    against `engine.yaml` `expected_counts` (`exactly`, `at_least`, `at_most` or `unlimited`).
    - Exactly 1: both paddles taken, first placement, apical and sternal placements, removal,
      shock on screen.
    - Unlimited: every command.
    - Undecided, so not checked: gel, buttons pressed, paddles firmly on chest. These are tied
      to the supervisor's repeated-actions questions OQ-021, OQ-022, OQ-023.
    - Every value is a placeholder.
    - A count outside its range raises `count_violation`, naming the event, the expected and
      found counts, and the event IDs.
  - **Paddle identity:** two or more apical placements and no sternal placement, or the
    reverse, raises `paddle_identity_conflict`.
  - **Possible duplicates:** for an event limited to one, an extra event within
    `simultaneous_window_seconds` of another is marked "possibly the same incident detected
    twice".
- **Effect:** never a Fail by itself; nothing is removed or merged. A rule may fail on a
  repeated action only once the supervisor decides that the repetition is a mistake. The
  proposal that both codes block an overall Pass, extending the D-069 list, is OQ-046. Until
  it is answered, both are in `review_anomalies`, and that setting is marked undecided.
- **Reason:** A repeated one-off event (two shocks, two removals) or a swapped paddle identity
  usually means a detection or annotation problem. A rule using such data could give a wrong
  result without anyone noticing.
- **Affects:** P-005, P-017; Increment 9a. **Assumption:** A-018. **Open questions:** OQ-046,
  OQ-021, OQ-022, OQ-023.

### D-072 Count anomalies block an overall Pass; no events at all is a missing event
- **Date / by / status:** 2026-10-14 · Arnikan · approved
- **Decision:**
  - `count_violation` and `paddle_identity_conflict` are review anomalies (`review_anomalies`,
    now decided). With either, the overall result is never Pass: a Fail stays Fail, flagged
    `timeline_needs_review`, and any other result is Incomplete, checked before the
    Unable-to-Verify setting, as for the other review anomalies (D-069).
  - A-018 is confirmed: no confident event at all is a missing event, decided by the coverage
    step and the rules, and never a count violation.
- **Reason:** A repeated one-off event or a swapped paddle identity means the evidence may be
  wrong. The result must then be reviewed rather than passed, but a data problem must never
  fail a learner.
- **Affects:** P-005, P-017; `engine.yaml` `review_anomalies`. Extends D-069 and D-071.
  **Resolved:** OQ-046.

### D-066 Results from annotation data are marked as development data
- **Date / by / status:** 2026-10-14 · Arnikan · approved
- **Decision:** When any rule result carries `annotation_coverage_assumed` (an annotation
  timeline, A-001, D-035), the overall result is marked as development data, not a real
  assessment (`development_data`). The result itself is still computed, so the rules can be
  tested.
- **Affects:** P-017, P-018; Increments 8 and 10.

### D-067 The overall result explains itself
- **Date / by / status:** 2026-10-14 · Arnikan · approved
- **Decision:** The overall result lists:
  - the rules that decided it: every Fail, or every incomplete rule with its reason, or every
    unverified rule;
  - every named mistake (each Fail with its failure code and rule title);
  - R7 and A6 as one entry (D-044);
  - the policy step or setting that decided it, including any undecided setting (for example
    `unable_to_verify_outcome = None (undecided, OQ-002)`).
- **Affects:** P-017, P-018.

### D-068 No rule evaluated is Incomplete
- **Date / by / status:** 2026-10-14 · Arnikan · approved
- **Decision:** A config with no rules to evaluate (for example every rule disabled) gives
  **Incomplete**, flagged `no_rules_evaluated`, never Pass.
- **Affects:** P-017.

### D-056 "Not evaluable" counts like Unable to Verify in the overall result
- **Date / by / status:** 2026-10-13 · Arnikan · approved
- **Decision:** A rule result "not evaluable because of X" is treated like Unable to Verify by
  the overall policy (D-042). It never makes the overall result Pass.
- **Reason:** The step was not checked. Its cause (X) is reported once, under its own rule
  (D-003).
- **Affects:** P-017; Increment 8. **Open question:** OQ-002.

### D-057 Approved inference applies when direct evidence is missing, not only weak
- **Date / by / status:** 2026-10-13 · Arnikan · approved
- **Decision:** For rules with an approved inference (R3, R4 via P-016), the inference is
  checked when direct evidence is **missing** as well as when it is weak, **before** the
  coverage step decides what the missing evidence means.
- **Reason:** The proposal's inference is for "insufficient" direct evidence, and a single
  camera often cannot see placement or button presses at all.
- **Affects:** R3, R4; P-014, P-016.

### D-044 R7 and A6 are one check reported under two IDs
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** "Restart compressions promptly" is implemented once and reported as both R7
  and A6.
- **Affects:** R7, A6; Increments 2 and 21.

---

## Rule definitions

### D-018 Gel: applied twice within the approved period; order versus placement not checked
- **Date / by / status:** 2026-10-10 · Arnikan · approved (the period itself awaits OQ-016)
- **Decision:** R1 passes when gel is applied twice, as two separate applications, within an
  approved time period. Whether gel comes before paddle placement is **not** checked.
- **Reason:** This is the procedure taught. It replaces the proposal document's "gel before
  placement".
- **Affects:** R1; Increment 17. **Open questions:** OQ-016 (the period), OQ-021 (more than
  twice).

### D-051 R2: second paddle taken only after the first is placed
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** R2 passes when the order is first paddle taken → first paddle placed firmly →
  second paddle taken. "Taken" means the first frame where the paddle is clearly visible.
- **Affects:** R2; Increment 11.

### D-052 New rules R8 (apical before sternal) and A8 (pre-shock pause)
- **Date / by / status:** 2026-10-10 · Arnikan · approved (the final IDs await OQ-015)
- **Decision:** R8 and A8 are added to the rule set, and the proposal's R1 and R2 are
  redefined (D-018, D-051).
- **Affects:** R8, A8; Increments 2, 12, 23.

### D-016 A8: the 5-second pre-shock pause limit is approved
- **Date / by / status:** 2026-10-10 · supervisor (Dr. Senani Samarasinghe) · approved
- **Decision:** The time from "Stop CPR" to "Start CPR" must be at most 5 seconds. The value
  was provided by Arnikan on 2026-10-10 from team discussion; the approval date is still to be
  confirmed (`date_pending: true`, see D-033).
- **Affects:** A8; Increment 23. **Resolved:** OQ-014, OQ-033.

### D-027 A7 checks command order only; A4 owns stop-before-continue
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** A7 checks the order of commands only. When a command is missing, A7 reports
  "not evaluable because of Ax". A "stop" given before "continue" is A4's mistake; A2 does not
  also fail for it.
- **Reason:** One mistake is reported once (D-003).
- **Affects:** A2, A4, A7; Increments 19 and 22. **Resolved:** OQ-011.

### D-013 R8: one-visible-zone inference, owned by the rule engine
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:**
  - **Both placement zones visible:** compare the apical and sternal placement times directly.
  - **Only one zone visible:** compare that zone's placement time with the first placement time.
    The same time (within a window) means that paddle was first; clearly later means the other
    paddle was first. The result is recorded as inferred.
  - **Not determinable:** Unable to Verify.
  - **Who infers:** the rule engine; upstream only reports what is visible.
- **Reason:** In some camera angles only one zone is annotated, and the zones are far apart.
  The idea came from Arnikan.
- **Alternatives considered:** No inferred result for R8 (the original brief), and inference
  in video postprocessing.
- **Affects:** R8; P-015; Increments 4, 5, 10, 12. **Related:** D-014, D-015, OQ-004, OQ-006.

### D-058 R8 with a missing placement event: Unable to Verify, no inference
- **Date / by / status:** 2026-10-13 · agent proposal approved by Arnikan · approved
- **Decision:** In both of these cases R8 gives **Unable to Verify**, flagged
  `placement_missing`, with no inference and never `wrong_order`. R3 reports the missing
  placement.
  - **(a)** the visible zone's paddle has no placement event;
  - **(b)** both zones are visible but one paddle's placement event is missing.
- **Reason:** A missing event does not show the order, and the missing placement is R3's
  finding (D-003). "The visible paddle was never placed, so the other was first" is not shown
  by the evidence, because it may have been placed outside its zone.
- **Affects:** R8, R3; P-015; Increment 12. **Resolved:** OQ-040.

### D-060 An assumed result prevents an overall Pass
- **Date / by / status:** 2026-10-13 · Arnikan · approved
- **Decision:** When R8 uses the apical-first fallback (D-014), its result is **assumed**, not
  evaluated. Like a pending rule (D-055), it makes the overall result **incomplete** ("assumed
  result, to be checked by the evaluator"), never Pass. A Fail in an evaluated rule still makes
  the overall result Fail.
- **Reason:** Consistency with D-055: a Pass must mean every step was actually checked.
- **Affects:** R8; P-015, P-017; Increments 8 and 12.

### D-014 "First paddle taken is apical" is an off-by-default fallback
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** The team's assumption that the first paddle taken is the apical one may be used
  only as a configurable last resort, **off by default**. If it is used, R8's result is
  "assumed apical first, to be checked by the evaluator", and it prevents an overall Pass
  (D-060).
- **Affects:** R8; P-015; setting `assume_first_taken_is_apical`. **Open question:** OQ-006.

### D-015 Whether an inferred Fail counts as Fail is undecided
- **Date / by / status:** 2026-10-10 · Arnikan · undecided
- **Decision:** One setting, `inferred_fail_outcome`. Until it is decided, an inferred Fail is
  reported as Unable to Verify, flagged `inferred_fail_policy_undecided`.
- **Affects:** R8; P-015. **Open question:** OQ-005.

### D-017 Command names follow the proposal (A1–A6) and are provisional
- **Date / by / status:** 2026-10-10 · Arnikan · interim
- **Decision:** There are six action-specific command names: oxygen away, continue
  compressions, stand clear, stop compressions, shock, start compressions. All names and phrases
  are provisional until the medical-faculty supervisor confirms them.
- **Alternatives considered:** One combined "compressions command" (AI proposal), rejected
  because it does not say which action was meant.
- **Affects:** A1–A8, R7; P-003, P-011. **Open question:** OQ-010. **Resolved:** OQ-032.

### D-047 The real CVAT tag for "first paddle placed"
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** CVAT `first_paddle_firmly_on_the_chest` means `first_paddle_placed`. There are
  no separate apical or sternal placement tags, so those names stay placeholders.
- **Affects:** R2, R8; P-003. **Resolved:** OQ-003. **Open questions:** OQ-004, OQ-008.

---

## Evidence and coverage

### D-007 Coverage policy for a missing event: covered → Fail, not covered → Unable to Verify
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** If a required event is missing and the area or audio was clearly observable, the
  result is Fail. If it was not observable, the result is Unable to Verify. Rules never decide
  this themselves; one configurable policy does.
- **Affects:** all rules; P-008; Increment 4.

### D-008 Coverage "unknown" is undecided (interim: Unable to Verify)
- **Date / by / status:** 2026-10-10 · Arnikan · undecided
- **Decision:** When nobody knows whether the event was observable, the interim result is
  Unable to Verify, flagged `coverage_policy_undecided`. Changing the config is the only change
  needed once this is decided.
- **Affects:** all rules; P-008. **Open question:** OQ-001.

### D-009 Coverage by region, source and modality, from a timeline header
- **Date / by / status:** 2026-10-13 · Arnikan (agent proposal approved) · approved
- **Decision:**
  - **Where coverage comes from:** a header sent with each timeline (which analyses ran, and
    explicit coverage per camera region, source or modality). The most specific information
    wins.
  - **No header:** coverage is unknown.
  - **Outcome overrides:** each outcome can be overridden per region, source or modality.
- **Reason:** Without it, "no audio events" cannot be told apart from "audio not analysed".
- **Affects:** all rules; P-006, P-007, P-008; Increment 4. **Open question:** OQ-020.

### D-010 Low confidence is never absence
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** If an event is missing but a low-confidence detection of it exists, the result
  is Unable to Verify (`low_confidence_evidence`), **never Fail**. This is not configurable, and
  it includes low-confidence ambiguous commands that could have been the event.
- **Affects:** all rules; P-008, P-012, P-013; Increments 4, 5, 6.

### D-011 Event time is the start time
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** All order and timing comparisons use when an event **starts**. (The check that
  events fit inside the recording uses the end time; see D-034.)
- **Affects:** all timing rules; P-002 to P-012.

### D-012 Repeated events are kept
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** Every occurrence of an event is kept in time order; none is merged or dropped.
  Each rule decides which occurrence counts.
- **Affects:** all rules; P-003, P-012. **Open questions:** OQ-021, OQ-022, OQ-023.

### D-021 Duplicate merging and confidence thresholds belong upstream
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** Video postprocessing and audio command detection merge duplicate detections and
  choose their own thresholds. The rule engine keeps its own threshold check as a configurable
  safety net (a threshold of 0 disables it).
- **Affects:** P-004, P-005. **Open question:** OQ-019.

### D-029 Unknown labels raise a warning
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** Any label not in the vocabulary raises the `unknown_labels_present` anomaly, so
  the report shows a possible naming mismatch instead of silently treating the event as
  missing.
- **Affects:** P-003, P-005.

### D-030 Duplicate shocks are not merged
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** Two shock indications are not merged. The `multiple_shocks` anomaly records
  whether they fall within the simultaneous window ("possibly the same shock detected twice").
- **Affects:** R5 and every shock-dependent rule; P-005, P-009. **Resolved:** OQ-024.

### D-031 Human and model evidence for one event is flagged, not rejected
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** `mixed_evidence_sources` stays a flag.
- **Affects:** P-005. **Resolved:** OQ-025.

### D-032 One camera angle and one recording per timeline
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** A timeline mixing camera angles or recordings is rejected. Events with no camera
  angle (such as audio) do not count as a second angle.
- **Affects:** P-002. **Resolved:** OQ-026. **Open question:** OQ-038.

### D-034 Duration tolerance for the timeline header
- **Date / by / status:** 2026-10-13 · Arnikan · interim (placeholder value)
- **Decision:** An event may end up to `duration_tolerance_seconds` (placeholder 0.5 s) after
  the recording's stated duration. Beyond that, the header is rejected.
- **Affects:** P-006. **Open question:** OQ-018.

### D-035 Annotation timelines: video assumed covered, flagged
- **Date / by / status:** 2026-10-13 · Arnikan · interim (development assumption A-001)
- **Decision:** The annotation adapter declares `analyses_run: {video: true, audio: false}`.
  Every result built on an annotation timeline carries `annotation_coverage_assumed`, so it is
  never mistaken for a real assessment.
- **Affects:** P-001; Increment 10. **Resolved:** OQ-028.

### D-036 No time windows for coverage yet
- **Date / by / status:** 2026-10-13 · Arnikan · approved
- **Decision:** Coverage applies to the whole recording. The engine already accepts an optional
  time window per question, so windows can be added later without changing any rule.
- **Affects:** P-007, P-008. **Resolved:** OQ-027.

---

## Shock time and command timing

### D-023 Shock time falls back to paddle removal, flagged
- **Date / by / status:** 2026-10-13 · Arnikan · approved
- **Decision:** If no shock is confirmed on screen, the shock time is taken from the first
  paddle removal. Every timing result that uses it is flagged `shock_time_from_removal`.
- **Reason:** Removal happens after the shock, so delays measured from it look shorter.
- **Affects:** R6, R7/A6, A1–A5, A8; P-009, P-011, P-012.

### D-039 Multiple shocks: no shock time is chosen
- **Date / by / status:** 2026-10-13 · Arnikan · approved
- **Decision:** With more than one shock indication there is no shock time, not even from a
  removal. Shock-dependent facts are absent and flagged, never guessed.
- **Affects:** P-009 to P-012.

### D-040 Several candidates: use the earliest, record them all
- **Date / by / status:** 2026-10-13 · Arnikan · approved
- **Decision:** When a key time has several candidate events (for example two "first paddle
  placed"), the earliest is used, and all candidates are recorded and flagged.
- **Affects:** P-009, P-012. **Open question:** OQ-022.

### D-041 Ambiguous commands near the shock, or with no shock time, stay unresolved
- **Date / by / status:** 2026-10-13 · Arnikan · approved
- **Decision:** A "resume compressions" command within the simultaneous window of the shock
  (`command_near_shock`), or when there is no shock time (`no_shock_time`), is classified as
  neither continue nor start.
- **Affects:** A2, R7/A6, A7, A8; P-011.

### D-024 Under the removal fallback, commands before the removal stay unresolved
- **Date / by / status:** 2026-10-13 · Arnikan · approved
- **Decision:** When the shock time comes from removal, every "resume compressions" command
  before the removal time is left unresolved and flagged `command_before_removal`.
- **Reason:** The real shock was earlier than the removal, so "before removal" does not prove
  "before the shock".
- **Alternatives considered:** Classify it as continue, with a flag (the Increment 5
  behaviour).
- **Affects:** A2, R7/A6, A7; P-011. **Resolved:** OQ-029.

### D-025 The restart is the earliest start command after the shock
- **Date / by / status:** 2026-10-13 · Arnikan · approved
- **Decision:** For R7/A6 and A8, the "start compressions" anchor is the earliest start command
  after the shock. A start command at or before the shock does not count as the restart, and
  A7 reports it as a sequence problem (`start_command_before_shock`).
- **Affects:** R7/A6, A7, A8; P-012. **Resolved:** OQ-030. **Refined by:** D-053, D-054 and D-059, for the
  case where the shock time is not known exactly.

### D-053 A start command before the removal is timing-ambiguous, not a mistake
- **Date / by / status:** 2026-10-13 · Arnikan · approved
- **Decision:** Under the removal fallback, an explicit "start compressions" said before the
  removal is treated like a "resume compressions" there (D-024). The real shock happened at an
  unknown time before the removal, so the command may be a genuine restart. Therefore:
  - It does **not** count as the restart, and it is **not** treated as a mistake. It is flagged
    `command_before_removal` and listed as ambiguous, not as a start before the shock.
  - Rules that need the restart (R7/A6, A8) give **Unable to Verify, not Fail**, whenever the
    restart is ambiguous, even if a later start command exists.
  - A7 must **not** report it as a sequence error.
  - Each start command is checked on its own, so a later start after the removal can still be
    the restart.
- **Reason:** D-004 (never blame the learner for missing data) and consistency with D-024.
- **See also:** D-054 (the same principle when there is no shock time at all), and OQ-041
  (planned R7/A6 and A8 behaviour under the fallback).
- **Alternatives considered:** Treat it as a start before the shock, which does not count and
  is reported by A7 (the agent's A-014 proposal), rejected.
- **Affects:** R7/A6, A7, A8; P-012, P-014. **Resolved:** OQ-039.

### D-059 R7/A6 and A8 under the removal fallback
- **Date / by / status:** 2026-10-13 · Arnikan · approved
- **Decision:** When the shock time comes from paddle removal:
  - **Ambiguous restart:** an unresolved "resume compressions" before the removal (D-024) makes
    the restart ambiguous, exactly like an explicit start command before the removal (D-053).
    R7/A6 and A8 then give Unable to Verify.
  - **With no ambiguous command:** a start command after the removal is definitely the restart.
    It carries no fallback flag of its own.
  - **A8:** stop → restart does not depend on the shock time, so it is measured normally,
    without the fallback flag.
  - **R7/A6:** the delay measured from the removal is shorter than the real delay. If it
    already exceeds the limit, the result is a confident **Fail `too_late`**. If it is within
    the limit, the result is **Unable to Verify**, flagged `shock_time_from_removal`.
- **Reason:** The removal time is a lower bound for the delay since the real shock. A delay
  over the limit is therefore certain, and one within it is not.
- **Affects:** R7/A6, A8; P-012, P-014; Increments 21 and 23. **Resolved:** OQ-041.

### D-054 With no shock time, start commands are timing-ambiguous
- **Date / by / status:** 2026-10-13 · agent proposal approved by Arnikan · approved
- **Decision:** When there is no shock time at all (no shock and no removal, or multiple
  shocks), every "start compressions" command is listed as ambiguous: not counted as the
  restart, and **not** a mistake. A7 must not report it as a sequence error. Rules that need
  the restart are "not evaluable because of R5".
- **Reason:** The command's position relative to the shock is unknown, as in D-053. It was
  first included in D-053 and recorded separately on Arnikan's request.
- **Alternatives considered:** Listing them as ineligible, so A7 would report them (the
  Increment 5 behaviour), rejected.
- **Affects:** R7/A6, A7, A8; P-012.

---

## Engine design and configuration

### D-005 Rules in Python; clinical values in config, with provenance
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:**
  - Rules are written by developers in Python.
  - Clinical values (time limits) live in `configs/rules.yaml` with who provided and approved
    them, and when.
  - Unapproved values stay empty (null). A rule with an empty limit checks presence and order
    only, and says "timing not checked".
- **Affects:** all rules; Increment 2. **Open question:** OQ-016.

### D-006 Display order is separate from evaluation order
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** The order of rules in `rules.yaml` is the report and checklist order only. The
  engine works out the evaluation order from which rules need other rules' results; only
  circular dependencies are rejected.
- **Alternatives considered:** Evaluation order fixed in config (rejected: it would have
  refused valid configs).
- **Affects:** all rules; Increments 2 and 7.

### D-020 Canonical event names are emitted upstream
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** Video postprocessing and audio command detection emit the agreed names directly.
  `vocabulary.yaml` is a thin safety layer and the team's reference list of agreed names.
- **Affects:** P-003; [upstream_requirements.md](upstream_requirements.md).

### D-028 The rule engine does not change `configs/pipeline.yaml`
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** Audio command gaps are raised with Sanjeevan, not changed by the rule engine.
- **Affects:** OQ-009.

### D-061 A time limit with a value but no approver is ignored
- **Date / by / status:** 2026-10-14 · agent proposal approved by Arnikan · approved
- **Decision:** A clinical limit that has a value but no `approved_by` is not used. Timing is not
  checked, and the result is flagged `timing_not_checked` and `limit_not_approved`.
- **Reason:** D-005; clinical values are never invented or used before approval.
- **Affects:** every timed rule; P-024. **Resolved:** OQ-042. **See also:** D-062 (unchecked
  timing prevents an overall Pass).

### D-033 Approval date: structured `date_pending` flag
- **Date / by / status:** 2026-10-13 · Arnikan · approved
- **Decision:** An approved value may have no approval date only when its record says
  `date_pending: true`. Notes are human explanations only, and the system never reads them.
- **Alternatives considered:** Approver and date always together (Increment 2); approver
  without date allowed (`ddfa846`); a note-text check (Increment 4 draft). All replaced.
- **Affects:** Increment 4; D-016.

### D-037 Keep the new limit names and the unused limits
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** The new limit names are kept. `charge_to_shock_seconds` and every other unused
  limit stay empty, each with a note that no rule uses it yet.
- **Resolved:** OQ-034, OQ-035.

### D-038 No shared schema changes
- **Date / by / status:** 2026-10-10 · agent proposal approved by Arnikan · approved
- **Decision:** The shared event and rule-result formats are not changed. Extra detail (failure
  codes, flags, coverage) stays inside the rule engine.
- **Reason:** Ananth and Sanjeevan depend on the shared formats.

### D-045 Existing result statuses only
- **Date / by / status:** 2026-10-10 · agent proposal approved by Arnikan · approved
- **Decision:** Pass – Direct, Pass – Inferred and Fail use their existing statuses. Unable to
  Verify, "not evaluable" and "pending" all use `unable_to_assess`, told apart by their reason
  and flags.
- **Affects:** all rules; P-014.

### D-049 Missing settings are errors, not silent defaults
- **Date / by / status:** 2026-10-10 · agent proposal approved by Arnikan · approved
- **Decision:** Every engine setting must be present in config, and a missing or mistyped
  setting stops the run with a clear message.
- **Reason:** A silent default would change results without anyone noticing.

### D-050 Rejections and anomalies have stable codes
- **Date / by / status:** 2026-10-10 · agent proposal approved by Arnikan · approved
- **Decision:** Every rejection, anomaly and flag has a stable code, listed in
  [anomalies.md](anomalies.md) and in [decision_flow.yaml](decision_flow.yaml), and checked by
  a test.

### D-070 The JSON report is a versioned contract with the feedback module
- **Date / by / status:** 2026-10-14 · Arnikan; the version triggers are set by Arnikan · interim
  until Sanjeevan confirms (OQ-045)
- **Decision:** The report from `rules/render.py` carries `report_version` (now 1).
  [output_contract.md](output_contract.md) documents its structure and every result, flag and
  code that the feedback module may receive, with each code's status (built, planned, interim,
  undecided).
- **Version triggers:**
  - The version goes up whenever a report field or a code (overall result, rule kind, flag,
    anomaly, failure code or rejection) is **added, removed or renamed**, or its **meaning
    changes**.
  - A code already listed as planned **becoming built does not** change the version; only its
    status in the contract changes.
  - Every version change updates the contract and adds a changelog line.
- **Reason:** Sanjeevan builds the feedback module against this output. A versioned contract
  makes every change visible to him instead of silently breaking his code.
- **How it is kept true:** a test checks that the contract's version equals `report_version`,
  that its top-level keys and example match a real report, that its result tables match the
  code, and that it lists every code in [decision_flow.yaml](decision_flow.yaml) and every code
  the engine raises.
- **Affects:** P-027; Increment 9 onward. **Open question:** OQ-045.

### D-073 CVAT is frozen: names are mapped, never changed
- **Date / by / status:** 2026-10-14 · Arnikan · approved
- **Decision:** The CVAT project is frozen. Annotation is almost done and model training is about
  to start. The existing CVAT tags and component (track) names are used throughout the project
  and will not change.
  - Renaming or adding a CVAT label is never proposed. Any difference between a CVAT name and
    a canonical event name is handled by a mapping in `configs/rule_engine/vocabulary.yaml`.
  - The annotation entries `apical_paddle_placed` and `sternal_paddle_placed` in the vocabulary
    will therefore never be CVAT tags. They are planned as events derived by the rule engine's
    own exporter (Step 9c).
- **Reason:** Changing a label would invalidate annotations and training data that the whole
  team relies on.
- **Affects:** P-003; the vocabulary; Steps 9b and 9c.

### D-074 Annotation data for the rule engine comes from a separate exporter
- **Date / by / status:** 2026-10-14 · Arnikan · approved
- **Decision:**
  - **Ananth's dataset files are not modified:** `build_yolo_video_dataset.py`,
    `create_grouped_video_split.py`, `validate_yolo_dataset.py`, `events.jsonl`,
    `sample_manifest.csv`, the split files, and the existing audit script and its outputs.
  - **A separate exporter** reads the CVAT backups directly. It writes rule-engine annotation
    records to a separate output that the training pipeline never reads. The records contain:
    - every tag, including `first_paddle_firmly_on_the_chest`;
    - zone visibility from the zone tracks;
    - `stop_frame` and `duration_seconds`.
  - **The new annotation checks go in a separate audit script**, so the existing audit outputs
    don't change.
  - **Both run on the current backups now** and on the final backups once annotation is
    complete.
  - **A missing zone track means visibility unknown,** not "not visible".
  - **Off-pattern videos are listed for annotation review:** those whose zone tracks differ from
    their camera view's usual pattern, including the 6 with no zone track at all.
  - **The learner's procedure order is information only,** never an annotation issue.
  - **Thresholds (placeholders, accepted):** a zone moving more than 5% of the frame diagonal;
    repeated tags within 15 frames marked "possibly the same incident tagged twice".
- **Reason:** Training is about to start. The rule engine must not change any file that the
  training pipeline reads, or the image set it was built from.
- **Affects:** Steps 9b and 9c; Increment 10 (the adapter reads the exporter's output).
  **Resolves:** OQ-007, OQ-008.

### D-076 Video fps comes from the conversion report only
- **Date / by / status:** 2026-10-16 · Arnikan · approved
- **Decision:** The exporter takes each video's fps, width and height from
  `annotation/reports/phase4/video_conversion.csv` only, which it reads but never changes. There
  is no MP4 parser. A video missing from the report is an export issue (`fps_missing`), and no
  record is written for it. A frame count different from the report's is a warning.
- **Open question:** whether the converted videos have a constant frame rate is OQ-053 (Ananth).
- **Affects:** P-028. **Resolves:** OQ-047.

### D-077 The usual zone pattern per view is fixed in config
- **Date / by / status:** 2026-10-16 · Arnikan · approved
- **Decision:** `configs/rule_engine/annotation_export.yaml` `usual_zone_pattern` defines which
  zones each view normally shows:
  - LL: apical only;
  - LS: both;
  - T: both.

  The audit report prints the actual distribution per view beside it.
- **Affects:** P-029. **Resolves:** OQ-048.

### D-078 Output folders of the exporter and the audit
- **Date / by / status:** 2026-10-16 · Arnikan · approved
- **Decision:**
  - **Exporter:** writes to `data/rule_engine/annotation_export/<run>/`. It is not committed,
    and writing inside `data/video/` is refused.
  - **Audit:** writes to `annotation/reports/rule_engine_audit/<run>/`. These are small reports
    and can be committed, like the Phase 1 reports.
  - **Both** refuse a folder that is not empty.
- **Affects:** P-028, P-029. **Resolves:** OQ-049.

### D-079 The exporter reuses the training code by import, pinned by tests
- **Date / by / status:** 2026-10-16 · Arnikan · approved
- **Decision:**
  - **What is reused, by import only, from the existing scripts:** task discovery (from
    `audit_cvat_backups.py`) and box geometry (from `build_yolo_video_dataset.py`).
  - **So zone visibility always matches the training boxes:** a zone is visible on exactly the
    frames where the training dataset has a box for it (`track_box_at`, then `clip_box`).
  - **Tests pin the behaviour:**
    - the `track_box_at` behaviour itself;
    - the visible frames equal the frames on which `frame_boxes` returns the zone.
- **Affects:** P-028.
- **Resolves:** OQ-050.

### D-080 A zone track that is never visible means not covered
- **Date / by / status:** 2026-10-16 · Arnikan · approved
- **Decision:** A zone track that exists but is outside on every frame means the annotator saw no
  zone: coverage **not covered**. The audit lists it as information (`zone_track_never_visible`),
  not as an issue.
- **Affects:** P-029, P-030. **Resolves:** OQ-051.

### D-081 Derived per-paddle placements (Step 9c)
- **Date / by / status:** 2026-10-16 · Arnikan · approved (plan only; not built)
- **Decision:**
  - **Placeholders accepted:**
    - overlap ≥ 0.5 of the paddle box;
    - steady for 5 frames;
    - centre moving < 2% of the frame diagonal;
    - agreement with the tags within 15 frames.
  - **Evidence:** derived placements are **direct** evidence, flagged `derived_placement`, with
    the method in metadata.
  - **No event** when they disagree with the tags.
  - **Validation gate:** it needs `first_paddle_firmly_on_the_chest`, so it runs on the final
    backups. **R8 may not use derived placements until Arnikan has reviewed that report.**
- **Note (2026-10-16):** the smoke run found the tag already present in the corrected backups of
  one annotator. This doesn't change the gate.
- **Affects:** P-031; R8 (Increment 12). **Resolves:** OQ-052.

### D-082 The zone pattern is for the review list only; reviewed exceptions
- **Date / by / status:** 2026-10-16 · Arnikan · approved
- **Decision:**
  - **Where the usual pattern is used:** only by the annotation audit's review list. The rule
    engine never uses it, and it never affects a result.
  - **Reviewed exceptions:** `annotation_export.yaml` `reviewed_zone_exceptions` lists videos
    where an annotator confirmed that a zone was genuinely not visible. Each entry gives the
    task, the zone, `confirmed_by` and `confirmed_on`.
  - **Their effect:** those videos leave the review list (information
    `zone_exception_confirmed`), and Increment 10 treats the confirmed zone as **not covered**
    instead of unknown.
  - **A contradicted exception** (an exception for a zone that is visible) is put on the review
    list (`zone_exception_contradicted`).
- **Affects:** P-029, P-030.

### D-083 Ananth runs the exporter and the audit on the final backups
- **Date / by / status:** 2026-10-16 · Arnikan · approved
- **Decision:** The corrected CVAT backups are handed over to Ananth, and Arnikan no longer works
  with them. Ananth runs `export_rule_engine_records.py` and `audit_rule_engine_checks.py` on the
  final backup set, following [docs/annotation/rule_engine_export_howto.md](../annotation/rule_engine_export_howto.md).
  He sends Arnikan only:
  - `records.jsonl`;
  - `export_manifest.json`;
  - the audit outputs.

  He never sends any media. The scripts change nothing in his training data (D-074).
- **Open question:** when the final export will be available is OQ-054.
- **Affects:** P-028, P-029; Increment 10.

### D-084 Interim development data: the smoke-run export
- **Date / by / status:** 2026-10-16 · Arnikan · approved
- **Decision:**
  - Until the final export arrives, Increment 10 uses the smoke-run output of the 39 corrected
    backups as development data:
    - the records: `data/rule_engine/annotation_export/smoke-kartheepan/`;
    - the audit: `data/rule_engine/audit_smoke/kartheepan/`.
  - The data stays in the gitignored `data/rule_engine/` folder. **Exported records are never
    committed.**
  - P14_LS in this set is unreliable: `P14_LL.zip` contains a task named P14_LS, so the record may
    be either video.
- **Note:** this smoke run was made before D-085. Its manifest therefore hashed the whole ZIPs;
  nothing was opened or printed from the media. The exporter now hashes only the annotation JSON.
- **Affects:** Increment 10.

### D-085 Privacy: media in the CVAT backups is never read
- **Date / by / status:** 2026-10-16 · Arnikan · approved
- **Decision:** The CVAT backups may contain the video files.
  - Media content is never opened, listed in detail, or printed. Only the annotation JSON is
    read: `task.json` and `annotations.json`.
  - The exporter's manifest hashes only those two entries. A media entry's file name is used
    only to recognise the task.
  - A test checks that the export and the audit open no other ZIP entry.
  - Exported records and media are never committed.
- **Recorded in:** `agent_brief.md` (section 6, rule 8) and the agent's memory.
- **Affects:** P-028, P-029; Step 9c.

### D-086 Derived placements are checked against the tags, including parallel placement
- **Date / by / status:** 2026-10-16 · Arnikan · approved
- **Decision:** The tags are T1 (`first_paddle_firmly_on_the_chest`) and T2
  (`paddles_firmly_on_chest`), following the annotators' convention (A-019). The window is 15
  frames.
  - **T1 present, both paddles derived:** the earlier placement must be within the window of
    T1. If not, there is no event for **either** paddle.
  - **T1 present, one paddle derived** (for example a one-zone view): the placement must not be
    earlier than T1 minus the window. The visible paddle may be the second one.
  - **T1 missing, both placements within `simultaneous_window_seconds` of each other:** both
    events are kept, flagged **`possible_parallel_placement`**. R2 and R8 can then fail with
    `simultaneous` on positive evidence (OQ-056). The window is read from `engine.yaml`, so the
    exporter and the rule engine never differ.
  - **T1 missing otherwise:** no events.
  - **T2 is used only when present.** Each kept paddle's first placement must be at or before T2
    plus the window. In a parallel placement, both are dropped if either fails.
  - **Re-placement:** a re-placement counts only after the paddle has been out of its zone for
    `exit_frames` frames. This is a separate setting (placeholder 5), not `steady_frames`.
- **Reason:** A placement that contradicts the human tags is more likely a derivation error than
  a learner's mistake. No event is safer: R8 then reports Unable to Verify, not a wrong result.
- **Affects:** P-031; R2 and R8 (Increments 11 and 12). **Assumption:** A-019. **Open question:**
  OQ-056.

### D-087 Placements are derived per paddle label, across all its tracks
- **Date / by / status:** 2026-10-16 · Arnikan · approved
- **Decision:**
  - **Per label, never per track:** annotators sometimes used several tracks of one label, with
    different IDs. Placements are therefore derived per paddle **label**, across all its tracks.
    A track split in the middle of a placement is then not mistaken for a re-placement.
  - **Overlapping tracks:** frames where two tracks of the same paddle overlap (two boxes on one
    frame) produce no event. This applies from `exit_frames` before a placement until its end. It
    is a review issue, `placement_duplicate_paddle_box`.
  - **Fixing them is Ananth's job,** because overlapping tracks also affect the training labels.
    The how-to says so.
- **Affects:** P-031.

### D-088 The gate for R8: a review record tied to one export and one set of settings
- **Date / by / status:** 2026-10-16 · Arnikan · approved
- **Decision:**
  - **The record:** R8 may use derived placements only after Arnikan has reviewed the validation
    report. The review is recorded in `annotation_export.yaml`
    `derived_placements.reviewed_for_r8`: reviewer, date, the export's `export_id` (the SHA-256 of
    its `records.jsonl`) and its `placement_settings_sha256` (a hash of every 9c setting,
    including the parallel window).
  - **Its scope:** an approval doesn't apply to another export or to other settings.
  - **Enforcement:** by the Increment 10 adapter, through `derived_placements_approved()`. It is
    built and tested in Step 9c.
  - **The engine flag `derived_placement`** enters the output contract with R8, in Increment 12.
- **Affects:** P-031, P-001; Increments 10 and 12.

### D-089 The validation report supports tuning
- **Date / by / status:** 2026-10-16 · Arnikan · approved
- **Decision:**
  - **`placement_validation.csv`,** for each video and paddle:
    - the highest overlap reached;
    - the steady frames achieved (up to 50);
    - the centre motion over the best steady window;
    - frames with the zone not visible;
    - frames with overlapping boxes;
    - the gap to T1;
    - the outcome and its reason;
    - the flags.
  - **`placement_validation.md`:**
    - the distributions of overlap, steady frames, motion and gap;
    - the count of videos with possible parallel placement;
    - the agreement with T1;
    - the no-event reasons;
    - every disagreement;
    - the `export_id` and the settings hash.
  - Ananth sends both files with the records. They contain no media.
- **Affects:** P-031.

### D-090 A frame where the zone isn't visible is unknown for a placement
- **Date / by / status:** 2026-10-16 · Arnikan · approved (it changes A-020's first version)
- **Decision:** For derived placements, a frame with exactly one box of the paddle but no visible
  zone box is **unknown**, neither in nor out of the zone.
  - It doesn't start a placement episode and doesn't end one.
  - If the paddle is in its zone on both sides of the gap, it is the same episode.
  - Only out frames count towards `exit_frames`. Unknown frames between them are skipped.
  - The not-visible frames are still counted per paddle in the validation report.
- **Reason:** otherwise a zone occlusion longer than `exit_frames` would invent a re-placement.
- **Affects:** P-031. **Assumption:** A-020.

### D-091 A possible parallel placement is enough for a Fail, once the gate is approved
- **Date / by / status:** 2026-10-16 · Arnikan · approved
- **Decision:** Derived placements flagged `possible_parallel_placement` are enough for R2 and R8
  to **Fail** with `simultaneous`. They need no extra review, but **only once the gate is
  approved** for that export and its settings, as for every derived placement (D-088). Before
  that, the Increment 10 adapter doesn't pass them on, and the rules can't use them.
- **Affects:** R2, R8 (Increments 11 and 12); P-031. **Resolves:** OQ-056.

---

## Working method

### D-063 A rule that raises an error is recorded, never skipped
- **Date / by / status:** 2026-10-14 · Arnikan · approved
- **Decision:**
  - A registered rule that raises an exception, or returns something invalid (not an outcome, the
    wrong rule ID, or evidence outside the timeline), gets the result **`engine_error`**,
    including the error message.
  - Every other rule is still evaluated.
  - Rules that depend on it are **not evaluable because of it**.
  - It makes the overall result **incomplete**, never Pass.
- **Reason:** One broken rule must not stop the assessment (D-002), and must not disappear
  silently from the report.
- **Exception kept on purpose:** a rule configured by `implementation: module:function` (the
  shared contract in `docs/contracts.md`) that breaks the contract still stops the run, as the
  shared contract test requires. Malformed input and invalid config also still stop the run
  (P-002, D-049).
- **Affects:** all rules; P-017, P-026; Increments 7 and 8.

### D-064 Rules register themselves next to their logic
- **Date / by / status:** 2026-10-14 · Arnikan (brief §3) · approved
- **Decision:** A rule is a Python function marked `@rule("A3", requires=(...))`, declaring its
  ID and the events it reads. The engine discovers every `*_rules` module in `rules/`, so adding
  a rule needs no engine change. Display order, status, dependencies and clinical values stay in
  `rules.yaml` (D-005, D-006).
- **Load-time checks (2026-10-14, Arnikan):** when the engine loads, the registered rules must
  match `rules.yaml`. Each mismatch is a clear error with a code, and no assessment is produced:
  - an approved rule with no registered implementation (and no implementation path) is an error
    (`approved_rule_not_registered`), **not** a pending result;
  - two different implementations for one rule ID is an error naming both locations
    (`duplicate_rule_registration`);
  - a registered rule ID that is not in the **full catalogue** in `configs/rules.yaml` is an
    error, probably a typo (`registered_rule_not_in_config`). This is checked against the
    catalogue whatever config is being assessed, so copying the config elsewhere cannot hide an
    unknown ID. A smaller config (for example a one-rule test config) only decides which rules
    are evaluated; registered rules outside it are simply not run, and that is not an error;
  - an event the rule declares must exist in the vocabulary (`unknown_required_event`).
- **Affects:** all rules; P-026; Increment 7. **Resolved:** OQ-043.

### D-022 The shared contract test is updated as rules change
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** The rule count in `tests/test_pipeline_contracts.py` was changed from 14 to 16.
  It is updated whenever rules are added or removed, and every change is logged.
- **Alternatives considered:** Generalising the test (AI recommendation), rejected.

### D-026 No Claude attribution in commits
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** Commit messages carry no Co-Authored-By or other AI attribution. AI use is
  disclosed in [ai_usage_log.md](ai_usage_log.md). Commit messages are shown before
  committing.

### D-075 Commit and push only on explicit instruction
- **Date / by / status:** 2026-10-14 · Arnikan · approved
- **Decision:** The agent commits only when Arnikan explicitly tells it to commit, and pushes
  only when explicitly told to push (`feature/rule-engine` only). This includes
  documentation-only commits. It replaces every earlier commit rule. Still in force: the commit
  message is shown before committing, and no commit carries Claude attribution (D-026).
- **Reason:** Arnikan controls what enters the history and the remote. The OQ-046 decision was
  committed as a separate commit without its message being shown first.
- **Recorded in:** `agent_brief.md` (section 6, rule 7), `implementation_plan.md` (section C),
  and the agent's memory.

### D-046 Environment and dependencies
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** All commands run in `.venv` (Python 3.11). No new heavy dependencies. Work
  happens on the `feature/rule-engine` branch.

### D-048 Charging-sound packages are not installed locally
- **Date / by / status:** 2026-10-10 · Arnikan · approved
- **Decision:** The one charging-sound test that is skipped locally is run by CI.
- **Resolved:** OQ-031.
