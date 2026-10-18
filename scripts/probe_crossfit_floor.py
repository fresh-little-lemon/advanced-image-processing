#!/usr/bin/env python3
"""Fixed noise-bias corrections after the first residual-floor probe."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO),str(REPO/'src')]
from reliable_focus.crossfit_floor import estimate_crossfit
from reliable_focus.residual_floor import estimate_floor
from reliable_focus.core import decode_srgb
from reliable_focus.io import read_rgb
from reliable_focus.metrics import psnr
from reliable_focus.diagnostic import energy_fuse,DiagnosticConfig
from probe_shared_support import candidate
from probe_residual_floor import write_csv,generate_case,textures
METHODS=['calibrated_residual_mean','crossfit_residual_mean','crossfit_residual_full']


def run(a,b,method,ratio):
 if method=='calibrated_residual_mean':
  sigmas,info=estimate_floor(a,b);sigmas=tuple(s/np.sqrt(ratio) for s in sigmas)
 else:sigmas,info=estimate_crossfit(a,b)
 delta=sigmas[0]**2-sigmas[1]**2
 output=(energy_fuse(a,b,DiagnosticConfig(sigma_mode='oracle_known'),sigmas)[0]
         if method=='crossfit_residual_full' else candidate(a,b,delta))
 return output,delta,info


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);p.add_argument('--data-root',required=True,type=Path);p.add_argument('--protocol',required=True,type=Path);args=p.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
 protocol=json.loads(args.protocol.read_text());assert protocol['methods']==METHODS;ratio=protocol['fixed_variance_ratio']
 state={'status':'running','protocol':protocol,'protocol_sha256':hashlib.sha256(args.protocol.read_bytes()).hexdigest(),'sources':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),REPO/'src/reliable_focus/crossfit_floor.py',REPO/'src/reliable_focus/residual_floor.py']}}
 (out/'run.json').write_text(json.dumps(state,indent=2));rows=[];swaps=[]
 def record(context,a,b,gt,swap=False):
  for method in METHODS:
   start=time.perf_counter();result,delta,info=run(a,b,method,ratio);seconds=time.perf_counter()-start
   rows.append({**context,'method':method,'psnr_linear_rgb':float(psnr(gt,result)),'mae_linear_rgb':float(np.mean(abs(gt-result))),'delta':delta,'seconds_pipeline':seconds,'details':json.dumps(info)})
   if swap:
    reverse,rd,_=run(b,a,method,ratio);error=float(np.max(abs(reverse-result)));assert error<1e-10 and abs(rd+delta)<1e-14
    swaps.append({**context,'method':method,'max_rgb_error':error})
 tex=textures();mixed=tex['stochastic'].copy();mixed[:,:48]=tex['sine'][:,:48]
 for name,t in [('stochastic',tex['stochastic']),('mixed_sine_left_stochastic_right',mixed)]:
  for fraction in [.25,.5,.75]:
   for brightness in ['normal','dark','extreme_white']:
    for na,nb in [(0,0),(0,5),(5,0),(5,5)]:
     for seed in [11,23]:
      a,b,gt=generate_case(t,fraction,brightness,na,nb,seed)
      record({'dataset':'procedural','scene_id':'','texture':name,'sharp_a_fraction':fraction,'brightness':brightness,'noise_a_255':na,'noise_b_255':nb,'seed':seed},a,b,gt,True)
 write_csv(out/'procedural_metrics.csv',rows);write_csv(out/'source_swap.csv',swaps);rows=[]
 print('procedural complete',flush=True)
 scenes=json.loads((REPO/'data/manifests/validation_v1.json').read_text());assert len(scenes)==26 and all(s['split']=='validation' for s in scenes)
 for scene in scenes:
  images={}
  for f in scene['files']:
   path=args.data_root/f['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==f['sha256'];images[f['role']]=decode_srgb(read_rgb(path,profile_policy='encoded_ignore'))
  for na,nb in [(0,0),(0,5),(5,0)]:
   rng=np.random.default_rng(11);a=np.clip(images['A']+rng.normal(0,na/255,images['A'].shape),0,1);b=np.clip(images['B']+rng.normal(0,nb/255,images['B'].shape),0,1)
   record({'dataset':'WHU_validation','scene_id':scene['scene_id'],'texture':'','sharp_a_fraction':'','brightness':'','noise_a_255':na,'noise_b_255':nb,'seed':11},a,b,images['GT'])
  print(scene['scene_id'],flush=True)
 write_csv(out/'validation_metrics.csv',rows)
 state.update(status='complete',procedural_rows=432,validation_rows=len(rows),max_swap_error=max(r['max_rgb_error'] for r in swaps));(out/'run.json').write_text(json.dumps(state,indent=2))
if __name__=='__main__':main()
