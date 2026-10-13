# Rule engine: decision pathways

The readable version of [decision_flow.yaml](decision_flow.yaml). The first part lists, stage by
stage, every decision point (P-xxx) with its conditions, outcomes and flags. The second part
follows **worked pathways**: complete routes from a timeline to a result. New worked pathways
are added as rules are built. Diagrams of the same logic: [diagrams.md](diagrams.md). Every code
is explained in [anomalies.md](anomalies.md).

**Built** means implemented and tested; **planned** means designed but not yet built.

---

## Part 1: decision points by stage

### Stage: adapter

#### P-001 Annotation timeline adapter (planned, Increment 10)
| Condition | Outcome | Flags |
|---|---|---|
| A CVAT record is converted | Events, plus a header saying video was analysed and audio was not | `annotation_coverage_assumed` on every result |
| No zone annotation information | Zone coverage unknown | — |

### Stage: preparation

#### P-002 Timeline validation (built)
| Condition | Outcome | Code |
|---|---|---|
| Not a list of events | Rejected; no assessment | `not_a_list` |
| An item is not a shared event record | Rejected | `not_an_event` |
| An event has no ID | Rejected | `missing_event_id` |
| Two events share an ID | Rejected | `duplicate_event_id` |
| More than one camera angle (audio, which has no angle, is ignored) | Rejected | `multiple_camera_angles` |
| More than one recording | Rejected | `multiple_recordings` |
| Otherwise (an empty timeline is fine) | Accepted → P-003 | — |

#### P-003 Vocabulary mapping (built)
| Condition | Outcome | Code |
|---|---|---|
| Label known for its source | Renamed to the agreed name; original kept → P-004 | — |
| Ambiguous label ("resume compressions") | Kept; resolved later by its position relative to the shock → P-011 | — |
| Known but unused (raw object detections) | Kept, ignored by rules | — |
| Not in the vocabulary | Kept but cannot count as evidence; warning | `unknown_labels_present` |

#### P-004 Confidence exclusion (built)
| Condition | Outcome | Code |
|---|---|---|
| The source has no threshold | Rejected | `no_confidence_threshold` |
| Confidence at or above the threshold (0 disables the check) | Used as evidence → P-005 | — |
| Below the threshold | Set aside; never used as evidence, but never treated as absence (D-010) | (see P-008) |

#### P-005 Anomaly detection (built)
| Condition | Outcome | Code |
|---|---|---|
| More than one confident shock | Anomaly; "possibly the same shock detected twice" if within the window; not merged → P-009 | `multiple_shocks` |
| One event reported by both a human tag and a model | Flag only | `mixed_evidence_sources` |
| Any unknown label | Warning listing the labels | `unknown_labels_present` |

### Stage: coverage

#### P-006 Header validation (built)
| Condition | Outcome | Code |
|---|---|---|
| No header | Accepted; all coverage unknown → P-007 | — |
| Malformed header | Rejected | `invalid_header` |
| Header contradicts the events (camera, recording, an event ending more than 0.5 s after the stated duration, "audio did not run" but audio events exist) | Rejected | `header_mismatch` |
| Valid | Accepted → P-007 | — |

#### P-007 Coverage status lookup (built)
The most specific information wins.

| Condition | Coverage |
|---|---|
| No header | unknown |
| Header states coverage for the event's camera region (apical or sternal zone) | that status |
| Header states coverage for the event's source | that status |
| Header states coverage for the modality, or says whether that analysis ran | covered (ran) / not covered (did not run) / the stated status |
| Nothing stated | unknown |

#### P-008 Missing-event outcome (built)
| Condition | Outcome | Flags |
|---|---|---|
| A low-confidence detection of the event exists | **Unable to Verify, never Fail** | `low_confidence_evidence` |
| Coverage: covered | **Fail** | — |
| Coverage: not covered | Unable to Verify | — |
| Coverage: unknown | Unable to Verify (interim, D-008) | `coverage_policy_undecided` |

