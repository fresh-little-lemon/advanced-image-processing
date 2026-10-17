#!/usr/bin/env python3
import csv,json,math,statistics
from pathlib import Path
p=Path('results');r=list(csv.DictReader(open(p/'phase2_procedural/metrics.csv')))
def finite_mean(values):
 values=[float(x) for x in values if math.isfinite(float(x))]
 return statistics.mean(values) if values else None
summary={}
for name,select in {'clean_nonconstant':lambda r:r['texture']!='constant' and int(r['noise_a_255'])==int(r['noise_b_255'])==0,'symmetric_noise':lambda r:int(r['noise_a_255'])==int(r['noise_b_255'])>0,'asymmetric_noise':lambda r:int(r['noise_a_255'])!=int(r['noise_b_255'])}.items():
 subset=[x for x in r if select(x)];summary[name]={}
 for m in sorted({x['method'] for x in subset}):
  group=[x for x in subset if x['method']==m]
  summary[name][m]={k:finite_mean(x[k] for x in group) for k in ['psnr_linear','raw_brier','raw_ece','raw_accuracy','smooth_brier','smooth_ece','smooth_accuracy','energy_bias_a','energy_bias_b','sigma_est_a','sigma_est_b','fallback']}
  summary[name][m]['conditions']=len(group)
summary['notes']=['All values from development procedural/validation data. Holdouts unopened.','Each condition is texture, exposure, noise-pair, seed; repeated conditions share base texture.','Constant clean target has infinite PSNR, excluded from clean_nonconstant aggregate.','Brier/ECE use known sharp-source labels only on identifiable interiors, with clipped support and source boundary excluded.','Guided raw score is its final guided mask; energy raw and smoothed scores are reported separately.','Sigma modes describe pre-clipping luma covariance; exposed/clipped source pixels excluded from diagnostic supports.']
(p/'phase2_summary.json').write_text(json.dumps(summary,indent=2))
