"""
constants.py

Shared constants used throughout the assessment pipeline.
This file contains only project-wide constant values.
"""

# ------------------------------------------------------------------
# Overall Assessment Results
# ------------------------------------------------------------------

CORRECTLY_DONE = "CORRECTLY_DONE"
WRONGLY_DONE = "WRONGLY_DONE"


# ------------------------------------------------------------------
# Rule Results
# ------------------------------------------------------------------

PASS = "PASS"
FAIL = "FAIL"


# ------------------------------------------------------------------
# Event Sources
# ------------------------------------------------------------------

AUDIO = "audio"
VIDEO = "video"


# ------------------------------------------------------------------
# Audio Events
# ------------------------------------------------------------------

OXYGEN_AWAY = "oxygen_away"

CONTINUE_CHEST_COMPRESSIONS = "continue_chest_compressions"

ALL_STAND_CLEAR = "all_stand_clear"

STOP_CHEST_COMPRESSIONS = "stop_chest_compressions"

START_CHEST_COMPRESSIONS = "start_chest_compressions"


# ------------------------------------------------------------------
# Video Events
# ------------------------------------------------------------------

TAKE_FIRST_PADDLE = "take_first_paddle"

TAKE_SECOND_PADDLE = "take_second_paddle"

PLACE_PADDLES = "place_paddles"

SHOCK_DELIVERED = "shock_delivered"

REMOVE_PADDLES = "remove_paddles"