#!/usr/bin/env python3
"""Continuous two-layer GFF on same decoded linear WHU validation inputs."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import argparse,csv,json,hashlib
from pathlib import Path
import numpy as np
from baselines_gff import GFFConfig,fuse_gff
from reliable_focus.core import decode_srgb
from reliable_focus.io import read_rgb
from reliable_focus.metrics import psnr
p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--data-root',type=Path,required=True);args=p.parse_args();scenes=json.loads(args.manifest.read_text())
if len(scenes)!=26 or any(s.get('split')!='validation' for s in scenes):raise ValueError('Only frozen validation26 accepted')
rows=[]
for scene in scenes:
 images={}
 for f in scene['files']:
  path=args.data_root/f['path']
  if hashlib.sha256(path.read_bytes()).hexdigest()!=f['sha256']:raise ValueError('Hash mismatch')
  images[f['role']]=decode_srgb(read_rgb(path,profile_policy='encoded_ignore'))
 output=fuse_gff([images['A'],images['B']],GFFConfig(profile='continuous_shared_gray'))
 # API may include diagnostics if requested; default is image.
 rows.append({'scene_id':scene['scene_id'],'method':'gff_continuous_linear','psnr_linear':psnr(images['GT'],output),'mae_linear':float(np.mean(abs(images['GT']-output)))})
 print(scene['scene_id'],flush=True)
folder=Path('results/gff_linear_validation');folder.mkdir(parents=True,exist_ok=True)
with (folder/'metrics.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
summary={'profile':'continuous_shared_gray','domain':'decoded sRGB to linear, same inputs as phase2_validation','scenes':26,'mean_psnr_linear':float(np.mean([x['psnr_linear'] for x in rows])),'mean_mae_linear':float(np.mean([x['mae_linear'] for x in rows])),'scope':'Independent GFF two-layer adaptation with continuous linear-domain arithmetic; author-aligned encoded profile measured separately'}
(folder/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
