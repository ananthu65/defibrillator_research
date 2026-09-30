"""
Demonstration of the complete Defibrillation Assessment Pipeline.

This script runs all predefined assessment scenarios and prints
the generated checklist and feedback.

Run:

    python assessment_pipeline/demo_pipeline.py
"""

from assessment_pipeline.core.assessment_pipeline import assess

from assessment_pipeline.tests.sample_events import (
    perfect_defibrillation_events,
    missing_gel_events,
    delayed_cpr_events,
    delayed_shock_events,
    inferred_button_press_events,
    empty_events,
)


def print_report(title, report):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)

    passed = sum(item.passed for item in report.checklist)
    total = len(report.checklist)

    print(f"\nOverall Score : {passed}/{total}\n")

    print("CHECKLIST")
    print("-" * 80)

    for item in report.checklist:

        status = "PASS" if item.passed else "FAIL"

        if getattr(item, "inferred", False):
            status += " (INFERRED)"

        print(f"[{status:<15}] {item.description}")

        if getattr(item, "comments", ""):
            print(f"   Comment : {item.comments}")

    print("\nFEEDBACK")
    print("-" * 80)

    for feedback in report.feedback:
        print(f"• {feedback}")

    print()


def run_demo():

    scenarios = [

        (
            "Scenario 1 - Perfect Defibrillation",
            perfect_defibrillation_events(),
        ),

        (
            "Scenario 2 - Missing Gel",
            missing_gel_events(),
        ),

        (
            "Scenario 3 - Delayed CPR",
            delayed_cpr_events(),
        ),

        (
            "Scenario 4 - Delayed Shock",
            delayed_shock_events(),
        ),

        (
            "Scenario 5 - Inferred Shock Button Press",
            inferred_button_press_events(),
        ),

        (
            "Scenario 6 - Empty Timeline",
            empty_events(),
        ),
    ]

    print()
    print("#" * 80)
    print("DEFIBRILLATION ASSESSMENT PIPELINE DEMONSTRATION")
    print("#" * 80)

    for title, events in scenarios:

        report = assess(events)

        print_report(title, report)

    print("#" * 80)
    print("END OF DEMONSTRATION")
    print("#" * 80)


if __name__ == "__main__":
    run_demo()