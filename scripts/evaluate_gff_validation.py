"""Fixed GFF comparison, permitted 26-scene validation manifest only."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import sys,csv,json,time,hashlib,platform
from pathlib import Path
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[1]
FOUNDATION=ROOT
sys.path[:0]=[str(ROOT),str(FOUNDATION/'src')]
import numpy as np
from baselines_gff import GFFConfig,fuse_gff
from reliable_focus import Config,fuse
from reliable_focus.io import read_rgb
from reliable_focus.metrics import psnr
ALLOWED={f'WHU-{i:03d}' for i in (4,8,11,18,20,21,22,44,51,52,56,58,60,67,71,73,77,79,80,83,85,91,97,98,105,118)}
manifest=FOUNDATION/'data/manifests/validation_v1.json'
data_root=Path(os.environ.get('MULTIFOCUS_DATA_ROOT',str(ROOT.parent/'multifocus_data')))
scenes=json.loads(manifest.read_text())
assert {s['scene_id'] for s in scenes}==ALLOWED and len(scenes)==26
out=ROOT/'results/gff_validation';out.mkdir(parents=True,exist_ok=True)
configs={p:GFFConfig(profile=p) for p in ('author_aligned','continuous_shared_gray')}
config_json=json.dumps({k:asdict(v) for k,v in configs.items()},sort_keys=True,indent=2)
(out/'frozen_configs.json').write_text(config_json)
meta=dict(status='running',scene_count=26,manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
config_sha256=hashlib.sha256(config_json.encode()).hexdigest(),source_sha256=hashlib.sha256((ROOT/'baselines_gff.py').read_bytes()).hexdigest(),
threads=1,timing='single fusion call per scene, excludes decode/metrics; sequential same process',python=platform.python_version(),
author_reference_status='source inspected; MATLAB author program not executed',input_domain='encoded_RGB_0_1',evaluation_track='encoded_RGB_supplementary',metric_channels='RGB_all_channels',metric_extent='full_image_no_border_crop',metric_peak=1.0,aggregation='per_scene_metric_then_unweighted_scene_mean')
(out/'run.json').write_text(json.dumps(meta,indent=2));rows=[]
for scene in scenes:
 images={}
 for item in scene['files']:
  p=data_root/item['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
  images[item['role']]=read_rgb(p,profile_policy='encoded_ignore')
 a,b,gt=images['A'],images['B'],images['GT']
 for method in ('guided','author_aligned','continuous_shared_gray'):
  start=time.perf_counter()
  f=fuse(a,b,Config(method='guided')) if method=='guided' else fuse_gff([a,b],configs[method])
  elapsed=time.perf_counter()-start
  rows.append(dict(scene_id=scene['scene_id'],method=method,psnr=psnr(gt,f),mse=float(np.mean((gt-f)**2)),mae=float(np.mean(abs(gt-f))),fusion_seconds=elapsed))
 print(scene['scene_id'],flush=True)
with (out/'metrics.csv').open('w',newline='') as h:
 w=csv.DictWriter(h,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
summary={m:{k:float(np.mean([r[k] for r in rows if r['method']==m])) for k in ('psnr','mse','mae','fusion_seconds')} for m in ('guided',*configs)}
lookup={(r['scene_id'],r['method']):r for r in rows};rng=np.random.default_rng(1701)
for m in configs:
 delta=np.array([lookup[s['scene_id'],m]['psnr']-lookup[s['scene_id'],'guided']['psnr'] for s in scenes])
 bs=delta[rng.integers(0,26,(10000,26))].mean(1)
 summary[m]['paired_psnr_difference']=float(delta.mean());summary[m]['paired_bootstrap95']=np.quantile(bs,[.025,.975]).tolist();summary[m]['wins']=int((delta>0).sum())
(out/'summary.json').write_text(json.dumps(summary,indent=2));meta['status']='complete';(out/'run.json').write_text(json.dumps(meta,indent=2));print(json.dumps(summary,indent=2))
