# Rule engine: diagrams

Mermaid diagrams (they render on GitHub). They follow [decision_flow.yaml](decision_flow.yaml),
and boxes are labelled with its decision-point IDs (P-xxx). **Dashed boxes are planned**, not
built yet. Detailed conditions are in [pathways.md](pathways.md).

## (a) End to end: from recording to report

```mermaid
flowchart LR
    rec["Recording<br/>one camera angle + audio"]
    subgraph ananth["Ananth: video and pipeline"]
        vid["Video model<br/>+ postprocessing"]
        merge["Merge into one timeline<br/>+ header (requested)"]
    end
    subgraph sanjeevan["Sanjeevan: audio, feedback, app"]
        asr["Speech recognition<br/>+ command detection"]
        fb["Feedback wording"]
        app["App: report viewer"]
    end
    subgraph arnikan["Arnikan: rule engine"]
        eng["Rule engine<br/>P-001 to P-031"]
        ann["Annotation exporter<br/>(development / evaluation, see h)"]
    end
    rec --> vid --> merge
    rec --> asr --> merge
    merge --> eng
    ann -.->|"development / evaluation"| eng
    eng --> fb --> app
    eng --> app
```

## (b) Inside the rule engine

```mermaid
flowchart TD
    A0["P-028 Annotation exporter<br/>(development / evaluation;<br/>CVAT backups, built; see h)"]
    A["P-001 / P-030 Adapter<br/>(annotation: development / evaluation;<br/>transcript adapter later, D-117)"]
    A0 --> A
    B["P-002 Validate timeline"]
    C["P-003 Map names"]
    D["P-004 Set aside low-confidence events"]
    E["P-005 Flag anomalies<br/>incl. event counts, paddle identity"]
    F["P-006 Check header"]
    G["P-007 Coverage status<br/>P-008 What missing means"]
    H["P-009 Shock time · P-010 Phases<br/>P-011 Resolve commands · P-012 Key times<br/>P-013 Weak ambiguous commands"]
    I["P-026 Rule runner + P-019 to P-025 checks built<br/>P-014 individual rules planned<br/>P-015 R8, P-016 R3/R4 planned"]:::planned
    J["P-017 Overall result"]
    K["P-027 JSON report<br/>(versioned output contract)"]
    L["P-018 Checklist and<br/>feedback handover"]:::planned
    X["Rejected: no assessment, no report<br/>(rules.run exits with code 2)"]
    A --> B
    B -->|malformed| X
    B --> C --> D --> E --> F
    F -->|invalid or contradicts events| X
    F --> G --> H --> I --> J --> K
    J --> L
    classDef planned stroke-dasharray: 5 5
```

## (c) The decision ladder every rule follows (P-026, P-014)

The rule runner (P-026, Increment 7) and the shared checks (P-019 to P-025, Increment 6) are
**built**; the individual rules that use them come in Increments 11 to 23. Times on the ladder are
compared with P-025, and time limits with P-024 (timing not checked when there is no limit).

```mermaid
flowchart TD
    S["Rule"] --> P1{"P-026 Approved?"}
    P1 -->|no| R0["Pending<br/>overall cannot be Pass"]
    P1 -->|yes| P2{"P-019 Rules it depends on<br/>evaluable and passed?"}
    P2 -->|no| R1["Not evaluable<br/>because of that rule"]
    P2 -->|yes| P3{"P-020 Facts it needs present?<br/>e.g. shock time"}
    P3 -->|no| R2["Not evaluable<br/>because of the missing step"]
    P3 -->|yes| PA{"P-021 Needs the restart, and a start<br/>or resume command is ambiguous?"}
    PA -->|yes| RA["Unable to Verify<br/>never Fail (D-053, D-059)"]
    PA -->|no| P4{"P-022 Direct evidence?<br/>any valid occurrence counts"}
    P4 -->|present, valid| R3["Pass – Direct"]
    P4 -->|present, shows the mistake| R4["Fail<br/>with failure code"]
    P4 -->|weak or missing| P5{"P-023 Approved inference?<br/>P-015 / P-016 (D-057)"}
    P5 -->|yes, it applies| R5["Pass – Inferred"]
    P5 -->|no, or it does not apply| M["What missing means<br/>P-013 / P-008 coverage step"]
    S -.->|"the rule raises an error<br/>at any step (D-063)"| EE["engine_error<br/>others still run<br/>overall incomplete"]
```

