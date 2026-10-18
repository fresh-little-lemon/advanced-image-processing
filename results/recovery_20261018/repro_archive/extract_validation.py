import ctypes as C
import ctypes.util
import hashlib
import json
import os
from pathlib import Path

# Path-only archival adaptation; extraction and hash checks are unchanged.
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ROOT = Path(os.environ.get('FUSION_REPRO_ROOT', str(REPOSITORY_ROOT))).expanduser().resolve()
manifest = json.loads((REPOSITORY_ROOT/'data/manifests/validation_v1.json').read_text())
assert len(manifest) == 26 and all(s['split']=='validation' for s in manifest)
wanted = {f['upstream_path'].split('#',1)[1]:f for s in manifest for f in s['files']}
archive = ROOT/'MFI-WHU.rar'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == 'ec6bb595a56ca1b4a36d4ac2081cadb915a9e4718d54391d05c9dbcb419ea413'
lib = C.CDLL(ctypes.util.find_library('archive'))
for name, args, result in [
 ('archive_read_new',[],C.c_void_p),
 ('archive_read_support_filter_all',[C.c_void_p],C.c_int),
 ('archive_read_support_format_all',[C.c_void_p],C.c_int),
 ('archive_read_open_filename',[C.c_void_p,C.c_char_p,C.c_size_t],C.c_int),
 ('archive_read_next_header',[C.c_void_p,C.POINTER(C.c_void_p)],C.c_int),
 ('archive_entry_pathname',[C.c_void_p],C.c_char_p),
 ('archive_read_data',[C.c_void_p,C.c_void_p,C.c_size_t],C.c_ssize_t),
 ('archive_read_data_skip',[C.c_void_p],C.c_int),
 ('archive_read_free',[C.c_void_p],C.c_int),
 ('archive_error_string',[C.c_void_p],C.c_char_p),
]:
 fn=getattr(lib,name);fn.argtypes=args;fn.restype=result
a=lib.archive_read_new();lib.archive_read_support_filter_all(a);lib.archive_read_support_format_all(a)
assert lib.archive_read_open_filename(a,str(archive).encode(),10240)==0
entry=C.c_void_p(); restored=[]
while True:
 status=lib.archive_read_next_header(a,C.byref(entry))
 if status==1: break
 if status<0: raise RuntimeError(lib.archive_error_string(a))
 name=lib.archive_entry_pathname(entry).decode().replace('\\','/')
 if name not in wanted:
  lib.archive_read_data_skip(a);continue
 f=wanted[name];p=ROOT/'data'/f['path'];p.parent.mkdir(parents=True,exist_ok=True)
 chunks=[];buf=C.create_string_buffer(65536)
 while True:
  n=lib.archive_read_data(a,buf,len(buf))
  if n==0: break
  if n<0: raise RuntimeError(lib.archive_error_string(a))
  chunks.append(buf.raw[:n])
 data=b''.join(chunks)
 assert hashlib.sha256(data).hexdigest()==f['sha256'],name
 p.write_bytes(data);restored.append(f['path'])
lib.archive_read_free(a)
assert len(restored)==78
(ROOT/'data_restoration.json').write_text(json.dumps({'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'restored_files':restored,'count':len(restored),'heldout_files_extracted':0},indent=2))
print('Verified and restored 78 files / 26 validation scenes; no holdout extracted.')
