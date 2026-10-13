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
| A start command at or before the shock | Not the restart (D-025); kept for A7 | `start_command_before_shock` |
| No shock time (start only) | No restart time | `no_shock_time` |
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
| Rule not yet approved | Reported as pending; not counted |
| A rule it depends on failed or was not evaluable | "Not evaluable because of …" |
| Required facts missing (e.g. no shock time) | "Not evaluable because of …", with the facts' flags |
| Evidence present, in order and in time | Pass – Direct |
| Evidence clearly shows the mistake | Fail, with the rule's failure code |
| Evidence weak, but an approved inference applies | → P-015 or P-016 |
| Required event missing | → P-008 |

#### P-015 R8 inference (planned, Increment 12)
| Condition | Outcome | Codes |
|---|---|---|
| Both zones visible | Compare the two placement times | `wrong_order`, `simultaneous` |
| One zone visible, its placement matches the first placement | That paddle was first (inferred) | `inferred_fail_policy_undecided` if it is the sternal one |
| One zone visible, its placement clearly after the first | The other paddle was first (inferred) | `inferred_fail_policy_undecided` if that means a mistake |
| The visible paddle placed clearly before the first placement | Unable to Verify | `contradictory` |
| Not determinable | Unable to Verify (or "assumed apical first", not counted, if the fallback is on) | — |

#### P-016 R3/R4 inferred pass (planned, Increments 15–16)
| Condition | Outcome | Codes |
|---|---|---|
| Direct evidence in time | Pass – Direct | — |
| Direct evidence shows the mistake | Fail | `not_in_zone`, `placed_after_shock`, `before_placement`, `not_pressed` |
| Direct evidence weak; shock on screen or removal confirmed | Pass – Inferred | — |
| Neither | → P-008 | — |

### Stage: overall policy (planned)

#### P-017 Overall result (planned, Increment 8)
| Condition | Overall result |
|---|---|
| Any counted rule fails | Fail |
| No Fail, some Unable to Verify | Fail or faculty review (undecided, OQ-002) |
| All counted rules pass | Pass |

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
2. "Start compressions" at 55 s → P-012: the restart anchor is 55 s, carrying the flag.
3. Shock → restart = 3 s, flagged `shock_time_from_removal`. Removal comes after the real
   shock, so the real delay was longer.
4. R7/A6 (Increment 21) report the timing with the flag.

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
1. Shock at 30 s. Start commands at 20 s and 35 s.
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
