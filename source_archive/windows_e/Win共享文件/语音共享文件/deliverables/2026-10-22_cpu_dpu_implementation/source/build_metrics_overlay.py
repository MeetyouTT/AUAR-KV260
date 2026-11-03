"""Reproducible small overlay over the frozen, retained YuNet baseline."""
import ast,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BASE=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_vision_start/candidate/aura')
OUTPUT=ROOT/'metrics-candidate/aura'


def replace(source,old,new):
    assert source.count(old)==1,repr(old[:100])
    return source.replace(old,new,1)


def build():
    ui=BASE/'board/vision/ui_camera_service.py'
    runtime=BASE/'board/vision/dpu_vision_runtime.py'
    assert hashlib.sha256(ui.read_bytes()).hexdigest()=='890fea726de2c6d29581ab2ee4c36db5e36df52f3e84ee20cd634fc8961ec2ce'
    assert hashlib.sha256(runtime.read_bytes()).hexdigest()=='f5fe60a61eb9c3944d1d64097ce4cc838132a65243f28f011758da9d654dd2e6'
    source=ui.read_text()
    source=replace(source,"        self.started = clock()", "        from board.vision.pipeline_metrics import PipelineMetrics\n        self.pipeline_metrics = PipelineMetrics(enabled=os.environ.get('AURA_PIPELINE_METRICS')=='1')\n        self.started = clock()")
    source=replace(source,"                'timestamp_kind':'appsink_dequeue_monotonic'", "                'pipeline_metrics':self.pipeline_metrics.snapshot(),\n                'timestamp_kind':'appsink_dequeue_monotonic'")
    source=replace(source,"    stop=threading.Event();condition=threading.Condition();latest=[None]", "    if detector is not None:detector.pipeline_metrics=state.pipeline_metrics\n    stop=threading.Event();condition=threading.Condition();latest=[None]")
    source=replace(source,"        def sample(sink):\n            try:", "        def sample(sink):\n            stage_started=time.monotonic_ns()\n            try:")
    source=replace(source,"                source=cv2.flip(image,1)", "                source=cv2.flip(image,1)\n                state.pipeline_metrics.elapsed('capture.callback_prepare',stage_started)")
    source=replace(source,"                        inference_started=time.monotonic()", "                        inference_started=time.monotonic()\n                        state.pipeline_metrics.value('yolo.source_age_at_start',max(0,millis()-stamp))\n                        schedule_started=time.monotonic_ns()")
    source=replace(source,"                                detections=detector.detect_bgr(image)", "                                state.pipeline_metrics.elapsed('yolo.schedule_wait',schedule_started)\n                                native_started=time.monotonic_ns()\n                                detections=detector.detect_bgr(image)\n                                state.pipeline_metrics.elapsed('yolo.native_and_decode',native_started)")
    source=replace(source,"                        with state.lock:\n                            observation=tracker.update", "                        track_started=time.monotonic_ns()\n                        with state.lock:\n                            observation=tracker.update")
    source=replace(source,"                        elapsed=round((time.monotonic()-inference_started)*1000,2)", "                        state.pipeline_metrics.elapsed('yolo.track',track_started)\n                        elapsed=round((time.monotonic()-inference_started)*1000,2)\n                        state.pipeline_metrics.value('yolo.path',elapsed)")
    source=replace(source,"                        state.observed(fid,stamp,observation,elapsed)", "                        state.observed(fid,stamp,observation,elapsed)\n                        state.pipeline_metrics.value('yolo.publish_source_age',max(0,millis()-stamp))")
    source=replace(source,"                    # Capture/inference share an immutable source. Paint on a copy.", "                    preview_started=time.monotonic_ns()\n                    # Capture/inference share an immutable source. Paint on a copy.")
    source=replace(source,"                    state.publish_preview(fid,stamp,encoded.tobytes())", "                    state.publish_preview(fid,stamp,encoded.tobytes())\n                    state.pipeline_metrics.elapsed('preview.render_encode_publish',preview_started)\n                    state.pipeline_metrics.value('preview.publish_source_age',max(0,millis()-stamp))")
    paths={'board/vision/ui_camera_service.py':source}
    source=runtime.read_text()
    source=replace(source,"        self.last_ms = None", "        from board.vision.pipeline_metrics import PipelineMetrics\n        self.metrics=getattr(owner,'pipeline_metrics',None) or PipelineMetrics()\n        self.stage_kind='sface' if list(self.inputs[0].dims)==[1,112,112,3] else 'yunet'\n        self.last_ms = None")
    source=replace(source,"        outputs = [np.empty(tuple(t.dims), dtype=np.int8) for t in self.outputs]", "        allocate_started=time.monotonic_ns()\n        outputs = [np.empty(tuple(t.dims), dtype=np.int8) for t in self.outputs]\n        self.metrics.elapsed(self.stage_kind+'.allocate',allocate_started)\n        slot_started=time.monotonic_ns()")
    source=replace(source,"            if not acquired:\n                return None", "            slot_wait_ms=(time.monotonic_ns()-slot_started)/1e6\n            if not acquired:\n                self.metrics.value(self.stage_kind+'.slot_wait',slot_wait_ms)\n                return None")
    source=replace(source,"        # Output conversion is CPU work; the next YOLO job can own the DPU now.", "        self.metrics.value(self.stage_kind+'.slot_wait',slot_wait_ms)\n        self.metrics.value(self.stage_kind+'.execute_wait',self.last_ms)\n        # Output conversion is CPU work; the next YOLO job can own the DPU now.")
    source=replace(source,"        return {t.name: a.astype(np.float32) * (2. ** -t.get_attr('fix_point'))\n                for t, a in zip(self.outputs, outputs)}", "        dequantize_started=time.monotonic_ns()\n        result={t.name: a.astype(np.float32) * (2. ** -t.get_attr('fix_point'))\n                for t, a in zip(self.outputs, outputs)}\n        self.metrics.elapsed(self.stage_kind+'.dequantize',dequantize_started)\n        return result")
    source=replace(source,"    source = (crop[:, :, ::-1].astype(np.float32)[None] - 127.5) / 128.", "    prepare_started=time.monotonic_ns()\n    source = (crop[:, :, ::-1].astype(np.float32)[None] - 127.5) / 128.\n    metrics=getattr(runner,'metrics',None)\n    if metrics:metrics.elapsed('sface.normalize_input',prepare_started)")
    source=replace(source,"    feature = next(iter(result.values())).reshape(-1)", "    validate_started=time.monotonic_ns()\n    feature = next(iter(result.values())).reshape(-1)")
    source=replace(source,"    return feature\n", "    if metrics:metrics.elapsed('sface.validate_output',validate_started)\n    return feature\n")
    paths['board/vision/dpu_vision_runtime.py']=source
    for name,body in paths.items():
        ast.parse(body,filename=name)
        out=OUTPUT/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(body)
    files={str(p.relative_to(OUTPUT)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
        for p in sorted(OUTPUT.rglob('*.py'))}
    manifest={'status':'SOFTWARE_CANDIDATE_NOT_BOARD_DEPLOYED','default_enabled':False,
        'enable_environment':'AURA_PIPELINE_METRICS=1', 'files':files,
        'baseline':{str(p.relative_to(BASE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ui,runtime]},
        'yolo_pre_dpu_post_inside_native_are_individually_measured':False,
        'sensor_exposure_display_consumption_or_identity_publication_measured':False,
        'quantiles':'latest256 samples per stage; cumulative count/min/max/mean separately reported'}
    (ROOT/'metrics-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'files':len(files),'status':manifest['status']}))


if __name__=='__main__':build()
