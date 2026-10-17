#!/usr/bin/env python3
"""Repeat native core and end-to-end benchmarks. Linux required for RSS units.
Usage: python cpp/tests/benchmark.py imageA imageB output.json [--build-dir build/cpp]
"""
import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('image_a', type=Path)
p.add_argument('image_b', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--build-dir', type=Path, default=Path('build/cpp'))
args = p.parse_args()
if platform.system() != 'Linux':
    p.error('This benchmark driver requires Linux wait4 RSS units')
results = []
with tempfile.TemporaryDirectory(prefix='fusion-benchmark-') as temp:
    for method in ('average', 'laplacian', 'sml', 'guided'):
        r = json.loads(subprocess.check_output([
            str(args.build_dir/'fusion_benchmark'), str(args.image_a),
            str(args.image_b), method], text=True))
        r['method'] = method
        r['core_median_ms'] = statistics.median(r['core_ms'])
        r['core_min_ms'], r['core_max_ms'] = min(r['core_ms']), max(r['core_ms'])
        cmd = [str(args.build_dir/'multifocus_cli'), str(args.image_a),
               str(args.image_b), str(Path(temp)/'output.png'), method]
        for _ in range(3):
            subprocess.run(cmd, check=True)
        times, rss = [], []
        for _ in range(10):
            start = time.perf_counter()
            proc = subprocess.Popen(cmd)
            _, status, usage = os.wait4(proc.pid, 0)
            proc.returncode = os.waitstatus_to_exitcode(status)
            if proc.returncode:
                raise RuntimeError(f'CLI failed: {proc.returncode}')
            times.append((time.perf_counter()-start)*1000)
            rss.append(usage.ru_maxrss)
        r.update(cli_end_to_end_ms=times, cli_median_ms=statistics.median(times),
                 cli_peak_rss_kib=max(rss))
        results.append(r)
        print(method, 'core median ms:', r['core_median_ms'],
              'CLI median ms:', r['cli_median_ms'], flush=True)
out = {
    'date_utc': time.strftime('%Y-%m-%d', time.gmtime()),
    'architecture': platform.machine(), 'platform': platform.platform(),
    'compiler': subprocess.check_output(['g++', '--version'], text=True).splitlines()[0],
    'flags': '-std=c++17 -O2 -Wall -Wextra -Wpedantic',
    'input_pair': f'{args.image_a.name} / {args.image_b.name}',
    'input_resolution_note': 'Native dimensions, no resize', 'threads': 1,
    'core_timing_scope': 'fuse only, including input validation and allocations, excluding decode/conversion/output encoding; 3 warmups and 10 repeats in same process',
    'cli_timing_scope': 'Fresh process startup + decode + RGB conversion + fuse + PNG encoding/write; 3 warmups and 10 timed child processes',
    'memory_scope': 'Actual Linux ru_maxrss in KiB, process-wide peak including libraries and decoded images; not incremental algorithm allocations',
    'caveat': 'Shared cloud CPU with warm caches; no concurrent project experiment jobs during recorded pass; not ARM64 evidence or target-device performance guarantee',
    'methods': results,
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(out, indent=2)+'\n')
