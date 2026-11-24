# Rule engine: open questions in one table

**For:** the medical supervisor, Sanjeevan, Ananth and the team · **Date:** 2026-11-24 · **Source:**
the register [open_questions.md](open_questions.md), which has each question's full history.

Every **open** question, grouped by who must answer it. "Meanwhile" is what the rule engine does until
the answer comes; nothing waits on an answer to run. Rule IDs: R1–R8 are the video rules, A1–A8 the
audio (spoken command) rules, R7/A6 one check reported under two IDs, S1 the procedure order. Decisions
are D-, pathways (decision points) P-. Answered questions are listed at the end.

## For the medical supervisor

| ID | Question | Why it matters | Meanwhile | Affects |
|---|---|---|---|---|
| OQ-002 | When no rule fails but some steps couldn't be verified, is the overall result Fail or "faculty review"? | It decides whether gaps in the evidence ever fail a learner | Reported as Unable to Verify, never Pass, flagged `overall_policy_undecided` (D-042) | the overall result (P-017) |
| OQ-010 | Which command names, accepted phrases and order are confirmed? | The audio rules can't give a reliable result until the wording is approved | The proposal's names, marked provisional (D-017) | A1–A8, R7/A6 |
| OQ-065 | Which phrases are accepted for each command? | The audio detector matches phrases; the lecturer's phrases are only proposed | The proposal's examples and the lecturer's phrases, provisional | the audio command events (Sanjeevan's phrase list) |
| OQ-012 | Which chest regions are approved, and what counts as a paddle outside its zone? | Without them R3 can judge *when*, not *where*, a paddle was placed | R3 checks timing and presence only; never `not_in_zone` (D-106) | R3 |
| OQ-016 | What are the missing clinical time limits? (gel period, shock → removal, shock → restart, stop → shock, how early the shock command may come, oxygen away and stand clear before the shock) "No limit" is a valid answer | Without a limit, timing can't be checked | Timing not checked, so the overall result stays Incomplete, never Pass (D-005, D-062, D-103) | R1, R6, R7/A6, A4, A5, A1, A3 |
| OQ-021 | Is gel applied more than twice a mistake? | Defines R1 for repeats | Passes; every application is kept (D-012) | R1 |
| OQ-022 | Are paddles lifted and placed again before the shock acceptable, and which placement counts? | Defines the placement time for R2, R3, R8 | The earliest placement counts; repeats are flagged, never a Fail by themselves (D-040) | R2, R3, R8 |
| OQ-023 | Are the buttons pressed more than once acceptable, and which press counts? | Defines R4 for repeats | Any valid press counts (D-012, D-108) | R4 |
| OQ-057 | Are you content that the shock time comes only from the screen? | In a view without the screen, every rule needing the shock time is "not evaluable because of R5" | No shock time without the screen; never estimated (D-093, D-115) | R3, R4, R6, R7/A6, A1–A8 |
| OQ-059 | Does a parallel placement (both paddles at once) count as one mistake or two? | It fails R2 and R8, each on its own evidence (D-119) | Two mistakes, both flagged `possible_parallel_placement` so the feedback can say one action caused both | R2, R8, the feedback |
| OQ-061 | Should the shock on the screen still infer R3 and R4 when the zones or paddles were in view and the step wasn't seen? | While it infers, R3's `missing` and R4's `not_pressed` can't be produced | The inference applies (D-102, D-115) | R3, R4 |
| OQ-062 | Is the complete order of the audio and video steps confirmed? | S1, A7 and every order relation follow it | The lecturer's interim order (D-127), marked NOT clinically approved; unknown pairs are not checked | S1, A7, every order relation |
| OQ-063 | Which steps, if any, may swap? | A swap allowed by you must not fail a learner | None, except the gel and "applying gel" (said together) | S1, A7 |
| OQ-064 | Is the procedure order (S1) its own checklist item? | Decides whether S1 appears in the evaluator checklist | S1 is built (Increment 27, P-046), pending, and held back in the demo | S1, the checklist |
| OQ-072 | Is the spoken "charging" a compulsory command? | If yes, a presence rule (A9) is needed | Optional: its position is checked when said, never reported missing | the charging step |
| OQ-073 | Is the spoken "applying gel" compulsory? | As charging | Optional, as charging | the "applying gel" step |
| OQ-074 | Does the defibrillator's charging sound count as evidence for charging? | The audio branch detects it already | Only the spoken command is the step | the charging step |
| OQ-075 | Is the shock command (A5) required, and where does it go among the shocking actions? | The lecturer gave none, so a required A5 would fail his demonstration | A5 built, pending, held back in the demo; only stop → shock command and shock command → shock are checked | A5, A7, S1 |
| OQ-076 | Is the pre-shock pause (A8) stop → start, or stop → shock? | On a lecturer-like timeline stop → start is 6–8 s (Fail), stop → shock 3–4 s (Pass) | Stop → start (the approved definition, D-016); A8 held back in the demo; a change is one config value | A8 |
| OQ-077 | Must oxygen away, stand clear and continue be in exactly this order? | Another correct order (for example "continue" first) would otherwise fail | Strict; a swap would be a config change (an interchangeable group) | A7, S1 |