## (d) What a missing event means (P-007, P-008, P-013)

```mermaid
flowchart TD
    Q["A required event is missing<br/>(and no approved inference applies)"] --> L{"Low-confidence detection<br/>of it exists? P-008, P-013"}
    L -->|yes| U1["Unable to Verify<br/>low_confidence_evidence<br/>(never Fail)"]
    L -->|no| C{"Coverage P-007<br/>region → source → modality"}
    C -->|covered| F["Fail"]
    C -->|not covered| U2["Unable to Verify"]
    C -->|unknown, incl. no header| U3["Unable to Verify (interim)<br/>coverage_policy_undecided"]
```

## (e) Shock time, phases and command resolution (P-009, P-010, P-011; D-093)

The shock time comes only from the screen. It is never inferred, from the paddle removal or
anything else, and there is no fallback setting (D-093, D-115).

```mermaid
flowchart TD
    S0{"How many confident<br/>shock indications<br/>on the screen?"} -->|two or more| N1["No shock time<br/>multiple_shocks<br/>(not guessed)"]
    S0 -->|one| T1["Shock time = shock on screen"]
    S0 -->|"none (even if the paddles<br/>were removed, D-115)"| N0["No shock time, never inferred<br/>no_shock<br/>shock-dependent rules:<br/>Not evaluable because of R5"]
    T1 --> PH["P-010 Phases: before / at / after"]
    PH --> CR{"P-011 'Resume compressions'<br/>relative to the shock"}
    CR -->|"within simultaneous_window_seconds<br/>(configurable, placeholder 0.5 s)"| UR2["Unresolved<br/>command_near_shock"]
    CR -->|before| CO["Continue"]
    CR -->|after| ST["Start"]
    N1 --> UR3["Commands unresolved<br/>no_shock_time"]
    N0 --> UR3
```

### (e2) Which start command is the restart (P-012)

Every start command goes through these checks **on its own**. Commands that do not count are
set aside, and the **earliest remaining** one is the restart, so a later start can still be
the restart. The shock time is either from the screen or absent (D-093, D-115).

```mermaid
flowchart TD
    K{"For each start command:<br/>is there a shock time? P-009"} -->|"no shock time<br/>(no shock on screen, D-093;<br/>or two shocks)"| A0["Ambiguous, not a mistake<br/>no_shock_time<br/>no restart time; R7/A6, A8, A7<br/>Not evaluable because of R5"]
    K -->|shock on screen| B{"This command at or<br/>before the shock?"}
    B -->|yes| B1["Does not count: a mistake<br/>start_command_before_shock<br/>(A7 reports it)"]
    B -->|no| RS["Candidate: after the shock"]
    RS --> E["Restart = earliest candidate"]
```

## (f) R8: apical before sternal (P-015, built in Increment 12; pending until approved)

Zones count as visible when covered over the placement phase, from the first paddle taken to
paddles firmly on chest (D-092, D-099). Derived placements reach R8 only past the gate (D-088).
A parallel placement fails R2 as well, separately, with the same cause flag (D-098). With only
one zone in view the order can't be established: there is no one-zone inference (D-116).

```mermaid
flowchart TD
    PP{"Derived placements flagged<br/>possible_parallel_placement?"} -->|yes| FP["Fail simultaneous<br/>cause flag possible_parallel_placement<br/>(R2 fails too, separately, D-098)"]
    PP -->|no| BOTH{"Both placements<br/>observed?"}
    BOTH -->|yes| D1{"Compare apical and<br/>sternal placement times"}
    D1 -->|apical first| P["Pass – Direct"]
    D1 -->|sternal first| F["Fail wrong_order"]
    D1 -->|same time| FS["Fail simultaneous"]
    BOTH -->|no| Z{"A zone in view during the<br/>placement phase, but its<br/>placement missing?"}
    Z -->|yes| PM["Unable to Verify<br/>placement_missing (D-058)<br/>R3 reports the missing placement"]
    Z -->|no| ONE{"One placement observed,<br/>the other zone not in view?"}
    ONE -->|yes| U1["Unable to Verify<br/>one_zone_in_view (D-116)<br/>no inference: the first-placement tag<br/>is the apical placement (A-027)"]
    ONE -->|"no: nothing observed<br/>and no zone in view"| N{"Fallback switched on?<br/>(off by default)"}
    N -->|no| U["Unable to Verify"]
    N -->|yes| AS["Assumed apical first<br/>to be checked by the evaluator<br/>overall cannot be Pass (D-060)"]
```

