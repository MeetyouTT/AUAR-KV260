"""Run one bounded midpoint calibration step within the previously tested range."""
import base64,contextlib,gzip,hashlib,io,json,os,subprocess,sys,time,traceback,urllib.request
from pathlib import Path
BOOT='3e1add36-b917-4289-91dc-699348528782'
TX=Path('/home/root/aura-pan-follow-20261020/midpoint-step-01')
RAW=gzip.decompress(base64.b64decode('H4sIAAAAAAAC/7VY63PiOBL/zl+hy32wvQHzJsAdV0USZoe6Cckm2bm6ylEqYYugG9vySHIeOzX/+7YeEBMIk62tpWoyttTd6uevWz46OvrAMqYoSlmcc5YpJBXN0YJm0WqIYrokRaJQLmBHIoLyhGRVlNEHKhDPaSbRioj4kQgaVirNbqODCokYUGZIi2UkYb8RxXiGFJUgR58A/FyBrJQSWQgaw0O0IhmLSIIEXVIBZ4O42xXIUZwnKCKZ5pCKCAUvKRUELXmS8EeW3SMu4CjYSxKQueCakIoHpkUcHR1VWJpzYCPiPidC0vX7ishVwhbr1/9LnlWWgqcoJ0pvILdxBa9rIvks14+KpbRSOb28vEUj5LVpk8Rxu1dbDJontU6rP6gNmnFU6w0G7U6/2+qf9Fte5dpSa4m+V1/xlNYFqFsnhSA1EpNcGU/VWo1Wr9lo9OoPUjzUJC9ERGvNTkwatNeoF1lOoi809oLK1afxDAR+876wLPaGyLuYnl9dTme3+GY6+/nTBN/cTq7w6WR29tGrIs8FBOdFIikuJHDoiFUryP088OI91et337wYtNLqYP0edoEf3H9PlWU0Mr5DFIR9hBAg30hDr/8G89IJCcSc4tSc3WiA0K1jWrBACsVTWIrwJsSw84HAISU5LymDNymD4Y0tQByN93AI+rVgwljnnfFMsaygSK0oJCwVNTh1xQX7DbJxLUUn7SNTK7BMk5FEUBI/mzwGKkGye+qV5PNC5YXCYAl9YkqfcnN7efUPcExMoVBiCqUFJqcvFYOMMxBbQnnxiEqJYiZJnlPIU+97pVKB6kMpYZkfDM05JoEFRHydzOFY3BcpSL4yO35MZSRYrlUfYRzzCOOgxBlCkmLiWHyvVqNPNCoUmIFIZJggA7igWImCegc5I54tmUiNl4A9WnEoODm626SgjnytdePND4qxTgMB6jmnI10ZlhxoJNjpuMx/mk/6dhtcZiAEVkJnw3ATCYNVvi7oMC7SXPoxi5Sva6WqIUQVcuTpN3w5+/RfPLvEH8fX5/8ZX0/w5dVkNjn3gioCYANkwkRGjI1sJplAZmrUCoLNUYKqQmRrlYw6Zcegv43QjkM0XhlKa7sGyxnPyvpbo6kQXPjexJinha0TGLkjIAldRaOUP1DtUhRBSkFmRpCuWQxwmNFH5M5ZsmQdU4dhXFpfSzhOv4VFBtjqB2FKIsh6ikagPiEiWvU6nhEINIAAtGCxH+jdRlmAwzWdy3VAyvoXKjKa1EGdmKd1DcyYAWqFuoywok8KTpIK0tXK0lhaFucAOpQr0ur2fCddC9bG6/qpL2O1lrd4hrr0gyBc0aeYAYgpK9XrNprRst+jUb89aJ+042X3pN9rLfutQdzuRP1FlywGDUBWShe9eNEgUe9ksIhov93sDwaD1sA7oJOvEb3uRTxNIdny5x8qs+y2Bt1uIx70m6TXbHYWvd6g3W3Duf2o0W2edEiPdrqtVjPqtfvdTrcXdxr9QS9q9heNKOoQqwz4INRdKoS2B1r5DZ3XwigTbAXYKmZWnI6uYW187ZbvC4AkV1tuKVrR6AsWRaY7ndtyXnAUGjIeqLXszq2Nr67mJlPc+zpUluqF6NgLF0zBv8yaZDqvbnc4FkzPFs6CzzfXn8/NShWdTmfnVXQ9+TC5ho42qaLx9UUVnV1eXEytMVAbelbRDVGPKQDBtui9de4NjeGwkK+epekdYENhMWyIbgH0XvDcobpuDnhTVXgL9oa7Fb/DD2kOZQAnPZIHCt0yxWALW7JSi3rVzGTOIay6f1xPfvl1ej25wb/eTK7x5Sn8/Ty+nV7OvN1jHqD6TeOefzd7f0eTpygpJLiuFkFSKtvr6AOLdauE+Q6U0SjxvMaHnIqUSamRBiBJUhUaQboDlvEq1FOf7z15AaQDSvj9C3AZUhdjTQXG3DNolgJqQRMzPtzS24V6VIqyz3gVNZ7Ww07VBCzY4lLiefjKfLQBwpETGlqg94MdSpfDvuO485YJuZfe3MCZSd3Njp1VErpUemCZvwDevt8WJwxoWNKvlqfT2958ZLFa6SnK7EJbeKfQlzmnzLtN8zKibQh2XbBxEc/3OEhSkwTQA3MercCjjSc7kLYgHM1dz/PwUcD9wYeoaSCy3MFBuo4TfpCq1bElv0dDpdP53aE25Ftx7hunuXWnsd1xL+V9o6ndNY+HdG5HbuT9kWEbFPsLrGu2yurvzZpOmWInHzs/0h6A96/Q22rlbnp603YYb74nR7+ifcVob4gjczsLAYa44gCre5TQ9xZz2cF6qnuq2hd9iaFZoe+XYKtuHnfrK9E8GO6tUisExns41Zx+7JfkHjeDn8zrXfmeMz8gScMneEGit7DmcQVz3I6B6J8vmgzfhBPttuPRniLeYKuBD2uKVroEJ2/ylAu7rwHga/AuWigVK/5d5Bp8bEA2N8j5+xg76xnhbfL3pu7rHvIqTbfLjsg1qDTKG1utAR7ePKTcAxzvK3R30foTWPa2iXaWulsPFvNQ30uz2P/m0YTkksb2Di94AYv+63SsmVIIfoL7LsStFVR/aOXOb+trg32umg8UyqwYg74fDGm5mg5nvdZeJpTmfrgPu/9oirwgXFmFf41QazsRdrNmG4rfUYTrMDm/zPXHqA/T2fR2Yj/74PHZv/HV+OYGX0zOPo5n07Pxp/IkieHGez6d/extSaZPEc0VOoVCm5hHk0ZSrw/fp8J4+gku0m/SmrutIdX3fh/kBiHG+vaJ8bEefY/1hUYv74ogTNKt1SWD+TrZMxTunRTLahhOo8bhkegP+WPbJzzHf8LY/QYfNFr/YCp3+Ff6CmJ1+sGnjWPvf5kXvCl0CTeKlXPQzmeWtw+AW2mlwpZobbW5C2OsP21h7Fkb7Heuyu8NINCjkBYAAA=='))
SHA='2706fac7aa4aad8935c1b7e4407cafcf408bf06c8e57de387b5fb5e331a633c4'
assert hashlib.sha256(RAW).hexdigest()==SHA
assert os.uname().machine=='aarch64' and os.geteuid()==0
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()=='aura-visual-servo-b4096-v1.bit.bin'
assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
assert Path('/etc/vart.conf').read_text()=='firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-v1/aura-visual-servo-b4096-v1.xclbin\n'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with opener.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as r:return json.load(r)
def unit(unit):
 return {k:subprocess.check_output(['systemctl','show',unit,'-p',k,'--value'],text=True,timeout=5).strip()
         for k in ['ActiveState','MainPID','WorkingDirectory']}
