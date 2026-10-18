#!/usr/bin/env python3
"""Malformed fixture inputs must fail safely with a nonzero exit."""
import argparse,json,struct,subprocess,tempfile
from pathlib import Path
import numpy as np
parser=argparse.ArgumentParser();parser.add_argument('--executable',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
header=b'CFITF64\0'+struct.pack('<QQ',12,12)
a=np.full((12,12,3),.4,dtype='<f8');valid=header+a.tobytes()*2
bad=a.copy();bad[0,0,0]=float('nan')
cases={'empty_file':b'','short_header':b'CFITF64\0','wrong_magic':b'BADMAGIC'+valid[8:],'truncated_payload':valid[:-1],'trailing_payload':valid+b'X','too_small_height':b'CFITF64\0'+struct.pack('<QQ',11,12),'zero_width':b'CFITF64\0'+struct.pack('<QQ',12,0),'oversized_dimensions':b'CFITF64\0'+struct.pack('<QQ',100000,100000),'nan_value':header+bad.tobytes()+a.tobytes()}
rows=[]
with tempfile.TemporaryDirectory() as tmp:
 for name,body in cases.items():
  p=Path(tmp)/'input.bin';p.write_bytes(body);r=subprocess.run([str(args.executable.resolve()),str(p)],capture_output=True,text=True)
  rows.append({'name':name,'passed':r.returncode==2 and bool(r.stderr.strip()),'exit_code':r.returncode,'stderr':r.stderr.strip()})
 r=subprocess.run([str(args.executable.resolve())],capture_output=True,text=True);rows.append({'name':'missing_argument','passed':r.returncode==2,'exit_code':r.returncode,'stderr':r.stderr.strip()})
result={'suite':'malformed_cli_fixtures','total':len(rows),'failed':sum(not r['passed'] for r in rows),'tests':rows}
args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['total','failed']}));raise SystemExit(bool(result['failed']))
