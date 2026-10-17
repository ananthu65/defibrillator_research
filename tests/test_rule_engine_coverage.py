import copy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

import yaml

from pipeline.config import ROOT
from rules.config import EngineSettings, RuleEngineConfig, load_rules_config
from rules.coverage import Coverage, TimelineHeader
from rules.errors import ConfigError, TimelineError
from rules.prepare import prepare_timeline
from schemas.event import Event

CONFIG = load_rules_config()
ENGINE = yaml.safe_load((ROOT / "configs/rule_engine/engine.yaml").read_text(encoding="utf-8"))
RULES = yaml.safe_load((ROOT / "configs/rules.yaml").read_text(encoding="utf-8"))
REGIONS = tuple(CONFIG.engine.regions)


def event(name, t, source="annotation", confidence=1.0, event_id=None, **fields):
    return Event(name, t, t, source, confidence, event_id=event_id or f"{name}@{t}", **fields)


def header(**fields):
    return TimelineHeader.from_dict(fields, regions=REGIONS)


def coverage(events, head=None, config=CONFIG):
    return Coverage(prepare_timeline(events, config), config, head)


def with_policy(**policy):
    """CONFIG with coverage_policy keys replaced (outcomes, by_modality, by_source, by_region)."""
    data = copy.deepcopy(ENGINE)
    data["coverage_policy"].update(policy)
    return replace(CONFIG, engine=EngineSettings.from_dict(data))


VIDEO_TIMELINE = [event("Gel applied", 1), event("shock_delivered_on_screen", 30)]  # annotation, no audio


class Header(unittest.TestCase):
    def test_full_header_is_accepted(self):
        head = header(recording_id="P03_LL", camera_angle="LL", duration_seconds=95.5,
                      analyses_run={"video": True, "audio": False}, coverage={"region:apical_zone": "not_covered"})
        self.assertEqual((head.recording_id, head.analyses_run["audio"], head.coverage["region:apical_zone"]),
                         ("P03_LL", False, "not_covered"))

    def test_empty_header_is_accepted(self):
        self.assertEqual(header(), TimelineHeader())

    def test_invalid_headers_are_rejected(self):
        cases = [({"recording": "x"}, "unknown keys"),
                 ({"duration_seconds": 0}, "positive number"),
                 ({"duration_seconds": True}, "positive number"),
                 ({"camera_angle": " "}, "nonempty string"),
                 ({"analyses_run": {"smell": True}}, "analyses_run"),
                 ({"analyses_run": {"audio": "yes"}}, "analyses_run"),
                 ({"coverage": {"region:left_zone": "covered"}}, "unknown coverage scope"),
                 ({"coverage": {"modality:audio": "partly"}}, "must be one of")]
        for data, message in cases:
            with self.subTest(data=data), self.assertRaisesRegex(TimelineError, message) as caught:
                TimelineHeader.from_dict(data, regions=REGIONS)
            self.assertEqual(caught.exception.code, "invalid_header")
        with self.assertRaisesRegex(TimelineError, "expected a mapping"):
            TimelineHeader.from_dict(["video"], regions=REGIONS)

    def test_header_that_contradicts_its_events_is_rejected(self):
        shock = Event("shock_delivered_on_screen", 30, 30, "video", 0.9, camera_angle="LL", event_id="s",
                      metadata={"task_id": "P03_LL"})
        cases = [(header(camera_angle="T"), "camera_angle"),
                 (header(recording_id="P04_LL"), "recording_id"),
                 (header(duration_seconds=20), "end after duration_seconds"),
                 (header(analyses_run={"video": False}), "video did not run")]
        for head, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(TimelineError, message) as caught:
                coverage([shock], head)
            self.assertEqual(caught.exception.code, "header_mismatch")

    def test_matching_header_is_accepted(self):
        shock = Event("shock_delivered_on_screen", 30, 30, "video", 0.9, camera_angle="LL", event_id="s",
                      metadata={"task_id": "P03_LL"})
        coverage([shock], header(recording_id="P03_LL", camera_angle="LL", duration_seconds=60,
                                 analyses_run={"video": True, "audio": True}))


