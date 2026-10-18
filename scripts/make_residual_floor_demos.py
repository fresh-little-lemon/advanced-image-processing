#!/usr/bin/env python3
"""Generate self-owned procedural comparison images, with no benchmark images."""
import argparse,json,sys
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO),str(REPO/'src')]
from make_phase2_demos import panel
from probe_residual_floor import generate_case,run_method,textures
from reliable_focus.metrics import psnr
from probe_crossfit_floor import run as run_crossfit

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);p.add_argument('--method',choices=['independent_residual','crossfit_residual_mean'],default='independent_residual');args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
 tex=textures();mixed=tex['stochastic'].copy();mixed[:,:48]=tex['sine'][:,:48]
 # Two fixed design examples plus the prior spatial-gate worst loss. No result-driven best-case search.
 selections=[('normal_clean_quarter',tex['stochastic'],.25,'normal',0,0,11),('normal_noisy_three_quarters',tex['stochastic'],.75,'normal',0,5,11),('prior_gate_worst_loss',mixed,.5,'dark',0,5,11)]
 records=[]
 for name,texture,fraction,brightness,na,nb,seed in selections:
  a,b,gt=generate_case(texture,fraction,brightness,na,nb,seed);images=[a,b];labels=['Source A','Source B'];metrics={}
  for method,title in [('guided','Guided baseline'),('shared_delta','Shared correction'),(args.method,'Cross-fit correction' if args.method=='crossfit_residual_mean' else 'Residual ranking')]:
   result,delta,_=(run_crossfit(a,b,method,1.) if method=='crossfit_residual_mean' else run_method(a,b,method,(0.,0.)));score=float(psnr(gt,result));images.append(result);labels.append(f'{title} {score:.2f} dB');metrics[method]={'psnr_linear_rgb':score,'mae_linear_rgb':float(np.mean(abs(result-gt))),'estimated_delta_sigma2':delta}
  images.append(gt);labels.append('Clean reference')
  path=args.output/(name+'.png');panel(images,labels,name.replace('_',' '),f'Sharp A coverage={fraction:g}; brightness={brightness}; noise A={na}/255 B={nb}/255; seed={seed}',path)
  records.append({'file':path.name,'type':'self-generated procedural texture','sharp_a_fraction':fraction,'brightness':brightness,'noise_a_255':na,'noise_b_255':nb,'seed':seed,'metrics':metrics})
 (args.output/'manifest.json').write_text(json.dumps(records,indent=2));print(json.dumps(records,indent=2))
if __name__=='__main__':main()
