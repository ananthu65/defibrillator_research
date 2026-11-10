# Audio rules and the combined procedure flow: integration plan

**Status:** approved plan (Arnikan, 2026-10-20; Step 0 re-sync approved 2026-11-09). **Decisions:**
D-120 to D-125.
The procedure order below is **NOT clinically approved**: it is a draft for the supervisor.
Synthetic timelines only; no dataset is used to tune or conclude anything.
**Step 0 re-sync (2026-11-09):** see section 10. Changes from it are marked **[2026-11-09]**
and were approved by Arnikan on 2026-11-09 (D-125).

The procedure is **one combined flow** (D-120). Every audio and video step has a defined position
relative to the others, and any mistake, in a step or in the order, fails the procedure. The
audio rules (A1–A8, R7/A6) are not a separate system. They run in the same engine, over the same
merged timeline, in the same evaluation order, with the same procedure context. Order source: the
ARTS proposal (Figure 2 and the audio command sequence in §5.2.2).

## 0. What already exists (reused, not rebuilt)
- **`rules/context.py`:**
  - the anchors `continue_compressions`, `stop_compressions` and `start_compressions` (the
    earliest start after the shock, D-025);
  - `phase_of(time)`, which gives before, at or after the shock;
  - the shock time, from the screen only (D-093);
  - `resolve_by_shock` for `resume_compressions_command` (P-011, D-041);
  - `ineligible` / `ambiguous` starts (D-053) and low-confidence candidates (P-013).
- **`configs/rule_engine/vocabulary.yaml`:**
  - all six command events exist (provisional);
  - the label `resume_compressions_command` is resolved by shock;
  - continue, stop, shock and start are placeholders.

  **No new canonical events are needed.**
- **`rules/coverage.py`:** policy by modality and region, the header's `analyses_run` and
  `visibility` intervals, and `region_status`.
- **`configs/rules.yaml`:** `pre_shock_pause_seconds` = 5 (approved, date pending). The limits for
  R7/A6, A4 and A5 are null.
- **`rules/checks.py`:** `relation()`, `requires()` and the limit checks.

## 1. Shared context additions (where each lives)
| Addition | Where | What |
|---|---|---|
| Command times | `rules/context.py` `ANCHOR_EVENTS` | Add `oxygen_away`, `stand_clear` and `shock_command` anchors, beside continue, stop and start |
| Phase split | `context.phase_of` + `resolve_by_shock` (exists) | "Continue/resume" before the shock is A2, after it R7/A6. With no shock time, or close to it, it stays unresolved (D-041) and is **unseen** for both |
| Audio coverage | `engine.yaml` region `audio` (all six command events), from header `visibility["region:audio"]` (clear-audio intervals) and `analyses_run.audio` | Within a clear interval, a missing command is "covered" and may Fail. **No clear-audio intervals → "unknown" → Unable to Verify, never Fail** (D-122). Audio not run → not covered |
| Cross-modal tolerance | `engine.yaml` `cross_modal_tolerance_seconds: {value: 1.0, placeholder: true}` | For any audio–video comparison (Whisper timestamps are approximate). Same-modality comparisons keep `simultaneous_window_seconds` |
| Tolerance-aware comparison | `rules/checks.py` `relation_between(a, b, ctx)` | Picks the window from the events' modalities, then calls `relation()` |
| Partial-result convention (D-121) | `rules/checks.py` helper + `rules/outcome.py` | Any judgeable part shows a mistake → Fail. Else, a part can't be judged because of X → Not evaluable because of X, with the checked parts in the reason and evidence. Else → Pass |
| Procedure order | `configs/rule_engine/procedure_order.yaml` + `rules/procedure.py` | Section 2 |
| **[2026-11-09]** Segment-timed audio events | `rules/checks.py` (with `relation_between`) | Today's command events carry the Whisper **segment's** start and end, not the word's (section 10). Such an event may lie anywhere in `[start, end]`. "X before Y" is broken only when X is certainly after Y (beyond `w`); overlapping intervals are a tie. Two commands in one segment: their mutual order isn't checked (`order_partially_checked`). A time limit (A8, R7/A6, A4) is judged on bounds: Fail only if the shortest possible duration exceeds it, Pass only if the longest possible is within it, otherwise Unable to Verify, flag `timing_uncertain`. Events with word timing (when available) use their start |

