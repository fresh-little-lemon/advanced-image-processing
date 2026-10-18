"""Experimental residual-floor estimation; no reference or learned model is used.

Each source selects its own low-residual blocks. The method assumes that a
nontrivial part of each source has weak detail at the finest spatial scale.
The lower-tail selection is deliberately uncalibrated: its downward selection
bias is measured separately, rather than hidden by an image-tuned constant.
"""
import numpy as np
from scipy.ndimage import gaussian_filter
from .core import gray, validate
from .diagnostic import valid_support, energy_fuse, DiagnosticConfig


def mad_variance(values):
    values = np.asarray(values, dtype=float).ravel()
    return float((np.median(np.abs(values - np.median(values))) /
                  (2 * .6744897501960817)) ** 2)


def estimate_floor(a, b, ranking='residual', shared=False):
    """Return luma noise-floor estimates and auditable selected support.

    Fixed 8x8 diagonal high-pass blocks; retain lowest 20%, at least two.
    Support is identical to the earlier support probe; only ranking and
    whether the selected blocks are shared change. Missing support gives zero.
    """
    if ranking not in ('residual', 'guide'):
        raise ValueError('ranking must be residual or guide')
    a, b = validate(a), validate(b)
    if a.shape != b.shape or a.ndim != 3 or a.shape[-1] != 3 or min(a.shape[:2]) < 12:
        raise ValueError('require matching RGB arrays with spatial size at least 12')
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise ValueError('inputs must be finite')
    ys = [gray(a), gray(b)]
    valid = valid_support(a, b)
    h, w = valid.shape
    positions = [(i, j) for i in range(2, h - 9, 8) for j in range(2, w - 9, 8)
                 if valid[i:i+8, j:j+8].all()]
    k = max(1, int(np.ceil(.2 * len(positions))))
    info = {'eligible_blocks': len(positions), 'selected_blocks_per_source': k if positions else 0,
            'valid_pixel_fraction': float(valid.mean()), 'available': k >= 2 and bool(positions),
            'ranking': ranking, 'shared': shared, 'selected_quadrants': [], 'sigmas': [0., 0.]}
    if not info['available']:
        return (0., 0.), info
    blocks, scores, guide_energies = [], [], []
    for y in ys:
        hp = y[1:, 1:] - y[:-1, 1:] - y[1:, :-1] + y[:-1, :-1]
        values = np.stack([hp[i:i+8, j:j+8].ravel() for i, j in positions])
        blocks.append(values)
        if ranking == 'residual':
            medians = np.median(values, axis=1)
            scores.append(np.median(np.abs(values - medians[:, None]), axis=1))
        else:
            gy, gx = np.gradient(gaussian_filter(y, 1., mode='reflect'))
            energy = gx*gx + gy*gy
            guide_energies.append(energy)
            scores.append(np.array([energy[i:i+8, j:j+8].mean() for i,j in positions]))
    if shared:
        if ranking == 'guide':
            energy = np.maximum(*guide_energies)
            common = np.array([energy[i:i+8, j:j+8].mean() for i,j in positions])
        else:
            common = np.maximum(*scores)
        scores = [common] * 2
    selected = [np.argsort(score, kind='stable')[:k] for score in scores]
    sigmas = tuple(float(np.sqrt(mad_variance(values[ids]))) for values, ids in zip(blocks, selected))
    for ids in selected:
        counts = [0] * 4
        for index in ids:
            i, j = positions[index]
            counts[2 * int(i + 4 >= h/2) + int(j + 4 >= w/2)] += 1
        info['selected_quadrants'].append(counts)
    info['sigmas'] = list(sigmas)
    info['selected_overlap_fraction'] = len(set(selected[0]) & set(selected[1])) / k
    return sigmas, info


def fuse_floor(a, b, subtract_mean=True):
    """Factorial candidate using residual-floor mean and variance parameters."""
    sigmas, info = estimate_floor(a, b)
    output = energy_fuse(a, b, DiagnosticConfig(sigma_mode='oracle_known',
                        subtract_mean=subtract_mean), oracle_sigmas=sigmas)[0]
    return output, info