## (g) Overall result (P-017, built)

```mermaid
flowchart TD
    A{"1. Any evaluated rule Fail?"} -->|yes| AN{"Review anomaly in<br/>the timeline?"}
    AN -->|no| F["Overall Fail<br/>every Fail listed, R7/A6 once (D-001)"]
    AN -->|yes| FR["Overall Fail<br/>timeline_needs_review, anomalies listed"]
    A -->|no| N0{"2. Any rule evaluated?"}
    N0 -->|no| INC0["Incomplete<br/>no_rules_evaluated (D-068)"]
    N0 -->|yes| PD{"Pending, assumed (R8),<br/>engine error, timing not checked,<br/>or a review anomaly?"}
    PD -->|yes| INC["Incomplete: each rule and why<br/>or timeline needs review<br/>never Pass (D-055, D-060, D-062, D-063, D-065)"]
    PD -->|no| B{"3. Any Unable to Verify<br/>or Not evaluable? (D-056)"}
    B -->|yes| U{"unable_to_verify_outcome<br/>decided?"}
    U -->|yes| UD["Fail or faculty review<br/>as set"]
    U -->|no| UU["unable_to_verify<br/>overall_policy_undecided (OQ-002)"]
    B -->|no| P["4. Overall Pass<br/>every rule evaluated and passed,<br/>timing checked"]
    DEV["Any result from annotation data:<br/>marked development data (D-066)"] -.-> A
```

## (h) How annotation data reaches the rule engine (P-028, P-029, P-001; D-074, D-083)

**Ananth runs** the rule engine's exporter and audit on the final CVAT backups, which are with him
(D-083), and sends Arnikan only the records, the export manifest and the audit outputs, never
media (D-085). The training pipeline is untouched: none of its scripts or files change, and it
never reads the exporter's output. Until the final export arrives, Increment 10 uses the
smoke-run export of 39 corrected backups (D-084). This whole path is for development and
evaluation, not the runtime input: in production the engine will read the pipeline's procedure
transcript (D-117).

```mermaid
flowchart LR
    subgraph ananth["Ananth's machine"]
        CVAT[("Final CVAT backups<br/>frozen labels (D-073)<br/>only the annotation JSON is read (D-085)")]
        CONV[/"video_conversion.csv<br/>fps, frame size<br/>(read only, D-076)"/]
        subgraph training["Training pipeline: unchanged"]
            AUD1["audit_cvat_backups.py<br/>Phase 1 reports"]
            SPLIT["create_grouped_video_split.py<br/>split files"]
            BUILD["build_yolo_video_dataset.py<br/>images, labels, events.jsonl,<br/>sample_manifest.csv"]
            TRAIN["YOLO training"]
            AUD1 --> SPLIT --> BUILD --> TRAIN
        end
        EXP["P-028 export_rule_engine_records.py<br/>run by Ananth (how-to)"]
        AUD2["P-029 audit_rule_engine_checks.py<br/>run by Ananth"]
        CVAT --> AUD1
        CVAT --> EXP
        CVAT --> AUD2
        CONV --> EXP
        CONV --> AUD2
        BUILD -. "box geometry reused by import only (D-079)" .-> EXP
    end
    subgraph arnikan["Arnikan: rule engine (development / evaluation path)"]
        REC[("records.jsonl + export_manifest.json<br/>gitignored data/rule_engine/<br/>never committed (D-084)")]
        REP["Audit outputs<br/>review list, information"]
        SMOKE[("Interim: smoke-run export<br/>39 corrected backups (D-084)")]
        CFG[/"annotation_export.yaml<br/>zone labels, usual pattern,<br/>reviewed exceptions"/]
        ADP["P-001 / P-030 adapter<br/>header, zone coverage + intervals,<br/>gate for derived placements"]
        ENG["Rule engine<br/>P-002 onward"]
        REC --> ADP --> ENG
        SMOKE -.->|until the final export| ADP
        CFG --> ADP
    end
    EXP -->|"sent: records + manifest<br/>no media"| REC
    AUD2 -->|sent| REP
    REP -->|items to fix in the backups| CVAT
```

