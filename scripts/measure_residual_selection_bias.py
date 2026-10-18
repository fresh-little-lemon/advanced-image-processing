#!/usr/bin/env python3
"""Fixed homogeneous-noise calibration diagnostic; no calibration is applied."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import argparse,json,sys
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO),str(REPO/'src')]
from reliable_focus.residual_floor import estimate_floor
from reliable_focus.diagnostic import LUMA
from probe_residual_floor import write_csv

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
 protocol={'status':'running','purpose':'measure lower-tail selection bias on constant0.45 iidRGB Gaussian noise','sizes':[48,96,192],'noise_pairs_255':[[5,5],[0,5]],'seeds':list(range(128)),'methods':['independent_guide','independent_residual'],'calibration_applied':False}
 (args.output/'protocol.json').write_text(json.dumps(protocol,indent=2));rows=[]
 for size in protocol['sizes']:
  clean=np.full((size,size,3),.45)
  for na,nb in protocol['noise_pairs_255']:
   for seed in protocol['seeds']:
    rng=np.random.default_rng(seed);a=np.clip(clean+rng.normal(0,na/255,clean.shape),0,1);b=np.clip(clean+rng.normal(0,nb/255,clean.shape),0,1)
    for method in protocol['methods']:
     sigmas,info=estimate_floor(a,b,ranking='guide' if method=='independent_guide' else 'residual')
     true_b=float(np.linalg.norm(LUMA)*nb/255)**2
     rows.append({'size':size,'noise_a_255':na,'noise_b_255':nb,'seed':seed,'method':method,'variance_ratio_b':sigmas[1]**2/true_b,'delta':sigmas[0]**2-sigmas[1]**2,'selected_blocks':info['selected_blocks_per_source']})
 write_csv(args.output/'metrics.csv',rows)
 summary={}
 for size in protocol['sizes']:
  summary[str(size)]={}
  for na,nb in protocol['noise_pairs_255']:
   summary[str(size)][f'{na}_{nb}']={m:float(np.mean([r['variance_ratio_b'] for r in rows if r['size']==size and r['noise_a_255']==na and r['method']==m])) for m in protocol['methods']}
 (args.output/'summary.json').write_text(json.dumps(summary,indent=2));protocol.update(status='complete',rows=len(rows));(args.output/'protocol.json').write_text(json.dumps(protocol,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
