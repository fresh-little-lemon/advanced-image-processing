#!/usr/bin/env python3
"""Audit paired gains, failure cases, noise error and fixed demo selections."""
import argparse,csv,json
from pathlib import Path
import numpy as np

def paired(rows,method,baseline,key):
 index={(tuple(row[k] for k in key),row['method']):row for row in rows}
 changes=[]
 for (condition,m),row in index.items():
  if m!=method or (condition,baseline) not in index:continue
  other=index[condition,baseline]
  changes.append({'condition':dict(zip(key,condition)),'psnr_change':float(row['psnr_linear_rgb'])-float(other['psnr_linear_rgb']),'mae_change':float(row['mae_linear_rgb'])-float(other['mae_linear_rgb'])})
 return {'n':len(changes),'wins':sum(c['psnr_change']>1e-8 for c in changes),'losses':sum(c['psnr_change']< -1e-8 for c in changes),
         'ties':sum(abs(c['psnr_change'])<=1e-8 for c in changes),'mean_psnr_change':float(np.mean([c['psnr_change'] for c in changes])),
         'mean_mae_change':float(np.mean([c['mae_change'] for c in changes])),
         'worst':min(changes,key=lambda c:c['psnr_change']),'best':max(changes,key=lambda c:c['psnr_change'])}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True,type=Path);args=p.parse_args();root=args.root
 report={}
 for name,key in [('run',['texture','sharp_a_fraction','brightness','noise_a_255','noise_b_255','seed']),('validation',['scene_id','noise_a_255','noise_b_255','seed'])]:
  rows=list(csv.DictReader((root/name/'metrics.csv').open()));part={}
  groups=sorted(set(r['brightness'] for r in rows)) if name=='run' else ['0_0','0_5','5_0']
  for group in groups:
   selected=[r for r in rows if (r['brightness']==group if name=='run' else r['noise_a_255']+'_'+r['noise_b_255']==group)]
   part[group]={}
   for method in ('independent_residual','residual_full'):
    part[group][method]={baseline:paired(selected,method,baseline,key) for baseline in ('guided','gff_continuous_shared_gray','shared_delta','no_mean')}
  report[name]=part
 (root/'paired_analysis.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
