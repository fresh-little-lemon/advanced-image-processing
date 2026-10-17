#!/usr/bin/env python3
"""Phase2 clean validation only: decoded-sRGB linear working domain."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import argparse,csv,hashlib,json
from pathlib import Path
from dataclasses import asdict
import numpy as np
from reliable_focus import Config,fuse
from reliable_focus.core import decode_srgb
from reliable_focus.io import read_rgb
from reliable_focus.diagnostic import energy_fuse,DiagnosticConfig,valid_support
from reliable_focus.metrics import psnr
p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--data-root',type=Path,required=True);p.add_argument('--zero-limit-only',action='store_true');p.add_argument('--output',type=Path,default=Path('results/phase2_validation'));args=p.parse_args()
scenes=json.loads(args.manifest.read_text())
if len(scenes)!=26 or any(s.get('split') not in {'validation','val'} for s in scenes):raise ValueError('Phase2 runner restricted to the frozen 26-scene validation manifest')
configs={'global_full':DiagnosticConfig(),'flat_full':DiagnosticConfig(sigma_mode='estimated_flat'),'flat_fallback':DiagnosticConfig(sigma_mode='estimated_flat',fallback_quantization=True),'global_no_mean':DiagnosticConfig(subtract_mean=False),'global_no_variance':DiagnosticConfig(normalize_variance=False),'zero':DiagnosticConfig(sigma_mode='zero')}
if args.zero_limit_only:configs={'global_limit':DiagnosticConfig(epsilon_variance=0),'flat_limit':DiagnosticConfig(sigma_mode='estimated_flat',epsilon_variance=0),'zero_limit':DiagnosticConfig(sigma_mode='zero',epsilon_variance=0)}
args.output.mkdir(parents=True,exist_ok=True)
protocol={'manifest_sha256':hashlib.sha256(args.manifest.read_bytes()).hexdigest(),'domain':'sRGB code values decoded to linear; nominal source exposure unchanged','sigma_zero':'assumes zero residual noise as diagnostic, not verified camera-noise ground truth','configs':{k:asdict(v) for k,v in configs.items()},'status':'running'}
(args.output/'protocol.json').write_text(json.dumps(protocol,indent=2));rows=[]
for scene in scenes:
 images={}
 for file in scene['files']:
  path=args.data_root/file['path']
  if hashlib.sha256(path.read_bytes()).hexdigest()!=file['sha256']:raise ValueError('Hash mismatch')
  images[file['role']]=decode_srgb(read_rgb(path,profile_policy='encoded_ignore'))
 a,b,gt=images['A'],images['B'],images['GT'];valid=valid_support(a,b)
 for method,cfg in [('guided',None),*configs.items()]:
  if cfg is None:f=fuse(a,b,Config(method='guided'));details={'sigmas':[float('nan')]*2,'fallback':False,'estimator':[{'coverage':0},{'coverage':0}]}
  else:f,_,details=energy_fuse(a,b,cfg,valid=valid)
  rows.append({'scene_id':scene['scene_id'],'method':method,'psnr_linear':psnr(gt,f),'mae_linear':float(np.mean(abs(gt-f))),'sigma_a':details['sigmas'][0],'sigma_b':details['sigmas'][1],'coverage_a':details['estimator'][0]['coverage'],'coverage_b':details['estimator'][1]['coverage'],'fallback':int(details['fallback'])})
 print(scene['scene_id'],flush=True)
with (args.output/'metrics.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
summary={m:float(np.mean([r['psnr_linear'] for r in rows if r['method']==m])) for m in ['guided',*configs]}
(args.output/'summary.json').write_text(json.dumps(summary,indent=2));protocol['status']='complete';protocol['rows']=len(rows);(args.output/'protocol.json').write_text(json.dumps(protocol,indent=2));print(json.dumps(summary,indent=2))
