"""
End-to-end integration tests for the assessment pipeline.

These tests verify that the complete pipeline works from
input events through to the final assessment report.
"""

import pytest

from assessment_pipeline.core.assessment_pipeline import assess

from assessment_pipeline.tests.sample_events import (
    perfect_defibrillation_events,
    delayed_cpr_events,
    delayed_shock_events,
    missing_gel_events,
    inferred_button_press_events,
)


def _passed(report, description):
    """
    Return whether the checklist item with the given description passed.
    """
    for item in report.checklist:
        if item.description == description:
            return item.passed
    raise AssertionError(f"Checklist item not found: {description}")


def test_perfect_defibrillation_pipeline():
    """
    Perfect performance should pass every checklist item.
    """

    report = assess(perfect_defibrillation_events())

    assert len(report.checklist) == 8

    assert all(item.passed for item in report.checklist)

    assert len(report.feedback) >= 8


def test_missing_gel_pipeline():
    """
    Missing gel should only fail the gel criterion.
    """

    report = assess(missing_gel_events())

    assert not _passed(report, "Apply gel / pads")

    assert any(
        "gel" in feedback.lower()
        for feedback in report.feedback
    )


def test_delayed_cpr_pipeline():
    """
    Delayed CPR should fail the CPR timing criterion.
    """

    report = assess(delayed_cpr_events())

    assert not _passed(
        report,
        "Resumes chest compressions promptly"
    )

    assert any(
        "compressions" in feedback.lower()
        for feedback in report.feedback
    )


def test_delayed_shock_pipeline():
    """
    Delayed shock should fail the 5-second criterion.
    """

    report = assess(delayed_shock_events())

    assert not _passed(
        report,
        "Stop chest compressions → Shock within 5 seconds"
    )

    assert any(
        "5 seconds" in feedback
        or "shock" in feedback.lower()
        for feedback in report.feedback
    )


def test_inferred_button_press_pipeline():
    """
    Shock button press may be inferred.
    """

    report = assess(
        inferred_button_press_events()
    )

    assert _passed(
        report,
        "Presses both paddles simultaneously"
    )


def test_report_structure():
    """
    Report should expose the expected public interface.
    """

    report = assess(
        perfect_defibrillation_events()
    )

    assert hasattr(report, "checklist")
    assert hasattr(report, "feedback")

    assert isinstance(report.checklist, list)
    assert isinstance(report.feedback, list)


def test_print_report(capsys):
    """
    Demonstration output for the completed assessment.
    """

    report = assess(
        perfect_defibrillation_events()
    )

    print("\n")
    print("=" * 60)
    print("FINAL ASSESSMENT REPORT")
    print("=" * 60)

    for item in report.checklist:
        status = "PASS" if item.passed else "FAIL"
        print(f"{status:4} | {item.description}")

    print("\nFeedback:")

    for feedback in report.feedback:
        print(f" - {feedback}")

    captured = capsys.readouterr()

    assert "FINAL ASSESSMENT REPORT" in captured.out