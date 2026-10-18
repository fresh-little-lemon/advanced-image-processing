#!/usr/bin/env python3
"""Audit frozen metadata and optional result bundles without opening datasets.

No downloads, training, benchmark execution, or MATLAB/Octave invocation.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO/'src'))
import numpy as np
from reliable_focus.evaluation_contract import (
    digest, validate_manifest_bundle, validate_run_record, SCHEMA_VERSION, PROTOCOL_ID,
)
from reliable_focus.metric_contract import score_rgb


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selftest_bundle(repo):
    """Generated mathematical fixture; values are not method-quality evidence."""
    rng = np.random.Generator(np.random.PCG64(20261018))
    a, b = rng.uniform(.1, .9, (2, 16, 16, 3))
    gt, output = a.copy(), (a+b)/2
    pixel_sha = lambda x: hashlib.sha256(x.astype('<f8').tobytes()).hexdigest()
    scenes = [{"scene_id": "synthetic-schema-fixture", "group_id": "synthetic-schema-group",
        "split": "exploration", "files": [{"role": role, "path": f"synthetic/{role}.f64",
        "sha256": pixel_sha(x), "bytes": x.nbytes, "height": 16, "width": 16,
        "mode": "RGB"} for role, x in (("A",a),("B",b),("GT",gt))]}]
    hashes = {"A":pixel_sha(a), "B":pixel_sha(b)}
    codepaths = ["src/reliable_focus/metrics.py", "src/reliable_focus/metric_contract.py",
                 "src/reliable_focus/evaluation_contract.py", "scripts/check_evaluation_contract.py"]
    code = {"base_commit": "a9a8aec964999cfc2475be786561efa4635a238c",
            "source_sha256": {p:sha(repo/p) for p in codepaths}, "worktree": "local_contract_patch"}
    runtime = {"engine":"python", "version":platform.python_version(),
        "execution_label":"python_execution", "platform":platform.platform(),
        "dependencies":{p:importlib.metadata.version(p) for p in ("numpy","scipy","Pillow")}}
    model = {"kind":"non_learned", "artifact_sha256":None,
             "configs":{"synthetic_average":{"weight_a":.5, "purpose":"schema_selftest_only"}}}
    run = {"schema_version":SCHEMA_VERSION, "protocol_id":PROTOCOL_ID,
        "evidence_level":"synthetic_contract_only", "manifest_sha256":digest(scenes),
        "protocol_sha256":sha(repo/'baselines/gff_author/FORMAL_EVALUATION_PROTOCOL.md'),
        "code":code, "model":model, "runtime":runtime,
        "cases":[{"case_id":"synthetic-0", "scene_id":scenes[0]['scene_id'],
            "group_id":scenes[0]['group_id'], "split":"exploration", "seed":20261018,
            "noise_a_255":0, "noise_b_255":0, "input_order":["A","B"],
            "input_sha256":hashes, "shape":[16,16,3]}],
        "results":[{"case_id":"synthetic-0", "method_id":"synthetic_average", "seed":20261018,
            "input_sha256":dict(hashes), "status":"ok", "output_sha256":pixel_sha(output),
            "output_shape":[16,16,3], "metrics":score_rgb(reference=gt,output=output,color_domain="linear_rgb")}],
        "notes":"Pure synthetic schema fixture. No dataset image, MATLAB execution or quality comparison."}
    for key in ("code","model","runtime"):
        run[key+"_sha256"] = digest(run[key])
    return {"manifest":scenes, "manifest_hash_encoding":"canonical-json", "run":run}


def audit(repo):
    folder = repo/'data/manifests'
    master = json.loads((folder/'manifest_v1.json').read_text())
    splits = {s:json.loads((folder/f'{s}_v1.json').read_text())
              for s in ('validation','test','external_test','exploration')}
    report = {"status":"passed", "scope":"metadata_only_no_dataset_pixels_loaded",
              "manifests":validate_manifest_bundle(master,splits), "manifest_files":[]}
    for line in (folder/'SHA256SUMS').read_text().splitlines():
        expected,name = line.split(maxsplit=1)
        actual=sha(folder/name)
        if actual != expected:
            raise ValueError(f'Manifest file hash mismatch: {name}')
        report['manifest_files'].append({"path":f'data/manifests/{name}',"sha256":actual})
    report['legacy_runs'] = []
    for path in sorted((repo/'results').rglob('run.json')):
        run=json.loads(path.read_text())
        missing=[k for k in ('schema_version','code_sha256','model_sha256','runtime_sha256') if k not in run]
        report['legacy_runs'].append({"path":str(path.relative_to(repo)),"status":run.get('status'),
            "missing_new_contract_fields":missing,"interpretation":"legacy exploratory evidence; not retrospectively certified"})
    report['limitations'] = [
        "Group/hash checks do not certify semantic scene deduplication or historical tuning isolation.",
        "No training split exists in this classical pipeline; validation is the development set.",
        "SSIM is a locally formula-tested diagnostic, not official/reference-library validation.",
        "MATLAB native author-baseline acceptance is still pending; Octave is compatibility only.",
        "This checker does not enable test/external_test algorithm execution."]
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=REPO)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--write-selftest-bundle',type=Path)
    parser.add_argument('--run-bundle',type=Path,
        help='JSON with manifest and run; manifest hash is canonical JSON, not file-byte SHA')
    args=parser.parse_args(argv)
    try:
        report=audit(args.repo)
        if args.write_selftest_bundle:
            if args.write_selftest_bundle.exists():
                raise ValueError('Refusing to overwrite existing self-test bundle')
            bundle=selftest_bundle(args.repo)
            report['selftest']=validate_run_record(bundle['run'],scenes=bundle['manifest'],manifest_sha256=digest(bundle['manifest']))
            args.write_selftest_bundle.parent.mkdir(parents=True,exist_ok=True)
            args.write_selftest_bundle.write_text(json.dumps(bundle,indent=2,allow_nan=False)+'\n')
        if args.run_bundle:
            bundle=json.loads(args.run_bundle.read_text())
            if bundle.get('manifest_hash_encoding') != 'canonical-json':
                raise ValueError('Run bundle must declare canonical-json manifest hashing')
            report['run_bundle']=validate_run_record(bundle['run'],scenes=bundle['manifest'],manifest_sha256=digest(bundle['manifest']))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        report={"status":"failed", "error_type":type(exc).__name__, "error":str(exc)}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report,indent=2,allow_nan=False))
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