## (i) How a zone's coverage is decided for a recording (P-030, P-007; D-074, D-080, D-082, D-092, D-094)

Decided per zone (apical, sternal) for one annotated recording by the adapter (built, Increment
10). The defibrillator screen (region `screen`, R5) and each paddle (regions `apical_paddle`,
`sternal_paddle`, R4, D-108) go through the same steps, without reviewed exceptions (D-094). When a rule asks about a time window, P-007 uses the zone's visible intervals (D-092). The
view's usual zone pattern is used only by the audit's review list, never here.

```mermaid
flowchart TD
    Z["A placement zone of one recording"] --> X{"Reviewed exception:<br/>annotator confirmed it was<br/>genuinely not visible?"}
    X -->|yes| NC1["not covered (D-082)<br/>off the review list"]
    X -->|no| T{"Zone track in<br/>the CVAT backup?"}
    T -->|no| UN["unknown (D-074)<br/>on the review list if the view<br/>usually shows this zone"]
    T -->|yes| V{"Visible on which frames?<br/>(a training box exists, D-079)"}
    V -->|every frame| CO["covered"]
    V -->|some frames| PART["unknown for the recording<br/>intervals in the header"]
    V -->|none, outside on every frame| NC2["not covered (D-080)<br/>audit information only"]
    PART --> W{"P-007: rule asks about<br/>a time window?"}
    W -->|"visible throughout it"| WC["covered"]
    W -->|"visible for part of it"| WU["unknown"]
    W -->|"never visible in it"| WN["not covered"]
    W -->|no window| PART2["unknown"]
    NC1 --> P8["→ P-008 what a missing<br/>placement means"]
    UN --> P8
    CO --> P8
    NC2 --> P8
    WC --> P8
    WU --> P8
    WN --> P8
    PART2 --> P8
```

## (j) Derived per-paddle placement (P-031, Step 9c; D-081, D-086 to D-088, D-090, D-091)

Built in the exporter, per paddle **label** across all its tracks (D-087). T1 is
`first_paddle_firmly_on_the_chest` and T2 is `paddles_firmly_on_chest` (A-019). Settings are
placeholders.

```mermaid
flowchart TD
    F["Each frame, per paddle label"] --> B{"Boxes of this paddle?"}
    B -->|two or more| BL["blocked<br/>(overlapping tracks)"]
    B -->|none| O["out"]
    B -->|one| Z{"Its zone visible?"}
    Z -->|"no (A-020, D-090)"| UK["unknown<br/>neither in nor out:<br/>doesn't start or end a placement"]
    Z -->|yes| OV{"≥ 0.5 of the paddle<br/>box inside the zone?"}
    OV -->|no| O
    OV -->|yes| I["in"]
    I --> S{"In for 5 frames and centre<br/>moving < 2% of the diagonal?"}
    S -->|yes| P["Placement starts<br/>ends after 5 out frames (exit_frames),<br/>unknown frames skipped;<br/>then a re-placement can start"]
    UK -.->|"in on both sides of the gap:<br/>same placement"| P
    BL -.->|"touches a placement"| NB["No event for this paddle<br/>placement_duplicate_paddle_box<br/>(Ananth fixes the tracks)"]
    P --> T{"T1 tagged?"}
    T -->|yes, both paddles derived| T1{"Earlier placement within<br/>15 frames of T1?"}
    T1 -->|yes| K["Keep both"]
    T1 -->|no| N1["No event for either<br/>placement_disagrees_with_tag"]
    T -->|yes, one paddle derived| T1b{"Not earlier than<br/>T1 − 15 frames?"}
    T1b -->|yes| K
    T1b -->|no| N1
    T -->|no| PP{"Both derived, within<br/>simultaneous_window_seconds?"}
    PP -->|yes| KP["Keep both, flagged<br/>possible_parallel_placement<br/>(R2/R8 Fail simultaneous once<br/>the gate is approved, D-091)"]
    PP -->|no| N2["No events"]
    K --> T2{"T2 tagged?"}
    KP --> T2
    T2 -->|"no: not checked"| EV["Events: direct evidence,<br/>flagged derived_placement,<br/>method, end_seconds and<br/>ended_by_exit in metadata (R6)"]
    T2 -->|yes| T2c{"First placement at or<br/>before T2 + 15?"}
    T2c -->|yes| EV
    T2c -->|no| N3["No event for that paddle<br/>(both if parallel)"]
    EV --> G{"Gate (D-088): reviewed for this<br/>export_id and these settings?"}
    G -->|yes| R8["Adapter passes them on;<br/>R2, R8 and R6 may use them"]
    G -->|no| HOLD["Kept in records.jsonl,<br/>not passed to the engine"]
```

