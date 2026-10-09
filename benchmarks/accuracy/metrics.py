"""Full-canvas, origin-aligned binary ink comparison."""

import numpy as np

DIFFERENCE_PALETTE = [255, 255, 255, 0, 0, 0, 220, 0, 150, 0, 160, 220]


def compare(reference, actual, *, indexed=False):
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
    diff = np.zeros((h, w), dtype=np.uint8)
    diff[ref & out] = 1
    diff[ref & ~out] = 2
    diff[out & ~ref] = 3
    if not indexed:
        diff = np.asarray(DIFFERENCE_PALETTE, dtype=np.uint8).reshape(4, 3)[diff]
    return metrics, diff
