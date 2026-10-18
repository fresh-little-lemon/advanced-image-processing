import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import sys,json,csv,time,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
repo=Path(__file__).resolve().parents[1];R=Path(os.environ.get('FUSION_COMPARISON_ROOT',str(repo)));sys.path[:0]=[str(repo),str(repo/'src'),str(repo/'scripts')]
from reliable_focus.core import decode_srgb,encode_srgb
from reliable_focus.io import read_rgb
from reliable_focus.metrics import psnr
from probe_residual_floor import run_method
from probe_crossfit_floor import run

out=R/'deliverables';out.mkdir(exist_ok=True)
rows=[]
for path,ms in [(repo/'results/residual_floor_20261018/validation/metrics.csv',['guided','gff_continuous_shared_gray','shared_delta']),(repo/'results/residual_floor_20261018/crossfit/validation_metrics.csv',['crossfit_residual_mean'])]:
 with path.open() as f:
  rows += [x for x in csv.DictReader(f) if x['method'] in ms]
summary=[]
for na,nb in [(0,0),(0,5),(5,0)]:
 for m in ['guided','gff_continuous_shared_gray','shared_delta','crossfit_residual_mean']:
  rs=[x for x in rows if int(x['noise_a_255'])==na and int(x['noise_b_255'])==nb and x['method']==m]
  summary.append({'condition':f'{na}_{nb}','method':m,'n':len(rs),'psnr':float(np.mean([float(x['psnr_linear_rgb']) for x in rs])),'mae':float(np.mean([float(x['mae_linear_rgb']) for x in rs]))})
(out/'ranking.json').write_text(json.dumps(summary,indent=2))
# One clean example, plus largest and smallest current-vs-paper gains with B noise.
deltas=[]
for s in sorted(set(x['scene_id'] for x in rows)):
 vals={x['method']:float(x['psnr_linear_rgb']) for x in rows if x['scene_id']==s and int(x['noise_a_255'])==0 and int(x['noise_b_255'])==5}
 deltas.append((vals['crossfit_residual_mean']-vals['gff_continuous_shared_gray'],s))
deltas.sort();selected=[(deltas[-1][1],0,5,'largest_gain'),(deltas[0][1],0,5,'largest_loss'),(deltas[len(deltas)//2][1],0,0,'clean_example')]
scenes={s['scene_id']:s for s in json.loads((repo/'data/manifests/validation_v1.json').read_text())}
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
newrows=[]
for sid,na,nb,tag in selected:
 ims={}
 for f in scenes[sid]['files']:
  p=R/'data'/f['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'];ims[f['role']]=decode_srgb(read_rgb(p,profile_policy='encoded_ignore'))
 rng=np.random.default_rng(11);a=np.clip(ims['A']+rng.normal(0,na/255,ims['A'].shape),0,1);b=np.clip(ims['B']+rng.normal(0,nb/255,ims['B'].shape),0,1);gt=ims['GT']
 g=run_method(a,b,'gff_continuous_shared_gray',(0,0))[0];ours=run(a,b,'crossfit_residual_mean',1)[0]
 # choose ROI by largest difference between algorithm error maps, explicitly labelled.
 err=np.mean(abs(g-gt)-abs(ours-gt),axis=2);from scipy.ndimage import uniform_filter
 roi_score=uniform_filter(abs(err),size=80);h,w=err.shape;y,x=np.unravel_index(np.argmax(roi_score[40:h-40,40:w-40]),(h-80,w-80));y+=40;x+=40;box=(max(0,x-45),max(0,y-45),min(w,x+45),min(h,y+45))
 arrays=[a,b,gt,g,ours];labels=['Input A','Input B','Reference GT','GFF paper baseline*','Current crossfit method']
 panel=Image.new('RGB',(5*330,510),(246,247,250));d=ImageDraw.Draw(panel)
 d.text((12,8),f'{sid} | {tag} | added RGB noise A={na}/255 B={nb}/255 in linear domain',font=font,fill='black')
 for i,(arr,label) in enumerate(zip(arrays,labels)):
  im=Image.fromarray(np.uint8(np.clip(encode_srgb(arr),0,1)*255+.5)); thumb=im.copy();thumb.thumbnail((320,225));px=i*330+5;d.text((px,40),label,font=font,fill='black');panel.paste(thumb,(px,70))
  crop=im.crop(box).resize((170,170));panel.paste(crop,(px,325))
  if i>=3:
   score=float(psnr(gt,arr));ss=float(np.mean(abs(gt-arr)));d.text((px,300),f'PSNR {score:.3f} | MAE {ss:.4f}',font=font,fill='black');newrows.append({'scene':sid,'condition':f'{na}_{nb}','method':label,'psnr':score,'mae_linear_rgb':ss})
 panel.save(out/f'{tag}_{sid}.png');print(sid,'DONE',flush=True)
(out/'new_demo_metrics.json').write_text(json.dumps(newrows,indent=2));(out/'selected.json').write_text(json.dumps({'selection':selected,'delta_ranking':deltas,'roi':'largest absolute smoothed error difference between algorithms; identical crop across panels'},indent=2))
print(json.dumps(summary,indent=2))