## (k) R6: paddles removed after the shock (P-034, built in Increment 14; pending until approved)

`paddles_removed_after_shock` means the paddles were removed; it doesn't prove a shock (D-104).
The tolerance `w` is `removal_before_screen_tolerance_seconds` (the screen may show the shock after
the discharge, D-105).

```mermaid
flowchart TD
    S{"Shock time?<br/>(screen only, D-093)"} -->|"none, or several shocks"| NE["Not evaluable<br/>because of R5<br/>(even with a removal:<br/>it doesn't show a shock, D-115)"]
    S -->|yes| RB{"Removal tagged more than<br/>w before the shock?"}
    RB -->|yes| F1["Fail<br/>removed_before_shock"]
    RB -->|no| DE{"Past the gate: a derived placement<br/>ended by a real exit more than w<br/>before the shock, that paddle<br/>not on again at the shock?"}
    DE -->|yes| F2["Fail removed_before_shock<br/>derived_placement"]
    DE -->|no| RM{"Removal tagged?"}
    RM -->|"yes: after the shock, or<br/>within w before it (at the shock)"| L{"shock_to_removal_seconds<br/>(P-024)"}
    L -->|"unset (now)"| P1["Pass – Direct<br/>timing_not_checked<br/>overall Incomplete (D-062)"]
    L -->|"approved no limit (D-103)"| P2["Pass – Direct<br/>fully checked"]
    L -->|approved value, within| P2
    L -->|approved value, exceeded| F3["Fail too_late"]
    RM -->|"no; low-confidence one"| U1["Unable to Verify"]
    RM -->|no| Z{"Both placement zones visible<br/>from the shock to the end<br/>of the recording? (A-022)"}
    Z -->|yes| F4["Fail missing"]
    Z -->|"no: partly, never, unknown"| U2["Unable to Verify"]
```

## (l) R3: paddles placed firmly on the chest (P-035, built in Increment 15; pending until approved)

Placement timing and presence only; `not_in_zone` waits for the approved chest regions (OQ-012,
D-106). `w` is `simultaneous_window_seconds`. The only inference source is the shock on the
screen; a paddle removal never infers (D-115).

```mermaid
flowchart TD
    S{"Shock time?<br/>(screen only, D-093)"} -->|"no (even with a removal, D-115)"| NE["Not evaluable<br/>because of R5"]
    S -->|yes| T{"paddles_firmly_on_chest<br/>at or before shock + w?"}
    T -->|yes| P1["Pass – Direct"]
    T -->|no| D{"Past the gate: both derived<br/>placements before shock + w?"}
    D -->|yes| P2["Pass – Direct<br/>derived_placement"]
    D -->|no| L{"Tagged only after<br/>the shock?"}
    L -->|yes| F1["Fail placed_after_shock"]
    L -->|no| I{"The shock on screen an<br/>inference source? (default: yes)"}
    I -->|yes| P3["Pass – Inferred<br/>from the shock"]
    I -->|no| W{"Low-confidence<br/>firm placement?"}
    W -->|yes| U1["Unable to Verify"]
    W -->|no| Z{"Both placement zones visible<br/>first paddle taken → shock?"}
    Z -->|yes| F2["Fail missing"]
    Z -->|"no (e.g. one paddle visible,<br/>no tag then, A-019)"| U2["Unable to Verify"]
```

## (m) R4: both discharge buttons pressed (P-036, built in Increment 16; pending until approved)

The placement is the firm-placement tag, or past the gate the later derived placement. `w` is
`simultaneous_window_seconds`. The only inference source is the shock on the screen, so the
coverage branch is unreachable by default (OQ-061); a paddle removal never infers (D-115).

