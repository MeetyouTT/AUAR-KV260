"""Keep one exclusive UART session across switch, idle watch and camera start."""
import datetime,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('wire','/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
SOURCE='/home/root/aura-post-power-20261022/helpers/11bd178c302d1bc3/source.py'
PIN='11bd178c302d1bc3f0ccd2bc52f0afea0c5984ead744bdeede2d34b136f3afcb'
evidence=ROOT/('stable-session-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S'));evidence.mkdir()
status={'phases':[],'complete':False};uart=None
with (evidence/'serial.raw').open('xb') as raw:
 try:
  uart=wire.transport_module().UART(raw);uart.connect()
  for n,phase in enumerate(['stop','switch','watch','start-camera']):
   if (ROOT/'CANCEL_STABILITY_SESSION').exists():raise RuntimeError('Operator stopped the maintenance sequence')
   code="import hashlib,json,runpy,sys\nfrom pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='55152f95-ea3a-4c6c-82e6-51bd553d96fd'\n"
   if phase=='stop':
    code+="p=Path('/home/root/aura-pan-wide-resume-20261029/55152f95/motor-power-off.json')\nr={'boot_id':'55152f95-ea3a-4c6c-82e6-51bd553d96fd','user_reported_power_off':True,'quote':'舵机动力已断开，板卡仍通电','continued_disconnected_through_board_restart':True,'electrical_measurement':False}\nassert not p.exists()\np.write_text(json.dumps(r,ensure_ascii=False,indent=2))\n"
   code+='p=Path('+repr(SOURCE)+')\nassert hashlib.sha256(p.read_bytes()).hexdigest()=='+repr(PIN)+'\nsys.argv=[str(p),'+repr(phase)+'];runpy.run_path(str(p),run_name="__main__")\n'
   print(json.dumps({'phase':phase,'status':'STARTING'}),flush=True)
   rc,body,digest=uart.command(wire.wire(code),'WIDESTABLE'+str(n),150)
   (evidence/(phase+'.response')).write_bytes(body)
   row={'phase':phase,'exit_code':rc,'response_sha256':digest};status['phases'].append(row)
   if rc:raise RuntimeError('Phase failed: '+phase+'; details retained privately')
   doc=json.loads(body);(evidence/(phase+'.json')).write_text(json.dumps(doc,indent=2)+'\n')
   print(json.dumps({'phase':phase,'status':doc.get('phase'),'elapsed_s':doc.get('elapsed_s'),'camera_pid':doc.get('camera_pid')}),flush=True)
   (evidence/'status.json').write_text(json.dumps(status,indent=2)+'\n')
  status['complete']=True
 finally:
  if uart:status['console_echo_restored']=uart.close()
  (evidence/'status.json').write_text(json.dumps(status,indent=2)+'\n');(ROOT/'STABILITY_SESSION.json').write_text(json.dumps({'evidence':str(evidence),**status},indent=2)+'\n')
