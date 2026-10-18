#!/usr/bin/env python3
"""Reproduce paired summaries of residual and cross-fitted noise corrections."""
import argparse,csv,json
from pathlib import Path
import numpy as np
from analyze_residual_floor import paired


def read(path):
 return list(csv.DictReader(path.open()))


def summarize(root):
 combined={}
 for dataset,old,new,key in [('procedural','run/metrics.csv','crossfit/procedural_metrics.csv',['texture','sharp_a_fraction','brightness','noise_a_255','noise_b_255','seed']),('validation','validation/metrics.csv','crossfit/validation_metrics.csv',['scene_id','noise_a_255','noise_b_255','seed'])]:
  rows=read(root/old)+read(root/new)
  groups=[(b,g) for b in ['normal','dark','extreme_white'] for g in ['clean','equal_noise','asymmetric']] if dataset=='procedural' else [('0','0'),('0','5'),('5','0')]
  result={}
  for group in groups:
   if dataset=='procedural':selected=[r for r in rows if r['brightness']==group[0] and ('clean' if r['noise_a_255']==r['noise_b_255']=='0' else 'equal_noise' if r['noise_a_255']==r['noise_b_255'] else 'asymmetric')==group[1]]
   else:selected=[r for r in rows if (r['noise_a_255'],r['noise_b_255'])==group]
   result['_'.join(group)]={'means':{m:{k:float(np.mean([float(r[k]) for r in selected if r['method']==m])) for k in ['psnr_linear_rgb','mae_linear_rgb','seconds_pipeline']} for m in sorted({r['method'] for r in selected})},'crossfit_paired':{m:paired(selected,'crossfit_residual_mean',m,key) for m in ['guided','gff_continuous_shared_gray','shared_delta','no_mean','independent_residual']}}
  combined[dataset]=result
 (root/'combined_analysis.json').write_text(json.dumps(combined,indent=2))
 if (root/'transfer/metrics.csv').exists():
  rows=read(root/'transfer/metrics.csv');report={}
  key=['texture','brightness','sharp_a_fraction','exposure_b','noise_a_255','noise_b_255','seed']
  for brightness in ['normal','dark']:
   for exposure in ['0.7','1.3']:
    for group in ['clean','equal_noise','asymmetric']:
     selected=[r for r in rows if r['brightness']==brightness and r['exposure_b']==exposure and ('clean' if r['noise_a_255']==r['noise_b_255']=='0' else 'equal_noise' if r['noise_a_255']==r['noise_b_255'] else 'asymmetric')==group and r['texture']!='constant']
     report['_'.join([brightness,exposure,group])]={'constant_excluded_from_psnr_aggregate':True,'means':{m:{k:float(np.mean([float(r[k]) for r in selected if r['method']==m])) for k in ['psnr_linear_rgb','mae_linear_rgb']} for m in sorted({r['method'] for r in selected})},'crossfit_paired':{m:paired(selected,'crossfit_residual_mean',m,key) for m in ['guided','gff_continuous_shared_gray','shared_delta','no_mean']}}
  (root/'transfer/summary_nonconstant.json').write_text(json.dumps(report,indent=2))
 return combined


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True,type=Path);args=p.parse_args();summarize(args.root)
if __name__=='__main__':main()
