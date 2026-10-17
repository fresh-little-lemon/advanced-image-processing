#!/usr/bin/env python3
"""Fixed phase-2 procedural grid, known linear exposure, 3 seeds, no holdout access."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import argparse,csv,json,time
from pathlib import Path
from dataclasses import asdict
import numpy as np
from scipy.ndimage import gaussian_filter,laplace
from reliable_focus.core import fuse,Config,gray,box
from reliable_focus.diagnostic import energy_fuse,DiagnosticConfig,luminance_sigma,valid_support,reliability,LUMA
from reliable_focus.metrics import psnr
from reliable_focus.io import write_rgb

def textures(n=96):
    y,x=np.mgrid[:n,:n];rng=np.random.default_rng(7281)
    maps={'constant':np.full((n,n),.45),'sine':.45+.18*np.sin(x*.45)+.08*np.sin(y*.23),'checker':.3+.3*((x//3+y//3)%2),'step':np.where(x+y<n,.3,.7),'stochastic':np.clip(.5+.12*rng.normal(size=(n,n)),.2,.8)}
    return {name:np.stack([v,.85*v+.07,.65*v+.15],-1) for name,v in maps.items()}

def configurations():
    return {'oracle_full':DiagnosticConfig(sigma_mode='oracle_known'),'oracle_no_mean':DiagnosticConfig(sigma_mode='oracle_known',subtract_mean=False),'oracle_no_variance':DiagnosticConfig(sigma_mode='oracle_known',normalize_variance=False),'oracle_neither':DiagnosticConfig(sigma_mode='oracle_known',subtract_mean=False,normalize_variance=False),'global_full':DiagnosticConfig(),'global_no_mean':DiagnosticConfig(subtract_mean=False),'global_no_variance':DiagnosticConfig(normalize_variance=False),'flat_full':DiagnosticConfig(sigma_mode='estimated_flat'),'flat_fallback':DiagnosticConfig(sigma_mode='estimated_flat',fallback_quantization=True),'zero':DiagnosticConfig(sigma_mode='zero')}

def main():
 p=argparse.ArgumentParser();p.add_argument('--zero-limit-only',action='store_true');p.add_argument('--output',type=Path,default=Path('results/phase2_procedural'));args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
 cfgs=({'oracle_limit':DiagnosticConfig(sigma_mode='oracle_known',epsilon_variance=0),'global_limit':DiagnosticConfig(epsilon_variance=0),'flat_limit':DiagnosticConfig(sigma_mode='estimated_flat',epsilon_variance=0)} if args.zero_limit_only else configurations());noise_pairs=[(0,0),(2,2),(5,5),(10,10),(0,5),(2,10)]
 protocol={'domain':'linear RGB; known exposure compensation applied identically to all methods','textures':list(textures()),'size':96,'exposures_b':[.7,1.,1.3],'noise_rgb_pairs_255':noise_pairs,'seeds':[11,23,47],'validity':'exclude clipped support, radius4 image border, source-mask boundary4px; label only pixels whose known sharp/blurred RGB local MSE>1e-6','fixed_configs':{k:asdict(v) for k,v in cfgs.items()},'fallback_threshold':'operational norm(luma)/255, not quantization noise standard deviation','sigma_oracle':'known preclipping independent RGB Gaussian propagated by luma covariance and inverse exposure; saturated support excluded','status':'running'}
 (args.output/'protocol.json').write_text(json.dumps(protocol,indent=2));rows=[];start=time.time()
 for name,gt in textures().items():
  n=gt.shape[0];mask=np.indices((n,n))[1]<n//2;blur=gaussian_filter(gt,(1.5,1.5,0),mode='reflect');ca=np.where(mask[...,None],gt,blur);cb=np.where(mask[...,None],blur,gt)
  identifiable=box(np.mean((gt-blur)**2,axis=-1),7)>1e-6;identifiable[:,n//2-4:n//2+4]=False
  clean_energy=[box(laplace(gray(c))**2,7) for c in (ca,cb)]
  for exposure in [.7,1.,1.3]:
   for na,nb in noise_pairs:
    for seed in [11,23,47]:
     rng=np.random.default_rng(seed);oa=np.clip(ca+rng.normal(0,na/255,gt.shape),0,1);ob=np.clip(exposure*cb+rng.normal(0,nb/255,gt.shape),0,1)
     a=oa;b=np.clip(ob/exposure,0,1);valid=valid_support(oa,ob)&valid_support(a,b);evaluation=valid&identifiable
     sigmas=(luminance_sigma(np.eye(3)*(na/255)**2),luminance_sigma(np.eye(3)*(nb/255/exposure)**2))
     for method,cfg in [('guided',None),*cfgs.items()]:
      t=time.perf_counter()
      if cfg is None:
       out,w=fuse(a,b,Config(method='guided'),True);details={'sigmas':[float('nan')]*2,'fallback':False,'raw_weight':w,'estimator':[{'coverage':0,'guide_energy':0}]*2}
      else:out,w,details=energy_fuse(a,b,cfg,sigmas,valid)
      elapsed=time.perf_counter()-t;rel=reliability(details['raw_weight'],mask,evaluation);smooth=reliability(w,mask,evaluation)
      bias=[]
      for j,key in enumerate(['energy_a','energy_b']):
       bias.append(float(np.mean((details[key]-clean_energy[j])[valid])) if key in details and valid.any() else float('nan'))
      rows.append({'texture':name,'exposure_b':exposure,'noise_a_255':na,'noise_b_255':nb,'seed':seed,'method':method,'psnr_linear':psnr(gt,out),'boundary_mae':float(np.mean(abs(out[:,n//2-4:n//2+4]-gt[:,n//2-4:n//2+4]))),'sigma_true_a':sigmas[0],'sigma_true_b':sigmas[1],'sigma_est_a':details['sigmas'][0],'sigma_est_b':details['sigmas'][1],'energy_bias_a':bias[0],'energy_bias_b':bias[1],'raw_brier':rel['brier'],'raw_ece':rel['ece'],'raw_accuracy':rel['accuracy'],'smooth_brier':smooth['brier'],'smooth_ece':smooth['ece'],'smooth_accuracy':smooth['accuracy'],'valid_focus_pixels':rel['pixels'],'valid_energy_pixels':int(valid.sum()),'flat_coverage_a':details['estimator'][0]['coverage'],'flat_guide_energy_a':details['estimator'][0]['guide_energy'],'fallback':int(details['fallback']),'seconds':elapsed})
      if seed==11 and exposure==1 and (na,nb) in [(0,0),(2,10)] and method in ['guided','global_full','flat_full','flat_fallback']:
       write_rgb(args.output/'procedural_visuals'/f'{name}_{na}_{nb}_{method}.png',out)
  print(name,'done',flush=True)
 with (args.output/'metrics.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 protocol.update(status='complete',rows=len(rows),elapsed_seconds=time.time()-start)
 (args.output/'protocol.json').write_text(json.dumps(protocol,indent=2));print(len(rows),'rows',flush=True)
if __name__=='__main__':main()
