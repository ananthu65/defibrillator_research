# Assessment Pipeline Flow
# Version 2

## Overview

This document describes how data flows through the ARTS Defibrillation Assessment Pipeline from raw inputs to the final assessment report.

The pipeline separates AI-based event detection from deterministic rule-based assessment.

---

# Complete Pipeline

```
               VIDEO
                  │
                  ▼
      Video Detection Module
                  │
                  ▼
        Video Event Generator
                  │
                  │
                  ├───────────────┐
                  │               │
                  ▼               │

               AUDIO             │
                  │              │
                  ▼              │
         Whisper Transcription   │
                  │              │
                  ▼              │
      Audio Command Detection    │
                  │              │
                  ▼              │
        Audio Event Generator    │
                  │              │
                  └──────────────┘
                         │
                         ▼

              Timeline Fusion Engine
                         │
                         ▼

         Unified Chronological Timeline
                         │
                         ▼

            Rule Evaluation Engine
                         │
                         ▼

          Criterion Evaluation Results
                         │
                         ▼

             Feedback Generation
                         │
                         ▼

            Final Assessment Report
```

---

# Stage 1 – Video Detection

Input

- Video recording

Output

- Timestamped visual events

Responsibilities

- Detect actions
- Detect paddle interactions
- Detect shock delivery
- Estimate confidence

No assessment is performed.

---

# Stage 2 – Audio Detection

Input

- Audio recording

Output

- Timestamped command events

Responsibilities

- Speech recognition
- Command classification
- Timestamp extraction

No assessment is performed.

---

# Stage 3 – Timeline Fusion

Inputs

- Video events
- Audio events

Responsibilities

- Merge event streams
- Sort chronologically
- Preserve confidence
- Preserve event source
- Remove duplicate events where appropriate

Output

One unified event timeline.

---

# Stage 4 – Rule Evaluation

The Rule Evaluation Engine processes every criterion independently.

Each rule follows the same evaluation order.

```
Timeline
    │
    ▼
Presence
    │
    ▼
Dependencies
    │
    ▼
Order
    │
    ▼
Timing
    │
    ▼
Inference
    │
    ▼
Safety
    │
    ▼
CriterionEvaluation
```

---

# Stage 5 – Feedback

The Feedback Generator converts CriterionEvaluation objects into human-readable assessment feedback.

Feedback is deterministic and based entirely on rule evaluation outcomes.

---

# Design Philosophy

The pipeline follows these principles:

- AI detects events.
- The Rule Engine performs assessment.
- Assessment decisions are deterministic.
- Detection and assessment remain independent.
- Each module has a single responsibility.
- New rules can be added without changing the AI models.

---

# Version 2 Improvements

Compared to Version 1, Version 2 introduces:

- Timeline Fusion Engine
- Timing rule evaluation
- Inference-based assessment
- Expanded criterion outcomes
- Modular assessment architecture
- Improved documentation