"""Linux per-child wait4 peak RSS. Includes input buffers and executable overhead."""
import os,sys,json,struct,subprocess,tempfile,hashlib
from pathlib import Path
import numpy as np
p=Path(__file__).resolve().parents[1];exe=p/'build/crossfit_cli';rows=[]
for h,w in [(480,640),(720,1280),(1080,1920)]:
 with tempfile.TemporaryDirectory() as d:
  f=Path(d)/'input.bin';rng=np.random.default_rng(20261018)
  with f.open('wb') as s:
   s.write(b'CFITF64\0'+struct.pack('<QQ',h,w))
   for _ in range(2):s.write(rng.uniform(.15,.85,(h,w,3)).astype('<f8').tobytes())
  with open(Path(d)/'output.json','wb') as out:
   child=subprocess.Popen([str(exe),str(f)],stdout=out,stderr=subprocess.PIPE)
   pid,status,usage=os.wait4(child.pid,0);child.returncode=os.waitstatus_to_exitcode(status)
   assert child.returncode==0, child.stderr.read()
  rows.append({'width':w,'height':h,'max_rss_kib':usage.ru_maxrss,'output':json.loads((Path(d)/'output.json').read_text())})
report={'scope':'whole Linux CLI process peak RSS incl two RGB64 buffers, estimator temporaries, runtime and IO; not estimator-only incremental memory','method':'os.wait4 per child; Linux ru_maxrss KiB','seed':20261018,'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'cases':rows}
target=p/'results_root_recheck/peak_rss.json';target.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
