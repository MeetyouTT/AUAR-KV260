from pathlib import Path
import json,re,hashlib,subprocess
HERE=Path(__file__).resolve().parent;E=json.loads((HERE/'expected.json').read_bytes());R=Path(E['runtime']);p=R.parent/'stage.log'
if not p.exists():p=R.parent/'launch.log'
files=[R.parent/'stage.log',R/'stage.log',R.parent/'supervisor.log']
out=[]
for p in files:
 if not p.is_file():continue
 raw=p.read_bytes();lines=raw.decode(errors='replace').splitlines();frames=[]
 for line in lines[-400:]:
  m=re.search(r'File "([^\"]+)", line (\d+), in ([a-zA-Z0-9_<>]+)',line)
  if m:frames.append(dict(file=Path(m[1]).name,line=int(m[2]),function=m[3]))
 classes=['PairRejected','ClockUnavailable','RuntimeError','ValueError','ImportError','ModuleNotFoundError','AssertionError','FileNotFoundError','TypeError','AttributeError']
 errors=[k for k in classes if any(line.startswith(k+':') for line in lines[-120:])]
 markers=['sample_rtt_exceeded','fingerprint changed','formal image/persona pair','native_preparation_failed','Required Yuki','Secondary motion','Unexpected arm','four arm branches','clock','Traceback','private','Start operation timed out','READY']
 hits={k:sum(k in line for line in lines[-120:]) for k in markers}
 out.append(dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),exception_classes=errors,traceback_public_frames=frames,static_marker_counts=hits))
print(json.dumps(dict(status='FILTERED_START_FAILURE_DIAGNOSIS',logs=out)))
