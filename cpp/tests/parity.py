#!/usr/bin/env python3
"""Compare unquantized C++ output to Python. Build first or pass --build.

PYTHONPATH=src python cpp/tests/parity.py --probe build/cpp/fusion_probe
Requires the project's Python dependencies. Does not silently skip missing builds.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import numpy as np
from reliable_focus.core import Config, fuse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', type=Path, default=Path('build/cpp/fusion_probe'))
    parser.add_argument('--build', action='store_true', help='Configure/build with system OpenCV')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.build:
        build = args.probe.resolve().parent
        subprocess.run(['cmake', '-S', str(root / 'cpp'), '-B', str(build), '-DCMAKE_BUILD_TYPE=Release'], check=True)
        subprocess.run(['cmake', '--build', str(build), '--parallel', '2'], check=True)
    probe = args.probe.resolve()
    if not probe.is_file():
        parser.error(f'C++ probe not built: {probe}; use --build with CMake and OpenCV installed')
    rng = np.random.default_rng(8201)
    cases = []
    for h, w in [(2, 2), (2, 3), (7, 5), (32, 41), (65, 71)]:
        a = rng.random((h, w, 3))
        b = rng.random((h, w, 3))
        cases.extend([(f'random-{h}x{w}', a, b),
                      (f'identical-{h}x{w}', a, a.copy()),
                      (f'constant-tie-{h}x{w}', np.zeros_like(a), np.ones_like(a))])
    count = 0
    for name, a, b in cases:
        payload = f'{a.shape[0]} {a.shape[1]}\n' + '\n'.join(
            format(float(v), '.17g') for v in np.concatenate((a.ravel(), b.ravel())))
        for method in ('average', 'laplacian', 'sml', 'guided'):
            completed = subprocess.run([str(probe), method], input=payload, text=True,
                                       capture_output=True, check=True)
            actual = np.fromstring(completed.stdout, sep=' ').reshape(a.shape)
            expected = fuse(a, b, Config(method=method))
            # FP64 box-filter summation order can differ. Hard masks should agree
            # on these fixtures; this is not an arbitrary-image near-tie guarantee.
            np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-10,
                                       err_msg=f'{name}: {method}')
            count += 1
    print(f'{count} float64 C++/Python parity cases passed')


if __name__ == '__main__':
    main()
