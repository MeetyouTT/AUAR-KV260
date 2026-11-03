"""Execute one user-requested finite 1430us correction after preparation and a start cue."""
import base64,contextlib,gzip,hashlib,io,json,os,subprocess,sys,time,traceback,urllib.request
from pathlib import Path
BOOT='3e1add36-b917-4289-91dc-699348528782'
TX=Path('/home/root/aura-pan-follow-20261020/midpoint-step-06')
RAW=gzip.decompress(base64.b64decode('H4sIAAAAAAAC/7VY6XPbuBX/rr8CdT+QXEsURR2W1Koziq00miaSa3vT6bgaDERCFja8ApA+NpP/fR8OSpR1xJ3MasYJAbz38M4fHnB2dvaeJSynKGZhlrIkRyKnGVrSJFgPUUhXpIhylHFYEYigLCJJHSX0kXKUZjQRaE14+EQ4dWu1VqfroUIgBpQJkmIZidjvJGdpgnIqQI7cAfjTHGTFlIiC0xA+gjVJWEAixOmKctgbxN2tQU6ephEKSCI5RE54DoOYcoJWaRSlTyx5QCmHrWAtikDmMpWElD8yKeLs7KzG4iwFNsIfMsIFLcdrItYRW5bD30Sa1FY8jVFGcrmAzMI1DEsi8SLKz5zFtFZ7N5/foRGy2rRFwrDdaywHrYtGx+8PGoNWGDR6g0G70+/6/Yu+b9VuNLWUaFvNdRrTJgd1m6TgpEFCkuXKUw3f83stz+s1HwV/bIi04AFttDoh8WjPaxZJRoIvNLSc2vXH8QwEfrO+sCS0hsh6P51N7yb40/Tqej6d3eHbu8k1fjeZXX6w6sgyAcFZEQmKCwEcMmL1GjI/C7z4QOX8/TcrBK2kOliOfdcDAeD/B5prTiXkO4SB60+IAbJbnbZXdxYViRHEmOJY7eVJGbtiYYIUeRrDVIA3IYWV9wRkVuRsUwRvUgTDiC1BHA0PcHD6tWBcWWPNE4pWOs2lipCiKslVvI1XlCsKUUc+/JU5jUREn1DEYib3qAhPizwrcgxm0GeWyy1u7+bXfwNhIYWqCCnUEdgbb8sDKU8gtoJaSgMqBAqZIFlGISmt77VaDUoNxYQltjNU+6hs5RDeMnPdMX8oYpB8rVbskIqAs0w6c4RxmAYYOxVOFzISE8NiW40GfaZBkVPIBBIoJgh3yinOeUGtk5xBmqwYj1XcgD1Yp1BdYnRvlYkmndrwb63FSTHaaSAgf8noSJaBJgcaAXYaLvWf5BO2XgaXKbyAGdfYMNxEQgGTLavXDYs4E3bIgtyWhVGXeJEXYmTJEZ7PPv4Xz+b4w/jm6j/jmwmeX09mkyvLqSNAMYAhTETA2EinkQpkko98x9lsxWle8KRUSalTdQz6CwDBa4dIcFKU2naJjLM0qeqvjaacp9y2Jso8KazMXmS2AJQsEzVOH6l0KQogpTiBQgC0DQH7EshVs8+KRWVMDWClQvtawHZy5BYJAKntuDEJ1gzqYwTqE8KDda9jKYFAA9VOCxbajlz1qgIMiMlcbgIsNr9QntCoCeqEadyUKIwZQJTLKQlxTp9z2EnkkK5algTOqjiDxq5YE7/bs410KVgaL+unuQrzUt7yBQ4T23HcNX0OGSBWrqVaXa8VrPo9GvTbg/ZFO1x1L/o9f9X3B2G7E/SXXbIceACjlC574dIjQe9isAxov93qDwYDf2Cd0MmW8N20gjSOIdmylx8qs+r6g27XCwf9Fum1Wp1lrzdod9uwbz/wuq2LDunRTtf3W0Gv3e92ur2w4/UHvaDVX3pB0CFaGfCBK48kF8440Mr2ZF5zpYyzE2CtmJoxOprTaeNrM/1QACSZ2jJTwZoGXzAvEnmsmSXjBUMhIeORasvuzdz4+nqhMsWMy1Bpqi3RueUuWQ5/iTZJwa4823DImWwkjAWfb28+X6mZOno3nV3V0c3k/eQGjq9JHY1vPtXR5fzTp6k2BmpDNiby9JM9CUCwLnqrzL2hMhwmsvWLUAcH2FBoDBuiOwC9LZ4bVC/AYrypKrwDe8P9it/jhzSHMoCdnsgjhZMxxmALW7HK+fTqJBNZCmGV58fN5N+/Tm8mt/jX28kNnr+Dfz+P76bzmbW/zSNUvzqlF9/V2l/R5DmICgGuawSQlHDM5WuK6CML5TkJzRwoI1HipcSHjPKYCSGRBiBJ0NxVgp5Yvq7ilStbPNt6thxIBxSlD1vgUqQmxpIKjHlgcKpyqAVJzNLhjt4m1KNKlG2W1pH3XHY2dRUwZ4cr5y/DV+ajDRCOjFBXA73t7FGaHLYNx721isiDsBYKzlTqblZ0oxLRVS67lcUW8A79djihG8OCftU8nd7uIs3SYK2XLnZXnliYr2UvpRZl9/G27bbtz5b34pUx20ZtI3zfORvnpdkB1wmq0gNOR2kB+Np71n2pD4Hq78ckdZ84dEk2xFNClOZ2TtJ1jPCTVH5Hg8EBDXOZ6G9OAkW+kwF95TQzbzTWK2ZQXa8EUn2e0rkd1I/4/JVhG3z7E6xr+VX1D2VN16tSvCEfX2kPkPxn6N1RWpkLn1zUZ4+1OJCjX9GhMtUXxZG6pLkAUGmeAuAeUELeXtSdB8t+77muB/IqQ5NCXjPBVnms3Jc3o4UzPFilWgg0/rCr2v3crsg9bzm/qOF99fqzOCFJAit4QaBjKPS0hg5vz0D0960mw6NwIt12Do4+SqDhQ5sila7AyVGeamH3JQB8dd5EC6Wixb+JXIKPDsjmYrl4G2On7B6Ok781dV+fLq/SdLfsiChBZafadg4N+Di6SfUMMLyv0N1E6yew7LiJusu6L1uOhStvrElof7NoRDJBQ32152kBk/brdGyoUnB+gZswxM136j+0cu+38+agv+vqnSJXM8qg7ydDWq2m01kvtYcLP81s1+s4tZ9NkS3CVVX4xwj5u4mwnzW7UPyGIizDZPyykG9S5i1Ivf7g8eW/8PX49hZ/mlx+GM+ml+OP1R4Tw134ajr7p7UjmT4HNMvROyi0ifpUaSTk/PBtKoynH+GKfZRW3XoVqXwRsEGu42Is76UYn8um+FxedeT0vgjCBN2ZXTHovKMD7eLBHrKqhuJUapxuif4vf+z6JM3wTxh72OCTRssf9OsG/yrvI1qnHzx6nFv/SyznqNAV3DXWxkF7DzDHN4D7aq3GVqi0Wt2SMZaPXhhb2gb9Alb7A6mBRSOXFgAA'))
SHA='34801a6c61d335b47f52a47b5e4fdb0e37d4c9d8fe5bcfecfbdd65bf4d574bb4'
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
try:
 gui=get(8783,'/api/state')