def health():
 v=get(8790,'/health')
 assert not v['camera_error'] and not v['detector_error'] and v['identity_recognition']
 return {k:v.get(k) for k in ['pid','detected_frames','observation_age_ms','detection_hz','identity_recognition','camera_error','detector_error']}
before={u:unit(u) for u in ['aura-camera-ui.service','aura-avatar-ui.service']}
before['camera']=health()
gui=get(8783,'/api/state')
assert gui['phase']=='IDLE' and not gui['playing']
assert gui.get('automatic_conversation',{}).get('state')=='STOPPED'
TX.mkdir(parents=True,exist_ok=False);os.chmod(TX,0o700)
script=TX/'midpoint1504_bench.py'
with script.open('xb') as f:f.write(RAW)
report={'status':'STARTING','boot_id':BOOT,'test_script_sha256':SHA,
 'authorization':'Continue user-authorized axis calibration after field feedback: 1500us points right; same tested envelope',
 'test_scope':'MIDPOINT1504-2S','field_feedback':'偏右','previous_test_point_us':1500,'before':before,'automatic_following_enabled':False}
(TX/'authorization.json').write_text(json.dumps(report,indent=2)+'\n')
namespace={'__name__':'frozen_bench','__file__':str(script)}
exec(compile(RAW,str(script),'exec'),namespace)
sys.argv=[str(script),'--execute','--confirmation','MIDPOINT1504-2S','--output',str(TX/'bench.json')]
captured=io.StringIO();start=time.monotonic()
try:
 with contextlib.redirect_stdout(captured):namespace['main']()
 report['status']='FINITE_MIDPOINT_STEP_FINISHED'
except BaseException as exc:
 report['status']='FINITE_MIDPOINT_STEP_FAILED'
 report['error']=type(exc).__name__+': '+str(exc)
 (TX/'failure-traceback.txt').write_text(traceback.format_exc())
report['script_elapsed_s']=round(time.monotonic()-start,3)
if (TX/'bench.json').exists():
 report['bench']=json.loads((TX/'bench.json').read_text())
try:
 import common
 from vsrv_driver import VSRVDriver
 with common.open_registers() as registers:
  driver=VSRVDriver(registers,0x14da0e60,BOOT)
  final=driver.status()
  assert not final['active'] and not final['armed'] and final['lease_left_ms']==0
  report['independent_final_readback']=final
except BaseException as exc:report['final_readback_error']=type(exc).__name__+': '+str(exc)
report['after']={u:unit(u) for u in ['aura-camera-ui.service','aura-avatar-ui.service']}
try:report['after']['camera']=health()
except Exception as exc:report['after']['camera_error']=str(exc)
(TX/'result.json').write_text(json.dumps(report,indent=2)+'\n')
summary={k:v for k,v in report.items() if k!='bench'}
if 'bench' in report:
 b=report['bench']
 summary['bench']={k:v for k,v in b.items() if k!='events'}
 summary['bench']['commands_accepted']=len(b['events'])
 summary['bench']['target_pulses_us']=sorted(set(e['target_us'] for e in b['events']))
print(json.dumps(summary),flush=True)
