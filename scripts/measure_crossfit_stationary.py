#!/usr/bin/env python3
"""Reproduce the independent stationary-noise check for cross-fitted selection."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import argparse,sys
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO),str(REPO/'src')]
from reliable_focus.crossfit_floor import estimate_crossfit
from reliable_focus.diagnostic import LUMA
from probe_residual_floor import write_csv

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);args=p.parse_args()
 if args.output.exists():raise FileExistsError(args.output)
 rows=[]
 for n in [48,96,192]:
  clean=np.full((n,n,3),.45)
  for seed in range(128):
   rng=np.random.default_rng(seed);a=clean+rng.normal(0,5/255,clean.shape);b=clean+rng.normal(0,5/255,clean.shape)
   sigmas,_=estimate_crossfit(a,b);true=(np.linalg.norm(LUMA)*5/255)**2
   rows.append({'size':n,'seed':seed,'ratio_a':sigmas[0]**2/true,'ratio_b':sigmas[1]**2/true})
 write_csv(args.output,rows)
if __name__=='__main__':main()
