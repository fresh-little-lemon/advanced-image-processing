#!/usr/bin/env python3
"""Recompute published phase-2 code in a fresh output directory; never use holdouts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[1]


def rebuild(output, data_root=None):
    output = Path(output).resolve()
    if output == REPO or REPO in output.parents:
        raise ValueError('Choose an output directory outside the source repository')
    # Exclusive creation deliberately prevents accidental replacement of old evidence.
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONPATH=str(REPO / 'src'), OMP_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    manifest = REPO / 'data/manifests/validation_v1.json'
    provenance = {
        'status': 'running', 'kind': 'new recomputation, not recovered historical output',
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'source_sha256': {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(REPO.rglob('*.py'))
                          if '.venv' not in p.parts and '.git' not in p.parts},
        'validation_manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'real_validation_requested': data_root is not None,
        'holdouts': 'never evaluated', 'commands': [],
    }
    record = output / 'rebuild.json'

    def run(script, *args):
        command = [sys.executable, str(REPO / 'scripts' / script), *map(str, args)]
        provenance['commands'].append(command)
        record.write_text(json.dumps(provenance, indent=2) + '\n')
        subprocess.run(command, cwd=output, env=env, check=True)

    try:
        run('run_phase2_diagnostics.py', '--output', output / 'results/phase2_procedural')
        run('run_phase2_diagnostics.py', '--zero-limit-only', '--output', output / 'results/phase2_zero_limit')
        run('summarize_phase2.py')
        if data_root is not None:
            data_root = Path(data_root).resolve()
            for name, extra in [('phase2_validation', []), ('phase2_validation_zero_limit', ['--zero-limit-only'])]:
                run('evaluate_phase2_validation.py', '--manifest', manifest, '--data-root', data_root,
                    '--output', output / 'results' / name, *extra)
            run('make_phase2_demos.py', '--manifest', manifest, '--data-root', data_root,
                '--output', output / 'deliverables')
        provenance['status'] = 'complete'
    except BaseException:
        provenance['status'] = 'failed; partial output preserved'
        raise
    finally:
        record.write_text(json.dumps(provenance, indent=2) + '\n')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='Fresh, nonexisting directory outside the repo')
    parser.add_argument('--data-root', type=Path, help='Optional existing hash-verifiable WHU data; only frozen 26-scene validation is evaluated')
    args = parser.parse_args()
    rebuild(args.output, args.data_root)


if __name__ == '__main__':
    main()
