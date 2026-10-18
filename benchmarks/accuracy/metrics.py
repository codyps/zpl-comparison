"""Full-canvas, origin-aligned binary ink comparison."""

import numpy as np

DIFFERENCE_PALETTE = [255, 255, 255, 0, 0, 0, 220, 0, 150, 0, 160, 220]


def compare(reference, actual, *, indexed=False, exclude=None):
    h = max(reference.shape[0], actual.shape[0])
    w = max(reference.shape[1], actual.shape[1])
    if h * w > 16_000_000:
        raise ValueError("Comparison canvas limit exceeded")
    ref = np.zeros((h, w), dtype=bool)
    out = ref.copy()
    ref[: reference.shape[0], : reference.shape[1]] = reference < 128
    out[: actual.shape[0], : actual.shape[1]] = actual < 128
    excluded_pixels = 0
    if exclude is not None:
        if exclude.shape != actual.shape or exclude.dtype != bool:
            raise ValueError("Exclusion mask must match the actual raster")
        ref_region = ref[: actual.shape[0], : actual.shape[1]]
        ref_region[exclude] = False
        out_region = out[: actual.shape[0], : actual.shape[1]]
        out_region[exclude] = False
        excluded_pixels = int(np.count_nonzero(exclude))
    compared_pixels = h * w - excluded_pixels
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
        canvas_disagreement=(missing + extra) / compared_pixels if compared_pixels else 0.0,
        dimensions_match=reference.shape == actual.shape,
        ink_exact=missing + extra == 0 and not excluded_pixels,
        exact=missing + extra == 0 and reference.shape == actual.shape and not excluded_pixels,
        output_dimensions=[actual.shape[1], actual.shape[0]],
    )
    diff = np.zeros((h, w), dtype=np.uint8)
    diff[ref & out] = 1
    diff[ref & ~out] = 2
    diff[out & ~ref] = 3
    if not indexed:
        diff = np.asarray(DIFFERENCE_PALETTE, dtype=np.uint8).reshape(4, 3)[diff]
    return metrics, diff


def compare_trial(reference, actual, color, *, indexed=False):
    """Ignore chromatic stamp pixels on monochrome ZPL, never infer hidden ink.

    Grayscale antialiasing and black errors remain scored. Grayscale-only saved
    images and achromatic stamps cannot be isolated by this method.
    """
    if color.shape != (*actual.shape, 3):
        raise ValueError("Color evidence must match the actual raster")
    mask = color.max(axis=2) != color.min(axis=2)
    raw, diff = compare(reference, actual, indexed=indexed)
    excluded = int(np.count_nonzero(mask))
    if not excluded:
        return raw, diff
    metrics, diff = compare(reference, actual, indexed=indexed, exclude=mask)
    metrics.update(
        raw_comparison=raw,
        raw_score=raw["iou"] if raw["reference_ink"] else None,
        watermark_filter=dict(
            method="neodynamic-chromatic-pixels-v1",
            status="applied",
            excluded_pixels=excluded,
            excluded_reference_ink=raw["reference_ink"] - metrics["reference_ink"],
            retained_reference_fraction=metrics["reference_ink"] / raw["reference_ink"] if raw["reference_ink"] else None,
        ),
    )
    return metrics, diff


def compare_render(reference, actual, path, library, *, indexed=False):
    if library == "neodynamic":
        from .pixels import rgb
        return compare_trial(reference, actual, rgb(path), indexed=indexed)
    return compare(reference, actual, indexed=indexed)
