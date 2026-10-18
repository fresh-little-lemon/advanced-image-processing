#!/usr/bin/env python3
"""Evaluate fixed residual candidates on the frozen26 validation scenes only."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO),str(REPO/'src')]
from probe_residual_floor import run_method,write_csv
from reliable_focus.core import decode_srgb
from reliable_focus.io import read_rgb
from reliable_focus.metrics import psnr
from reliable_focus.diagnostic import LUMA

METHODS=['guided','gff_continuous_shared_gray','no_mean','shared_delta','independent_guide','shared_residual','independent_residual','residual_variance_no_mean','residual_full']

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-root',required=True,type=Path);p.add_argument('--output',required=True,type=Path);args=p.parse_args()
 out=args.output;out.mkdir(parents=True,exist_ok=False)
 manifest=REPO/'data/manifests/validation_v1.json';scenes=json.loads(manifest.read_text());assert len(scenes)==26 and all(s['split']=='validation' for s in scenes)
 protocol={'status':'running','methods':METHODS,'conditions':[[0,0],[0,5],[5,0]],'seed':11,'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'references':'quality metrics only; original scene noise is unknown','selection':'same fixed26 validation scenes; no holdout use','source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),REPO/'src/reliable_focus/residual_floor.py',REPO/'scripts/probe_residual_floor.py']},'metric_domain':'full-image linear RGB; equally weighted scene means'}
 (out/'run.json').write_text(json.dumps(protocol,indent=2));rows=[]
 for scene in scenes:
  inputs={}
  for f in scene['files']:
   path=args.data_root/f['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==f['sha256'];inputs[f['role']]=decode_srgb(read_rgb(path,profile_policy='encoded_ignore'))
  ca,cb,gt=inputs['A'],inputs['B'],inputs['GT']
  for na,nb in protocol['conditions']:
   # Draw both fields in every condition, matching the procedural RNG convention.
   rng=np.random.default_rng(11);a=np.clip(ca+rng.normal(0,na/255,ca.shape),0,1);b=np.clip(cb+rng.normal(0,nb/255,cb.shape),0,1)
   known=tuple(float(np.linalg.norm(LUMA)*n/255) for n in (na,nb))
   for method in METHODS:
    start=time.perf_counter();result,delta,info=run_method(a,b,method,known);elapsed=time.perf_counter()-start
    rows.append({'scene_id':scene['scene_id'],'noise_a_255':na,'noise_b_255':nb,'seed':11,'method':method,'psnr_linear_rgb':float(psnr(gt,result)),'mae_linear_rgb':float(np.mean(abs(gt-result))),'estimated_delta_sigma2':delta,'seconds_pipeline':elapsed,'details':json.dumps(info)})
  print(scene['scene_id'],'complete',flush=True)
 write_csv(out/'metrics.csv',rows)
 summary={}
 for na,nb in protocol['conditions']:
  selected=[r for r in rows if (r['noise_a_255'],r['noise_b_255'])==(na,nb)]
  summary[f'{na}_{nb}']={m:{k:float(np.mean([r[k] for r in selected if r['method']==m])) for k in ('psnr_linear_rgb','mae_linear_rgb','seconds_pipeline')} for m in METHODS}
 (out/'summary.json').write_text(json.dumps(summary,indent=2));protocol.update(status='complete',rows=len(rows));(out/'run.json').write_text(json.dumps(protocol,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