Each outcome can be overridden per region, source or modality in `engine.yaml`, except the
low-confidence rule.

### Stage: context

#### P-009 Shock time (built)
| Condition | Outcome | Flags |
|---|---|---|
| Two or more shocks | No shock time (not guessed) | `multiple_shocks` |
| One shock on screen | Shock time = the shock | — |
| No shock on screen, but a paddle removal | Shock time = first removal; every timing result using it is flagged | `shock_time_from_removal` (+ `multiple_candidates` if several removals) |
| Neither | No shock time | `no_shock` |

#### P-010 Phase of a time (built)
| Condition | Phase |
|---|---|
| No shock time | none |
| Earlier than the shock | before the shock |
| Same moment | at the shock |
| Later | after the shock |

#### P-011 Command resolution (built): what "resume compressions" means
| Condition | Outcome | Flags |
|---|---|---|
| No shock time | Unresolved | `no_shock_time` |
| Shock time from removal, command before the removal | Unresolved (D-024) | `command_before_removal`, `shock_time_from_removal` |
| Within 0.5 s of the shock | Unresolved | `command_near_shock` |
| Before the shock | "Continue compressions" | — |
| After the shock | "Start compressions" | `shock_time_from_removal` under the fallback |

#### P-012 Anchor selection (built): which event gives each key time
| Condition | Outcome | Flags |
|---|---|---|
| One candidate | Its time | — |
| Several candidates | The earliest; all recorded | `multiple_candidates` |
| Only a low-confidence candidate | Absent | `low_confidence_evidence` |
| No candidate | Absent, with a reason | — |
| A start command at or before a confirmed on-screen shock | Not the restart (D-025); a mistake A7 reports | `start_command_before_shock` |
| Shock time from removal, and a start command at or before the removal | Timing-ambiguous: not the restart, **not a mistake** (D-053); a later start is still used, but stays flagged | `command_before_removal`, `shock_time_from_removal` |
| Shock time from removal, no start command before the removal | The first start after the removal is definitely the restart; no fallback flag on the restart itself (OQ-041, interim) | — |
| No shock time (start only) | No restart time; start commands are ambiguous, not mistakes (D-054) | `no_shock_time` |

Each start command is checked on its own, so a later start can still be the restart when an
earlier one does not count.
| A "resume" command is unresolved | Continue and start times may be incomplete | `unresolved_commands` |

#### P-013 Low-confidence ambiguous command (built)
| Condition | Outcome | Flags |
|---|---|---|
| A weak "resume compressions" would mean this event, or cannot be resolved | The missing event is Unable to Verify | `low_confidence_evidence` |
| It would mean the other command | Not evidence → P-008 | — |

### Stage: rule (planned)

#### P-014 Rule decision ladder (planned, Increments 6–7)
| Condition | Outcome |
|---|---|
| Rule not yet approved | Reported as pending; the overall result cannot be Pass (D-055) |
| A rule it depends on failed or was not evaluable | "Not evaluable because of …" |
| Required facts missing (e.g. no shock time) | "Not evaluable because of …", with the facts' flags |
| The restart is needed (R7/A6, A8), but a start command is timing-ambiguous | **Unable to Verify, never Fail**; A7 does not report it (D-053, D-054) |
| R7/A6 under the removal fallback, no ambiguous start, delay **from the removal** already over the limit | **Fail `too_late`**: the real delay is even longer (planned, OQ-041) |
| R7/A6 under the removal fallback, no ambiguous start, delay from the removal within the limit | Unable to Verify, `shock_time_from_removal`: the real delay may be over the limit (planned, OQ-041) |
| A8 under the removal fallback, no ambiguous start | Stop → restart measured normally, without the fallback flag (planned, OQ-041) |
| Evidence present, in order and in time | Pass – Direct |
| Evidence clearly shows the mistake | Fail, with the rule's failure code |
| Evidence weak **or missing**, and the rule has an approved inference (R3, R4) | → P-016, **before** the coverage step (D-057) |
| R8 order not directly observable | → P-015 |
| Required event missing, and no approved inference applies | → P-008 |

