#!/usr/bin/env python3
"""Numerically faithful diagnostic panels; images remain a local deliverable."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import argparse,csv,json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image,ImageDraw,ImageFont
from reliable_focus.core import Config,fuse,decode_srgb,encode_srgb
from reliable_focus.diagnostic import DiagnosticConfig,energy_fuse,valid_support
from reliable_focus.io import read_rgb
from reliable_focus.metrics import psnr
from run_phase2_diagnostics import textures
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def read_rows(path):return list(csv.DictReader(open(path)))
def to_image(linear):return Image.fromarray(np.uint8(np.floor(encode_srgb(linear)*255+.5)))
def panel(images,labels,title,subtitle,outfile):
 width=1920;cw=320;height=810
 canvas=Image.new('RGB',(width,height),'#f0f2f5');draw=ImageDraw.Draw(canvas)
 font=ImageFont.truetype(FONT,19);small=ImageFont.truetype(FONT,16);heading=ImageFont.truetype(FONT,25)
 draw.text((20,14),title,font=heading,fill='#152239');draw.text((20,50),subtitle,font=small,fill='#334155')
 draw.text((20,77),'PSNR: full-image linear RGB; display: sRGB encoding | Red box: same centered crop in every column',font=small,fill='#334155')
 h,w=images[0].shape[:2];side=max(12,min(h,w)//3);x0=w//2-side//2;y0=h//2-side//2;crop=(x0,y0,x0+side,y0+side)
 for i,(im,label) in enumerate(zip(images,labels)):
  left=i*cw;draw.text((left+10,115),label,font=font,fill='#17213a')
  full=to_image(im);scale=min((cw-16)/w,330/h);thumb=full.resize((round(w*scale),round(h*scale)),Image.Resampling.NEAREST if scale>=1 else Image.Resampling.LANCZOS)
  x=left+(cw-thumb.width)//2;y=153+(330-thumb.height)//2;canvas.paste(thumb,(x,y));sx=thumb.width/w;sy=thumb.height/h
  draw.rectangle((x+crop[0]*sx,y+crop[1]*sy,x+crop[2]*sx,y+crop[3]*sy),outline='#e84444',width=2)
  patch=full.crop(crop).resize((cw-16,cw-16),Image.Resampling.NEAREST)
  canvas.paste(patch,(left+8,493));draw.text((left+10,469),'Center crop',font=small,fill='#475569')
 canvas.save(outfile)

def outcomes(a,b,gt,valid):
 guided=fuse(a,b,Config(method='guided'))
 global_f,_,_=energy_fuse(a,b,DiagnosticConfig(),valid=valid)
 flat_f,_,_=energy_fuse(a,b,DiagnosticConfig(sigma_mode='estimated_flat'),valid=valid)
 return [guided,global_f,flat_f],{m:psnr(gt,f) for m,f in zip(['guided','global','flat'],[guided,global_f,flat_f])}

def main():
 p=argparse.ArgumentParser();p.add_argument('--data-root',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,default=Path('deliverables'));args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
 record=[];rows=read_rows('results/phase2_validation/metrics.csv');indexed={(r['scene_id'],r['method']):r for r in rows};scene_ids=sorted({r['scene_id'] for r in rows})
 deltas={s:float(indexed[s,'global_full']['psnr_linear'])-float(indexed[s,'guided']['psnr_linear']) for s in scene_ids}
 selections=[('fixed_first',scene_ids[0]),('largest_gain',max(deltas,key=deltas.get)),('largest_regression',min(deltas,key=deltas.get))]
 manifest={s['scene_id']:s for s in json.loads(args.manifest.read_text())}
 for rule,sid in selections:
  inputs={f['role']:decode_srgb(read_rgb(args.data_root/f['path'],profile_policy='encoded_ignore')) for f in manifest[sid]['files']};a,b,gt=inputs['A'],inputs['B'],inputs['GT'];outs,scores=outcomes(a,b,gt,valid_support(a,b))
  labels=['Source A','Source B',f'Guided {scores["guided"]:.2f} dB',f'Global energy {scores["global"]:.2f} dB',f'Flat patch {scores["flat"]:.2f} dB','Provided clear GT']
  outfile=args.output/f'WHU_{rule}_{sid}.png'
  panel([a,b,*outs,gt],labels,f'{sid} | validation | {rule.replace("_"," ")}',f'No added degradation; sRGB decoded to linear | global-guided = {deltas[sid]:+.3f} dB | crop fixed at image center',outfile)
  record.append({'file':outfile.name,'dataset':'MFI-WHU validation','scene_id':sid,'selection':rule,'psnr_linear':scores,'global_minus_guided_db':deltas[sid]})
 rows=read_rows('results/phase2_procedural/metrics.csv');key=lambda r:(r['texture'],r['exposure_b'],r['noise_a_255'],r['noise_b_255'],r['seed']);idx={(key(r),r['method']):r for r in rows};keys=sorted({key(r) for r in rows if r['texture']!='constant'})
 deltas={k:float(idx[k,'global_full']['psnr_linear'])-float(idx[k,'guided']['psnr_linear']) for k in keys}
 selections=[('fixed_asymmetric',('stochastic','1.0','2','10','11')),('largest_gain',max(deltas,key=deltas.get)),('largest_regression',min(deltas,key=deltas.get))]
 for rule,k in selections:
  name,e,na,nb,seed=k;e=float(e);na=int(na);nb=int(nb);seed=int(seed);gt=textures()[name];n=gt.shape[0];mask=np.indices((n,n))[1]<n//2;blur=gaussian_filter(gt,(1.5,1.5,0),mode='reflect');ca=np.where(mask[...,None],gt,blur);cb=np.where(mask[...,None],blur,gt);rng=np.random.default_rng(seed);oa=np.clip(ca+rng.normal(0,na/255,gt.shape),0,1);ob=np.clip(e*cb+rng.normal(0,nb/255,gt.shape),0,1);a=oa;b=np.clip(ob/e,0,1);outs,scores=outcomes(a,b,gt,valid_support(oa,ob)&valid_support(a,b))
  outfile=args.output/f'procedural_{rule}_{name}.png';labels=['Observed A','Observed B',f'Guided {scores["guided"]:.2f} dB',f'Global energy {scores["global"]:.2f} dB',f'Flat patch {scores["flat"]:.2f} dB','Exact clean GT']
  panel([oa,ob,*outs,gt],labels,f'Procedural {name} | {rule.replace("_"," ")}',f'Exposure B={e:g}; RGB sigma A={na}/255, B={nb}/255; seed={seed} | all methods receive the same known exposure compensation',outfile)
  record.append({'file':outfile.name,'dataset':'procedural','texture':name,'selection':rule,'exposure_b':e,'noise_a_255':na,'noise_b_255':nb,'seed':seed,'psnr_linear':scores,'global_minus_guided_db':scores['global']-scores['guided']})
  if rule=='largest_regression':
   limit,_,_=energy_fuse(a,b,DiagnosticConfig(epsilon_variance=0),valid=valid_support(oa,ob)&valid_support(a,b));limit_score=psnr(gt,limit);fixedfile=args.output/'procedural_zero_variance_fix_sine.png'
   panel([oa,ob,outs[0],outs[1],limit,gt],['Observed A','Observed B',f'Guided {scores["guided"]:.2f} dB',f'Old floor {scores["global"]:.2f} dB',f'Zero limit {limit_score:.2f} dB','Exact clean GT'],'Zero-variance limit | same largest-regression case',f'Exposure B={e:g}; RGB sigma A={na}/255, B={nb}/255; seed={seed} | same data and all parameters except denominator floor',fixedfile)
   record.append({'file':fixedfile.name,'dataset':'procedural','selection':'mechanism_fix_on_same_largest_regression','psnr_linear':{'guided':scores['guided'],'old_floor':scores['global'],'zero_limit':limit_score}})
 (args.output/'demo_manifest.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
if __name__=='__main__':main()
