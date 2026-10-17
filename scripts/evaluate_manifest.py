#!/usr/bin/env python3
"""Evaluate a frozen paired-scene manifest. No parameter search or downloads."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import argparse,csv,hashlib,json,time
from pathlib import Path
from dataclasses import asdict
import numpy as np
from reliable_focus import Config,fuse
from reliable_focus.io import read_rgb,write_rgb
from reliable_focus.metrics import diagnostics,psnr

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--data-root',type=Path,default=Path(os.environ.get('MULTIFOCUS_DATA_ROOT','.')),help='Root for relative manifest paths');parser.add_argument('--output',type=Path,required=True);parser.add_argument('--visuals',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True);args.visuals.mkdir(parents=True,exist_ok=True)
    configs={m:Config(method=m) for m in ['average','laplacian','sml','guided','experimental','noise_energy']}
    configs.update({'energy_no_noise':Config(method='noise_energy',noise_correction=False),'energy_no_exposure':Config(method='noise_energy',exposure_normalization=False),'energy_no_confidence':Config(method='noise_energy',confidence_weighting=False)})
    config_json=json.dumps({k:asdict(v) for k,v in configs.items()},indent=2,sort_keys=True)
    (args.output/'frozen_configs.json').write_text(config_json)
    (args.output/'run.json').write_text(json.dumps({'manifest_sha256':hashlib.sha256(args.manifest.read_bytes()).hexdigest(),'config_sha256':hashlib.sha256(config_json.encode()).hexdigest(),'threads':1,'profile_policy':'encoded_ignore','status':'running','timing':'one call per method, excludes decoding/metrics'},indent=2))
    rows=[];public_manifest=[]
    for scene in json.loads(args.manifest.read_text()):
        images={}
        for file in scene['files']:
            path=Path(file['path'])
            if not path.is_absolute():path=args.data_root/path
            if hashlib.sha256(path.read_bytes()).hexdigest()!=file['sha256']:raise ValueError(f'Hash mismatch {path.name}')
            images[file['role']]=read_rgb(path,profile_policy='encoded_ignore')
        public_scene={k:v for k,v in scene.items() if k!='files'}
        public_scene['files']=[{k:v for k,v in f.items() if k!='path'} for f in scene['files']]
        public_manifest.append(public_scene)
        a,b=images['A'],images['B']
        for method,cfg in configs.items():
            start=time.perf_counter();f=fuse(a,b,cfg);elapsed=time.perf_counter()-start
            row={'scene_id':scene['scene_id'],'dataset':scene['dataset'],'method':method,'fusion_seconds':elapsed,**diagnostics(a,b,f)}
            if 'GT' in images:
                row['psnr']=psnr(images['GT'],f);row['mae']=float(np.mean(abs(images['GT']-f)))
            rows.append(row)
            if method in ['guided','noise_energy']:write_rgb(args.visuals/f"{scene['scene_id']}_{method}.png",f)
        print(scene['scene_id'],flush=True)
    with (args.output/'metrics.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    summary={method:{key:float(np.mean([r[key] for r in rows if r['method']==method])) for key in rows[0] if key not in ['scene_id','dataset','method']} for method in configs}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2))
    (args.output/'manifest_public.json').write_text(json.dumps(public_manifest,indent=2))
    meta=json.loads((args.output/'run.json').read_text());meta['status']='complete';meta['scene_count']=len(public_manifest)
    (args.output/'run.json').write_text(json.dumps(meta,indent=2))
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
