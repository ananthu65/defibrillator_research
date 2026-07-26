"""
rule_definitions.py

Defines every assessment rule used by the Rule Engine.

Version 1:
- Presence
- Order
- Dependencies

Future versions will extend this with timing,
confidence and inference rules.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Rule:
    """
    Definition of one assessment criterion.
    """

    criterion_id: str

    event_name: str

    must_follow: str | None = None

    depends_on: list[str] = field(default_factory=list)


RULES = [

    #
    # -------------------------
    # Visual Rules
    # -------------------------
    #

    Rule(
        criterion_id="R1",
        event_name="gel_applied",
    ),

    Rule(
        criterion_id="R2",
        event_name="take_second_paddle",
        must_follow="take_first_paddle",
        depends_on=[
            "take_first_paddle",
        ],
    ),

    Rule(
        criterion_id="R3",
        event_name="place_paddles",
        depends_on=[
            "take_first_paddle",
            "take_second_paddle",
        ],
    ),

    Rule(
        criterion_id="R4",
        event_name="shock_button_pressed",
        depends_on=[
            "place_paddles",
        ],
    ),

    Rule(
        criterion_id="R5",
        event_name="shock_delivered",
        must_follow="shock_button_pressed",
        depends_on=[
            "shock_button_pressed",
        ],
    ),

    Rule(
        criterion_id="R6",
        event_name="remove_paddles",
        must_follow="shock_delivered",
        depends_on=[
            "shock_delivered",
        ],
    ),

    #
    # -------------------------
    # Audio Rule
    # -------------------------
    #

    Rule(
        criterion_id="R7",
        event_name="start_chest_compressions",
        must_follow="shock_delivered",
        depends_on=[
            "shock_delivered",
        ],
    ),

]