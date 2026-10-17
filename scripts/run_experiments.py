#!/usr/bin/env python3
"""Fixed exploration cohort. Never downloads/uploads datasets or selects winners."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import argparse,csv,hashlib,json,platform,resource,time
from pathlib import Path
from dataclasses import asdict
import numpy as np
import scipy
from scipy.ndimage import gaussian_filter
from reliable_focus import Config,fuse
from reliable_focus.io import read_rgb,write_rgb
from reliable_focus.metrics import diagnostics,psnr

def main():
    p=argparse.ArgumentParser();p.add_argument('--pilot-root',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('results/exploration_v1'))
    p.add_argument('--visuals',type=Path,default=Path('private_results/exploration_v1'))
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True);args.visuals.mkdir(parents=True,exist_ok=True)
    configs={m:Config(method=m) for m in ['average','laplacian','sml','guided','experimental']}
    configs.update({'exp_no_noise':Config(method='experimental',noise_correction=False),'exp_no_exposure':Config(method='experimental',exposure_normalization=False),'exp_no_confidence':Config(method='experimental',confidence_weighting=False)})
    (args.output/'configs.json').write_text(json.dumps({k:asdict(v) for k,v in configs.items()},indent=2))
    manifest=[];rows=[];synthetic=[]
    ed=json.loads((args.pilot_root/'edmf_manifest.json').read_text())
    cohorts=[('Lytro',range(1,21),'data','lytro-{id:02d}-{side}.jpg'),('EDMF',ed['ids'],'edmf_data','bg-{side}-{id}.jpg')]
    for dataset,ids,folder,pattern in cohorts:
        expected=json.loads((args.pilot_root/('manifest.json' if dataset=='Lytro' else 'edmf_manifest.json')).read_text())
        if isinstance(expected,dict):expected=expected['files']
        hashes={x['name']:x['sha256'] for x in expected}
        for i in ids:
            paths=[args.pilot_root/folder/pattern.format(id=i,side=s) for s in 'AB']
            for path in paths:
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                if digest!=hashes[path.name]:raise ValueError(f'Hash mismatch: {path}')
                manifest.append({'dataset':dataset,'scene':i,'filename':path.name,'sha256':digest,'split':'previously_used_exploration'})
            a,b=[read_rgb(path,profile_policy="encoded_ignore") for path in paths]
            for method,cfg in configs.items():
                start=time.perf_counter();f=fuse(a,b,cfg);elapsed=time.perf_counter()-start
                row={'dataset':dataset,'scene':i,'method':method,'height':a.shape[0],'width':a.shape[1],'fusion_seconds':elapsed,**diagnostics(a,b,f)};rows.append(row)
                # Keep all experimental outputs private, including failures.
                if method in ['guided','experimental']:write_rgb(args.visuals/f'{dataset}_{i}_{method}.png',f)
            print(f'{dataset} {i} done',flush=True)
    # Fully procedural GT, not a false all-in-focus reference from real sources.
    size=192;yy,xx=np.mgrid[:size,:size];rng=np.random.default_rng(20261017)
    texture=.45+.16*np.sin(xx*.31)+.12*np.cos(yy*.23)+.06*rng.normal(size=(size,size))
    gt=np.clip(np.stack([texture,texture*.85+.07,texture*.65+.14],axis=-1),.03,.97)
    blurred=gaussian_filter(gt,(2.0,2.0,0),mode='reflect')
    mask=xx<size//2
    clean_a=np.where(mask[...,None],gt,blurred);clean_b=np.where(mask[...,None],blurred,gt)
    for exposure in [1.,.7,1.3]:
      for sigma in [0.,.01,.03]:
       for seed in [11,23,47]:
        rng=np.random.default_rng(seed)
        a=np.clip(clean_a+rng.normal(0,sigma,gt.shape),0,1)
        b=np.clip(exposure*clean_b+rng.normal(0,sigma,gt.shape),0,1)
        for method,cfg in configs.items():
            start=time.perf_counter();f=fuse(a,b,cfg);elapsed=time.perf_counter()-start
            synthetic.append({'exposure_b':exposure,'sigma':sigma,'seed':seed,'method':method,'psnr_to_canonical_gt':psnr(gt,f),'boundary_mae':float(np.mean(abs(gt[:,size//2-4:size//2+4]-f[:,size//2-4:size//2+4]))),'fusion_seconds':elapsed,**diagnostics(a,b,f)})
            if seed==11 and method in ['guided','experimental']:write_rgb(args.visuals/f'synthetic_e{exposure}_n{sigma}_{method}.png',f)
    for name,data in [('real_metrics.csv',rows),('synthetic_metrics.csv',synthetic)]:
        with (args.output/name).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=data[0].keys());writer.writeheader();writer.writerows(data)
    (args.output/'data_manifest.json').write_text(json.dumps(manifest,indent=2))
    meta={'platform':platform.platform(),'machine':platform.machine(),'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'logical_cpus':os.cpu_count(),'thread_limit':1,'peak_process_rss_kib_linux':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'timing':'single cold-ish call per scene; excludes decode and metric computation; not benchmark-quality steady-state','cpu_info':Path('/proc/cpuinfo').read_text().split('model name')[1].split('\n')[0].strip(':\t ') if Path('/proc/cpuinfo').exists() else 'unavailable','profile_policy':'encoded_ignore: benchmark evaluates stored RGB codes, ignores embedded ICC to match historical pilot; not colorimetric comparison','synthetic_seed':20261017,'synthetic_notes':'Procedural GT. Exposure changes source B only; PSNR to canonical GT penalizes brightness changes. No exposure restoration in any method.'}
    (args.output/'environment.json').write_text(json.dumps(meta,indent=2))
    summary={}
    for dataset in ['Lytro','EDMF']:
        summary[dataset]={m:float(np.mean([r['q_local'] for r in rows if r['dataset']==dataset and r['method']==m])) for m in configs}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
