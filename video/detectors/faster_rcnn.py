from video.detectors.base import Detector


class FasterRCNNDetector(Detector):
    def __init__(self, **kwargs):
        raise NotImplementedError("Faster R-CNN needs a project-trained checkpoint and class mapping; adapter pending")

    def detect(self, video):
        raise NotImplementedError
