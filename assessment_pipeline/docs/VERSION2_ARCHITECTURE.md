# ARTS Defibrillation Assessment Pipeline
# Version 2 Architecture

## Overview

Version 2 extends the Version 1 rule-based assessment pipeline by introducing a complete assessment architecture that supports:

- Unified audio and video event processing
- Timeline fusion
- Presence evaluation
- Order evaluation
- Timing evaluation
- Inference-based assessment
- Safety rule evaluation
- Deterministic feedback generation

The AI models are responsible only for detecting events. All assessment decisions are made by a deterministic Python Rule Evaluation Engine.

---

# System Architecture

```
                   VIDEO
                      │
          Object / Action Detection
                      │
               Video Event Generator
                      │
                      ▼

                   AUDIO
                      │
      Whisper + Command Classification
                      │
               Audio Event Generator
                      │
                      ▼

             Timeline Fusion Engine
                      │
                      ▼

          Unified Chronological Timeline
                      │
                      ▼

             Rule Evaluation Engine
          ├── Presence Rules
          ├── Order Rules
          ├── Timing Rules
          ├── Inference Rules
          └── Safety Rules
                      │
                      ▼

           Criterion Evaluations
                      │
                      ▼

             Feedback Generator
                      │
                      ▼

             Final Assessment Report
```

---

# Video Engine

## Responsibilities

The video engine is responsible for detecting visual actions and objects from a single-camera recording.

It produces timestamped events only.

The video engine does not perform assessment.

### Output

Each detected event contains:

- Event name
- Timestamp
- Confidence
- Source = VIDEO

Typical events include:

- gel_applied
- take_first_paddle
- take_second_paddle
- place_paddles
- shock_button_pressed
- shock_delivered
- remove_paddles

---

# Audio Engine

## Responsibilities

The audio engine converts speech into timestamped clinical command events.

Speech recognition is performed using Whisper.

Command classification converts transcript phrases into structured assessment events.

The audio engine performs no assessment.

### Output

Each detected event contains:

- Event name
- Timestamp
- Confidence
- Source = AUDIO

Typical events include:

- oxygen_away
- continue_chest_compressions
- all_stand_clear
- stop_chest_compressions
- dc_shock_command
- start_chest_compressions

---

# Timeline Fusion Engine

The Timeline Fusion Engine combines video events and audio events into one chronological event list.

Responsibilities:

- Merge event streams
- Sort by timestamp
- Preserve source information
- Preserve confidence
- Validate timestamps
- Remove duplicate events where appropriate

Output:

A unified ordered event timeline.

---

# Rule Evaluation Engine

The Rule Evaluation Engine is the core of the assessment system.

It evaluates every assessment criterion using the unified timeline.

Each rule may evaluate:

- Event presence
- Event order
- Event timing
- Approved inference
- Safety conditions

Each rule returns a CriterionEvaluation object.

Possible outcomes are:

- PASS_DIRECT
- PASS_INFERRED
- FAIL
- UNABLE_TO_ASSESS
- MANUAL_REVIEW
- CRITICAL_ERROR

---

# Rule Categories

## Presence Rules

Evaluate whether required events are present.

Examples:

- R1
- R3
- R5
- R6

---

## Order Rules

Evaluate procedural sequence.

Examples:

- R2
- R4

---

## Timing Rules

Evaluate clinically approved timing requirements.

Current timing rules:

- R7
- R8

---

## Inference Rules

Apply approved downstream inference when direct evidence is unavailable.

Current inference rule:

- R9

---

## Safety Rules

Evaluate critical safety violations.

Safety rules may return CRITICAL_ERROR when configured.

---

# Feedback Generator

The feedback generator converts CriterionEvaluation results into predefined feedback messages.

Feedback is deterministic.

No free-text generation is used.

Each assessment criterion has predefined pass and fail messages.

---

# Repository Structure

```
assessment_pipeline/

audio/

video/

core/

docs/

local_tests/
```

---

# Version 2 Objectives

Version 2 introduces:

- Timeline Fusion
- Timing Rules
- Inference Rules
- Improved Rule Engine
- Expanded Unit Testing
- Improved Documentation

Version 2 maintains deterministic rule-based assessment while remaining modular and extensible for future assessment criteria.