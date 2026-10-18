#!/usr/bin/env python3
"""Frozen procedural probe of spatial support reliability for noise correction."""
import os
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
import argparse
import csv
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / 'src')]
from baselines_gff import GFFConfig, fuse_gff
from reliable_focus.core import Config, decode_srgb, fuse, gray
from reliable_focus.diagnostic import DiagnosticConfig, LUMA, energy_fuse, valid_support
from reliable_focus.metrics import psnr
from probe_shared_support import candidate
from run_phase2_diagnostics import textures

METHODS = ('guided', 'gff_continuous_shared_gray', 'no_mean', 'shared_delta',
           'bootstrap_shrink', 'count_gate', 'spatial_gate', 'oracle_preclip')


def estimate_support(a, b, bootstrap=False):
    """Paired MAD estimate and fixed spatial support, with optional block bootstrap."""
    ya, yb = gray(a), gray(b)
    valid = valid_support(a, b)
    gradients = []
    for y in (ya, yb):
        gy, gx = np.gradient(gaussian_filter(y, 1, mode='reflect'))
        gradients.append(gx * gx + gy * gy)
    score = np.maximum(*gradients)
    h, w = ya.shape
    eligible = []
    for i in range(2, h - 9, 8):
        for j in range(2, w - 9, 8):
            area = (slice(i, i + 8), slice(j, j + 8))
            if valid[area].all():
                eligible.append((float(score[area].mean()), i, j))
    eligible.sort()
    selected = eligible[:max(1, int(np.ceil(.2 * len(eligible))))]
    quadrants = [0] * 4
    for _, i, j in selected:
        quadrants[2 * int(i + 4 >= h / 2) + int(j + 4 >= w / 2)] += 1
    info = {
        'valid_pixel_fraction': float(valid.mean()),
        'eligible_blocks': len(eligible), 'selected_blocks': len(selected),
        'selected_pixels': len(selected) * 64,
        'selected_pixel_fraction': len(selected) * 64 / (h * w),
        'image_pixels': h * w, 'quadrant_blocks': quadrants,
        'occupied_quadrants': sum(n > 0 for n in quadrants),
        'available': len(selected) >= 2, 'raw_delta': 0., 'alpha': 0.,
    }
    if not info['available']:
        return 0., info
    residuals = [y[1:, 1:] - y[:-1, 1:] - y[1:, :-1] + y[:-1, :-1] for y in (ya, yb)]
    values = [np.stack([hp[i:i + 8, j:j + 8].ravel() for _, i, j in selected])
              for hp in residuals]

    def variance_estimate(blocks):
        x = blocks.ravel()
        return (np.median(abs(x - np.median(x))) / (.6744897501960817 * 2)) ** 2

    delta = float(variance_estimate(values[0]) - variance_estimate(values[1]))
    info['raw_delta'], info['alpha'] = delta, 1.
    if bootstrap:
        rng = np.random.default_rng(7281)
        samples = []
        for _ in range(64):
            ids = rng.integers(0, len(selected), len(selected))
            samples.append(variance_estimate(values[0][ids]) - variance_estimate(values[1][ids]))
        variance = float(np.var(samples, ddof=1))
        info['alpha'] = max(0., 1 - variance / delta ** 2) if delta else 0.
        delta *= info['alpha']
    return delta, info


def accept_support(info, rule):
    if rule == 'count_gate':
        return info['selected_blocks'] >= 8
    if rule == 'spatial_gate':
        return min(info['quadrant_blocks']) >= 2
    return info['available']


def run_method(a, b, method, known_sigmas):
    """End-to-end pipeline; reference image is not an input."""
    if method == 'guided':
        return fuse(a, b, Config(method='guided')), None, None
    if method == 'gff_continuous_shared_gray':
        return fuse_gff([a, b], GFFConfig(profile='continuous_shared_gray')), None, None
    if method == 'oracle_preclip':
        output = energy_fuse(a, b, DiagnosticConfig(sigma_mode='oracle_known'), known_sigmas)[0]
        return output, known_sigmas[0] ** 2 - known_sigmas[1] ** 2, None
    if method == 'no_mean':
        return candidate(a, b, 0.), 0., None
    delta, info = estimate_support(a, b, bootstrap=method == 'bootstrap_shrink')
    accepted = accept_support(info, method)
    if not accepted:
        delta = 0.
    info['accepted'] = accepted
    return candidate(a, b, delta), delta, info


def generate_case(texture, fraction, brightness, noise_a, noise_b, seed):
    gt = texture.copy()
    if brightness == 'dark':
        gt = .01 + .12 * gt
    elif brightness == 'extreme_white':
        gt = .999 - .01 * gt
    elif brightness != 'normal':
        raise ValueError('Unknown brightness state')
    h, w = gt.shape[:2]
    mask = np.indices((h, w))[1] < int(w * fraction)
    blurred = gaussian_filter(gt, (1.5, 1.5, 0), mode='reflect')
    clean_a = np.where(mask[..., None], gt, blurred)
    clean_b = np.where(mask[..., None], blurred, gt)
    rng = np.random.default_rng(seed)
    a = np.clip(clean_a + rng.normal(0, noise_a / 255, gt.shape), 0, 1)
    b = np.clip(clean_b + rng.normal(0, noise_b / 255, gt.shape), 0, 1)
    return a, b, gt


def finite_mean(values):
    values = [float(v) for v in values if v is not None and np.isfinite(v)]
    return float(np.mean(values)) if values else None