except Exception as gui_exc:
 gui={'phase':'STATUS_UNAVAILABLE','playing':None,'automatic_conversation':{'state':'UNKNOWN'}}
gui_at_start={k:gui.get(k) for k in ['phase','playing']}
gui_at_start['automatic_state']=gui.get('automatic_conversation',{}).get('state')
identity_state=get(8790,'/v1/ui/status').get('modules',{}).get('identity',{}).get('state')
assert identity_state not in ['ENROLLING','SAMPLING'], 'Identity sampling in progress; no axis test'
TX.mkdir(parents=True,exist_ok=False);os.chmod(TX,0o700)
script=TX/'midpoint_step_bench.py'
with script.open('xb') as f:f.write(RAW)
report={'status':'STARTING','boot_id':BOOT,'test_script_sha256':SHA,
 'authorization':'User saw the larger movement, reported residual right bias and requested another correction; one 1430us hold for2s from1450us',
 'test_scope':'MIDPOINT1430-2S','field_feedback':'还有点偏右','previous_test_point_us':1450,'before':before,'automatic_following_enabled':False,
 'gui_at_start':gui_at_start,'identity_state_at_start':identity_state}
(TX/'authorization.json').write_text(json.dumps(report,indent=2)+'\n')
namespace={'__name__':'frozen_bench','__file__':str(script)}
exec(compile(RAW,str(script),'exec'),namespace)
sys.argv=[str(script),'--execute','--confirmation','MIDPOINT1430-2S','--output',str(TX/'bench.json')]
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
