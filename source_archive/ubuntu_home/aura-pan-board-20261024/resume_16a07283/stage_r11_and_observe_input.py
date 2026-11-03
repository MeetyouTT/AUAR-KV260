import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');P=F/'continuous-v10r11';OLD=F/'continuous-v10r10'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(P/'deployment-manifest.json')=='8d24c7e2258f7e44f8cf26476e1734b89d70e5d9f902db92f531e1df2ca74653'
for row in json.loads((P/'deployment-manifest.json').read_text())['files']:
 d=Path(row['destination'])
 if not d.exists():
  src=OLD/d.relative_to(P);assert sha(src)==row['sha256'];d.parent.mkdir(parents=True,exist_ok=True)
  with d.open('xb') as out:out.write(src.read_bytes())
 assert sha(d)==row['sha256']
s=json.loads((R/'state.json').read_text());ctx=json.loads((R/'context.json').read_text())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']==ctx['boot_id']
assert sha('/sys/firmware/fdt')==ctx['fdt_sha256']
assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()==ctx['firmware_name']
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
m=get(8783,'/api/state')['manual_pan'];before=get(8790,'/health')
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
assert before['pid']==189651 and not before['dpu_schedule']['owner_fenced']
cfg=json.loads((G/'startup/config.json').read_text());assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
sm=json.loads((F/'face-source-v12/deployment-manifest.json').read_text());assert all(sha(n)==v for n,v in sm['pins'].items())
out=P/('input-diagnostic-'+str(time.monotonic_ns())+'.json')
p=subprocess.run(['/usr/bin/python3','-B',str(P/'run_input_diagnostics.py'),'--settings',str(R/'face-zone-settings.json'),
 '--output',str(out),'--duration','15'],capture_output=True,text=True,timeout=22)
assert p.returncode==0,p.stderr[-800:]
d=json.loads(out.read_text());after=get(8790,'/health');end=get(8783,'/api/state')['manual_pan']
assert not d['MMIO_opened'] and not d['ARM_sent'] and not d['COMMIT_sent'] and not d['actuator_module_loaded']
assert end['readback']==m['readback'] and after['pid']==before['pid']
print(json.dumps({'status':'R11_STAGED_READ_ONLY_INPUT_DIAGNOSTICS','diagnostics':d,'output':str(out),
 'source_pins':len(sm['pins']),'control_pins':21,'gui_pins':len(cfg['component_sha256']),
 'readback_unchanged':end['readback'],'camera_pid':after['pid'],'identity_ready':after['identity']['ready'],
 'primary_overruns':after['dpu_schedule']['primary_period_overruns'],
 'optional_overruns':{k:after['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')}}))
