from video.detectors.yolo import YOLODetector


class RTDETRDetector(YOLODetector):
    """Same event interface, using an Ultralytics RT-DETR checkpoint."""
    backend = "RTDETR"
