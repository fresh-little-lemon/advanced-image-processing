#!/usr/bin/env python3
"""Fixed residual-ranking and estimator-separation experiment."""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse, csv, hashlib, json, platform, sys, time
from pathlib import Path
import numpy as np
REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO/'src')]
from probe_spatial_support import generate_case, run_method as old_method
from probe_shared_support import candidate
from run_phase2_diagnostics import textures
from reliable_focus.residual_floor import estimate_floor
from reliable_focus.diagnostic import energy_fuse, DiagnosticConfig, LUMA
from reliable_focus.metrics import psnr

METHODS = ['guided','gff_continuous_shared_gray','no_mean','shared_delta','spatial_gate',
           'independent_guide','shared_residual','independent_residual',
           'residual_variance_no_mean','residual_full','oracle_preclip']


def run_method(a, b, method, known):
    if method in ('guided','gff_continuous_shared_gray','no_mean','shared_delta','spatial_gate','oracle_preclip'):
        return old_method(a,b,method,known)
    sigmas, info = estimate_floor(a,b, ranking='guide' if method == 'independent_guide' else 'residual',
                                 shared=method == 'shared_residual')
    delta = sigmas[0]**2-sigmas[1]**2
    if method in ('residual_full','residual_variance_no_mean'):
        subtract = method == 'residual_full'
        result = energy_fuse(a,b,DiagnosticConfig(sigma_mode='oracle_known', subtract_mean=subtract),sigmas)[0]
        if not subtract: delta = 0.
    else:
        result = candidate(a,b,delta)
    return result,delta,info


def write_csv(path, rows):
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--protocol',required=True,type=Path)
    args=parser.parse_args();protocol=json.loads(args.protocol.read_text())
    assert protocol['methods']==METHODS
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    sourcefiles=[Path(__file__), REPO/'src/reliable_focus/residual_floor.py', REPO/'src/reliable_focus/diagnostic.py', REPO/'scripts/probe_spatial_support.py',REPO/'scripts/probe_shared_support.py']
    status={'status':'running','protocol':protocol,'protocol_sha256':hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
            'source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sourcefiles},
            'python':platform.python_version(),'numpy':np.__version__,'timing':'one full estimator+pipeline call, three warmups, shared x86 cloud CPU; not embedded timing'}
    (out/'run.json').write_text(json.dumps(status,indent=2))
    tex=textures(96);mixed=tex['stochastic'].copy();mixed[:,:48]=tex['sine'][:,:48]
    fixtures={'stochastic':tex['stochastic'],'mixed_sine_left_stochastic_right':mixed}
    warm=generate_case(tex['stochastic'],.5,'normal',0,5,11)
    for method in METHODS:
        for _ in range(3):run_method(*warm[:2],method,(0.,.01))
    rows=[];swaps=[]
    for texture_name,texture in fixtures.items():
      for fraction in protocol['sharp_a_fractions']:
       for brightness in protocol['brightness']:
        for na,nb in protocol['noise_rgb_pairs_255']:
         for seed in protocol['seeds']:
          a,b,gt=generate_case(texture,fraction,brightness,na,nb,seed)
          known=tuple(float(np.linalg.norm(LUMA)*n/255) for n in (na,nb));true=known[0]**2-known[1]**2
          context={'texture':texture_name,'sharp_a_fraction':fraction,'brightness':brightness,'noise_a_255':na,'noise_b_255':nb,'seed':seed}
          for method in METHODS:
            start=time.perf_counter();result,delta,info=run_method(a,b,method,known);elapsed=time.perf_counter()-start
            rows.append({**context,'method':method,'psnr_linear_rgb':float(psnr(gt,result)),
                         'mae_linear_rgb':float(np.mean(abs(result-gt))),'estimated_delta_sigma2':delta,
                         'true_preclip_delta_sigma2':true,'delta_absolute_error':abs(delta-true) if delta is not None else None,
                         'seconds_pipeline':elapsed,'details':json.dumps(info)})
            if method in METHODS[5:10]:
                reverse,rd,_=run_method(b,a,method,known[::-1]);error=float(np.max(abs(reverse-result)))
                assert error<1e-10 and abs(rd+delta)<1e-14
                swaps.append({**context,'method':method,'max_rgb_error':error,'delta_antisymmetry_error':abs(rd+delta)})
      print(texture_name,'complete',flush=True)
    assert len(rows)==144*len(METHODS)
    write_csv(out/'metrics.csv',rows);write_csv(out/'source_swap.csv',swaps)
    summary={}
    for brightness in protocol['brightness']:
      summary[brightness]={}
      for group in ('clean','equal_noise','asymmetric'):
        selected=[r for r in rows if r['brightness']==brightness and ('clean' if r['noise_a_255']==r['noise_b_255']==0 else 'equal_noise' if r['noise_a_255']==r['noise_b_255'] else 'asymmetric')==group]
        summary[brightness][group]={method:{key:float(np.mean([r[key] for r in selected if r['method']==method])) for key in ('psnr_linear_rgb','mae_linear_rgb','seconds_pipeline')} for method in METHODS}
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    status.update(status='complete',rows=len(rows),source_swap_cases=len(swaps),max_swap_error=max(r['max_rgb_error'] for r in swaps))
    (out/'run.json').write_text(json.dumps(status,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