class DurationTolerance(unittest.TestCase):
    """duration_tolerance_seconds is 0.5 (placeholder); the check uses each event's end time."""

    def command(self, start, end):
        return Event("stand_clear_command", start, end, "audio", 0.9, event_id="c")

    def test_event_ending_exactly_at_duration_is_accepted(self):
        coverage([self.command(58, 60)], header(duration_seconds=60))

    def test_event_ending_within_the_tolerance_is_accepted(self):
        coverage([self.command(59, 60.4)], header(duration_seconds=60))
        coverage([self.command(59, 60.5)], header(duration_seconds=60))  # boundary is inclusive

    def test_event_ending_beyond_the_tolerance_is_a_mismatch(self):
        with self.assertRaisesRegex(TimelineError, r"end after duration_seconds 60 \+ duration_tolerance_seconds 0.5") \
                as caught:
            coverage([self.command(59, 60.6)], header(duration_seconds=60))
        self.assertEqual(caught.exception.code, "header_mismatch")

    def test_low_confidence_events_are_checked_too(self):
        weak = Event("stand_clear_command", 70, 71, "audio", 0.1, event_id="weak")
        with self.assertRaisesRegex(TimelineError, "weak"):
            coverage([weak], header(duration_seconds=60))

    def test_tolerance_is_configurable(self):
        data = copy.deepcopy(ENGINE)
        data["duration_tolerance_seconds"] = {"value": 2.0, "placeholder": True}
        config = replace(CONFIG, engine=EngineSettings.from_dict(data))
        coverage([self.command(59, 61.9)], header(duration_seconds=60), config)

    def test_negative_tolerance_is_rejected(self):
        data = copy.deepcopy(ENGINE)
        data["duration_tolerance_seconds"] = -0.1
        with self.assertRaisesRegex(ConfigError, "nonnegative"):
            EngineSettings.from_dict(data)


class Status(unittest.TestCase):
    def test_no_header_means_unknown_for_everything(self):
        cov = coverage(VIDEO_TIMELINE)
        for name in ("gel_applied", "stand_clear_command", "apical_paddle_placed"):
            with self.subTest(name=name):
                self.assertEqual(cov.status(name).status, "unknown")
                self.assertEqual(cov.status(name).basis, "no timeline header")

    def test_header_without_the_modality_means_unknown(self):
        status = coverage(VIDEO_TIMELINE, header(analyses_run={"video": True})).status("stand_clear_command")
        self.assertEqual((status.status, status.basis), ("unknown", "not stated in timeline header"))

    def test_analyses_run_sets_modality_coverage(self):
        cov = coverage(VIDEO_TIMELINE, header(analyses_run={"video": True, "audio": False}))
        self.assertEqual(cov.status("gel_applied").status, "covered")
        self.assertEqual(cov.status("stand_clear_command").status, "not_covered")
        self.assertEqual(cov.status("stand_clear_command").basis, "header.analyses_run")

    def test_explicit_modality_coverage_wins_over_analyses_run(self):
        # audio ran, but upstream marks the whole audio track unusable
        status = coverage(VIDEO_TIMELINE, header(analyses_run={"audio": True},
                                                 coverage={"modality:audio": "not_covered"})).status("shock_command")
        self.assertEqual((status.status, status.scope, status.basis),
                         ("not_covered", "modality:audio", "header.coverage"))

    def test_region_coverage_applies_only_to_its_events(self):
        cov = coverage(VIDEO_TIMELINE, header(analyses_run={"video": True},
                                              coverage={"region:sternal_zone": "not_covered"}))
        self.assertEqual(cov.status("sternal_paddle_placed").status, "not_covered")
        self.assertEqual(cov.status("sternal_paddle_placed").scope, "region:sternal_zone")
        self.assertEqual(cov.status("apical_paddle_placed").status, "covered")  # falls back to modality
        self.assertEqual(cov.status("gel_applied").status, "covered")

    def test_region_beats_source_beats_modality(self):
        head = header(analyses_run={"video": True}, coverage={"region:apical_zone": "unknown",
                                                              "source:annotation": "not_covered"})
        cov = coverage(VIDEO_TIMELINE, head)
        self.assertEqual(cov.status("apical_paddle_placed").scope, "region:apical_zone")
        self.assertEqual(cov.status("gel_applied").scope, "source:annotation")
        self.assertEqual(cov.status("gel_applied").status, "not_covered")

    def test_window_is_accepted_and_does_not_change_whole_recording_coverage(self):
        # Reserved for time-windowed coverage (open question 16, deferred): rules can already pass it.
        cov = coverage(VIDEO_TIMELINE, header(analyses_run={"audio": True}))
        self.assertEqual(cov.status("stand_clear_command", window=(10, 30)), cov.status("stand_clear_command"))
        self.assertEqual(cov.missing("stand_clear_command", window=(10, 30)), cov.missing("stand_clear_command"))

    def test_malformed_window_is_a_programming_error(self):
        cov = coverage(VIDEO_TIMELINE)
        for window in ((30, 10), (-1, 5), [1, 2], (1,), (0, float("nan"))):
            with self.subTest(window=window), self.assertRaises(ValueError):
                cov.status("stand_clear_command", window=window)

    def test_source_scope_needs_a_single_source_for_the_modality(self):
        cov = coverage(VIDEO_TIMELINE)
        self.assertEqual(cov.scopes("gel_applied"), ["source:annotation", "modality:video"])
        self.assertEqual(cov.scopes("stand_clear_command"), ["modality:audio"])  # no audio events at all
        self.assertEqual(cov.scopes("apical_paddle_placed"),
                         ["region:apical_zone", "source:annotation", "modality:video"])


