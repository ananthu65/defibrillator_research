from audio_rules import evaluate_audio_rules
from video_rules import evaluate_video_rules


def evaluate_rules(events):

    audio = evaluate_audio_rules(events)

    video = evaluate_video_rules(events)

    return audio + video