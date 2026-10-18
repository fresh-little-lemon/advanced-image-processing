import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import sys,json,csv,hashlib
from pathlib import Path
import numpy as np
from scipy.ndimage import laplace,gaussian_filter
from scipy.stats import spearmanr
repo=Path(__file__).resolve().parents[1];sys.path[:0]=[str(repo),str(repo/'src')]
from reliable_focus.core import Config,fuse,gray,box,decode_srgb,noise_sigma
from reliable_focus.diagnostic import DiagnosticConfig,energy_fuse,valid_support
from reliable_focus.io import read_rgb
from reliable_focus.metrics import psnr
from baselines_gff import GFFConfig,fuse_gff
import argparse
parser=argparse.ArgumentParser(description='Diagnose the frozen 26-scene validation set; writes numerical results only.')
parser.add_argument('--data-root',required=True,type=Path)
parser.add_argument('--output',required=True,type=Path,help='Fresh directory; existing output is never replaced')
args=parser.parse_args();out=args.output.resolve();root=args.data_root.resolve();out.mkdir(parents=True,exist_ok=False)
scenes=json.loads((repo/'data/manifests/validation_v1.json').read_text());assert len(scenes)==26 and all(s['split']=='validation' for s in scenes)
rows=[]
for scene in scenes:
 im={}
 for f in scene['files']:
  p=root/f['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'];im[f['role']]=decode_srgb(read_rgb(p,profile_policy='encoded_ignore'))
 a,b,gt=im['A'],im['B'],im['GT'];ya,yb,yg=map(gray,[a,b,gt]);valid=valid_support(a,b)
 guided=fuse(a,b,Config(method='guided'));global_f,_,d=energy_fuse(a,b,DiagnosticConfig(),valid=valid);no_mean,_,dn=energy_fuse(a,b,DiagnosticConfig(subtract_mean=False),valid=valid);flat,_,df=energy_fuse(a,b,DiagnosticConfig(sigma_mode='estimated_flat'),valid=valid);gff=fuse_gff([a,b],GFFConfig(profile='continuous_shared_gray'))
 outputs={'guided':guided,'global':global_f,'no_mean':no_mean,'flat':flat,'gff':gff}
 s0=box(laplace(ya)**2-laplace(yb)**2,7);shift=20*(d['sigmas'][0]**2-d['sigmas'][1]**2)
 np.testing.assert_allclose(d['energy_a']-d['energy_b'],s0-shift,atol=1e-14)
 ea=box(np.mean((a-gt)**2,axis=-1),7);eb=box(np.mean((b-gt)**2,axis=-1),7);ident=valid&(abs(ea-eb)>1e-6);label_a=ea<eb
 before=s0>=0;after=(s0-shift)>=0;flipped=before!=after
 gty,gtx=np.gradient(gaussian_filter(yg,1,mode='reflect'));tex=gtx*gtx+gty*gty;qlo,qhi=np.quantile(tex,[.2,.8]);low=tex<=qlo;high=tex>=qhi
 def avg(v,m):return float(np.mean(v[m])) if m.any() else None
 row={'scene_id':scene['scene_id'],'sigma_a':d['sigmas'][0],'sigma_b':d['sigmas'][1],'sigma_gt':noise_sigma(yg),'flat_sigma_a':df['sigmas'][0],'flat_sigma_b':df['sigmas'][1],'flat_coverage_a':df['estimator'][0]['coverage'],'flat_coverage_b':df['estimator'][1]['coverage'],'energy_shift':shift,'abs_energy_shift':abs(shift),'valid_fraction':float(valid.mean()),'saturated_fraction':float(np.mean(np.any((a<=0)|(a>=1)|(b<=0)|(b>=1),axis=-1))),'median_luma_ratio_b_a':float(np.median(yb[valid]/np.maximum(ya[valid],1e-8))),'mean_luma_a':float(ya.mean()),'mean_luma_b':float(yb.mean()),'texture_mean':float(tex.mean()),'preferred_a_fraction':avg(label_a,ident),'identifiable_pixels':int(ident.sum()),'flipped_fraction_valid':avg(flipped,valid),'flipped_fraction_identifiable':avg(flipped,ident),'before_accuracy':avg(before==label_a,ident),'after_accuracy':avg(after==label_a,ident),'harmful_flip_fraction_identifiable':avg(flipped&(before==label_a),ident),'helpful_flip_fraction_identifiable':avg(flipped&(after==label_a),ident)}
 for name,f in outputs.items():
  mse=np.mean((f-gt)**2,axis=-1);row[name+'_psnr']=float(psnr(gt,f));row[name+'_mse']=float(mse.mean())
  for region,m in [('low_texture',low),('high_texture',high),('valid',valid),('excluded',~valid)]:row[name+'_mse_'+region]=avg(mse,m)
 row['global_minus_guided']=row['global_psnr']-row['guided_psnr'];row['global_minus_no_mean']=row['global_psnr']-row['no_mean_psnr'];row['sigma_delta']=row['sigma_a']-row['sigma_b']
 rows.append(row);print(scene['scene_id'],flush=True)
with (out/'per_scene_diagnostics.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
summary={'scope':'26 frozen validation scenes; no holdouts','labels':'local RGB MSE preference vs provided GT, not physical focus ground truth; |difference|>1e-6, valid_support only','oracle_noise':'unknown on original photos; zero-noise mode is a diagnostic assumption, not oracle','correlations':{}}
for target,features in [('global_minus_guided',['abs_energy_shift','flipped_fraction_identifiable','saturated_fraction','valid_fraction','median_luma_ratio_b_a','texture_mean']),('global_minus_no_mean',['abs_energy_shift','flipped_fraction_identifiable','saturated_fraction','texture_mean']),('sigma_delta',['preferred_a_fraction'])]:
 for feature in features:
  pairs=[(r[feature],r[target]) for r in rows if r[feature] is not None and r[target] is not None]
  result=spearmanr(*zip(*pairs));summary['correlations'][target+'~'+feature]={'spearman_rho':float(result.statistic),'p_descriptive_uncorrected':float(result.pvalue)}
for group,selected in [('all',rows),('global_losers',[r for r in rows if r['global_minus_guided']<0]),('global_winners',[r for r in rows if r['global_minus_guided']>0])]:
 summary[group]={'n':len(selected),'mean':{k:float(np.mean([r[k] for r in selected])) for k in ['global_minus_guided','global_minus_no_mean','sigma_a','sigma_b','sigma_gt','flat_sigma_a','flat_sigma_b','flipped_fraction_identifiable','harmful_flip_fraction_identifiable','helpful_flip_fraction_identifiable','saturated_fraction']},'no_mean_recovers_global_loss':sum(r['no_mean_psnr']>r['global_psnr'] for r in selected),'no_mean_beats_guided':sum(r['no_mean_psnr']>r['guided_psnr'] for r in selected)}
summary['worst_scenes']=sorted(rows,key=lambda r:r['global_minus_guided'])[:5]
(out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items() if k!='worst_scenes'},indent=2))