class NoAudioVersusAudioNotAnalysed(unittest.TestCase):
    """The same timeline with no audio events, under three headers."""

    def test_audio_ran_and_heard_nothing_is_a_fail(self):
        result = coverage(VIDEO_TIMELINE, header(analyses_run={"video": True, "audio": True})).missing(
            "stand_clear_command")
        self.assertEqual((result.outcome, result.coverage.status, result.flags), ("fail", "covered", ()))

    def test_audio_not_analysed_is_unable_to_verify(self):
        result = coverage(VIDEO_TIMELINE, header(analyses_run={"video": True, "audio": False})).missing(
            "stand_clear_command")
        self.assertEqual((result.outcome, result.coverage.status, result.flags),
                         ("unable_to_verify", "not_covered", ()))

    def test_no_header_is_unknown_and_flagged_undecided(self):
        result = coverage(VIDEO_TIMELINE).missing("stand_clear_command")
        self.assertEqual((result.outcome, result.coverage.status, result.flags),
                         ("unable_to_verify", "unknown", ("coverage_policy_undecided",)))
        self.assertEqual(result.decided_by, "coverage_policy.outcomes.unknown")


class LowConfidenceIsNotAbsence(unittest.TestCase):
    def test_excluded_event_gives_unable_to_verify_even_when_covered(self):
        timeline = [*VIDEO_TIMELINE, event("stand_clear_command", 20, "audio", 0.2, event_id="weak")]
        result = coverage(timeline, header(analyses_run={"video": True, "audio": True})).missing(
            "stand_clear_command")
        self.assertEqual((result.outcome, result.flags, result.low_confidence_event_ids),
                         ("unable_to_verify", ("low_confidence_evidence",), ("weak",)))
        self.assertEqual(result.coverage.status, "covered")  # still reported

    def test_never_fail_under_any_policy(self):
        timeline = [*VIDEO_TIMELINE, event("stand_clear_command", 20, "audio", 0.2)]
        config = with_policy(outcomes={"covered": "fail", "not_covered": "fail", "unknown": "fail"},
                             by_modality={"audio": {"covered": "fail"}})
        for head in (None, header(analyses_run={"audio": True}), header(coverage={"modality:audio": "not_covered"})):
            with self.subTest(head=head):
                self.assertEqual(coverage(timeline, head, config).missing("stand_clear_command").outcome,
                                 "unable_to_verify")

    def test_only_the_same_canonical_name_counts(self):
        timeline = [*VIDEO_TIMELINE, event("oxygen_away_command", 20, "audio", 0.2)]
        result = coverage(timeline, header(analyses_run={"audio": True})).missing("stand_clear_command")
        self.assertEqual(result.outcome, "fail")


