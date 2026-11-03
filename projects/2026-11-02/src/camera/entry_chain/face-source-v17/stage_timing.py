"""Constant-size per-source wall/thread-CPU timings around unchanged calls.

Nested stages overlap. Native call time includes result handling; it is not
pure DPU execution. No images, model outputs, names or identity vectors kept.
"""
import threading,time

_local=threading.local()


def measured(name,function,*args,**kwargs):
    record=getattr(_local,'record',None)
    if record is None:return function(*args,**kwargs)
    wall=time.monotonic_ns();cpu=time.thread_time_ns()
    try:return function(*args,**kwargs)
    finally:
        try:
            elapsed=time.monotonic_ns()-wall;used=time.thread_time_ns()-cpu
            row=record['stages'].setdefault(name,dict(calls=0,wall_ms=0.,thread_cpu_ms=0.))
            row['calls']+=1;row['wall_ms']+=elapsed/1e6;row['thread_cpu_ms']+=used/1e6
        except Exception:pass


def wrap_method(cls,attribute,name):
    original=getattr(cls,attribute)
    def call(self,*args,**kwargs):return measured(name,original,self,*args,**kwargs)
    setattr(cls,attribute,call)


def wrap_function(module,attribute,name):
    original=getattr(module,attribute)
    def call(*args,**kwargs):return measured(name,original,*args,**kwargs)
    setattr(module,attribute,call)


def wrap_compat_detect(cls):
    original=cls.detect
    def detect(self,*args,**kwargs):
        active=getattr(_local,'record',None)
        if active is None:return original(self,*args,**kwargs)
        depth=getattr(_local,'compat_depth',0);_local.compat_depth=depth+1
        try:return measured('compat_detect',original,self,*args,**kwargs)
        finally:_local.compat_depth=depth
    cls.detect=detect


def wrap_cv(module,attribute,name):
    original=getattr(module,attribute)
    def call(*args,**kwargs):
        if not getattr(_local,'compat_depth',0):return original(*args,**kwargs)
        return measured(name,original,*args,**kwargs)
    setattr(module,attribute,call)


def install(service_type=None,*,components=None):
    if service_type is None:
        from board.identity.face_targets import FaceTargetService
        service_type=FaceTargetService
    if getattr(service_type,'_edge_stage_timing_v15',False):return
    if components is None:
        import cv2
        from board.vision import dpu_yunet,dpu_vision_runtime,native_runtime,reference_faces
        components=dict(adapter=dpu_yunet.DpuYuNet,compat=reference_faces.YuNetCompat,
            network=dpu_vision_runtime.YuNetNetwork,native=native_runtime.NativePinnedRunner,
            adapter_module=dpu_yunet,runtime_module=dpu_vision_runtime,cv=cv2)
    for key,attribute,name in (('adapter','detect','adapter_detect'),
            ('adapter','scheduled','encode_and_schedule'),('adapter','_native_scheduled','native_admission_loop'),
            ('network','setInput','layout_normalize'),('network','forward','network_forward'),
            ('native','execute_encoded','native_call_with_result_handling')):
        wrap_method(components[key],attribute,name)
    wrap_compat_detect(components['compat'])
    wrap_function(components['adapter_module'],'encode','encode_int8')
    wrap_function(components['runtime_module'],'yunet_outputs','output_layout')
    wrap_cv(components['cv'],'resize','compat_resize')
    wrap_cv(components['cv'].dnn,'blobFromImage','compat_blob')
    wrap_cv(components['cv'].dnn,'NMSBoxes','compat_nms')
    original_initialize=service_type.__init__;original_process=service_type.process
    def initialize(self,factory,on_face,camera_epoch,**kwargs):
        def callback(*args,**options):return measured('identity_callback',on_face,*args,**options)
        return original_initialize(self,factory,callback,camera_epoch,**kwargs)
    def process(self,packet,detector,*args,**kwargs):
        prior=getattr(_local,'record',None)
        record=dict(frame_id=packet[1],source_mono_ms=packet[2],thread_id=threading.get_native_id(),stages={})
        _local.record=record
        try:return measured('total_process',original_process,self,packet,detector,*args,**kwargs)
        finally:
            _local.record=prior
            try:
                stages=record['stages']
                for row in stages.values():
                    row['wall_ms']=round(row['wall_ms'],3);row['thread_cpu_ms']=round(row['thread_cpu_ms'],3)
                native=stages.get('native_admission_loop');calls=stages.get('native_call_with_result_handling')
                if native and calls:
                    record['admission_wait_and_python_ms']=round(max(0.,native['wall_ms']-calls['wall_ms']),3)
                compat=stages.get('compat_detect')
                if compat:
                    children=('compat_resize','compat_blob','layout_normalize','network_forward','fast_input_encode','fast_network_forward','direct_bgr_encode')
                    record['decode_and_compat_bookkeeping_ms']=round(max(0.,compat['wall_ms']-
                        sum(stages.get(k,{}).get('wall_ms',0.) for k in children)),3)
                record['scope']='nested stage durations overlap; wall minus calling-thread CPU includes waits/GIL/descheduling; not pure DPU kernel'
                with self.lock:self._edge_latest_stage_timing=record
            except Exception:pass
    service_type.__init__=initialize;service_type.process=process
    service_type._edge_stage_timing_v15=True
