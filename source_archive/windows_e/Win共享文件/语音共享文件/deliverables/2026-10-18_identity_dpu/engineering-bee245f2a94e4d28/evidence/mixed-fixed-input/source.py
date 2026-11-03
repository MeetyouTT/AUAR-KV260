"""Use the pinned restoration controller for a same-process two-model check."""
import hashlib
from pathlib import Path

controller_path = Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/helpers/5da8d5977453312b/source.py')
controller = controller_path.read_text()
assert hashlib.sha256(controller.encode()).hexdigest() == '5da8d5977453312b60f49a3fbce99bbcf0ad5ef17c4e9ebadab2ee6a6eb26f22'
core = r'''
import ctypes,hashlib,json,time
from pathlib import Path
import cv2,numpy as np,xir,vart
root=Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/bee245f2a94e4d28')
assets={
 '/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura/board/vision/native/libaura_yolox.so':'14524ca6364f7ecab3464999a1f20271d9f3b13e80684859f6da1573caf6efa8',
 '/home/root/aura-bytetrack-20261011/models/yolox_nano_person.xmodel':'def64abdeeccbd020cb651913ba907464c1a1786e30ba7d4aa077b601388950a',
 '/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura/tests/fixtures/vision/person_bus.jpg':'975917d943c3dd367a27c37c4a9b0cdaf28c73ce671c881f6489a18bda20b46f',
 str(root/'sface_engineering.xmodel'):'bee245f2a94e4d28cc00d7f367fa08c7c375feee2081267c8e414033067df3d8'}
for p,sha in assets.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha
paths=list(assets)
lib=ctypes.CDLL(paths[0]);lib.aura_yolox_create.argtypes=[ctypes.c_char_p];lib.aura_yolox_create.restype=ctypes.c_void_p
lib.aura_yolox_error.restype=ctypes.c_char_p
lib.aura_yolox_detect.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_int)]
lib.aura_yolox_detect.restype=ctypes.c_int
lib.aura_yolox_destroy.argtypes=[ctypes.c_void_p]
detector=lib.aura_yolox_create(paths[1].encode());assert detector,lib.aura_yolox_error()
image=np.ascontiguousarray(cv2.imread(paths[2]));h,w=image.shape[:2];boxes=np.zeros((32,6),np.float32)
g=xir.Graph.deserialize(str(root/'sface_engineering.xmodel'))
sub=next(s for s in g.get_root_subgraph().toposort_child_subgraph() if s.has_attr('device') and s.get_attr('device')=='DPU')
runner=vart.Runner.create_runner(sub,'run')
data=np.load(str(root/'hardware-reference.npz'),allow_pickle=False)
source=np.ascontiguousarray(data['input_public_reference'],dtype=np.int8);expected=data['quantized_public_reference'];output=np.zeros((1,128),np.int8)
def detect():
 count=ctypes.c_int();start=time.monotonic()
 rc=lib.aura_yolox_detect(detector,image.ctypes.data,w,h,image.strides[0],boxes.ctypes.data,32,0,ctypes.byref(count))
 assert rc==0 and count.value>0,lib.aura_yolox_error()
 return (time.monotonic()-start)*1000,count.value
def identity():
 start=time.monotonic();job=runner.execute_async([source],[output]);assert runner.wait(job)==0
 elapsed=(time.monotonic()-start)*1000
 assert np.array_equal(output.reshape(-1),expected),'Feature mismatch during model switching'
 return elapsed
def summary(values):
 a=np.asarray(values);return {'samples':len(a),'median_ms':float(np.median(a)),'p95_ms':float(np.percentile(a,95)),'maximum_ms':float(a.max())}
try:
 detect();identity()
 results=[]
 for name,slots,with_identity in [('yolo_only',50,False),('yolo_and_identity',100,True)]:
  start=time.monotonic();detection=[];features=[];late=[];counts=[];overruns=0
  for i in range(slots):
   deadline=start+i*.1;time.sleep(max(0,deadline-time.monotonic()))
   late.append(max(0,(time.monotonic()-deadline)*1000))
   elapsed,count=detect();detection.append(elapsed);counts.append(count)
   if with_identity and i%5==0:features.append(identity())
   if time.monotonic()>deadline+.1:overruns+=1
  total=time.monotonic()-start
  results.append({'mode':name,'scheduled_detection_hz':10,'detection_calls':slots,'identity_calls':len(features),
   'duration_s':total,'detection':summary(detection),'identity':summary(features) if features else None,
   'deadline_lateness':summary(late),'period_overruns':overruns,'minimum_people':min(counts)})
 print(json.dumps({'scope':'SAME_PROCESS_FIXED_IMAGES_NOT_LIVE_CAMERA_OR_TRACKER','results':results,
  'all_host_quantized_agreement':True,'mixed_identity_outputs_bit_exact':True}),flush=True)
finally:lib.aura_yolox_destroy(detector)
'''
start = controller.index("core = r'''")
end = controller.index("'''\n\n\ndef service", start)+3
controller = controller[:start]+'core = '+repr(core)+controller[end:]
controller = controller.replace('STANDALONE_ENGINEERING_TEST_WITH_CAMERA_TEMPORARILY_STOPPED', 'SAME_PROCESS_FIXED_INPUT_BENCHMARK_WITH_CAMERA_TEMPORARILY_STOPPED')
controller = controller.replace('PASS_STANDALONE_DPU_ENGINEERING', 'PASS_FIXED_INPUT_TWO_MODEL_BENCHMARK')
controller = controller.replace('FAILED_STANDALONE_DPU_ENGINEERING', 'FAILED_FIXED_INPUT_TWO_MODEL_BENCHMARK')
controller = controller.replace("ROOT/'standalone-result.json'", "ROOT/'fixed-input-mixed-result.json'")
exec(compile(controller, str(controller_path)+'-mixed', 'exec'))
