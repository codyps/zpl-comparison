"""Full-canvas, origin-aligned binary ink comparison."""

import numpy as np


def compare(reference, actual):
    h = max(reference.shape[0], actual.shape[0])
    w = max(reference.shape[1], actual.shape[1])
    if h * w > 16_000_000:
        raise ValueError("Comparison canvas limit exceeded")
    ref = np.zeros((h, w), dtype=bool)
    out = ref.copy()
    ref[: reference.shape[0], : reference.shape[1]] = reference < 128
    out[: actual.shape[0], : actual.shape[1]] = actual < 128
    both = int(np.count_nonzero(ref & out))
    missing = int(np.count_nonzero(ref & ~out))
    extra = int(np.count_nonzero(out & ~ref))
    union = both + missing + extra
    metrics = dict(
        reference_ink=both + missing,
        output_ink=both + extra,
        missing=missing,
        extra=extra,
        iou=both / union if union else 1.0,
        precision=both / (both + extra) if both + extra else 0.0,
        recall=both / (both + missing) if both + missing else 0.0,
        canvas_disagreement=(missing + extra) / (h * w),
        dimensions_match=reference.shape == actual.shape,
        ink_exact=missing + extra == 0,
        exact=missing + extra == 0 and reference.shape == actual.shape,
        output_dimensions=[actual.shape[1], actual.shape[0]],
    )
    diff = np.full((h, w, 3), 255, dtype=np.uint8)
    diff[ref & out] = [0, 0, 0]
    diff[ref & ~out] = [220, 0, 150]
    diff[out & ~ref] = [0, 160, 220]
    return metrics, diff
