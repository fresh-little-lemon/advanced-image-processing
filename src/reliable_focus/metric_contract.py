"""Explicit metric contract for the 2026-10-18 formal *draft*.

This is a tested local formula implementation, not an official benchmark or a
completed MATLAB/reference validation. It does not relabel historical scores.
"""
import numpy as np
from scipy.signal import convolve2d
from .metrics import normalized_metric_pair

REC709 = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)
SSIM_SPEC = {
    "window": 11, "sigma": 1.5, "K1": 0.01, "K2": 0.03,
    "data_range": 1, "covariance": "population", "boundary": "valid",
    "luma": "Rec.709", "validation": "local_formula_tests_only",
}


def score_rgb(*, reference, output, color_domain, crop_border=0, valid_mask=None):
    """Score explicit normalized RGB, without inferring a color domain.

    The same crop/mask applies to both images. SSIM includes only 11x11 windows
    entirely inside the valid support. Empty SSIM support is an error, not NaN.
    Exact-match PSNR is JSON-safe null plus an explicit positive_infinity status.
    """
    if color_domain not in {"linear_rgb", "srgb_encoded_rgb"}:
        raise ValueError("Declare linear_rgb or srgb_encoded_rgb explicitly")
    a, b = normalized_metric_pair(reference, output)
    if a.ndim != 3:
        raise ValueError("score_rgb requires HxWx3 RGB")
    if type(crop_border) is not int or crop_border < 0:
        raise ValueError("crop_border must be a nonnegative integer")
    h, w = a.shape[:2]
    if min(h, w) - 2 * crop_border < 11:
        raise ValueError("Require at least 11x11 after the common crop")
    if valid_mask is None:
        mask = np.ones((h, w), dtype=bool)
    else:
        mask = np.asarray(valid_mask)
        if mask.shape != (h, w) or mask.dtype != np.bool_:
            raise ValueError("valid_mask must be boolean HxW with exact dimensions")
    if crop_border:
        s = (slice(crop_border, -crop_border),) * 2
        a, b, mask = a[s], b[s], mask[s]
    if not mask.any():
        raise ValueError("No valid metric pixels")
    mse = float(np.mean((a[mask] - b[mask]) ** 2))
    y1, y2 = a @ REC709, b @ REC709
    axis = np.arange(-5, 6, dtype=np.float64)
    g = np.exp(-(axis * axis) / (2 * 1.5 ** 2))
    g /= g.sum()
    kernel = np.outer(g, g)
    mean = lambda x: convolve2d(x, kernel, mode="valid")
    u1, u2 = mean(y1), mean(y2)
    v1, v2 = mean(y1*y1)-u1*u1, mean(y2*y2)-u2*u2
    cov = mean(y1*y2)-u1*u2
    c1, c2 = 0.01**2, 0.03**2
    ss = ((2*u1*u2+c1)*(2*cov+c2))/((u1*u1+u2*u2+c1)*(v1+v2+c2))
    centers = convolve2d(mask.astype(np.int16), np.ones((11,11), np.int16), mode="valid") == 121
    if not centers.any():
        raise ValueError("No fully valid 11x11 SSIM windows")
    return {
        "color_domain": color_domain, "data_range": 1, "crop_border": crop_border,
        "psnr_rgb": None if mse == 0 else float(-10*np.log10(mse)),
        "psnr_status": "positive_infinity" if mse == 0 else "finite",
        "mae_rgb": float(np.mean(np.abs(a[mask]-b[mask]))),
        "ssim_y_rec709_local": float(ss[centers].mean()),
        "ssim_spec": dict(SSIM_SPEC), "valid_pixels": int(mask.sum()),
        "ssim_valid_centers": int(centers.sum()),
    }
