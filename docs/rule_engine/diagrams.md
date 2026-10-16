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
        ann["Annotation exporter<br/>(development data, see h)"]
    end
    rec --> vid --> merge
    rec --> asr --> merge
    merge --> eng
    ann -.-> eng
    eng --> fb --> app
    eng --> app
```

## (b) Inside the rule engine

```mermaid
flowchart TD
    A0["P-028 Annotation exporter<br/>(CVAT backups, built; see h)"]
    A["P-001 Adapter<br/>(annotation now, models later)"]:::planned
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

## (e) Shock time, phases and command resolution (P-009, P-010, P-011)

```mermaid
flowchart TD
    S0{"How many confident<br/>shock indications?"} -->|two or more| N1["No shock time<br/>multiple_shocks<br/>(not guessed)"]
    S0 -->|one| T1["Shock time = shock on screen"]
    S0 -->|none| R{"Paddle removal?"}
    R -->|yes| T2["Shock time = first removal<br/>shock_time_from_removal<br/>(delays look shorter)"]
    R -->|no| N2["No shock time<br/>no_shock"]
    T1 --> PH["P-010 Phases: before / at / after"]
    T2 --> PH
    PH --> CR{"P-011 'Resume compressions'<br/>relative to the shock"}
    CR -->|before removal, fallback only| UR1["Unresolved<br/>command_before_removal"]
    CR -->|"within simultaneous_window_seconds<br/>(configurable, placeholder 0.5 s)"| UR2["Unresolved<br/>command_near_shock"]
    CR -->|before| CO["Continue"]
    CR -->|after| ST["Start"]
    N1 --> UR3["Commands unresolved<br/>no_shock_time"]
    N2 --> UR3
```

### (e2) Which start command is the restart (P-012)

Every start command goes through these checks **on its own**. Commands that do not count are
set aside, and the **earliest remaining** one is the restart, so a later start can still be
the restart.

```mermaid
flowchart TD
    K{"For each start command:<br/>how was the shock time<br/>established? P-009"} -->|no shock time| A0["Ambiguous, not a mistake<br/>no_shock_time (D-054)<br/>no restart time"]
    K -->|shock on screen| B{"This command at or<br/>before the shock?"}
    B -->|yes| B1["Does not count: a mistake<br/>start_command_before_shock<br/>(A7 reports it)"]
    B -->|no| RS["Candidate: after the shock"]
    K -->|from paddle removal| C{"This command at or<br/>before the removal?"}
    C -->|yes| C1["Ambiguous, not a mistake<br/>command_before_removal (D-053)<br/>R7/A6, A8 → Unable to Verify"]
    C -->|no| RR["Candidate: after the removal"]
    RES["Unresolved resume command<br/>before the removal (D-024)"] -->|"also makes the restart ambiguous (D-059)"| C1
    RS --> E["Restart = earliest candidate"]
    RR --> E
```

## (f) R8: apical before sternal (P-015, planned)

```mermaid
flowchart TD
    Z{"Placement zones visible?"} -->|both| B2{"Both placement<br/>events present?"}
    B2 -->|no| PM1["Unable to Verify<br/>placement_missing (D-058)<br/>R3 reports the missing placement"]
    B2 -->|yes| D1{"Compare apical and<br/>sternal placement times"}
    D1 -->|apical first| P["Pass – Direct"]
    D1 -->|sternal first| F["Fail wrong_order"]
    D1 -->|same time| FS["Fail simultaneous"]
    Z -->|one| V{"Visible paddle has<br/>a placement event?"}
    V -->|no| PM2["Unable to Verify, no inference<br/>placement_missing (D-058)"]
    V -->|yes| I{"Visible paddle placed at<br/>the first placement time?"}
    I -->|same time| W1["That paddle was first<br/>(inferred)"]
    I -->|clearly later| W2["The other paddle was first<br/>(inferred)"]
    I -->|clearly earlier| C["Unable to Verify<br/>contradictory"]
    W1 --> O{"Apical first?"}
    W2 --> O
    O -->|yes| PI["Pass – Inferred"]
    O -->|no| IF["Inferred mistake<br/>Unable to Verify until decided<br/>inferred_fail_policy_undecided"]
    Z -->|none, or no first placement| N{"Fallback switched on?<br/>(off by default)"}
    N -->|no| U["Unable to Verify"]
    N -->|yes| AS["Assumed apical first<br/>to be checked by the evaluator<br/>overall cannot be Pass (D-060)"]
    classDef planned stroke-dasharray: 5 5
    class Z,B2,PM1,D1,P,F,FS,V,PM2,I,W1,W2,C,O,PI,IF,N,U,AS planned
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
smoke-run export of 39 corrected backups (D-084).

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
    subgraph arnikan["Arnikan: rule engine"]
        REC[("records.jsonl + export_manifest.json<br/>gitignored data/rule_engine/<br/>never committed (D-084)")]
        REP["Audit outputs<br/>review list, information"]
        SMOKE[("Interim: smoke-run export<br/>39 corrected backups (D-084)")]
        CFG[/"annotation_export.yaml<br/>zone labels, usual pattern,<br/>reviewed exceptions"/]
        ADP["P-001 / P-030 adapter<br/>(Increment 10)"]
        ENG["Rule engine<br/>P-002 onward"]
        REC --> ADP --> ENG
        SMOKE -.->|until the final export| ADP
        CFG --> ADP
    end
    EXP -->|"sent: records + manifest<br/>no media"| REC
    AUD2 -->|sent| REP
    REP -->|items to fix in the backups| CVAT
    classDef planned stroke-dasharray: 5 5
    class ADP planned
```

## (i) How a zone's coverage is decided for a recording (P-030; D-074, D-080, D-082)

Decided per zone (apical, sternal) for one annotated recording, in Increment 10. The view's usual
zone pattern is used only by the audit's review list, never here.

```mermaid
flowchart TD
    Z["A placement zone of one recording"] --> X{"Reviewed exception:<br/>annotator confirmed it was<br/>genuinely not visible?"}
    X -->|yes| NC1["not covered (D-082)<br/>off the review list"]
    X -->|no| T{"Zone track in<br/>the CVAT backup?"}
    T -->|no| UN["unknown (D-074)<br/>on the review list if the view<br/>usually shows this zone"]
    T -->|yes| V{"Visible on any frame?<br/>(a training box exists, D-079)"}
    V -->|yes| CO["covered"]
    V -->|no, outside on every frame| NC2["not covered (D-080)<br/>audit information only"]
    NC1 --> P7["→ P-007 coverage status<br/>→ P-008 what a missing<br/>placement means"]
    UN --> P7
    CO --> P7
    NC2 --> P7
    classDef planned stroke-dasharray: 5 5
    class Z,X,NC1,T,UN,V,CO,NC2,P7 planned
```