Audio and video clock alignment stays upstream (`configs/pipeline.yaml` `offsets`, unchanged,
D-028).

## 2. Procedure order as config (a precedence graph), NOT clinically approved
`procedure_order.yaml` holds `approved_by: null` and `source: ARTS proposal (Figure 2, §5.2.2)`.
It contains:

**Steps**, each with its event(s):

| Step | Event(s) |
|---|---|
| `R1` | gel |
| `R2A` / `R2B` | the paddle taken first / second (by time, D-118) |
| `PLACE` | the earliest firm placement (R2/R8) |
| `R3` | `paddles_firmly_on_chest` |
| `R4` | `both_paddle_buttons_pressed` |
| `R5` | `shock_delivered_on_screen` |
| `R6` | `paddles_removed_after_shock` |
| `A1` / `A2` / `A3` / `A4` / `A5` | O₂ away / continue / stand clear / stop / shock command |
| `R7` | `start_compressions_command` (after the shock) |

**Relations** ("X before Y"), each with its source:

| Relation | Source |
|---|---|
| R1 → PLACE ("gel before paddle placement") | proposal R1 |
| R2A → PLACE → R2B (one paddle at a time, as built) | proposal Figure 2; D-051, D-118 |
| PLACE → R3 → R4 → R5 → R6 → R7 | proposal Figure 2; R4 "after placement, before shock confirmation"; R6; R7 |
| A1 → A2 → A3 → A4 → A5 → R5 → R7 | proposal A7 sequence; A1–A5 "before shock"; A6/R7 "after shock" |
| **A5 → R4** (the shock command before the button press) | Arnikan, **for supervisor confirmation** (OQ-062) |

**Status of the order (2026-11-10):** Arnikan has asked the medical supervisor for the complete
order (OQ-062). Until it arrives, the config holds only what the proposal states: the visual
sequence, the audio command sequence, their before/after-the-shock links, and A5 before R4 (pending
confirmation). Everything else is "unknown" and unchecked. Section 11 explains how to apply the
complete order.

**Unknown:** pairs the proposal is silent on. They are not checked, and they are listed in
OQ-062:
- A1, A2, A3, A4 and A5 relative to R1, R2A/PLACE/R2B and R3 (for example, may "O₂ away" come
  before the gel?);
- A1–A4 relative to R4 follow only through A5 → R4.

**Interchangeable:** groups whose mutual order is free (empty for now; OQ-063). A change is
config only.

**Owners:** section 3.

**The loader checks:**
- the graph is acyclic (an error names the cycle);
- every step's event is in the vocabulary;
- every pair in the transitive closure, apart from the unknown pairs, has exactly one owner.

## 3. One owner per order relation (D-123)
| Relation | Owner | Built? |
|---|---|---|
| R2A → PLACE → R2B | R2 | yes |
| Apical before sternal (inside PLACE) | R8 | yes |
| R1 → PLACE | R1 (`after_placement`) | yes |
| R3 → R5 | R3 (`placed_after_shock`) | yes |
| R3 → R4, R4 → R5 | R4 (`before_placement`; the `contradictory` case) | yes |
| R5 → R6 | R6 (`removed_before_shock`) | yes |
| A1 → R5, A3 → R5 | A1, A3 (`after_shock`) | planned |
| A2 → R5 | A2 (`wrong_stage`) | planned |
| A2 → A4, A4 → R5 | A4 (`wrong_order`, D-027; `after_shock`) | planned |
| A5 → R5 | A5 (with the tolerance once approved) | planned |
| R5 → R7 | R7/A6 (`before_shock`) | planned |
| The other audio–audio pairs (A1…A5, R7) | **A7** (`wrong_order`) | planned |
| Every remaining pair: PLACE → R3, R6 → R7, A5 → R4, and the transitive video and cross-modal pairs | **S1 "Procedure order"** (new, `wrong_order`) | new |

