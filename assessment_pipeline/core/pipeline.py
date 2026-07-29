"""
pipeline.py

Version 2 Assessment Pipeline
"""

from assessment_pipeline.core.timeline_fusion import merge_timelines

from assessment_pipeline.core.clinical_logic import apply_clinical_logic

from assessment_pipeline.core.rule_engine import evaluate_rules

from assessment_pipeline.core.final_assessment import (
    build_final_assessment,
)


def run_pipeline(audio_events, video_events):
    """
    Execute the complete assessment pipeline.

    Flow

    Audio + Video
            ↓
    Timeline Fusion
            ↓
    Clinical Logic
            ↓
    Rule Evaluation
            ↓
    Final Assessment Report
    """

    timeline = merge_timelines(
        audio_events,
        video_events,
    )

    clinical_events = apply_clinical_logic(
        timeline,
    )

    evaluations = evaluate_rules(
        clinical_events,
    )

    report = build_final_assessment(
        evaluations,
    )

    return report