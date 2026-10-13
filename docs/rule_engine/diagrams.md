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
        eng["Rule engine<br/>P-001 to P-018"]
        ann["Annotation timelines<br/>(development data)"]
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
    A["P-001 Adapter<br/>(annotation now, models later)"]:::planned
    B["P-002 Validate timeline"]
    C["P-003 Map names"]
    D["P-004 Set aside low-confidence events"]
    E["P-005 Flag anomalies"]
    F["P-006 Check header"]
    G["P-007 Coverage status<br/>P-008 What missing means"]
    H["P-009 Shock time · P-010 Phases<br/>P-011 Resolve commands · P-012 Key times<br/>P-013 Weak ambiguous commands"]
    I["P-014 Each rule (planned)<br/>shared checks P-019 to P-025 built<br/>P-015 R8, P-016 R3/R4 planned"]:::planned
    J["P-017 Overall result"]:::planned
    K["P-018 Report and checklist"]:::planned
    X["Rejected: no assessment"]
    A --> B
    B -->|malformed| X
    B --> C --> D --> E --> F
    F -->|invalid or contradicts events| X
    F --> G --> H --> I --> J --> K
    classDef planned stroke-dasharray: 5 5
```

## (c) The decision ladder every rule follows (P-014)

The shared checks (P-019 to P-025) are **built** (Increment 6). The engine that runs the ladder
for each rule, including the approval check, is planned for Increment 7. Times on the ladder are
compared with P-025, and time limits with P-024 (timing not checked when there is no limit).

```mermaid
flowchart TD
    S["Rule"] --> P1{"Approved?"}
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
    classDef planned stroke-dasharray: 5 5
    class S,P1,R0 planned
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

## (g) Overall result (P-017, planned)

```mermaid
flowchart TD
    A{"Any evaluated rule Fail?"} -->|yes| F["Overall Fail<br/>(any mistake fails, D-001)"]
    A -->|no| PD{"Any rule pending, or<br/>a result assumed (R8 fallback)?"}
    PD -->|yes| INC["Incomplete: rules not yet approved,<br/>or assumed result to be checked<br/>never Pass (D-055, D-060)"]
    PD -->|no| B{"Any Unable to Verify<br/>or Not evaluable? (D-056)"}
    B -->|yes| U["Fail or faculty review<br/>(undecided, OQ-002)"]
    B -->|no| P["Overall Pass<br/>every rule evaluated and passed"]
    classDef planned stroke-dasharray: 5 5
    class A,PD,INC,B,F,U,P planned
```
