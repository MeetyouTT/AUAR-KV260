# Appended to the reviewed callback microbenchmark definitions on the board.
def gst_check():
    import gi
    gi.require_version('Gst','1.0')
    from gi.repository import Gst
    Gst.init(None);cv2.setNumThreads(2)
    source=SOURCE.read_text();assert hashlib.sha256(source.encode()).hexdigest()==EXPECTED
    candidate=source.replace(OLD,NEW,1)
    data=((np.arange(640*480*3,dtype=np.uint32)*17+13)%256).astype(np.uint8).reshape(480,640,3)
    raw=data.tobytes();expected=np.ascontiguousarray(data[:,::-1,:]);before=health();results=[]
    for name,body in [('original',source),('candidate',candidate)]:
        cb,latest,state=callback(body)
        # Use genuine Gst Buffer/caps/extract_dup; no camera or audio element.
        pipeline=Gst.parse_launch('appsrc name=src is-live=true format=time block=true caps=video/x-raw,format=BGR,width=640,height=480,framerate=30/1 ! appsink name=dst sync=false max-buffers=1 drop=false')
        src=pipeline.get_by_name('src');dst=pipeline.get_by_name('dst')
        try:
            assert pipeline.set_state(Gst.State.PLAYING)!=Gst.StateChangeReturn.FAILURE
            for index in range(12):
                buffer=Gst.Buffer.new_allocate(None,len(raw),None);buffer.fill(0,raw)
                buffer.pts=index*Gst.SECOND//30;buffer.duration=Gst.SECOND//30
                assert src.emit('push-buffer',buffer)==Gst.FlowReturn.OK
                item=dst.emit('try-pull-sample',Gst.SECOND)
                assert item is not None,'Synthetic appsrc sample timeout'
                # Real item and Gst.Buffer pass through the exact callback.
                facade=SimpleNamespace(emit=lambda unused:item)
                assert cb(facade)==0 and not state.camera_error
                actual=latest[0][2];assert actual.flags.owndata and actual.flags.c_contiguous
                del buffer,item,facade
                np.testing.assert_array_equal(actual,expected)
            results.append({'variant':name,'real_gst_buffers_checked':12,'pixels_and_ownership_passed':True})
        finally:
            pipeline.set_state(Gst.State.NULL)
            change,current,pending=pipeline.get_state(2*Gst.SECOND)
            assert current==Gst.State.NULL,'Synthetic pipeline did not release'
    a,_,_=callback(source);b,_,_=callback(candidate);item=sink(raw);rows=[]
    for cb in (a,b):measure(cb,item,8)
    for pair in range(6):
        row={'pair':pair,'order':['original','candidate'] if pair%2==0 else ['candidate','original']}
        for name in row['order']:
            row[name]=measure(a if name=='original' else b,item,40);time.sleep(.15)
        rows.append(row)
    after=health();assert after['pid']==before['pid'] and after['detected_frames']>before['detected_frames']
    assert not after['camera_error'] and not after['detector_error']
    orig=statistics.median(row['original']['process_cpu_ms_per_call'] for row in rows)
    opt=statistics.median(row['candidate']['process_cpu_ms_per_call'] for row in rows)
    print(json.dumps({'scope':'REAL_GSTREAMER_SYNTHETIC_BUFFER_CALLBACK_ACCEPTANCE_AND_MATCHED_CPU_MICROBENCHMARK',
        'opencv_threads':cv2.getNumThreads(),'opencv':cv2.__version__,'gstreamer_version':Gst.version_string(),
        'source_sha256':EXPECTED,'candidate_sha256':hashlib.sha256(candidate.encode()).hexdigest(),
        'gst_checks':results,'pairs':rows,'median_original_cpu_ms':orig,'median_candidate_cpu_ms':opt,
        'cpu_reduction_fraction_in_callback_only':1-opt/orig,'camera_before':before,'camera_after':after,
        'real_camera_opened':False,'audio_opened':False,'dpu_opened':False,'production_modified':False,
        'scope_limit':'GStreamer buffers are generated synthetic BGR, not UVC capture; benchmark extract_dup is simulated; no whole-board CPU gain or live deployment acceptance'}))

gst_check()
