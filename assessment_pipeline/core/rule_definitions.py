"""
rule_definitions.py

Central repository of assessment rule definitions.

NOTE:
Clinical timing thresholds, accepted phrase variants and safety-critical
conditions are placeholders until approved by the supervising professor.
"""

AUDIO_RULES = [
    {
        "criterion_id": "A1",
        "event_name": "oxygen_away",
        "display_name": "Free Flow Oxygen Away",
        "required": True,
        "order": 1,
        "timing": None,
        "critical": False,
        "description": "Student gives the verbal command 'Free Flow Oxygen Away'."
    },
    {
        "criterion_id": "A2",
        "event_name": "continue_chest_compressions",
        "display_name": "Continue Chest Compressions",
        "required": True,
        "order": 2,
        "timing": None,
        "critical": False,
        "description": "Student instructs to continue chest compressions."
    },
    {
        "criterion_id": "A3",
        "event_name": "all_stand_clear",
        "display_name": "All Stand Clear",
        "required": True,
        "order": 3,
        "timing": None,
        "critical": True,   # Placeholder until supervisor confirmation
        "description": "Student instructs everyone to stand clear."
    },
    {
        "criterion_id": "A4",
        "event_name": "stop_chest_compressions",
        "display_name": "Stop Chest Compressions",
        "required": True,
        "order": 4,
        "timing": None,
        "critical": False,
        "description": "Student instructs to stop chest compressions."
    },
    {
        "criterion_id": "A5",
        "event_name": "start_chest_compressions",
        "display_name": "Start Chest Compressions",
        "required": True,
        "order": 5,
        "timing": None,
        "critical": False,
        "description": "Student instructs to resume chest compressions."
    },
]


VIDEO_RULES = [
    {
        "criterion_id": "R1",
        "event_name": "first_paddle_taken",
        "display_name": "Take One Paddle at a Time",
        "required": True,
        "order": 1,
        "timing": None,
        "critical": False,
        "description": "Student picks up the first paddle."
    },
    {
        "criterion_id": "R2",
        "event_name": "paddles_firmly_on_chest",
        "display_name": "Place Paddles Firmly on Chest",
        "required": True,
        "order": 2,
        "timing": None,
        "critical": False,
        "description": "Student places both paddles firmly on the chest."
    },
    {
        "criterion_id": "R3",
        "event_name": "shock_delivered",
        "display_name": "Deliver Shock",
        "required": True,
        "order": 3,
        "timing": None,
        "critical": True,   # Placeholder
        "description": "Shock is delivered."
    },
    {
        "criterion_id": "R4",
        "event_name": "remove_paddles",
        "display_name": "Remove Paddles",
        "required": True,
        "order": 4,
        "timing": None,
        "critical": False,
        "description": "Student removes the paddles after shock."
    },
]