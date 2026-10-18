#!/usr/bin/env python3
"""Deterministic Python-reference versus C++ estimator parity (not full fusion)."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# The four reference files are preserved original source, not rewritten or mocked.
from reference.crossfit_floor import estimate_crossfit


def cases():
    rng = np.random.default_rng(20261018)
    for h, w in [(12,12),(18,18),(26,26),(34,34),(35,50),(48,48),(63,65),(64,80),(96,96),(128,160),(192,192)]:
        a=rng.uniform(.15,.85,(h,w,3));b=rng.uniform(.15,.85,(h,w,3))
        yield f'uniform_{h}x{w}',a,b
        yield f'constant_{h}x{w}',np.full((h,w,3),.4),np.full((h,w,3),.6)
    for seed in range(16):
        rng=np.random.default_rng(seed)
        a=np.clip(.45+rng.normal(0,(seed%4)/255,(96,96,3)),0,1)
        b=np.clip(.45+rng.normal(0,(5+seed%4)/255,(96,96,3)),0,1)
        yield f'awgn_{seed}',a,b
    rng=np.random.default_rng(301)
    a=rng.uniform(.1,.9,(96,112,3));b=rng.uniform(.1,.9,(96,112,3))
    yield 'sources_original',a,b
    yield 'sources_swapped',b,a
    yield 'affine_original',a,b
    yield 'affine_half_plus_point_two',.5*a+.2,.5*b+.2
    for name, mutate in [
        ('all_zero', lambda x:x.fill(0)),
        ('all_one', lambda x:x.fill(1)),
        ('one_zero_channel', lambda x:x.__setitem__((slice(None),slice(None),1),0)),
        ('one_one_channel', lambda x:x.__setitem__((slice(None),slice(None),2),1)),
        ('single_hole',lambda x:x.__setitem__((35,43,1),0)),
        ('one_saturated_block',lambda x:x.__setitem__((slice(30,38),slice(30,38),0),1)),
        ('border_zero',lambda x:x.__setitem__((0,slice(None),0),0)),
        ('last_row_one',lambda x:x.__setitem__((-1,slice(None),2),1)),
        ('stripe_zero',lambda x:x.__setitem__((slice(None),50,0),0)),
    ]:
        c=a.copy();mutate(c);yield name,c,b
    for brightness in [.01,.45,.995]:
        c=np.clip(brightness+rng.normal(0,5/255,a.shape),0,1)
        d=np.clip(brightness+rng.normal(0,5/255,b.shape),0,1)
        yield f'clipped_awgn_{brightness}',c,d
    # Exact binary fractions generate real ties, unlike approximate trig patterns.
    yy,xx=np.indices((96,112));p=(yy%2)*(xx%2)/16+.375
    pattern=np.repeat(p[...,None],3,axis=-1)
    yield 'stable_ties_checker',pattern,pattern[::-1].copy()
    yield 'stable_ties_blocks',np.tile(pattern[:8,:8],(12,14,1)),a
    tied=np.full((96,112,3),.5)
    ordinal=0
    for i in range(2,96-9,8):
        for j in range(2,112-9,8):
            if i<4 or j<4 or i+7>=92 or j+7>=108: continue
            ordinal+=1
            amplitude=(1+ordinal%17)/128
            for u in range(4):
                for v in range(4):
                    if (u+v)%2==1:
                        tied[i+2*u+1,j+2*v+1,:]+=(1 if u%2 else -1)*amplitude
    # Fold-0 train MAD is exactly zero for every block; test dispersion varies.
    # Thus its result detects a nonstable tie order even when counts match.
    yield 'stable_ties_varying_heldout',tied,tied[:,::-1].copy()
    yield 'near_zero',np.full_like(a,np.nextafter(0.,1.)),b
    yield 'near_one',np.full_like(a,np.nextafter(1.,0.)),b


def run(executable, a, b, path):
    a=np.ascontiguousarray(a,dtype='<f8');b=np.ascontiguousarray(b,dtype='<f8')
    path.write_bytes(b'CFITF64\0'+struct.pack('<QQ',*a.shape[:2])+a.tobytes()+b.tobytes())
    raw=subprocess.run([str(executable),str(path)],capture_output=True,text=True,check=True)
    return json.loads(raw.stdout)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--executable',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();rows=[];all_ok=True;max_sigma=0.;max_fold=0.;actual={}
    with tempfile.TemporaryDirectory() as tmp:
        fixture=Path(tmp)/'case.bin'
        for name,a,b in cases():
            sigmas,info=estimate_crossfit(a,b);cpp=run(args.executable.resolve(),a,b,fixture);actual[name]=cpp
            sigma_error=float(np.max(np.abs(np.array(cpp['sigmas'])-sigmas)))
            fold_error=float(np.max(np.abs(np.array(cpp['fold_variances'])-info['fold_variances']))) if info['available'] else 0.
            checks={k:cpp[k]==info[k] for k in ['eligible_blocks','selected_blocks_per_source_per_fold','available','valid_pixel_fraction']}
            checks['sigmas_close']=bool(np.allclose(cpp['sigmas'],sigmas,rtol=1e-12,atol=2e-14))
            checks['fold_variances_close']=bool(np.allclose(cpp['fold_variances'],info['fold_variances'],rtol=1e-12,atol=2e-14))
            ok=all(checks.values());all_ok &= ok;max_sigma=max(max_sigma,sigma_error);max_fold=max(max_fold,fold_error)
            rows.append({'name':name,'shape':list(a.shape),'passed':ok,'checks':checks,'max_sigma_abs_error':sigma_error,'max_fold_variance_abs_error':fold_error,'python':dict(sigmas=list(sigmas),**info),'cpp':cpp})
            if not ok: print('FAILED:',name,checks,file=sys.stderr)
    invariants={
        'source_swap':actual['sources_original']['sigmas']==actual['sources_swapped']['sigmas'][::-1],
        'affine_half':bool(np.allclose(actual['affine_half_plus_point_two']['sigmas'],.5*np.array(actual['affine_original']['sigmas']),rtol=1e-12,atol=2e-14)),
    }
    references={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'reference').glob('*.py'))}
    result={'scope':'crossfit noise estimator only; reconstructed 2026-10-18','total_cases':len(rows),'passed_cases':sum(x['passed'] for x in rows),'max_sigma_abs_error':max_sigma,'max_fold_variance_abs_error':max_fold,'tolerances':{'rtol':1e-12,'atol':2e-14},'invariants':invariants,'reference_sha256':references,'cases':rows,'passed':bool(all_ok and all(invariants.values()))}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['total_cases','passed_cases','max_sigma_abs_error','max_fold_variance_abs_error','invariants','passed']}))
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