```mermaid
flowchart TD
    S{"Shock time?<br/>(screen only)"} -->|yes| V{"A press after placement − w<br/>and at or before shock + w?"}
    V -->|"yes, placement known"| P1["Pass – Direct"]
    V -->|"yes, no placement"| P2["Pass – Direct<br/>order_not_checked"]
    V -->|no| E{"A press clearly before<br/>the placement?"}
    E -->|yes| F1["Fail before_placement"]
    E -->|no| L{"Presses only<br/>after the shock?"}
    L -->|yes| U0["Unable to Verify<br/>contradictory"]
    L -->|no| I{"The shock on screen an<br/>inference source? (default: yes)"}
    I -->|yes| P3["Pass – Inferred<br/>from the shock"]
    I -->|no| W{"Low-confidence press?"}
    W -->|yes| U1["Unable to Verify"]
    W -->|no| Z{"Both paddles visible<br/>placement → shock?"}
    Z -->|yes| F2["Fail not_pressed"]
    Z -->|"no: partly, never, no track"| U2["Unable to Verify"]
    S -->|"no (even with a removal, D-115)"| E0{"A press clearly before the<br/>placement, and none after it?"}
    E0 -->|yes| F1
    E0 -->|no| NE["Not evaluable<br/>because of R5"]
```

## (n) Step 9d: derived per-zone gel application (P-037; D-111, D-112)

Built in the rule engine's exporter from the `learner_hand` box (the bottle hand only, A-024) and
the zone boxes. Settings are placeholders.

```mermaid
flowchart TD
    PH["Gel phase: start → first placement tag<br/>(else 9c placement, else first_paddle_taken)"] --> H{"learner_hand box<br/>in the gel phase?"}
    H -->|no| NH["Every zone unknown<br/>gel_hand_not_tracked"]
    H -->|yes| B["Bottle period: the hand box's<br/>first to last frame"]
    B --> F["Each frame: gap from the hand box to<br/>each visible zone box (over the diagonal)"]
    F --> N{"Nearest zone within<br/>gel_hand_zone_max_gap?"}
    N -->|no| AW["Away"]
    N -->|yes| R{"Other zone at least<br/>gel_zone_nearer_ratio × further?"}
    R -->|no| AM["Ambiguous"]
    R -->|yes| Z["Frame of that zone"]
    Z --> V["Visits: dips ≤ gel_exit_frames<br/>stay in one visit"]
    V --> D{"≥ gel_dwell_frames<br/>frames?"}
    D -->|yes| APP["Application: apical/sternal_gel_applied<br/>derived_gel_application"]
    D -->|no| NA["No application"]
    APP --> G1["Zone gelled"]
    NA --> S{"Zone visible and hand tracked<br/>throughout the bottle period?"}
    S -->|yes| G2["Zone not gelled"]
    S -->|no| G3["Zone unknown"]
    APP --> T["Cross-check with Gel applied tags<br/>(gel_validation.csv/.md)"]
    G1 --> GATE{"9d gate: reviewed for this<br/>export_id and gel settings?"}
    G2 --> GATE
    G3 --> GATE
    GATE -->|yes| USE["Adapter: events + gel regions<br/>(gelled/not gelled covered, unknown unknown)"]
    GATE -->|no| HOLD["Kept in records.jsonl;<br/>R1 uses the tag-count proxy"]
```

## (o) R1: gel twice, once to each zone, before placement (P-038, built in Increment 17; pending until approved)

```mermaid
flowchart TD
    A{"Gel only after the<br/>first placement?"} -->|yes| F0["Fail after_placement"]
    A -->|no| G{"Gel status per zone known?<br/>(past the 9d gate)"}
    G -->|yes| Z{"Zones"}
    Z -->|both gelled| P1["Pass – Direct<br/>derived_gel_application"]
    Z -->|"one gelled, other not"| F1["Fail applied_once"]
    Z -->|neither gelled| F2["Fail missing"]
    Z -->|a zone unknown| U1["Unable to Verify"]
    G -->|"no: tag-count proxy"| V{"Zones visible throughout<br/>the gel phase?"}
    V -->|both| C{"Separate gel tags"}
    C -->|2+| P2["Pass – Direct"]
    C -->|1| F3["Fail applied_once"]
    C -->|0| F4["Fail missing"]
    V -->|one| C1{"Tags?"}
    C1 -->|0| F4
    C1 -->|1+| U2["Unable to Verify"]
    V -->|none or unknown| U2
    P1 --> T{"gel_application_period_seconds"}
    P2 --> T
    T -->|"unset (now)"| TN["timing_not_checked"]
    T -->|"approved, exceeded"| F5["Fail outside_time_period"]
```
