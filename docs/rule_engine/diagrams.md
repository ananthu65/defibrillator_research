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
    H["P-009 Shock time · P-010 Phases<br/>P-011 Resolve commands · P-012 Key times"]
    I["P-014 Each rule<br/>(P-015 R8, P-016 R3/R4)"]:::planned
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

## (c) The decision ladder every rule follows (P-014, planned)

```mermaid
flowchart TD
    S["Rule"] --> P1{"Approved?"}
    P1 -->|no| R0["Pending<br/>not counted"]
    P1 -->|yes| P2{"Rules it depends on<br/>evaluable and passed?"}
    P2 -->|no| R1["Not evaluable<br/>because of that rule"]
    P2 -->|yes| P3{"Facts it needs present?<br/>e.g. shock time"}
    P3 -->|no| R2["Not evaluable<br/>because of the missing step"]
    P3 -->|yes| P4{"Evidence present?"}
    P4 -->|yes, correct| R3["Pass – Direct"]
    P4 -->|yes, shows the mistake| R4["Fail<br/>with failure code"]
    P4 -->|weak| P5{"Approved inference?<br/>P-015 / P-016"}
    P5 -->|yes| R5["Pass – Inferred"]
    P5 -->|no| M["What missing means<br/>P-008"]
    P4 -->|missing| M
    classDef planned stroke-dasharray: 5 5
    class S,P1,P2,P3,P4,P5,R0,R1,R2,R3,R4,R5 planned
```

## (d) What a missing event means (P-007, P-008, P-013)

```mermaid
flowchart TD
    Q["A required event is missing"] --> L{"Low-confidence detection<br/>of it exists? P-008, P-013"}
    L -->|yes| U1["Unable to Verify<br/>low_confidence_evidence<br/>(never Fail)"]
    L -->|no| C{"Coverage P-007<br/>region → source → modality"}
    C -->|covered| F["Fail"]
    C -->|not covered| U2["Unable to Verify"]
    C -->|unknown, incl. no header| U3["Unable to Verify (interim)<br/>coverage_policy_undecided"]
```

## (e) Shock time and phases (P-009, P-010, P-011)

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
    CR -->|within 0.5 s| UR2["Unresolved<br/>command_near_shock"]
    CR -->|before| CO["Continue"]
    CR -->|after| ST["Start"]
    N1 --> UR3["Commands unresolved<br/>no_shock_time"]
    N2 --> UR3
```

## (f) R8: apical before sternal (P-015, planned)

```mermaid
flowchart TD
    Z{"Placement zones visible?"} -->|both| D1{"Compare apical and<br/>sternal placement times"}
    D1 -->|apical first| P["Pass – Direct"]
    D1 -->|sternal first| F["Fail wrong_order"]
    D1 -->|same time| FS["Fail simultaneous"]
    Z -->|one| I{"Visible paddle placed at<br/>the first placement time?"}
    I -->|same time| W1["That paddle was first<br/>(inferred)"]
    I -->|clearly later| W2["The other paddle was first<br/>(inferred)"]
    I -->|clearly earlier| C["Unable to Verify<br/>contradictory"]
    W1 --> O{"Apical first?"}
    W2 --> O
    O -->|yes| PI["Pass – Inferred"]
    O -->|no| IF["Inferred mistake<br/>Unable to Verify until decided<br/>inferred_fail_policy_undecided"]
    Z -->|none, or no first placement| N{"Fallback switched on?<br/>(off by default)"}
    N -->|no| U["Unable to Verify"]
    N -->|yes| AS["Assumed apical first<br/>not counted"]
    classDef planned stroke-dasharray: 5 5
    class Z,D1,P,F,FS,I,W1,W2,C,O,PI,IF,N,U,AS planned
```

## (g) Overall result (P-017, planned)

```mermaid
flowchart TD
    A{"Any counted rule Fail?"} -->|yes| F["Overall Fail<br/>(any mistake fails, D-001)"]
    A -->|no| B{"Any Unable to Verify?"}
    B -->|yes| U["Fail or faculty review<br/>(undecided, OQ-002)"]
    B -->|no| P["Overall Pass"]
    N["Pending rules: reported, not counted"] -.-> A
    classDef planned stroke-dasharray: 5 5
    class A,B,F,U,P,N planned
```