def summarize(rows):
    summary = {}
    for brightness in ('normal', 'dark', 'extreme_white'):
        summary[brightness] = {}
        for group in ('clean', 'equal_noise', 'asymmetric'):
            selected = [r for r in rows if r['brightness'] == brightness and
                        ('clean' if r['noise_a_255'] == r['noise_b_255'] == 0 else
                         'equal_noise' if r['noise_a_255'] == r['noise_b_255'] else 'asymmetric') == group]
            summary[brightness][group] = {}
            for method in METHODS:
                data = [r for r in selected if r['method'] == method]
                summary[brightness][group][method] = {
                    'conditions': len(data),
                    **{key: finite_mean(r[key] for r in data) for key in
                       ('psnr_linear_rgb', 'mae_linear_rgb', 'delta_absolute_error',
                        'wrong_sign_when_active', 'abstained', 'gate_rejected',
                        'seconds_pipeline', 'selected_pixel_fraction', 'valid_pixel_fraction')},
                    'median_seconds_pipeline': float(np.median([r['seconds_pipeline'] for r in data])),
                }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Fresh output directory')
    parser.add_argument('--protocol', type=Path, default=REPO / 'results/spatial_support_20261018/protocol_frozen.json')
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text())
    assert protocol['condition_count'] == 144 and protocol['methods'] == list(METHODS)
    assert protocol['sharp_a_fractions'] == [.25, .5, .75]
    assert protocol['noise_rgb_pairs_255'] == [[0, 0], [0, 5], [5, 0], [5, 5]]
    assert protocol['seeds'] == [11, 23]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    tex = textures(96)
    mixed = tex['stochastic'].copy()
    mixed[:, :48] = tex['sine'][:, :48]
    fixtures = {'stochastic': tex['stochastic'], 'mixed_sine_left_stochastic_right': mixed}
    status = {
        'status': 'running', 'protocol_sha256': hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'working_domain': 'Procedurally generated linear RGB; all quality errors use full RGB samples',
        'python': platform.python_version(), 'numpy': np.__version__, 'architecture': platform.machine(),
        'threads': {k: os.environ[k] for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')},
        'timing_note': 'Shared cloud CPU, one call per condition after warmup; includes estimator and fusion; not edge-device timing',
    }
    (out / 'run.json').write_text(json.dumps(status, indent=2))
    wa, wb, _ = generate_case(tex['stochastic'], .5, 'normal', 0, 5, 11)
    for method in METHODS:
        for _ in range(3):
            run_method(wa, wb, method, (0., float(np.linalg.norm(LUMA) * 5 / 255)))
    rows, swaps = [], []
    for texture_name, texture in fixtures.items():
        for fraction in protocol['sharp_a_fractions']:
            for brightness in ('normal', 'dark', 'extreme_white'):
                for na, nb in protocol['noise_rgb_pairs_255']:
                    for seed in protocol['seeds']:
                        a, b, gt = generate_case(texture, fraction, brightness, na, nb, seed)
                        sigmas = tuple(float(np.linalg.norm(LUMA) * n / 255) for n in (na, nb))
                        true_delta = sigmas[0] ** 2 - sigmas[1] ** 2
                        context = {'texture': texture_name, 'sharp_a_fraction': fraction,
                                   'brightness': brightness, 'noise_a_255': na, 'noise_b_255': nb, 'seed': seed}
                        _, support = estimate_support(a, b)
                        saturated = float(np.mean(np.any((a <= 0) | (a >= 1) | (b <= 0) | (b >= 1), axis=-1)))
                        spatial_result = None
                        for method in METHODS:
                            start = time.perf_counter()
                            result, delta, info = run_method(a, b, method, sigmas)
                            seconds = time.perf_counter() - start
                            rows.append({
                                **context, 'method': method, 'true_preclip_delta_sigma2': true_delta,
                                'estimated_delta_sigma2': delta,
                                'delta_absolute_error': abs(delta - true_delta) if delta is not None else None,
                                'wrong_sign_when_active': int(delta * true_delta < 0) if delta and true_delta else None,
                                'abstained': int(delta == 0) if delta is not None else None,
                                'gate_rejected': int(not info['accepted']) if info is not None else None,
                                **{k: support[k] for k in ('valid_pixel_fraction', 'eligible_blocks', 'selected_blocks',
                                                          'selected_pixels', 'selected_pixel_fraction', 'image_pixels', 'occupied_quadrants')},
                                **{f'quadrant_{i}_blocks': n for i, n in enumerate(support['quadrant_blocks'])},
                                'saturated_pixel_fraction': saturated,
                                'psnr_linear_rgb': float(psnr(gt, result)),
                                'mae_linear_rgb': float(np.mean(abs(gt - result))), 'seconds_pipeline': seconds,
                            })
                            if method == 'spatial_gate':
                                spatial_result = (result, delta)
                        swapped, swapped_delta, _ = run_method(b, a, 'spatial_gate', sigmas[::-1])
                        error = float(np.max(abs(swapped - spatial_result[0])))
                        delta_error = abs(swapped_delta + spatial_result[1])
                        assert error < 1e-10 and delta_error < 1e-14
                        swaps.append({**context, 'max_rgb_error': error, 'contrast_antisymmetry_error': delta_error})
            print(texture_name, fraction, 'complete', flush=True)
    assert len(rows) == 1152 and len(swaps) == 144
    for name, data in (('metrics.csv', rows), ('source_swap.csv', swaps)):
        with (out / name).open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=data[0])
            writer.writeheader(); writer.writerows(data)
    (out / 'summary.json').write_text(json.dumps(summarize(rows), indent=2, allow_nan=False))
    status.update(status='complete', metric_rows=len(rows), source_swap_cases=len(swaps),
                  max_swap_rgb_error=max(r['max_rgb_error'] for r in swaps))
    (out / 'run.json').write_text(json.dumps(status, indent=2))
    print(json.dumps(status, indent=2))


if __name__ == '__main__':
    main()
