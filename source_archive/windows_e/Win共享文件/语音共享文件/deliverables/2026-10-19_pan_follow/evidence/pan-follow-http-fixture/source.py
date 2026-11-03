"""Exercise the optional route on an ephemeral fixture server, not port 8790."""
import importlib,json,subprocess,sys,threading,urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
stage=Path('/home/root/aura-pan-follow-20261019/test-2f1e928a6ec30f9b/aura')
working=Path(subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','WorkingDirectory','--value'],text=True).strip())
sys.path.insert(0,str(working))
import board,common
board.__path__=[str(stage/'board')]+list(board.__path__)
common.__path__=[str(stage/'common')]+list(common.__path__)
import board.motion
board.motion.__path__=[str(stage/'board/motion')]+list(board.motion.__path__)
from board.vision import ui_camera_service as camera
from board.motion.camera_feed import install
from common.motion_observation import PATH,validate
state=camera.CameraState('fixture-boot','fixture-service',clock=lambda:1000)
state.captured(1000)
state.observed(1,1000,{'target_id':1,'tracks':[{'track_id':1,'generation':1,'visible':True,'confirmed':True,
 'frame_id':1,'captured_at':1.,'box':[100.,0.,100.,480.],'score':.9}]},10.)
install(camera)
server=ThreadingHTTPServer(('127.0.0.1',0),camera.handler_for(state))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
 values={}
 for path in ['/health',PATH]:
  with opener.open('http://127.0.0.1:%d%s'%(server.server_port,path),timeout=2) as r:values[path]=json.load(r)
 assert values['/health']['detected_frames']==1
 assert validate(values[PATH],'fixture-boot',1000)['state']=='READY'
finally:
 server.shutdown();server.server_close();thread.join(timeout=2)
print(json.dumps({'status':'PASS_ACTUAL_CAMERA_MODULE_HTTP_FIXTURE_EXTENSION','original_health_preserved':True,
 'new_motion_route_passed':True,'server_port_was_ephemeral':True,'production_camera_not_restarted':True,
 'actual_live_frames_used':False,'physical_actuation':False}),flush=True)
