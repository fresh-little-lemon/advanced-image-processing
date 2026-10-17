"""Independent GFF two-layer reference, derived from Li/Kang/Hu TIP 2013.

The author_aligned profile follows inspected MATLAB operations, including
quantization, first-maximum ties and mixed boundary conventions. Numerical
parity with an executed author MATLAB reference remains unmeasured.
External source code is not imported or executed.
"""
from dataclasses import dataclass, asdict
import numpy as np
from scipy.ndimage import uniform_filter, convolve, convolve1d

LUMA = np.array([0.298936021293775, 0.587043074451121, 0.114020904255103])
LAPLACIAN = np.array([[0., 1., 0.], [1., -4., 1.], [0., 1., 0.]])

@dataclass(frozen=True)
class GFFConfig:
    profile: str = 'author_aligned'
    base_size: int = 31
    saliency_radius: int = 5
    saliency_sigma: float = 5.0
    base_radius: int = 45
    base_epsilon: float = 0.3
    detail_radius: int = 7
    detail_epsilon: float = 1e-6
    normalization_epsilon: float = 1e-12

    def __post_init__(self):
        if self.profile not in ('author_aligned', 'continuous_shared_gray'):
            raise ValueError('Unknown profile')
        if self.base_size < 1 or self.base_size % 2 != 1:
            raise ValueError('base_size must be positive odd')
        if min(self.saliency_radius, self.base_radius, self.detail_radius) < 0:
            raise ValueError('radii must be nonnegative')
        if min(self.saliency_sigma, self.base_epsilon, self.detail_epsilon,
               self.normalization_epsilon) <= 0:
            raise ValueError('scales and regularizers must be positive')


def quantize_u8_unit(x):
    """Saturate and round nonnegative unit data; ties round upward."""
    return np.floor(np.clip(x, 0., 1.) * 255. + .5) / 255.


def truncated_mean(x, radius):
    """Mean of in-image square support, independently for each trailing plane."""
    size = (2 * radius + 1,) * 2 + (1,) * (x.ndim - 2)
    numerator = uniform_filter(x, size=size, mode='constant', cval=0.)
    count = uniform_filter(np.ones(x.shape[:2]), size=2*radius+1,
                           mode='constant', cval=0.)
    return numerator / count[(...,) + (None,) * (x.ndim - 2)]


def guided_scalar(guide, mask, radius, epsilon):
    """Scalar guided filter; no clipping/quantization inside the regression."""
    mi, mp = truncated_mean(guide, radius), truncated_mean(mask, radius)
    covariance = truncated_mean(guide * mask, radius) - mi * mp
    variance = truncated_mean(guide * guide, radius) - mi * mi
    a = covariance / (variance + epsilon)
    b = mp - a * mi
    return truncated_mean(a, radius) * guide + truncated_mean(b, radius)


def _validate(images):
    if len(images) < 2:
        raise ValueError('At least two images required')
    shape = np.asarray(images[0]).shape
    if len(shape) not in (2, 3) or (len(shape) == 3 and shape[2] != 3):
        raise ValueError('Use grayscale HxW or RGB HxWx3')
    if min(shape[:2]) < 2:
        raise ValueError('Image dimensions must be >=2')
    out = []
    for image in images:
        x = np.asarray(image)
        if x.shape != shape or not np.issubdtype(x.dtype, np.floating):
            raise ValueError('Equal-shaped floating-point inputs required')
        if not np.isfinite(x).all() or x.min() < 0 or x.max() > 1:
            raise ValueError('Inputs must be finite and normalized to [0,1]')
        out.append(x.astype(np.float64, copy=False))
    return out


def fuse_gff(images, config=None, return_diagnostics=False):
    """Fuse registered gray/RGB sequence; return normalized encoded intensity.

    author_aligned: uint8-equivalent input/gray/weight/output quantization,
    first argmax ties. continuous_shared_gray: full precision, all-maxima
    ties, clipped continuous weights, same scalar-gray guidance.
    """
    c = config or GFFConfig()
    images = _validate(images)
    author = c.profile == 'author_aligned'
    if author:
        images = [quantize_u8_unit(x) for x in images]
    grays = [x @ LUMA if x.ndim == 3 else x for x in images]
    if author:
        grays = [quantize_u8_unit(x) for x in grays]
    axis = np.arange(-c.saliency_radius, c.saliency_radius+1, dtype=float)
    gaussian = np.exp(-axis**2 / (2*c.saliency_sigma**2))
    gaussian /= gaussian.sum()
    saliencies = []
    for gray in grays:
        response = abs(convolve(gray, LAPLACIAN, mode='nearest'))
        saliencies.append(convolve1d(convolve1d(response, gaussian, 0,
                           mode='nearest'), gaussian, 1, mode='nearest'))
    saliency = np.stack(saliencies) + c.normalization_epsilon
    saliency /= saliency.sum(axis=0, keepdims=True)
    if author:
        labels = np.argmax(saliency, axis=0)
        initial = np.stack([labels == i for i in range(len(images))]).astype(float)
    else:
        initial = (saliency == saliency.max(axis=0)).astype(float)
    weights = []
    for radius, epsilon in ((c.base_radius, c.base_epsilon),
                            (c.detail_radius, c.detail_epsilon)):
        raw = np.stack([guided_scalar(g, p, radius, epsilon)
                        for g, p in zip(grays, initial)])
        w = quantize_u8_unit(raw) if author else np.clip(raw, 0., 1.)
        w += c.normalization_epsilon
        w /= w.sum(axis=0, keepdims=True)
        weights.append(w)
    fused = np.zeros_like(images[0])
    for i, x in enumerate(images):
        size = (c.base_size, c.base_size) + (1,) * (x.ndim - 2)
        base = uniform_filter(x, size=size, mode='nearest')
        wb, wd = weights[0][i], weights[1][i]
        if x.ndim == 3:
            wb, wd = wb[..., None], wd[..., None]
        fused += wb * base + wd * (x - base)
    raw_range = (float(fused.min()), float(fused.max()))
    clipped_fraction = float(np.mean((fused < 0.) | (fused > 1.)))
    result = quantize_u8_unit(fused) if author else np.clip(fused, 0., 1.)
    if return_diagnostics:
        return result, dict(config=asdict(c), base_weights=weights[0],
                            detail_weights=weights[1], raw_range=raw_range,
                            raw_clipped_fraction=clipped_fraction,
                            initial_weights=initial)
    return result
