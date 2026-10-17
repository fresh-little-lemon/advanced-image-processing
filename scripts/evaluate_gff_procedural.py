#!/usr/bin/env python3
"""Frozen continuous GFF on the exact phase2 procedural conditions."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import csv,json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from baselines_gff import GFFConfig,fuse_gff
from run_phase2_diagnostics import textures
from reliable_focus.metrics import psnr
rows=[]
for name,gt in textures().items():
 n=gt.shape[0];mask=np.indices((n,n))[1]<n//2;blur=gaussian_filter(gt,(1.5,1.5,0),mode='reflect');ca=np.where(mask[...,None],gt,blur);cb=np.where(mask[...,None],blur,gt)
 for exposure in [.7,1.,1.3]:
  for na,nb in [(0,0),(2,2),(5,5),(10,10),(0,5),(2,10)]:
   for seed in [11,23,47]:
    rng=np.random.default_rng(seed);oa=np.clip(ca+rng.normal(0,na/255,gt.shape),0,1);ob=np.clip(exposure*cb+rng.normal(0,nb/255,gt.shape),0,1);a=oa;b=np.clip(ob/exposure,0,1)
    out=fuse_gff([a,b],GFFConfig(profile='continuous_shared_gray'))
    rows.append({'texture':name,'exposure_b':exposure,'noise_a_255':na,'noise_b_255':nb,'seed':seed,'method':'gff_continuous_linear','psnr_linear':psnr(gt,out),'mae_linear':float(np.mean(abs(gt-out))),'boundary_mae':float(np.mean(abs(out[:,n//2-4:n//2+4]-gt[:,n//2-4:n//2+4])))})
 print(name,flush=True)
p=Path('results/gff_procedural');p.mkdir(parents=True,exist_ok=True)
with (p/'metrics.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
summary={'conditions':len(rows),'domain':'linear RGB, same known exposure compensation and exact RNG order as phase2_procedural','profile':'continuous_shared_gray'}
for label,fn in [('symmetric_noise',lambda r:r['noise_a_255']==r['noise_b_255']>0),('asymmetric_noise',lambda r:r['noise_a_255']!=r['noise_b_255']),('clean_nonconstant',lambda r:r['noise_a_255']==r['noise_b_255']==0 and r['texture']!='constant')]:
 selected=[r for r in rows if fn(r)];summary[label]={k:float(np.mean([r[k] for r in selected])) for k in ['psnr_linear','mae_linear','boundary_mae']}
(p/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
