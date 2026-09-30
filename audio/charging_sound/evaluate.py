"""One-to-one event matching using temporal intersection over union."""


def event_metrics(predicted, truth, min_iou=0.1):
    if not 0 < min_iou <= 1:
        raise ValueError("min_iou must be in (0, 1]")
    candidates = []
    for i, event in enumerate(predicted):
        for j, (start, end) in enumerate(truth):
            overlap = max(0, min(event.end, end) - max(event.start, start))
            union = max(event.end, end) - min(event.start, start)
            iou = overlap / union if union else 0
            if iou >= min_iou:
                candidates.append((iou, i, j))
    matched_pred, matched_truth, start_errors = set(), set(), []
    for _, i, j in sorted(candidates, reverse=True):
        if i not in matched_pred and j not in matched_truth:
            matched_pred.add(i)
            matched_truth.add(j)
            start_errors.append(abs(predicted[i].start - truth[j][0]))
    return {"true_positives": len(matched_pred), "false_positives": len(predicted) - len(matched_pred),
            "false_negatives": len(truth) - len(matched_truth), "start_errors_seconds": start_errors}
