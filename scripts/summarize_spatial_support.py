#!/usr/bin/env python3
"""Paired analysis of the fixed spatial-support reliability grid."""
import argparse
import csv
import json
from pathlib import Path
import statistics

KEYS = ('texture', 'sharp_a_fraction', 'brightness', 'noise_a_255', 'noise_b_255', 'seed')


def summarize(path):
    rows = list(csv.DictReader(path.open()))
    indexed = {(tuple(r[k] for k in KEYS), r['method']): r for r in rows}
    conditions = sorted({tuple(r[k] for k in KEYS) for r in rows})
    methods = sorted({r['method'] for r in rows})
    output = {'conditions': len(conditions), 'rows': len(rows), 'by_brightness': {}, 'timing': {}}
    for method in methods:
        seconds = [float(r['seconds_pipeline']) for r in rows if r['method'] == method]
        output['timing'][method] = {'median_ms': 1000 * statistics.median(seconds),
                                    'mean_ms': 1000 * statistics.mean(seconds)}
    comparisons = []
    for brightness in ('normal', 'dark', 'extreme_white'):
        output['by_brightness'][brightness] = {}
        for group in ('clean', 'equal_noise', 'asymmetric'):
            keys = [key for key in conditions if key[2] == brightness and
                    ('clean' if key[3] == key[4] == '0' else
                     'equal_noise' if key[3] == key[4] else 'asymmetric') == group]
            table = {}
            for method in methods:
                rs = [indexed[key, method] for key in keys]
                active = [r for r in rs if r['wrong_sign_when_active'] != '']
                numeric = lambda name: [float(r[name]) for r in rs if r[name] != '']
                table[method] = {
                    'n': len(rs), 'psnr_db': statistics.mean(numeric('psnr_linear_rgb')),
                    'mae': statistics.mean(numeric('mae_linear_rgb')),
                    'delta_mae': statistics.mean(numeric('delta_absolute_error')) if numeric('delta_absolute_error') else None,
                    'wrong_sign_count': sum(int(r['wrong_sign_when_active']) for r in active),
                    'active_asymmetric_count': len(active),
                    'zero_correction_count': sum(int(r['abstained']) for r in rs if r['abstained'] != ''),
                    'gate_rejected_count': sum(int(r['gate_rejected']) for r in rs if r['gate_rejected'] != ''),
                }
                if method in ('count_gate', 'spatial_gate'):
                    differences = [float(indexed[key, method]['psnr_linear_rgb']) -
                                   float(indexed[key, 'shared_delta']['psnr_linear_rgb']) for key in keys]
                    table[method].update(mean_delta_vs_shared=statistics.mean(differences),
                                         losses_vs_shared=sum(d < -1e-10 for d in differences),
                                         gains_vs_shared=sum(d > 1e-10 for d in differences),
                                         min_delta_vs_shared=min(differences))
            output['by_brightness'][brightness][group] = table
    for key in conditions:
        base = indexed[key, 'shared_delta']
        for method in ('count_gate', 'spatial_gate'):
            r = indexed[key, method]
            comparisons.append({**{k: key[i] for i, k in enumerate(KEYS)}, 'method': method,
                                'delta_psnr_vs_shared': float(r['psnr_linear_rgb']) - float(base['psnr_linear_rgb']),
                                'gate_rejected': int(r['gate_rejected']),
                                'eligible_blocks': int(r['eligible_blocks']),
                                'selected_blocks': int(r['selected_blocks']),
                                'selected_pixel_fraction': float(r['selected_pixel_fraction']),
                                'valid_pixel_fraction': float(r['valid_pixel_fraction']),
                                'quadrant_blocks': [int(r[f'quadrant_{i}_blocks']) for i in range(4)]})
    output['largest_losses'] = sorted(comparisons, key=lambda r: r['delta_psnr_vs_shared'])[:8]
    output['largest_gains'] = sorted(comparisons, key=lambda r: -r['delta_psnr_vs_shared'])[:8]
    output['coverage'] = {}
    for brightness in ('normal', 'dark', 'extreme_white'):
        rs = [r for r in rows if r['brightness'] == brightness and r['method'] == 'shared_delta']
        output['coverage'][brightness] = {k: {'minimum': min(float(r[k]) for r in rs),
                                             'median': statistics.median(float(r[k]) for r in rs),
                                             'maximum': max(float(r[k]) for r in rs)}
                                         for k in ('eligible_blocks', 'selected_blocks', 'valid_pixel_fraction',
                                                   'selected_pixel_fraction', 'saturated_pixel_fraction')}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metrics', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New JSON file; refuses replacement')
    args = parser.parse_args()
    data = summarize(args.metrics)
    with args.output.open('x') as handle:
        json.dump(data, handle, indent=2, allow_nan=False)
    print(json.dumps({'conditions': data['conditions'], 'rows': data['rows'], 'timing': data['timing']}, indent=2))


if __name__ == '__main__':
    main()
