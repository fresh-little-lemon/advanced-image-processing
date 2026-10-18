from pathlib import Path
import csv,json,math,numpy as np
import argparse
parser=argparse.ArgumentParser(description='Summarize a completed fixed procedural grid by texture and known-noise condition.')
parser.add_argument('--metrics',required=True,type=Path)
parser.add_argument('--output',required=True,type=Path,help='Fresh directory; existing output is never replaced')
args=parser.parse_args();p=args.metrics;out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
rows=list(csv.DictReader(p.open()));keys=['texture','exposure_b','noise_a_255','noise_b_255','seed'];idx={(tuple(r[k] for k in keys),r['method']):r for r in rows};result=[]
for texture in sorted({r['texture'] for r in rows}):
 for category,sel in [('clean',lambda r:float(r['noise_a_255'])==float(r['noise_b_255'])==0),('symmetric',lambda r:float(r['noise_a_255'])==float(r['noise_b_255'])>0),('asymmetric',lambda r:r['noise_a_255']!=r['noise_b_255'])]:
  group=[r for r in rows if r['texture']==texture and r['method']=='global_full' and sel(r)]
  def mean(values):
   vals=[float(v) for v in values if math.isfinite(float(v))];return float(np.mean(vals)) if vals else None
  record={'texture':texture,'category':category,'conditions':len(group),'global_psnr':mean(r['psnr_linear'] for r in group),'oracle_psnr':mean(idx[tuple(r[k] for k in keys),'oracle_full']['psnr_linear'] for r in group),'guided_psnr':mean(idx[tuple(r[k] for k in keys),'guided']['psnr_linear'] for r in group),'mean_abs_sigma_a_error':mean(abs(float(r['sigma_est_a'])-float(r['sigma_true_a'])) for r in group),'mean_abs_sigma_b_error':mean(abs(float(r['sigma_est_b'])-float(r['sigma_true_b'])) for r in group),'mean_energy_bias_a':mean(r['energy_bias_a'] for r in group),'mean_energy_bias_b':mean(r['energy_bias_b'] for r in group)}
  record['global_minus_oracle']=record['global_psnr']-record['oracle_psnr'] if record['global_psnr'] is not None and record['oracle_psnr'] is not None else None;result.append(record)
with (out/'procedural_oracle_by_texture.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=result[0]);w.writeheader();w.writerows(result)
print(json.dumps(result,indent=2))