## For Sanjeevan (audio command detection and feedback)

| ID | Question | Why it matters | Meanwhile | Affects |
|---|---|---|---|---|
| OQ-009 | When will the missing command events come: stop compressions, the shock command, and a separate start command (with word timestamps)? | Without stop and shock, A4, A5 and A8 can't judge real recordings; without a separate start and word times, a restart said at the shock stays unresolved (top priority) | Placeholder names are ready; "resume" is resolved by its position relative to the shock (P-011) | A2, A4, A5, R7/A6, A7, A8 |
| OQ-068 | What signal and format will give the clear-audio intervals? | A missing or misplaced command can fail only where the audio was clear (D-122, D-128) (top priority) | Without them a missing command is Unable to Verify, never Fail | every missing-command and audio wrong-place result |
| OQ-066 | Is non-standard phrasing matched strictly or leniently? | Lenient matching finds more commands but risks false ones | Strict (approved phrases only) | the command events; A1–A8, R7/A6 |
| OQ-045 | Do you confirm the output contract's versioning rule? | The feedback module reads the report | D-070 is applied as written, interim | the report (P-027), the feedback module |

## For Ananth (video models and pipeline)

| ID | Question | Why it matters | Meanwhile | Affects |
|---|---|---|---|---|
| — | Visibility intervals for every region (both placement zones, the screen, the paddles, the learner's hand), in the annotation adapter's header format (top priority, upstream_requirements.md) | Without them every video "wrong place" Fail and every missing step is Unable to Verify (D-092, D-128) | Annotation timelines carry visibility from the CVAT tracks; model timelines have none yet | all video rules |
| OQ-004 | Who produces the per-paddle placement events? | R8 needs both placements | The names are placeholders; without them R8 is Unable to Verify | R8, R3 |
| OQ-020 | Can the timeline header be provided, and in what format? | Without it, "no audio events" can't be told from "audio analysis didn't run" | No header: coverage unknown, so missing events are Unable to Verify (D-008, D-009) | all rules |
| OQ-017 | When will the pipeline call the full rule-engine assessment? | The pipeline report lists the rule results only, without the overall result | The rule engine's own command (`rules.run`) gives the full report | all rules (P-017, P-018) |
| OQ-053 | Are the converted videos constant frame rate? | Video and audio times are compared (R7/A6, A8) | Constant frame rate assumed; fps read per video | all annotation times |
| OQ-054 | When will the final annotation export be available? | The derived placements and gel (Steps 9c, 9d) are reviewed on it | The interim export is used as development data (D-084) | the development data |
| OQ-055 | Does anything take the camera view from the backup file name? | One backup's name clashes with its content | P14_LS in the interim data is treated as unreliable (D-084) | Ananth's split and dataset |

## For Arnikan and the team (with the supervisor where noted)

| ID | Question | Why it matters | Meanwhile | Affects |
|---|---|---|---|---|
| OQ-001 | When it's unknown whether a step could have been seen, Fail or Unable to Verify? (with the supervisor) | Fail would fail learners for what a camera never showed | Unable to Verify, flagged `coverage_policy_undecided` (D-008) | all rules (P-008) |
| OQ-006 | May "the paddle taken first was also placed first" be assumed when no placement is seen? (with the supervisor) | A last-resort inference for R8 | Off (D-014) | R8 |
| OQ-015 | Final IDs for R8 and A8 (with the supervisor) | Naming in the checklist and the report | "R8" and "A8" | R8, A8 |
| OQ-036 | The evaluator checklist format and which rules feed each item (with the supervisor) | The checklist is the human-facing output | One item per rule (planned, not built) | the checklist (P-018) |
| OQ-018 | The engineering placeholder values (windows, thresholds) | They decide ties and low confidence | Placeholder values (A-002), never tuned on any dataset | R1, R2, R3, R6, R8; P-004 to P-006, P-011 |
| OQ-019 | Which side applies the confidence thresholds? | Double thresholds could hide evidence | The rule engine applies its placeholder thresholds as a safety check (D-021) | P-004 |
| OQ-037 | The model output formats and the meaning of confidence | The input adapters depend on them | Development uses annotation timelines | P-001, P-004, P-007 |
| OQ-038 | The final camera angle | Which zones and the screen are in view | Any single angle is accepted; mixing angles is rejected (D-032) | all video rules |

## Answered questions

| ID | Question | Answer | Decision |
|---|---|---|---|
| OQ-078 | S1: how to judge relations across a missing or unseen step? | Per recording, from the observed steps; a step another rule reports is left to it | D-131 |
| OQ-071 | Should S1 own relations other relations already imply? | No (option B) | D-126 |
| OQ-070 | Should charging be a step in the procedure order? | Yes, an optional step of the interim order | D-127 |
| OQ-067 | Audio input: command events or a raw transcript? | Sanjeevan's command events | D-125 |
| OQ-069 | Which phrase list is the single source? | `configs/pipeline.yaml` (the audio branch) | D-125 |
| OQ-060 | Should a paddle removal support an inferred Pass for R3 and R4? | No: a removal is never evidence of a shock | D-115 |
| OQ-058 | R2 in a parallel placement before the 9c gate | A first placement not observed is its own failure code | D-097 |
| OQ-056 | Is `possible_parallel_placement` alone enough for a Fail? | Yes, once the gate is approved | D-091 |
| OQ-052 | Derived placements: settings, evidence type, disagreement with tags | Step 9c as specified | D-081 |
| OQ-051 | A zone track that is never visible | Not covered | D-080 |
| OQ-050 | Reuse the training scripts by import or copy them? | By import, pinned by tests | D-079 |
| OQ-049 | Output folders of the exporter and the audit | The export under the gitignored `data/rule_engine/`; the audit's small reports under `annotation/reports/` | D-078 |
| OQ-048 | The usual zone pattern: computed or configured? | Configured per view | D-077 |
| OQ-047 | Where does the exporter get each video's fps? | The conversion report only | D-076 |
| OQ-046 | Do count anomalies block an overall Pass? | Yes; no events at all is a missing event | D-072 |
| OQ-044 | Which timeline anomalies block an overall Pass? | All three review anomalies, before the Unable-to-Verify setting | D-069 |
| OQ-043 | The registry check versus minimal test configs | Rules register themselves next to their logic | D-064 |
| OQ-042 | Is a time limit with a value but no approver used? | No: ignored, flagged `limit_not_approved` | D-061 |
| OQ-041 | R7/A6 and A8 under the removal fallback | Answered, then withdrawn with the fallback | D-059 (withdrawn by D-115) |
| OQ-040 | R8 when a placement event is missing | Unable to Verify, no inference | D-058 |
| OQ-039 | A start command before the removal under the fallback | Timing-ambiguous; withdrawn with the fallback | D-053 (withdrawn by D-115) |
| OQ-035 | Keep the unused `charge_to_shock_seconds`? | Yes | D-037 |
| OQ-034 | New time-limit names | Kept | D-037 |
| OQ-033 | Use a provided but unapproved clinical value? | No | D-016 |
| OQ-032 | Canonical names, one "compressions command" | The proposal's names, provisional | D-017 |
| OQ-031 | Install the charging-sound packages locally? | No; CI runs that test | D-048 |
| OQ-030 | Which start command counts as the restart? | The earliest start not before the shock | D-025 |
| OQ-029 | Commands between the real shock and the removal | Answered under the fallback, then withdrawn | D-024 (withdrawn by D-115) |
| OQ-028 | `analyses_run` for annotation timelines | Video assumed covered, flagged | D-035 |
| OQ-027 | Time-windowed coverage | Not at first; replaced by windowed coverage for the placement zones | D-036 (replaced by D-092) |
| OQ-026 | One camera and one recording per timeline as a hard error? | Yes | D-032 |
| OQ-025 | Reject mixed human and model evidence? | No: flagged | D-031 |
| OQ-024 | Merge duplicate shocks? | No | D-030 |
| OQ-014 | Approval of the A8 5-second limit | Approved by the supervisor | D-016 |
| OQ-011 | The A7 / A4 overlap | A7 checks the order only; A4 owns stop before continue | D-027 |
| OQ-008 | Label lists that drop the first-placement tag | A separate exporter | D-074 |
| OQ-007 | Zone visibility for annotation timelines | From the CVAT tracks, through the exporter | D-074 |
| OQ-003 | The real CVAT tag for "first paddle placed" | `first_paddle_firmly_on_the_chest` | D-047 |
| OQ-013 | Which steps must precede the shock (R5)? | Closed: superseded; each step's own rule judges its place before the shock | D-123 |
| OQ-005 | Does an inferred Fail count as a Fail? | Closed: no longer applicable (no inferred Fail since D-116) | D-116 |
