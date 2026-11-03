import json,shutil,subprocess,urllib.request
out={'scope':'Existing active camera metadata and read-only V4L2 query; no format/control/stream mutation'}
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=2) as r:s=json.load(r)
device=s.get('device') or {};resolved=device.get('resolved')
out['active_camera_pid']=s.get('pid');out['resolved_device']=resolved
tool=shutil.which('v4l2-ctl');out['query_tool_available']=bool(tool)
if tool and isinstance(resolved,str) and resolved.startswith('/dev/video'):
 for option in ['--get-parm','--list-ctrls']:
  p=subprocess.run([tool,'--device='+resolved,option],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=4)
  out[option]={'exit_code':p.returncode,'output':p.stdout.decode(errors='replace')[:6000],'stderr':p.stderr.decode(errors='replace')[:500]}
print(json.dumps(out))
