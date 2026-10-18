import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import csv,hashlib,json,sys
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter,laplace,median_filter
repo=Path(__file__).resolve().parents[1];sys.path[:0]=[str(repo),str(repo/'src')]
from reliable_focus.core import Config,fuse,gray,box,decode_srgb,noise_sigma,guided_filter
from reliable_focus.diagnostic import DiagnosticConfig,energy_fuse,valid_support,LUMA
from reliable_focus.io import read_rgb
from reliable_focus.metrics import psnr
from baselines_gff import GFFConfig,fuse_gff


def paired_delta(ya,yb,valid):
 energies=[]
 for y in [ya,yb]:
  gy,gx=np.gradient(gaussian_filter(y,1,mode='reflect'));energies.append(gx*gx+gy*gy)
 scores=np.maximum(*energies);h,w=ya.shape;choices=[]
 for i in range(2,h-9,8):
  for j in range(2,w-9,8):
   region=(slice(i,i+8),slice(j,j+8))
   if valid[region].all():choices.append((float(scores[region].mean()),i,j))
 choices.sort();selected=choices[:max(1,int(np.ceil(.2*len(choices))))]
 if len(selected)<2:return 0.,0.,{'blocks':len(selected),'alpha':0.,'bootstrap_se_delta':0.}
 hs=[y[1:,1:]-y[:-1,1:]-y[1:,:-1]+y[:-1,:-1] for y in [ya,yb]]
 vals=[np.stack([hp[i:i+8,j:j+8].ravel() for _,i,j in selected]) for hp in hs]
 def est(v):
  z=v.ravel();return (np.median(abs(z-np.median(z)))/(.6744897501960817*2))**2
 delta=float(est(vals[0])-est(vals[1]));rng=np.random.default_rng(7281);boot=[]
 for _ in range(64):
  inds=rng.integers(0,len(selected),len(selected));boot.append(est(vals[0][inds])-est(vals[1][inds]))
 variance=float(np.var(boot,ddof=1));alpha=max(0.,1-variance/delta**2) if delta else 0.
 return delta,delta*alpha,{'blocks':len(selected),'alpha':alpha,'bootstrap_se_delta':float(np.sqrt(variance))}

def candidate(a,b,delta):
 ya,yb=gray(a),gray(b);cfg=DiagnosticConfig();variances=[];energies=[]
 for y in [ya,yb]:
  response=laplace(y,mode='reflect');nu=20*noise_sigma(y)**2;energies.append(box(response**2,7));variances.append(4*box(2*nu**2+4*nu*np.maximum(response**2-nu,0),7)/49)
 gap=energies[0]-energies[1]-20*delta;denom=np.sqrt(variances[0]+variances[1]+1e-8);raw=1/(1+np.exp(-np.clip(gap/denom,-30,30)));w=guided_filter((ya+yb)/2,median_filter(raw,size=7,mode='reflect'))
 return np.clip(w[...,None]*a+(1-w[...,None])*b,0,1)

def main():
 import argparse
 parser=argparse.ArgumentParser(description='Fixed shared-support mechanism probe on the frozen 26-scene validation set.')
 parser.add_argument('--data-root',required=True,type=Path)
 parser.add_argument('--output',required=True,type=Path,help='Fresh directory; existing output is never replaced')
 args=parser.parse_args();out=args.output.resolve();root=args.data_root.resolve();out.mkdir(parents=True,exist_ok=False)
 protocol=json.loads((repo/'results/shared_support_probe_20261018/protocol.json').read_text())
 protocol['status']='running';protocol.pop('rows',None);protocol.pop('source_sha256',None)
 (out/'protocol.json').write_text(json.dumps(protocol,indent=2))
 scenes=json.loads((repo/'data/manifests/validation_v1.json').read_text());assert len(scenes)==26 and all(s['split']=='validation' for s in scenes);rows=[];diagnostics=[]
 for scene in scenes:
  im={}
  for f in scene['files']:
   p=root/f['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'];im[f['role']]=decode_srgb(read_rgb(p,profile_policy='encoded_ignore'))
  ca,cb,gt=im['A'],im['B'],im['GT']
  for condition,nb in [('original',0),('added_asymmetric_0_5',5/255)]:
   rng=np.random.default_rng(11);a=ca;b=np.clip(cb+rng.normal(0,nb,cb.shape),0,1);valid=valid_support(a,b);delta,shrunk,detail=paired_delta(gray(a),gray(b),valid)
   global_f,_,dg=energy_fuse(a,b,DiagnosticConfig(),valid=valid)
   predictions={'guided':fuse(a,b,Config(method='guided')),'global_full':global_f,'global_no_mean':energy_fuse(a,b,DiagnosticConfig(subtract_mean=False),valid=valid)[0],'flat_full':energy_fuse(a,b,DiagnosticConfig(sigma_mode='estimated_flat'),valid=valid)[0],'gff':fuse_gff([a,b],GFFConfig(profile='continuous_shared_gray')),'shared_delta':candidate(a,b,delta),'shared_delta_shrink':candidate(a,b,shrunk)}
   if nb:predictions['oracle_added_only']=energy_fuse(a,b,DiagnosticConfig(sigma_mode='oracle_known'),(0,float(np.linalg.norm(LUMA)*nb)),valid=valid)[0]
   # Algebraic regression test: zero correction must equal existing no_mean.
   np.testing.assert_allclose(candidate(a,b,0),predictions['global_no_mean'],rtol=0,atol=5e-12)
   for name,f in predictions.items():rows.append({'scene_id':scene['scene_id'],'condition':condition,'method':name,'psnr_linear_rgb':float(psnr(gt,f)),'mae_linear_rgb':float(np.mean(abs(gt-f)))})
   diagnostics.append({'scene_id':scene['scene_id'],'condition':condition,'global_delta_sigma2':dg['sigmas'][0]**2-dg['sigmas'][1]**2,'shared_delta_sigma2':delta,'shrunk_delta_sigma2':shrunk,**detail})
  print(scene['scene_id'],flush=True)
 for name,data in [('metrics.csv',rows),('estimator_diagnostics.csv',diagnostics)]:
  with (out/name).open('w') as f:w=csv.DictWriter(f,fieldnames=data[0]);w.writeheader();w.writerows(data)
 summary={}
 for cond in sorted({r['condition'] for r in rows}):
  summary[cond]={}
  for m in sorted({r['method'] for r in rows if r['condition']==cond}):
   selected=[r for r in rows if r['condition']==cond and r['method']==m];summary[cond][m]={k:float(np.mean([r[k] for r in selected])) for k in ['psnr_linear_rgb','mae_linear_rgb']}
 (out/'summary.json').write_text(json.dumps(summary,indent=2));protocol=json.loads((out/'protocol.json').read_text());protocol['status']='complete';protocol['rows']=len(rows);protocol['source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();(out/'protocol.json').write_text(json.dumps(protocol,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
