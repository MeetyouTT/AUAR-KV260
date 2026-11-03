#!/usr/bin/env python3
"""Verify original inputs or run the original model preparation code in the pinned Vitis AI CPU image."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'src';ADAPT=SRC/'models/adapt'
IMAGE='xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['check','fetch-lfw','quantize'])
    p.add_argument('--out',type=Path)
    p.add_argument('--lfw',type=Path,help='directory containing lfw_funneled and official pair files')
    p.add_argument('--python-deps',type=Path,help='optional compatible ONNX/Python packages to mount at /deps')
    p.add_argument('--kind',choices=['yunet','sface','both'],default='both')
    a=p.parse_args()
    models=json.loads((SRC/'config/model_manifest.json').read_text())['models']
    checked={}
    for m in models:
        if m.get('sha256') and m.get('path'):
            q=SRC/m['path']
            if not q.is_file() or sha(q)!=m['sha256']:raise ValueError('Reference model mismatch: '+m['id'])
            checked[m['id']]=m['sha256']
    if len(checked)!=2:raise ValueError('Expected both original vision inputs')
    if a.action=='check':
        print(json.dumps({'status':'PASS','original_models':checked,'inference_executed':False}));return
    if a.out is None:p.error('--out is required')
    out=a.out.resolve()
    if out==ROOT or ROOT in out.parents or out.exists():p.error('select a fresh external output directory')
    if a.action=='fetch-lfw':
        subprocess.run([sys.executable,'-B',str(ADAPT/'fetch_public_faces.py'),str(out)],check=True);return
    if not a.lfw or not all((a.lfw/n).exists() for n in ('lfw_funneled','pairsDevTrain.txt','pairsDevTest.txt')):p.error('--lfw requires the prepared public LFW split')
    out.mkdir(parents=True)
    shutil.copyfile(str(SRC/'models/calibration/arch.json'),str(out/'arch.json'))
    identity=json.loads((ROOT/'build/env.json').read_text())['vitis_ai_image_id']
    found=subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',IMAGE],text=True).strip()
    if found!=identity:raise ValueError('Vitis AI image ID differs from env.json')
    cmd=['docker','run','--rm','--network','none','--cpus','4','--memory','8g','--pids-limit','512','--cap-drop','ALL','--security-opt','no-new-privileges','--user',str(os.getuid())+':'+str(os.getgid()),'-w','/work','-e','PYTHONPATH=/deps:/source:/aura','-e','TORCH_EXTENSIONS_DIR=/work/torch-extensions']
    mounts=[(ADAPT,'/source','ro'),(SRC,'/aura','ro'),(SRC/'models/vision','/models','ro'),(out,'/work','rw'),(a.lfw.resolve(),'/data/lfw','ro')]
    if a.python_deps:mounts.append((a.python_deps.resolve(),'/deps','ro'))
    for host,guest,mode in mounts:cmd+=['-v',str(host)+':'+guest+':'+mode]
    cmd+=['--entrypoint','/bin/bash',IMAGE,'-c','source /opt/vitis_ai/conda/etc/profile.d/conda.sh && conda activate vitis-ai-pytorch && exec python -B "$@"','model-preparation']
    steps=[]
    def run(name,args):
        with (out/(name+'.log')).open('xb') as f:r=subprocess.run(cmd+args,stdout=f,stderr=subprocess.STDOUT)
        steps.append({'name':name,'argv':args,'exit_code':r.returncode})
        (out/'steps.json').write_text(json.dumps(steps,indent=2))
        if r.returncode:raise RuntimeError(name+' failed; see external log')
    if a.kind in ('sface','both'):
        run('prepare_faces',['/source/prepare_public_faces.py'])
        for mode in ('calib','test'):run('sface_'+mode,['/source/quantize_sface_public.py','--mode',mode])
        run('sface_export',['/source/export_sface_batch_one.py'])
        run('sface_compile',['/source/compile_candidate.py','sface'])
    if a.kind in ('yunet','both'):
        for mode in ('calib','test'):run('yunet_'+mode,['/source/quantize_yunet.py','--mode',mode])
        run('yunet_compile',['/source/compile_candidate.py','yunet'])
    products={p.name:sha(p) for p in sorted(out.glob('*-compiled/*.xmodel'))}
    if len(products)!=(2 if a.kind=='both' else 1):raise ValueError('compiled model output missing')
    (out/'models_result.json').write_text(json.dumps({'status':'PASS','files':products,'board_verified':False},indent=2))
if __name__=='__main__':main()