class EveryPolicySetting(unittest.TestCase):
    HEADERS = {"covered": {"analyses_run": {"audio": True}}, "not_covered": {"analyses_run": {"audio": False}},
               "unknown": None}

    def test_every_status_follows_its_configured_outcome(self):
        for status, head in self.HEADERS.items():
            for outcome in ("fail", "unable_to_verify"):
                with self.subTest(status=status, outcome=outcome):
                    outcomes = copy.deepcopy(ENGINE["coverage_policy"]["outcomes"])
                    outcomes[status] = outcome  # decided value replaces the default
                    config = with_policy(outcomes=outcomes)
                    result = coverage(VIDEO_TIMELINE, head and header(**head), config).missing("stand_clear_command")
                    self.assertEqual(result.outcome, outcome)
                    self.assertEqual(result.coverage.status, status)
                    self.assertEqual(result.flags, ())  # a decided setting raises no undecided flag

    def test_overrides_most_specific_first(self):
        config = with_policy(by_modality={"video": {"covered": "unable_to_verify"}},
                             by_source={"annotation": {"covered": "fail"}},
                             by_region={"apical_zone": {"covered": "unable_to_verify"}})
        cov = coverage(VIDEO_TIMELINE, header(analyses_run={"video": True}), config)
        self.assertEqual((cov.missing("apical_paddle_placed").outcome, cov.missing("apical_paddle_placed").decided_by),
                         ("unable_to_verify", "coverage_policy.by_region.apical_zone.covered"))
        self.assertEqual((cov.missing("gel_applied").outcome, cov.missing("gel_applied").decided_by),
                         ("fail", "coverage_policy.by_source.annotation.covered"))

    def test_modality_override_applies_when_nothing_more_specific(self):
        config = with_policy(by_modality={"audio": {"covered": "unable_to_verify"}})
        result = coverage(VIDEO_TIMELINE, header(analyses_run={"audio": True}), config).missing("shock_command")
        self.assertEqual((result.outcome, result.decided_by),
                         ("unable_to_verify", "coverage_policy.by_modality.audio.covered"))

    def test_override_for_another_status_falls_back_to_default(self):
        config = with_policy(by_modality={"audio": {"unknown": "fail"}})
        result = coverage(VIDEO_TIMELINE, header(analyses_run={"audio": True}), config).missing("shock_command")
        self.assertEqual(result.decided_by, "coverage_policy.outcomes.covered")

    def test_undecided_override_is_flagged(self):
        config = with_policy(by_modality={"audio": {"covered": {"value": "unable_to_verify", "undecided": True}}})
        result = coverage(VIDEO_TIMELINE, header(analyses_run={"audio": True}), config).missing("shock_command")
        self.assertEqual(result.flags, ("coverage_policy_undecided",))
        self.assertIn("coverage_policy.by_modality.audio.covered", config.engine.undecided)


class RepositoryPolicy(unittest.TestCase):
    def test_shipped_policy(self):
        engine = CONFIG.engine
        self.assertEqual({s: engine.coverage_outcomes[s].value for s in ("covered", "not_covered", "unknown")},
                         {"covered": "fail", "not_covered": "unable_to_verify", "unknown": "unable_to_verify"})
        self.assertTrue(engine.coverage_outcomes["unknown"].undecided)
        self.assertFalse(engine.coverage_outcomes["covered"].undecided)
        self.assertEqual(engine.coverage_overrides, {})
        self.assertEqual(engine.regions, {"apical_zone": ("apical_paddle_placed",),
                                          "sternal_zone": ("sternal_paddle_placed",),
                                          "screen": ("shock_delivered_on_screen",)})   # D-094


class InvalidCoverageConfig(unittest.TestCase):
    def assertRejected(self, message, **policy):
        data = copy.deepcopy(ENGINE)
        data["coverage_policy"].update(policy)
        with self.assertRaisesRegex(ConfigError, message):
            EngineSettings.from_dict(data)

    def test_missing_policy_section(self):
        data = copy.deepcopy(ENGINE)
        del data["coverage_policy"]["by_region"]
        with self.assertRaisesRegex(ConfigError, r"missing keys \['by_region'\]"):
            EngineSettings.from_dict(data)

    def test_unknown_modality(self):
        self.assertRejected("unknown modality 'smell'", by_modality={"smell": {"covered": "fail"}})

    def test_unknown_source(self):
        self.assertRejected("unknown source 'camera'", by_source={"camera": {"covered": "fail"}})

    def test_unknown_region(self):
        self.assertRejected("unknown region 'left_zone'", by_region={"left_zone": {"covered": "fail"}})

    def test_unknown_status(self):
        self.assertRejected("expected a mapping of", by_modality={"audio": {"partly": "fail"}})

    def test_bad_outcome(self):
        self.assertRejected("must be one of", by_modality={"audio": {"covered": "pass"}})

    def test_event_in_two_regions(self):
        self.assertRejected("already in region", regions={"a": ["apical_paddle_placed"],
                                                          "b": ["apical_paddle_placed"]})

    def test_empty_region(self):
        self.assertRejected("nonempty list", regions={"apical_zone": []})

    def test_region_event_must_be_a_video_event_in_the_vocabulary(self):
        for events in (["apical_paddle_placd"], ["stand_clear_command"]):
            with self.subTest(events=events), tempfile.TemporaryDirectory() as directory:
                data = copy.deepcopy(ENGINE)
                data["coverage_policy"]["regions"] = {"apical_zone": events}
                path = Path(directory) / "engine.yaml"
                path.write_text(yaml.safe_dump(data), encoding="utf-8")
                with self.assertRaisesRegex(ConfigError, "not a canonical video event"):
                    RuleEngineConfig.from_dict({**RULES, "engine": str(path)})


if __name__ == "__main__":
    unittest.main()