- **R5's `preceding_steps` is retired** (D-123): each X → R5 pair is owned by X's rule.
- **A7's `depends_on` is removed** (D-123): A7 and S1 read events, not rule results.
- **One step may break two relations** owned by different rules. Each rule then fails on its own
  evidence (D-119). No relation is judged twice.

## 4. Order-check method (S1, and A7 on its own pairs)
The **minimum set of misplaced steps** is the smallest set whose removal leaves every remaining
observed step consistent with the rule's own relations. For a total order, these are exactly the
steps outside the longest correctly ordered subsequence. Unlike that subsequence, this form also
handles a partial order (interchangeable groups), repeats and ties.
- **Consistency:** X → Y holds when `t_Y ≥ t_X − w`. Here `w` is the cross-modal tolerance across
  modalities, else the simultaneous window. A difference within `w` is a tie and satisfies either
  order.
- **Repeats:** any occurrence in the right position counts. For each candidate set of kept steps,
  a topological sweep takes each step's earliest occurrence at or after its kept predecessors
  (minus `w`). Earliest is optimal, because the constraints only push later steps later.
- **Search:** at most 15 steps. Kept sets are tried from the largest down, so the search is
  deterministic.
- **Missing steps** are left out: their own rule reports them.
- **Unseen steps** are left out: not observable, unknown audio coverage, low confidence, a
  non-standard phrase (lenient mode), or an unresolved continue or start command. The result is
  then flagged **`order_partially_checked`**, never a clean Pass.
- **Ties between equal-size solutions:** never broken arbitrarily, because blaming one step on
  another step's evidence would break D-119.
  - A step in **every** minimum solution is reported **misplaced**.
  - Steps in some minimum solutions but not all are reported as **one ordering mistake between
    them** (for example, "A5 and R4 are in the wrong order").
  - Either way it is one `wrong_order` Fail, listed in expected order.
- **Result:**
  - fewer than two observed steps → Unable to Verify;
  - none misplaced → Pass, flagged if the check was partial;
  - otherwise Fail `wrong_order`, with the misplaced steps and their times.

## 5. Each audio rule (partial-result convention, D-121)
A "missing" command is judged from audio coverage alone: Fail only within a clear-audio
interval, otherwise Unable to Verify.

