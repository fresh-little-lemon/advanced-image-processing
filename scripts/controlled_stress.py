#!/usr/bin/env python3
"""Controlled procedural experiment with exact canonical target, all frozen methods."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import csv,json,argparse
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from reliable_focus import Config,fuse
from reliable_focus.metrics import psnr
p=argparse.ArgumentParser();p.add_argument('--configs',required=True);p.add_argument('--output',required=True);args=p.parse_args()
configs={m:Config(**c) for m,c in json.load(open(args.configs)).items()}
size=192;yy,xx=np.mgrid[:size,:size];rng=np.random.default_rng(20261017)
texture=.45+.16*np.sin(xx*.31)+.12*np.cos(yy*.23)+.06*rng.normal(size=(size,size))
gt=np.clip(np.stack([texture,texture*.85+.07,texture*.65+.14],axis=-1),.03,.97)
blur=gaussian_filter(gt,(2.,2.,0),mode='reflect');mask=xx<size//2
ca=np.where(mask[...,None],gt,blur);cb=np.where(mask[...,None],blur,gt)
rows=[]
for exposure in [1.,.7,1.3]:
 for sigma in [0.,.01,.03]:
  for seed in [11,23,47]:
   rng=np.random.default_rng(seed);a=np.clip(ca+rng.normal(0,sigma,gt.shape),0,1);b=np.clip(exposure*cb+rng.normal(0,sigma,gt.shape),0,1)
   for method,cfg in configs.items():
    f,w=fuse(a,b,cfg,True)
    rows.append({'exposure_b':exposure,'sigma':sigma,'seed':seed,'method':method,'psnr_canonical':psnr(gt,f),'focus_mask_accuracy':float(np.mean((w>=.5)==mask)),'boundary_mae':float(np.mean(abs(gt[:,92:100]-f[:,92:100])))})
output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
with output.open('w',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
print(f'{len(rows)} rows')
