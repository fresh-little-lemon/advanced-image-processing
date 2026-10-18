#!/usr/bin/env python3
"""Prespecified procedural transfer: new size/seeds, five textures, exposure shifts."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO),str(REPO/'src')]
from reliable_focus.crossfit_fusion import fuse_crossfit
from reliable_focus.metrics import psnr
from probe_residual_floor import textures,write_csv,run_method


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);p.add_argument('--protocol',required=True,type=Path);args=p.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
 protocol=json.loads(args.protocol.read_text());state={'status':'running','protocol':protocol,'protocol_sha256':hashlib.sha256(args.protocol.read_bytes()).hexdigest(),'sources':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),REPO/'src/reliable_focus/crossfit_floor.py',REPO/'src/reliable_focus/crossfit_fusion.py']}}
 (out/'run.json').write_text(json.dumps(state,indent=2));rows=[]
 for texture,t in textures(protocol['size']).items():
  for brightness in protocol['brightness']:
   gt=t if brightness=='normal' else .01+.12*t
   blur=gaussian_filter(gt,(1.5,1.5,0),mode='reflect');h,w=gt.shape[:2]
   for fraction in protocol['sharp_a_fractions']:
    mask=np.indices((h,w))[1]<int(w*fraction);ca=np.where(mask[...,None],gt,blur);cb=np.where(mask[...,None],blur,gt)
    for exposure in protocol['exposure_b']:
     for na,nb in protocol['noise_rgb_pairs_255']:
      for seed in protocol['seeds']:
       rng=np.random.default_rng(seed);a=np.clip(ca+rng.normal(0,na/255,gt.shape),0,1);observed_b=np.clip(exposure*cb+rng.normal(0,nb/255,gt.shape),0,1);b=np.clip(observed_b/exposure,0,1)
       context={'texture':texture,'brightness':brightness,'sharp_a_fraction':fraction,'exposure_b':exposure,'noise_a_255':na,'noise_b_255':nb,'seed':seed,'capture_clipped_fraction':float(np.mean(np.any((a<=0)|(a>=1)|(observed_b<=0)|(observed_b>=1),axis=-1)))}
       for method in protocol['methods']:
        start=time.perf_counter()
        if method=='crossfit_residual_mean':result,details=fuse_crossfit(a,b,True);delta=details['delta_sigma2']
        else:result,delta,details=run_method(a,b,method,(0.,0.))
        seconds=time.perf_counter()-start
        rows.append({**context,'method':method,'psnr_linear_rgb':float(psnr(gt,result)),'mae_linear_rgb':float(np.mean(abs(result-gt))),'delta':delta,'seconds_pipeline':seconds})
  print(texture,flush=True)
 write_csv(out/'metrics.csv',rows);state.update(status='complete',rows=len(rows));(out/'run.json').write_text(json.dumps(state,indent=2))
if __name__=='__main__':main()