#### P-015 R8 inference (planned, Increment 12)
| Condition | Outcome | Codes |
|---|---|---|
| Both zones visible, both placements observed | Compare the two placement times | `wrong_order`, `simultaneous` |
| Both zones visible, one placement event missing | Unable to Verify, not `wrong_order`; R3 reports the missing placement (proposed, OQ-040) | `placement_missing` |
| One zone visible, its placement matches the first placement | That paddle was first (inferred) | `inferred_fail_policy_undecided` if it is the sternal one |
| One zone visible, its placement clearly after the first | The other paddle was first (inferred) | `inferred_fail_policy_undecided` if that means a mistake |
| One zone visible, its paddle has no placement event | Unable to Verify, no inference; R3 reports the missing placement (proposed, OQ-040) | `placement_missing` |
| The visible paddle placed clearly before the first placement | Unable to Verify | `contradictory` |
| Not determinable (no zone visible, or no first placement) | Unable to Verify (or "assumed apical first", not counted, if the fallback is on) | — |

#### P-016 R3/R4 inferred pass (planned, Increments 15–16)
| Condition | Outcome | Codes |
|---|---|---|
| Direct evidence in time | Pass – Direct | — |
| Direct evidence shows the mistake | Fail | `not_in_zone`, `placed_after_shock`, `before_placement`, `not_pressed` |
| Direct evidence weak **or missing**; shock on screen or removal confirmed | Pass – Inferred (D-057) | — |
| Neither | → P-008 | — |

### Stage: overall policy (planned)

#### P-017 Overall result (planned, Increment 8)
| Condition | Overall result |
|---|---|
| Any evaluated rule fails | **Fail** (any mistake fails, D-001), even if other rules are pending |
| No Fail, but any rule is pending | **Incomplete: "rules not yet approved"**, never Pass (D-055) |
| No Fail, no pending rule, any Unable to Verify **or Not evaluable** | Fail or faculty review (undecided, OQ-002; "not evaluable" counts as Unable to Verify, D-056) |
| Every rule evaluated and passed (direct or inferred) | **Pass** |

### Stage: renderer (planned)

#### P-018 Report and checklist (planned, Increments 9 and 25)
| Condition | Outcome | Flags |
|---|---|---|
| Annotation timeline | Development flag on the report and every result | `annotation_coverage_assumed` |
| Model timeline | No development flag | — |

---

## Part 2: worked pathways

Times are seconds from the start of the recording. "→" means "goes to". The rule results are
what the planned rule will report once built; everything before them is built and tested
today.

### W-1 Audio analysed, "stand clear" never said → Fail
1. The header says audio was analysed (`analyses_run: {audio: true}`). There are no
   stand-clear events, confident or weak.
2. P-007: stand-clear coverage = **covered** (the audio ran).
3. P-008: covered + missing → **Fail**.
4. A3 (Increment 18) reports Fail `missing`.

### W-2 "Stand clear" heard at confidence 0.3 → Unable to Verify
1. P-004: 0.3 is below the audio threshold (0.5), so the event is set aside.
2. P-008: a low-confidence detection exists → **Unable to Verify**, `low_confidence_evidence`.
   This holds even if audio was analysed: low confidence is never absence (D-010).

### W-3 No timeline header, "stand clear" missing → Unable to Verify (interim)
1. P-006: no header → accepted. P-007: coverage **unknown**.
2. P-008: unknown → **Unable to Verify**, `coverage_policy_undecided` (D-008, OQ-001).

### W-4 Audio not analysed → Unable to Verify
1. The header says `analyses_run: {audio: false}`, and there are no audio events.
2. P-007: coverage **not covered**. P-008 → **Unable to Verify**. The learner is not blamed
   for missing data (D-004).