| Rule | Events (modality) | References (modality) | A reference missing | Still checked | Failure codes |
|---|---|---|---|---|---|
| A1 Oxygen away | `oxygen_away_command` (audio) | shock time (video, R5) | Not evaluable because of R5 (timing) | presence | `missing`, `after_shock` |
| A2 Continue | `continue_compressions_command`, or a resume/continue phrase resolved before the shock (audio) | shock time (video) | An ambiguous phrase stays unresolved; an unambiguous continue → Not evaluable because of R5 (stage) | presence | `missing`, `wrong_stage` |
| A3 Stand clear | `stand_clear_command` (audio) | shock time (video) | as A1 | presence | `missing`, `after_shock` (no severity levels: the proposal's "Safety-Critical" is a plain Fail) |
| A4 Stop | `stop_compressions_command` (audio) | shock time (video); continue (audio, A2) | Not evaluable for `after_shock` because of R5, and for `wrong_order` because of A2 | presence; whichever order part has its reference | `missing`, `after_shock`, `wrong_order`; `stop_to_shock_seconds` null → `timing_not_checked` |
| A5 Shock command | `shock_command` (audio) | shock time (video) | Not evaluable because of R5 (timing) | presence | `missing`; `after_shock` once `shock_command_tolerance_seconds` is approved. Its failure never affects R5 (proposal; D-119) |
| R7/A6 Restart (one check, two IDs, D-044) | `start_compressions_command`, or a resume phrase resolved after the shock (audio) | shock time (video, screen only, D-115; the proposal's removal fallback is withdrawn) | Not evaluable because of R5 (timing); no start command at all → judged by coverage | presence; `before_shock` | `missing`, `before_shock`, `too_late`; limit null → `timing_not_checked` |
| A7 Command order | all commands (audio) | — | missing or unseen commands left out (section 4) | the order of the commands present, on its own pairs | `wrong_order` (each Ax owns its own `missing`) |
| A8 Pre-shock pause (5 s, approved) | stop (A4) and restart (R7) (audio) | shock time, to find the restart (video) | Not evaluable because of A4, R7 or R5 | — | `pre_shock_pause` ("Pre-Shock Pause") |
| S1 Procedure order (new) | every step (both modalities) | — | section 4 | section 4 | `wrong_order`; flag `order_partially_checked` |

**Also under D-121:** R3, R4 and R6 will judge the part that needs no shock time:
- R3: whether the paddles were placed at all;
- R4: the press, and its order against the placement;
- R6: whether the paddles were removed at all, never as evidence of a shock (D-115).

## 6. Audio input (D-125: Sanjeevan's command events)
**[2026-11-09]** The input is the command events produced by Sanjeevan's pipeline (Whisper →
`detect_commands`, the shared `Event` schema), D-125. This answers OQ-067; Sanjeevan is to confirm
it is final. The engine reads these events and never imports `audio/`. The raw transcript (b) is a
fallback only if the input format changes (D-124).
- **(a) Command events** (preferred: Sanjeevan's command detection) use the existing `Event`
  schema:
  - `event_name`: a canonical command, or `resume_compressions_command` where the stage is
    unknown;
  - `start` / `end`: seconds on the shared clock; `start` is the start of the utterance or of the
    command's first word;
  - `source: audio`, `confidence` 0–1 (its meaning is OQ-037), `event_id`, `camera_angle: null`;
  - optional `metadata` (phrase, model).
- **(a) exists today [2026-11-09]:** the pipeline (`pipeline/run.py`) runs Whisper
  (`audio/asr/whisper.py`), then Sanjeevan's `audio/commands/detect.py`. Each command event has:
  - `event_name` from the phrases in `configs/pipeline.yaml`;
  - the segment's `start`/`end`;
  - `confidence` = `exp(avg_logprob)` ("an ASR confidence proxy, not a calibrated command
    probability");
  - `metadata` `{text, confidence_kind: asr_proxy}`.

  The rule engine reads these unchanged, and none of its code imports `audio/`.
- **(b) Raw transcript** (fallback, **deferred, not built**, D-124): **[2026-11-09]** the shared schema
  `schemas/transcript.TranscriptSegment` `{start, end, text, confidence}` (it has no word timings
  and no `no_speech_prob`), not the draft dictionary first proposed here. Word timings or
  `no_speech_prob` would need a schema change agreed with the team; they are requested from
  Sanjeevan, and `schemas/` is not edited. The command-recognition adapter (6.1) would turn the
  segments into (a).
- **Header (both):** `analyses_run.audio`, and the **clear-audio intervals**
  `visibility["region:audio"]`.
  - **Upstream requirement (OQ-068):** Sanjeevan provides the intervals where a spoken command
    would have been recognised. They could come, for example, from Whisper's per-segment
    confidence (`avg_logprob`) and `no_speech_prob`, plus his own noise or silence handling. The
    thresholds are his engineering choice.
  - **Without them,** every missing command is "unknown" and gives Unable to Verify (D-122).
- **Vocabulary:** no new canonical events. The placeholder labels become real names when they
  are confirmed (OQ-009, OQ-010); that is a mapping update only.

### 6.1 Command recognition adapter (fallback for raw transcripts, D-124)
**[2026-11-09] Deferred, not built (D-124, D-125).** It is built only if the input format
changes. The engine keeps **no phrase list of its own**: the single phrase list is
`configs/pipeline.yaml` (Sanjeevan's; D-125, OQ-069). The pipeline already matches phrases
upstream, so a second matcher in `rules/` would duplicate Sanjeevan's module and could drift from
it. The design below is kept for that case only. Its matching requirements went to Sanjeevan
(`upstream_requirements.md`).
`rules/adapters/transcript.py` runs before the engine, like the annotation adapter. It is
**skipped when the input is already command events**. Command detection is Sanjeevan's area; this
adapter is only a fallback.
- **Accepted phrases:** in `configs/rule_engine/command_phrases.yaml`.
  - Each command can have several phrasings, each with provenance (`proposed_by`,
    `approved_by: null`, `source`), so a new variant is a config change.
  - The seed list is the proposal's examples:

    | Rule | Phrases |
    |---|---|
    | A1 | "oxygen away", "move the oxygen away" |
    | A2 | "continue compressions", "continue CPR" |
    | A3 | "all stand clear", "stand clear", "everyone clear" |
    | A4 | "stop compressions", "stop CPR", "hands off" |
    | A5 | "shock", "deliver shock", "discharge" |
    | A6 | "start compressions", "resume compressions", "continue CPR" |

  - `configs/pipeline.yaml` (Sanjeevan's file) is not changed. Which list is the single source is
    OQ-069.
- **Normalisation:** case, punctuation, whitespace, and number and spelling forms ("O2" /
  "o two" / "oxygen", "C.P.R." / "CPR"), from a config table.
- **Matching:** an approved phrase is looked for in a sliding window of words, after
  normalisation. Fuzzy matching uses the standard library's `difflib` (no new packages), with two
  placeholder thresholds:
  - `phrase_match_threshold` (e.g. 0.85): a transcription or accent variant of an approved phrase
    counts as a match;
  - `near_match_threshold` (e.g. 0.65): below a match but at or above this is non-standard
    phrasing.
- **Single-word phrases** (for example "shock" or "discharge") use **exact matching only, never
  fuzzy matching**. This avoids false matches on similar words ("shocked", "charge").
- **Non-standard phrasing:** set by `phrase_matching: lenient | strict` (OQ-066).
  - **Lenient** (the default until the supervisor decides): a near-match becomes a candidate that
    is never evidence and never absence → Unable to Verify, with the flag `non_standard_phrase`.
  - **Strict:** only approved phrases count; a near-match is only logged.
- **Ambiguous phrases:**
  - "continue CPR" means both A2 and A6, so it is emitted as `resume_compressions_command` and
    resolved by its position relative to the shock (P-011).
  - A phrase with no context rule is emitted as a candidate for each command it could be (as in
    P-013): Unable to Verify, never a guess, with the flag `ambiguous_phrase`.
- **Confidence:** the transcription confidence × the match score (a placeholder rule). Below
  `confidence_thresholds.audio` it is excluded and logged; it is never evidence and never absence
  (D-010).
- **Time:** the start of the matched phrase's first word when word timestamps exist; otherwise
  the segment start, flagged `segment_timestamp`.
- **Unrecognised speech** is kept for review, never dropped, and counted in the report. It is
  written to `unrecognised_speech.csv` (text and times).
  - **It is data:** it contains what learners said. It is written only under the gitignored
    `data/` folder (for example `data/rule_engine/transcript/<run>/unrecognised_speech.csv`).
  - It is never committed, and never copied into tests or docs. Tests use synthetic transcripts.
- **The engine core is unchanged:** it only ever sees command events.

## 7. Increments (each with synthetic tests, the full suite and the pipeline command, a report, then wait)
| # | Goal | Files | Tests | Needs from Arnikan |
|---|---|---|---|---|
| 18 | **Built 2026-11-09.** Shared context: command anchors; `cross_modal_tolerance_seconds` (1.0); `relation_between`; **[2026-11-09]** segment-timed audio events (interval comparison, timing bounds, `timing_uncertain`); the `audio` region (default unknown); the D-121 helper; `order_partially_checked`; R3, R4 and R6 under D-121 | `context.py`, `checks.py`, `outcome.py`, `engine.yaml`, `coverage.py`, `video_rules.py`, output contract | tolerance ties; clear, unknown and not-run audio; R3, R4 and R6 without a shock time | — |
| 19 | **[2026-11-09] deferred, not built (D-124, D-125).** Transcript command-recognition adapter (input `TranscriptSegment`), only if the input format changes | `rules/adapters/transcript.py`, `command_phrases.yaml` | skipped for command events; exact, fuzzy and near matches; **single-word phrases exact only** ("shocked" and "charge" don't match "shock" and "discharge"); strict and lenient; ambiguous phrases; word and segment times; unrecognised speech kept, written only under `data/`; low confidence | the phrase list, provisional |
| 20 | **Built 2026-11-09.** Procedure-order config and loader | `procedure_order.yaml`, `rules/procedure.py`, `rules/config.py` | a cycle, an unknown step, two owners, unknown pairs not checked | — |
| 21 | A1, A3 | `audio_rules.py`, `rules.yaml` | present/missing × shock/no shock × audio clear/unknown/not run | — |
| 22 | A2, A4 | same | stage; stop before continue; continue missing | A4 limit (null is fine) |
| 23 | A5 | same | presence; R5 unaffected | A5 tolerance (null is fine) |
| 24 | R7/A6 | same | `before_shock`, `too_late`, an unresolved resume command, two IDs | R7 limit (null is fine) |
| 25 | A8 | same | 4.9, 5.0 and 5.1 s; stop or restart missing | the approval date |
| 26 | A7 on its own pairs; remove `depends_on`; retire R5 `preceding_steps` | `audio_rules.py`, `procedure.py`, `rules.yaml`, `video_rules.py` | swaps, repeats, missing and unseen commands | — |
| 27 | S1 Procedure order | `rules/procedure_rules.py`, `rules.yaml`, checklist | the section 8 matrix | the checklist mapping (OQ-064) |
| 28 | Combined scenario matrix, demo scenarios, docs | `tests/test_rule_engine_combined.py`, demo | section 8 | — |

## 8. Combined scenario test matrix (synthetic merged timelines)
1. **Correct full procedure:** all rules pass; the overall result is Incomplete while the limits
   are unset.
2. **One step misplaced** (stand clear after the button press): S1 `wrong_order` naming A3; A3
   still passes if it came before the shock.
3. **Two steps swapped** (A5 and R4): one S1 `wrong_order` naming both.
4. **Missing step** (no stop, inside a clear-audio interval): A4 `missing`; A8 not evaluable
   because of A4; S1 doesn't fail for it.
5. **Unseen step** (stop outside the clear-audio intervals): A4 Unable to Verify; S1 flagged as
   partial.
6. **No audio** (`analyses_run.audio: false`), and audio without clear intervals: every audio
   rule is Unable to Verify; S1 checks the video steps only, flagged as partial.
7. **No shock seen:** A1, A3, A5 and R7 are not evaluable because of R5, with presence still
   checked; R3, R4 and R6 check their shock-free parts; resume commands stay unresolved.
8. **Timing noise:** an audio command 0.9 s and 1.1 s after a video step, with a tolerance of
   1.0 s: first a tie, then misplaced.
9. **Repeated commands:** one occurrence in the right place satisfies the order.
10. **Low-confidence commands:** excluded and logged; unseen, never Fail.
11. **Transcript input:**
    - the same procedure as a raw transcript gives the same results;
    - a near-match gives Unable to Verify (lenient) or is ignored (strict);
    - "continue CPR" before and after the shock;
    - unrecognised speech is logged under `data/` only.
12. **[2026-11-09] Two commands in one Whisper segment** ("stop compressions, all stand clear"):
    both events have the same interval, so their mutual order isn't checked
    (`order_partially_checked`), never a Fail.
13. **[2026-11-09] Segment timing near a limit:** stop and start segments whose possible pause
    spans 4–6 s against A8's 5 s → Unable to Verify, `timing_uncertain`. Entirely within 5 s →
    Pass; entirely beyond → Fail `pre_shock_pause`.

## 9. Open questions
- **For the medical supervisor:**
  - OQ-062: the approved full order, the positions marked unknown, A5 before R4, and R6 before R7;
  - OQ-063: which steps may swap;
  - OQ-064: is S1 its own checklist item;
  - OQ-065: the accepted phrases;
  - OQ-070: should charging be a step in the order? **[2026-11-09]**
- **For Sanjeevan (and the supervisor):**
  - OQ-066: strict or lenient phrasing, now a question about his matching **[2026-11-09]**.
- **For Sanjeevan:**
  - OQ-067: the audio input format, **answered 2026-11-09** (D-125: his command events; he is to
    confirm it is final);
  - OQ-068: the clear-audio intervals;
  - OQ-069: the single source of the phrase list, **answered 2026-11-09** (D-125:
    `configs/pipeline.yaml`).
- **Resolved by Arnikan on 2026-10-20:**
  - the partial-result convention (D-121, which also settles R3, R4 and R6);
  - one step may break two relations (D-123);
  - `cross_modal_tolerance_seconds` = 1.0 s (placeholder);
  - retiring R5's `preceding_steps` and removing A7's `depends_on` (D-123);
  - the audio coverage default is unknown (D-122).
- **Resolved by Arnikan on 2026-11-09 (D-125):**
  - the input is Sanjeevan's command events;
  - the transcript adapter is deferred;
  - the single phrase list is `configs/pipeline.yaml`;
  - the interval comparison for segment-timed audio;
  - charging as a step is an open question (OQ-070);
  - six requests to Sanjeevan.

## 10. Step 0 re-sync (2026-11-09)
**1. Git.** `feature/rule-engine` was merged into `main` through PR #7 (merge commit `62882f0`);
no rule-engine commits are left outside `main`. `feature/audio-rules` was created from
`origin/main` (`62882f0`). Nothing was merged by the agent.

**2. This plan in the repo.** The plan, D-120 to D-124, OQ-062 to OQ-069, and both review
additions are present: single-word phrases match exactly (6.1, D-124), and unrecognised speech is
data, gitignored and never committed (6.1, D-124, `upstream_requirements.md`). **They were never
committed:** they exist only in the working tree, carried onto `feature/audio-rules`
(`audio_integration_plan.md` new; `decisions.md`, `open_questions.md`,
`upstream_requirements.md`, `progress.md` and `ai_usage_log.md` modified). They need a commit on
Arnikan's instruction.

**3. Files we depend on but don't own, since 2026-10-20.** No commit on any branch since
2026-10-20. `main` gained only `webApp/` files (PR #6) relative to the last rule-engine commit.
`schemas/`, `audio/`, `pipeline/`, `video/` and `configs/pipeline.yaml` are unchanged, so nothing
there affects the plan.

**4. Audio input on Sanjeevan's side.** The code below predates the plan, which didn't reflect it:

| What exists | Where | Effect on the plan |
|---|---|---|
| Command events from phrase matching | `audio/commands/detect.py`, called by `pipeline/run.py` | Input path (a) is real and primary. The engine reads the events; `rules/` doesn't import `audio/` |
| Phrase list for 3 commands only: O₂ away ("oxygen away", "remove the oxygen"), stand clear ("all stand clear", "stand clear"), `resume_compressions_command` ("resume compressions", "continue compressions") | `configs/pipeline.yaml` `commands` | Stop, shock command, start and an unambiguous continue are not detected yet (OQ-009). A4, A5, A8 and R7/A6 stay Unable to Verify until they are. `configs/pipeline.yaml` is the natural single source (OQ-069) |
| Matching: whole-phrase containment after normalisation; no fuzzy matching; one event per command per segment | `detect.py` | Single-word phrases: whole-word containment already rejects "shocked", but "shock" would also match "no shock advised". Request a guard when shock is added |
| Times: the Whisper segment's start and end; no word timestamps (`word_timestamps` off) | `audio/asr/whisper.py` | Segment-timed comparison added to Increment 18 (section 1). Word timestamps requested |
| Confidence: `exp(avg_logprob)` per segment, an uncalibrated proxy; a missing confidence is refused | `whisper.py`, `detect.py` | The engine's audio threshold (0.5, placeholder) applies. Its meaning is OQ-037 |
| No clear-audio intervals and no `no_speech_prob`; VAD filtering is on | `whisper.py` | D-122 applies: every missing command is Unable to Verify. The VAD speech regions could help Sanjeevan build the intervals (OQ-068) |
| Transcript schema `TranscriptSegment {start, end, text, confidence}` | `schemas/transcript.py` | The adapter's input, if it is ever built (6.1); Increment 19 is deferred (D-124, D-125) |
| A `charging_sound` audio event (listed as unused in the vocabulary) | `audio/charging_sound/` | The proposal places A2 "during the preparation or charging stage". **OQ-070** (supervisor, Sanjeevan): should charging be a step in the order, bounding A2? No rule uses it until then |

**Requests for Sanjeevan (added to `upstream_requirements.md`, 2026-11-09):**
1. **Top priority:** detect the missing commands: stop, shock command, start, and an unambiguous
   continue (OQ-009). Until then A4, A5, A8 and R7/A6 give Unable to Verify.
2. Word timestamps (or the command's start time) in the command events.
3. Clear-audio intervals (OQ-068).
4. For single-word phrases, a guard against phrases such as "no shock".
5. Keep unrecognised speech for review as data, never committed.
6. Confirm that the command events are the final input format (OQ-067, D-125).

**5. Open questions still unanswered:**
- **Supervisor:**
  - OQ-062: the full order, including the unknown positions, A5 before R4, and R6 before R7;
  - OQ-063: which steps may swap;
  - OQ-064: whether S1 is its own checklist item;
  - OQ-065 and OQ-010: the accepted phrases;
  - OQ-016: the time limits (R7/A6, A4 stop-to-shock, the A5 tolerance, any for A1 and A3; A8's
    5 s is approved, its approval date pending);
  - OQ-070: charging as a step.
- **Sanjeevan:**
  - OQ-066: strict or lenient phrasing in his matching (with the supervisor);
  - OQ-067: confirm that the command events are final (answered by D-125, pending his
    confirmation);
  - OQ-068: the clear-audio intervals;
  - OQ-009: the missing command events;
  - OQ-037: what audio confidence means.

## 11. How to apply the approved order (a change to `procedure_order.yaml` only)
When the supervisor's complete order arrives (OQ-062), no code changes. In
`configs/rule_engine/procedure_order.yaml`:
1. **Record the approval:** fill `approval` (`approved_by`, `approved_on`, `source`) and change the
   note.
2. **Add the relations:** a new `chains` entry for each sequence, for example
   `{chain: [A1, A2, R1], source: "supervisor, <date>"}`. Drop `confirm: true` from A5 → R4 if it
   is confirmed; remove a chain the supervisor rejects.
3. **Remove the resolved pairs from `unknown`.** Each pair can be listed on its own
   (`{pairs: [[A1, PLACE], ...], question: OQ-062}`). A new relation also orders every pair implied
   through the existing chains. For example, "A1 before PLACE" also orders A1 before R2B and R3
   (PLACE → R2B, PLACE → R3), so those pairs leave `unknown` too. If one is left, the loader names
   it ("marked unknown … but the chains order them").
4. **Interchangeable steps:** list them under `interchangeable` (OQ-063). Their mutual order is
   then not checked.
5. **Owners:** nothing to add. A new relation without an owner goes to A7 when both steps are
   audio, otherwise to S1. The explicit owners stay for the existing rules. Edit them only if a
   relation they claim is removed: the loader then reports "not a relation of the procedure order".
6. **Check:** run the full suite. The loader refuses a cycle (naming it), a pair still marked
   unknown, or a relation claimed twice. A test shows the path: a copy with every unknown pair
   resolved loads, and every new relation gets an owner
   (`tests/test_rule_engine_procedure_order.py`, ApplyingTheCompleteOrder).

A new step that isn't a canonical event yet (for example charging, OQ-070) also needs a vocabulary
entry. That is a config change too, but outside this file.
