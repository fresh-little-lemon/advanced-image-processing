"""Prepare identical uint8 inputs for unmodified author GFF and Python candidates."""
from pathlib import Path
import json,sys,hashlib
import numpy as np
from PIL import Image
p=Path(__file__).resolve().parent;r=Path('/workspace/shared/fusion_comparison_20261018/repo');sys.path.insert(0,str(r/'src'))
from reliable_focus.core import decode_srgb,encode_srgb
from reliable_focus.io import read_rgb
out=p/'pilot';(out/'inputs').mkdir(parents=True,exist_ok=True);(out/'outputs').mkdir(exist_ok=True)
scenes=json.loads((r/'data/manifests/validation_v1.json').read_text());cases=[]
for scene in scenes:
 ims={}
 for f in scene['files']:
  path=Path('/workspace/shared/fusion_comparison_20261018/data')/f['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==f['sha256'];ims[f['role']]=decode_srgb(read_rgb(path,profile_policy='encoded_ignore'))
 for na,nb in [(0,0),(0,5),(5,0)]:
  rng=np.random.default_rng(11);a=np.clip(ims['A']+rng.normal(0,na/255,ims['A'].shape),0,1);b=np.clip(ims['B']+rng.normal(0,nb/255,ims['B'].shape),0,1)
  id=f"{scene['scene_id']}_n{na}_{nb}_s11"
  paths=[]
  for role,x in [('A',a),('B',b)]:
   name=out/'inputs'/f'{id}_{role}.png';Image.fromarray(np.uint8(np.floor(np.clip(encode_srgb(x),0,1)*255+.5))).save(name);paths.append(name)
  cases.append({'id':id,'scene_id':scene['scene_id'],'noise_a_255':na,'noise_b_255':nb,'seed':11,'a':str(paths[0]),'b':str(paths[1]),'gt':str(Path('/workspace/shared/fusion_comparison_20261018/data')/next(f['path'] for f in scene['files'] if f['role']=='GT')),'input_sha256':[hashlib.sha256(f.read_bytes()).hexdigest() for f in paths]})
(out/'cases.json').write_text(json.dumps(cases,indent=2));(out/'cases.tsv').write_text(''.join('\t'.join([c['id'],c['a'],c['b'],str(out/'outputs'/f"{c['id']}_author.png")])+'\n' for c in cases))
(out/'protocol.json').write_text(json.dumps({'purpose':'author baseline input/runtime validation pilot; not final 3-seed ablation','cases':78,'source_scenes':26,'input':'common quantized uint8 sRGB; added noise in linear RGB before encoding; all methods consume identical pixels','seed':11,'author_defaults':{'r1':45,'eps1':.3,'r2':7,'eps2':1e-6},'state':'inputs_prepared'},indent=2))
print(len(cases))
