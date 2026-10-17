#!/usr/bin/env python3
"""Predeclared mechanism diagnostic: estimate vs injected AWGN sigma; no tuning."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import argparse,csv
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scipy.ndimage import gaussian_filter
from reliable_focus.core import Config,fuse,noise_sigma,gray
from reliable_focus.metrics import psnr
p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
size=192;yy,xx=np.mgrid[:size,:size];rng=np.random.default_rng(20261017)
texture=.45+.16*np.sin(xx*.31)+.12*np.cos(yy*.23)+.06*rng.normal(size=(size,size))
gt=np.clip(np.stack([texture,texture*.85+.07,texture*.65+.14],axis=-1),.03,.97)
blur=gaussian_filter(gt,(2.,2.,0),mode='reflect');mask=xx<size//2
ca=np.where(mask[...,None],gt,blur);cb=np.where(mask[...,None],blur,gt)
rows=[]
# Noise is independently added per RGB channel. Luma sigma is sigma*||luma||2.
luma_norm=float(np.linalg.norm([.299,.587,.114]))
for exposure in [1.,.7,1.3]:
 for sigma in [0.,.01,.03]:
  for seed in [11,23,47]:
   rng=np.random.default_rng(seed);a=np.clip(ca+rng.normal(0,sigma,gt.shape),0,1);b=np.clip(exposure*cb+rng.normal(0,sigma,gt.shape),0,1)
   for method in ['guided','energy_no_noise','energy_estimated','energy_oracle']:
    cfg=Config(method='guided' if method=='guided' else 'noise_energy',noise_correction=method!='energy_no_noise')
    if method=='energy_oracle':
     with patch('reliable_focus.core.noise_sigma',return_value=sigma*luma_norm):f=fuse(a,b,cfg)
    else:f=fuse(a,b,cfg)
    rows.append({'exposure_b':exposure,'rgb_injected_sigma':sigma,'luma_preclipping_sigma':sigma*luma_norm,'seed':seed,'method':method,'estimated_sigma_a':noise_sigma(gray(a)),'estimated_sigma_b':noise_sigma(gray(b)),'psnr_canonical':psnr(gt,f)})
path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
with path.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
print(f'{len(rows)} rows; oracle is pre-clipping Gaussian luma sigma, not post-clipping exact covariance')
