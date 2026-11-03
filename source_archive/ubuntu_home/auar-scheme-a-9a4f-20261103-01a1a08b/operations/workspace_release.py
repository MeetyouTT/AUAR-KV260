from pathlib import Path
import base64, hashlib, json, os, shutil, subprocess, sys, time
REM=str(Path(__file__).resolve().parents[1]);RP=REM+'/auar_xuefei';RQ=REM+'/verification'
ROOT=Path(RP)
VIV='/home/ghmd/Xilinx_2022.2/Vivado/2022.2'
VIT='/home/ghmd/Xilinx_2022.2/Vitis/2022.2'
def put(path,data):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data.encode('utf8') if isinstance(data,str) else data)
def dump(path,v):put(path,json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def read_remote(paths):return {p:Path(p).read_bytes() for p in paths}
def remote(script,arg=None,timeout=120):
 prefix="import json,base64,os,sys,subprocess,hashlib,shutil,time\nfrom pathlib import Path\na=json.loads(base64.b64decode('"+base64.b64encode(json.dumps(arg).encode()).decode()+"'))\n"
 pr=subprocess.run([sys.executable,'-B','-'],input=prefix+script,capture_output=True,text=True,timeout=timeout)
 if pr.returncode:raise RuntimeError(pr.stderr[-1800:])
 return json.loads(pr.stdout)