### W-5 No shock on screen, paddles removed at 52 s → timing flagged
1. P-009: no shock indication; first removal at 52 s → shock time **52 s**, flagged
   `shock_time_from_removal`.
2. "Start compressions" at 55 s, and none before the removal → P-012: the restart is
   **definitely** 55 s, so the restart itself carries no fallback flag (OQ-041, interim).
3. Shock → restart = 3 s, flagged `shock_time_from_removal`. Removal comes after the real
   shock, so the real delay was **longer** than 3 s.
4. R7/A6 (Increment 21): see W-15 and W-16. A8 (Increment 23): see W-19.

### W-6 Under the removal fallback, "resume compressions" at 50 s
1. Shock time from removal at 52 s (W-5).
2. P-011: the command is before the removal → **unresolved**, `command_before_removal`
   (D-024). It counts as neither continue nor restart.
3. P-012: the continue and start anchors are flagged `unresolved_commands`.

### W-7 Two shocks 0.3 s apart → no shock time
1. P-005: two confident shocks → `multiple_shocks`, within the 0.5 s window ("possibly the
   same shock detected twice").
2. P-009: **no shock time** (not guessed). P-010: no phases. P-011: every "resume" command is
   unresolved (`no_shock_time`).
3. Shock-dependent rules (Increments 13–23) report "not evaluable because of R5", carrying
   the flags (D-003, D-039).

### W-8 "Resume compressions" before and after the shock
1. Shock on screen at 30 s.
2. P-011: "resume" at 10 s → **continue**; "resume" at 33 s → **start**.
3. P-012: the restart anchor is 33 s. A2 uses the continue command and R7/A6 the restart.

### W-9 "Resume compressions" 0.2 s after the shock
1. P-011: within 0.5 s of the shock → **unresolved**, `command_near_shock` (D-041).
2. P-012: the continue and start anchors are flagged `unresolved_commands`. If no other start
   command exists, the restart is absent, and the missing outcome comes from P-008.

### W-10 "Start compressions" said before and after the shock
1. Shock **confirmed on screen** at 30 s. Start commands at 20 s and 35 s.
2. P-012: the restart is the earliest start **after** the shock → **35 s**. The 20 s command
   is ineligible, flagged `start_command_before_shock` (D-025).
3. R7/A6 and A8 use 35 s. A7 (Increment 22) reports the 20 s command as a sequence problem.

### W-11 First placement tagged twice
1. Two `first_paddle_firmly_on_the_chest` tags, at 12 s and 14 s.
2. P-003: both become "first paddle placed". P-012: the key time is **12 s**, both IDs
   recorded, `multiple_candidates` (D-040; OQ-022 asks which placement should count).

### W-12 A label with a typo
1. The tag "gel applied" (lower case) is not in the vocabulary.
2. P-003/P-005: `unknown_labels_present` lists `annotation:gel applied`. The event cannot
   count as gel.
3. R1 (Increment 17) then finds gel missing → P-008. The warning shows a possible naming
   mismatch.

### W-13 A timeline mixing two camera angles → no assessment
1. Video events from camera "T" and camera "LS".
2. P-002: rejected, `multiple_camera_angles`; no assessment is produced (D-032).

### W-14 Under the removal fallback, "start compressions" before the removal → Unable to Verify
1. P-009: no shock on screen; paddles removed at 52 s → shock time **52 s** (from removal),
   flagged `shock_time_from_removal`. The real shock was at an unknown time before 52 s.
2. Explicit "start compressions" at 50 s, and again at 58 s.
3. P-012: the 50 s command is **timing-ambiguous**. It may have been the genuine restart after
   the real shock, so it is not counted and is **not a mistake**. It is listed as ambiguous and
   flagged `command_before_removal` (D-053). The 58 s command is used as the restart time, but
   the anchor stays flagged.
4. R7/A6 (Increment 21) and A8 (Increment 23): the restart is ambiguous → **Unable to Verify**,
   not Fail, not even `too_late` or `pre_shock_pause` measured to 58 s.
5. A7 (Increment 22) does **not** report the 50 s command as a sequence error. Compare W-10,
   where the shock was confirmed on screen and an early start command is a sequence problem.

### W-15 R7/A6 under the removal fallback, delay from the removal already too long → Fail
*(Planned, OQ-041. The R7 limit is not approved yet, OQ-016; a limit of 10 s is used here for
illustration only.)*
1. No shock on screen; removal at 52 s → shock time 52 s (`shock_time_from_removal`).
2. No start command before 52 s. First start after it at 64 s → definitely the restart.
3. Delay from the removal = 12 s, already over 10 s. The real shock was earlier, so the real
   delay is even longer.
4. R7/A6 → **Fail `too_late`**, a confident Fail even under the fallback, flagged
   `shock_time_from_removal` for transparency.

### W-16 R7/A6 under the removal fallback, delay from the removal within the limit → Unable to Verify
*(Planned, OQ-041; illustrative 10 s limit.)*
1. As W-15, but the first start after the removal is at 58 s → delay from the removal = 6 s.
2. The real delay is longer than 6 s by an unknown amount, so it may exceed 10 s.
3. R7/A6 → **Unable to Verify**, flagged `shock_time_from_removal`.

### W-17 R8, one zone visible, its paddle has no placement event → Unable to Verify
*(Proposed, OQ-040.)*
1. Only the apical zone is visible. The first paddle was placed at 12 s, but there is no
   apical placement event.
2. P-015: the visible paddle's placement is not observed, so the order cannot be established.
   **No inference** ("the apical paddle was never placed, so sternal was first" is not shown by
   the evidence).
3. R8 → **Unable to Verify**, `placement_missing`. R3 reports the missing placement (one
   mistake reported once, D-003).

### W-18 R8, both zones visible, one placement event missing → Unable to Verify
*(Proposed, OQ-040.)*
1. Both zones are visible. Apical placed at 12 s; no sternal placement event.
2. P-015: the order cannot be compared → **Unable to Verify**, `placement_missing`, and **not**
   Fail `wrong_order`. R3 reports the missing sternal placement.

### W-19 A8 under the removal fallback, no ambiguous start → measured normally
*(Planned, OQ-041.)*
1. Removal at 52 s (the shock time comes from removal). "Stop compressions" at 48 s; first
   start after the removal at 55 s; no start before the removal.
2. The restart is certain (P-012), and stop → restart = 7 s does not depend on the shock time,
   so it carries no fallback flag.
3. A8 (limit 5 s, approved, D-016) → **Fail `pre_shock_pause`**.

### W-20 R3 with no direct placement evidence, removal confirmed → Pass – Inferred
*(Planned, D-057.)*
1. The camera never shows both paddles stable in their zones (no `paddles_firmly_on_chest`).
2. P-014: R3 has an approved inference, so it is checked **before** the coverage step.
3. P-016: paddle removal is confidently confirmed → **Pass – Inferred**, naming the removal
   event. The coverage step (P-008) is not reached.

### W-21 Overall result with a pending rule → Incomplete
*(Planned, D-055.)*
1. Fifteen rules pass; R8 is still pending (not approved).
2. P-017: no Fail, but a rule is pending → **Incomplete: "rules not yet approved"**, never Pass.
3. If any evaluated rule had failed, the overall result would be **Fail** regardless (D-001).

### W-22 Overall result with a "not evaluable" rule → Unable to Verify policy
*(Planned, D-056.)*
1. No shock time (W-7). R7/A6 and A8 are "not evaluable because of R5"; R5 itself is Unable to
   Verify; every other rule passes; none is pending.
2. P-017: "not evaluable" counts like Unable to Verify → **Fail or faculty review**, per the
   undecided setting (OQ-002).
