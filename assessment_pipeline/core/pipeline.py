from timeline_fusion import merge_timelines

from clinical_logic import resolve_clinical_events

from rule_engine import evaluate_rules

from assessment_pipeline.core.assessment_report import calculate_score


def run_pipeline(audio_events, video_events):

    timeline = merge_timelines(

        audio_events,

        video_events

    )

    clinical_events = resolve_clinical_events(

        timeline

    )

    rule_results = evaluate_rules(

        clinical_events

    )

    report = calculate_score(

        rule_results

    )

    return report