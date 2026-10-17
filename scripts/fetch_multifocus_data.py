#!/usr/bin/env python3
"""Fetch pinned public research data; no uploads. Images remain outside the repo.
Python 3 stdlib + git + libarchive (or bsdtar/7z for RAR extraction).
"""
import argparse, ctypes as C, hashlib, json, shutil, subprocess, tempfile
from pathlib import Path
WHU='6071f2909f5563ccb9bcd71317f5102eefe13e6f'
MFIF='f0f0e0725e7d82fe91aa30eb6296d8241d26e4c9'
def run(*args): subprocess.run(args,check=True)
def checkout(url,commit,where,paths):
    run('git','clone','--filter=blob:none','--no-checkout',url,str(where))
    run('git','-C',str(where),'sparse-checkout','set','--no-cone',*paths)
    run('git','-C',str(where),'checkout',commit)
    actual=subprocess.check_output(['git','-C',str(where),'rev-parse','HEAD'],text=True).strip()
    if actual!=commit: raise RuntimeError('Unexpected source commit')
def extract_rar(src,dest):
    try: l=C.CDLL('libarchive.so.13')
    except OSError:
        if shutil.which('bsdtar'): run('bsdtar','-xf',str(src),'-C',str(dest)); return
        if shutil.which('7z'): run('7z','x',str(src),'-o'+str(dest),'-y'); return
        raise RuntimeError('RAR extraction requires libarchive, bsdtar, or 7z')
    l.archive_read_new.restype=C.c_void_p
    for n in ['archive_read_support_format_all','archive_read_support_filter_all','archive_read_free']:
        getattr(l,n).argtypes=[C.c_void_p]
    l.archive_read_open_filename.argtypes=[C.c_void_p,C.c_char_p,C.c_size_t]
    l.archive_read_next_header.argtypes=[C.c_void_p,C.POINTER(C.c_void_p)]
    l.archive_entry_pathname.argtypes=[C.c_void_p];l.archive_entry_pathname.restype=C.c_char_p
    l.archive_entry_filetype.argtypes=[C.c_void_p];l.archive_entry_filetype.restype=C.c_uint
    l.archive_read_data_skip.argtypes=[C.c_void_p]
    l.archive_read_data.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t];l.archive_read_data.restype=C.c_ssize_t
    a=l.archive_read_new();l.archive_read_support_format_all(a);l.archive_read_support_filter_all(a)
    if l.archive_read_open_filename(a,str(src).encode(),10240)!=0: raise RuntimeError('Cannot open RAR')
    e=C.c_void_p();buf=C.create_string_buffer(1048576)
    try:
        while True:
            status=l.archive_read_next_header(a,C.byref(e))
            if status==1: break
            if status!=0: raise RuntimeError('RAR header error '+str(status))
            name=Path(l.archive_entry_pathname(e).decode())
            if name.is_absolute() or '..' in name.parts: raise RuntimeError('Unsafe archive path')
            p=dest/name;chunks=[]
            kind=l.archive_entry_filetype(e)
            if kind==0o040000:
                p.mkdir(parents=True,exist_ok=True);l.archive_read_data_skip(a);continue
            if kind!=0o100000: raise RuntimeError('Unsupported archive entry type')
            while True:
                n=l.archive_read_data(a,buf,len(buf))
                if n<0: raise RuntimeError('RAR read error')
                if n==0: break
                chunks.append(buf.raw[:n])
            if chunks:
                p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b''.join(chunks))
    finally: l.archive_read_free(a)
def verify(root,manifest):
    count=0
    for s in json.loads(manifest.read_text())['scenes']:
        for f in s['files']:
            p=root/f['path']
            if hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:
                raise RuntimeError('Hash mismatch: '+str(p))
            count+=1
    print('Verified',count,'image files; no benchmark was run')
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data-root',required=True,type=Path)
    ap.add_argument('--verify-only',action='store_true')
    a=ap.parse_args();root=a.data_root.expanduser().resolve()
    repo=Path(__file__).resolve().parents[1]
    if root==repo or repo in root.parents: raise SystemExit('Data root must be outside the source repository')
    manifest=repo/'data/manifests/manifest_v1.json'
    if a.verify_only: verify(root,manifest); return
    print('MFI-WHU repository is MIT; source-photo rights are not individually documented.')
    print('MFIF/MFFW image redistribution license is not established. Keep downloaded images local.')
    root.mkdir(parents=True,exist_ok=True)
    if any(root.glob('MFI-WHU/**/*')) or any(root.glob('MFFW2/**/*')):
        raise SystemExit('Target dataset exists. Use --verify-only, or choose a fresh data root; no files overwritten.')
    with tempfile.TemporaryDirectory(prefix='multifocus_fetch_') as t:
        t=Path(t)
        checkout('https://github.com/HaoZhang1018/MFI-WHU.git',WHU,t/'whu',['/MFI-WHU.rar','/LICENSE','/README.md'])
        archive=t/'whu/MFI-WHU.rar'
        expected=(repo/'data/manifests/archive_sha256.json')
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=json.loads(expected.read_text())['MFI-WHU.rar']:
            raise RuntimeError('Archive hash mismatch')
        dest=root/'MFI-WHU';dest.mkdir(exist_ok=True);extract_rar(archive,dest)
        checkout('https://github.com/xingchenzhang/MFIF.git',MFIF,t/'mfif',['/input/mffw_*','/README.md'])
        for i in range(1,14):
            dest=root/'MFFW2'/f'{i:02d}';dest.mkdir(parents=True,exist_ok=True)
            for role in ['A','B']:
                name=f'mffw_{i:02d}_{role}.jpg'
                shutil.copyfile(t/'mfif/input'/f'mffw_{i:02d}'/name,dest/name)
        meta=root/'acquisition';meta.mkdir(exist_ok=True)
        for src,name in [(t/'whu/LICENSE','MFI-WHU_LICENSE'),(t/'whu/README.md','MFI-WHU_README.md'),(t/'mfif/README.md','MFIF_README.md')]:shutil.copyfile(src,meta/name)
    verify(root,manifest)
if __name__=='__main__':main()
