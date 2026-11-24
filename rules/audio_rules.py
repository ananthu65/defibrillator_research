"""Audio rules (Increment 21 onward). Each rule is one small function built from the shared checks.

The input is Sanjeevan's command events (Whisper -> detect_commands, the shared Event schema, D-125);
nothing here imports audio/. A command event carries its Whisper segment, so it is compared as an
interval (checks.relation_between, D-125). A missing command can Fail only inside stated clear-audio
intervals (the audio region, D-122). Registered rules run only when approved in configs/rules.yaml.
"""
from rules import checks
from rules.coverage import LOW_CONFIDENCE_FLAG
from rules.outcome import failed, passed, unable
from rules.registry import rule

SHOCK = "shock_delivered_on_screen"
OXYGEN_AWAY, STAND_CLEAR = "oxygen_away_command", "stand_clear_command"
FLAGS = ()   # rule-result flags raised here (the shared ones are in checks.FLAGS)


# ---- A1, A3: a command given before the shock -------------------------------------------------------

@rule("A1", requires=(OXYGEN_AWAY, SHOCK), description="Free-flow oxygen away before the shock")
def oxygen_away(ctx, definition, results):
    """A1 (P-040): "oxygen away" said before the shock on the screen. See _before_shock."""
    return _before_shock(ctx, "A1", OXYGEN_AWAY, "oxygen away", "oxygen_away_before_shock_seconds")


@rule("A3", requires=(STAND_CLEAR, SHOCK), description="All stand clear before the shock")
def stand_clear(ctx, definition, results):
    """A3 (P-040): "all stand clear" said before the shock on the screen. See _before_shock."""
    return _before_shock(ctx, "A3", STAND_CLEAR, "stand clear", "stand_clear_before_shock_seconds")


def _before_shock(ctx, rule_id, event_name, what, limit_name):
    """A1 and A3 (P-040; D-121, D-122, D-123, D-125). The rule owns the relation "command before the shock".

    With a shock time (the screen only, D-093):
    1. A command not certainly after the shock (before it, or within the cross-modal tolerance or its
       segment's overlap: a tie never breaks an order) -> Pass. Any one occurrence in the right place
       counts. The time limit before the shock is unset (timing_not_checked); an approved "no limit"
       passes fully (D-103).
    2. Commands only certainly after the shock -> Fail `after_shock`.
    3. No command -> Fail `missing` only if the audio was clear throughout from the start to the shock
       (stated clear-audio intervals, D-122); otherwise Unable to Verify. Low confidence is never a Fail.
    Without a shock time (D-121):
    4. A command seen -> Not evaluable because of R5, naming it.
    5. No command while the audio was clear throughout the recording -> Fail `missing`, on the rule's
       own evidence; otherwise Not evaluable because of R5.
    """
    commands = ctx.named(event_name)
    shock = ctx.shock
    if not shock.present:
        return _without_shock(ctx, rule_id, event_name, what, commands, shock)
    screen = next(e for e in ctx.events if e.event_id == shock.event_id)
    valid = [c for c in commands if checks.relation_between(ctx, c, screen) != checks.AFTER]
    if valid:
        return _given(ctx, rule_id, valid[0], screen, shock, what, limit_name)
    if commands:
        late = commands[0]
        return failed(rule_id, "after_shock", f"{what} said only at {late.start:g} s, after the shock on the screen at "
                      f"{shock.time:g} s", evidence=(late.event_id, shock.event_id), uses=(shock,),
                      timestamps={event_name: late.start, SHOCK: shock.time})
    found = ctx.missing(event_name, (0.0, shock.time))
    where = f"before the shock ({shock.time:g} s)"
    if found.outcome == "fail":
        return failed(rule_id, "missing", f"{what} not said {where}, although the audio was clear throughout (D-122)",
                      evidence=(shock.event_id,), uses=(shock, found))
    reason = ("a command may have been heard with low confidence" if LOW_CONFIDENCE_FLAG in found.flags else
              f"the audio was not clear throughout ({found.coverage.status}: {found.coverage.basis})")
    return unable(rule_id, f"{what} not heard {where}, but {reason}", evidence=found.low_confidence_event_ids,
                  uses=(shock, found))


def _given(ctx, rule_id, command, screen, shock, what, limit_name):
    limit = ctx.config.limit(limit_name)
    if limit.value is not None and limit.approved:
        # the brief defines no failure code for it: refused loudly as engine_error (D-063), never guessed
        raise ValueError(f"{rule_id}: an approved time limit before the shock ({limit_name}) is not implemented; "
                         "only an approved 'no limit' is (D-103)")
    check = checks.time_limit(None, limit)
    when = ("before" if checks.relation_between(ctx, command, screen) == checks.BEFORE
            else "at (within the tolerance of)")
    return passed(rule_id, f"{what} said at {command.start:g} s, {when} the shock on the screen at {shock.time:g} s: "
                  f"{check.note}", (command.event_id, shock.event_id), uses=(shock, check),
                  timestamps={command.event_name: command.start, SHOCK: shock.time}, timing_checked=check.checked)


def _without_shock(ctx, rule_id, event_name, what, commands, shock):
    """D-121: "before the shock" can't be judged without a shock time; whether the command was said still is."""
    if commands:
        command = commands[0]
        return checks.partly_evaluable(rule_id, shock, "R5", f"{what} said at {command.start:g} s; whether before the "
                                       "shock can't be judged", evidence=(command.event_id,),
                                       timestamps={event_name: command.start})
    found = ctx.missing(event_name)
    if found.outcome == "fail":
        return failed(rule_id, "missing", f"{what} not said in the recording, although the audio was clear throughout "
                      "(D-122); no shock time is needed to judge this (D-121)", uses=(found,))
    return checks.partly_evaluable(rule_id, shock, "R5", f"{what} not heard, and the audio was not clear throughout "
                                   f"({found.coverage.status}), so whether it was said is unknown too", uses=(found,))
