import hashlib, json, os, shutil, subprocess, sys, tarfile, zipfile
from pathlib import Path, PurePosixPath
W = Path(__file__).resolve().parent
SH = Path(r'E:\Win共享文件')
P = SH/'语音共享文件'
B = P/'deliverables/2026-11-02_5090_deployment'
CO = SH/'协作任务'
OUT = Path(r'E:\AUAR_工程交付_20261102')
ROOT = OUT/'aura'
QA = OUT/'verification'
ROOT.mkdir(parents=True,exist_ok=True)
QA.mkdir(parents=True,exist_ok=True)
def save(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def copy(a,b):
    b.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(a,b)
def ssh(script, args=()):
    return subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=7','aura-ubuntu','python3 - '+ ' '.join(args)],input=script.encode(),timeout=300).decode()
def unpack(stream, dest):
    with tarfile.open(fileobj=stream,mode='r|*') as t:
        for f in t:
            parts=PurePosixPath(f.name).parts
            if not parts or f.name.startswith('/') or any(x in ('.','..') or '\\' in x or ':' in x for x in parts):raise ValueError(f.name)
            if not f.isfile(): raise ValueError(f.name)
            q=dest.joinpath(*parts)
            q.parent.mkdir(parents=True,exist_ok=True)
            with q.open('wb') as out: shutil.copyfileobj(t.extractfile(f),out,1024*1024)
def remote_collect(src,dest):
    with subprocess.Popen(['ssh','-o','BatchMode=yes','aura-ubuntu','python3 -'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=None) as q:
        q.stdin.write(src.encode());q.stdin.close()
        unpack(q.stdout,dest)
        if q.wait()!=0:raise RuntimeError('Ubuntu transfer failed')
