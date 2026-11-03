"""Harden the reviewed synthetic benchmark without touching the GTK candidate."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
source=HERE.parent/'gtk/gst_synthetic_compare.py'
raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='ef9eedd2dfe5f57f921280310d9b59a400762ba91c843efd0d9e0a873139c296'
code=raw.decode().replace('\r\n','\n')

def replace(old,new):
    global code
    assert code.count(old)==1, old[:80]
    code=code.replace(old,new)

replace("CHAINS = {'original':'videoconvert ! videoscale', 'candidate':'videoscale ! videoconvert'}",
    "CHAINS = {'original':'videoconvert ! videoscale', 'candidate':'videoscale ! videoconvert'}\nDEADLINE = float('inf')")
replace("    sample=sink.emit('try-pull-sample',3*Gst.SECOND)\n    if sample is None:raise RuntimeError('Synthetic output timed out')\n    return sample",
    "    remaining=DEADLINE-time.monotonic()\n    if remaining<=0:raise RuntimeError('Synthetic global deadline expired')\n    sample=sink.emit('try-pull-sample',int(min(3,remaining)*Gst.SECOND))\n    if sample is None:raise RuntimeError('Synthetic output timed out')\n    returned=sample.get_buffer()\n    assert int(returned.offset)==index and int(returned.pts)==index*Gst.MSECOND\n    return sample")
begin=code.index('def packed(sample):')
end=code.index('def error(left,right):',begin)
code=code[:begin]+'''def packed(sample):
    caps=sample.get_caps()
    info=GstVideo.VideoInfo.new_from_caps(caps) if hasattr(GstVideo.VideoInfo,'new_from_caps') else GstVideo.VideoInfo()
    if not hasattr(GstVideo.VideoInfo,'new_from_caps'):assert info.from_caps(caps)
    bpp={'BGR':3,'RGB':3,'BGRx':4,'RGBx':4,'BGRA':4}[info.finfo.name]
    buffer=sample.get_buffer()
    meta=GstVideo.buffer_get_video_meta(buffer) if hasattr(GstVideo,'buffer_get_video_meta') else None
    if meta is not None:
        assert meta.n_planes==1 and (meta.width,meta.height)==(info.width,info.height)
        assert int(meta.format)==int(info.finfo.format)
        stride,offset=int(meta.stride[0]),int(meta.offset[0])
    else:
        stride,offset=int(info.stride[0]),int(info.offset[0])
    # Nondefault positive packed strides are valid. Never guess negative layouts.
    assert stride>=info.width*bpp and offset>=0
    ok,mapping=buffer.map(Gst.MapFlags.READ);assert ok
    try:
        raw=bytes(mapping.data)
        assert len(raw)>=offset+(info.height-1)*stride+info.width*bpp
        visible=b''.join(raw[offset+y*stride:offset+y*stride+info.width*bpp] for y in range(info.height))
        return {'width':info.width,'height':info.height,'format':info.finfo.name,'bpp':bpp,
                'data':visible,'offset':buffer.offset,'pts':buffer.pts,
                'caps':caps.to_string(),'row_stride':stride,'plane_offset':offset}
    finally:buffer.unmap(mapping)

def negotiated(graph):
    result={};iterator=graph.iterate_elements();resyncs=0
    while True:
        status,element=iterator.next()
        if status==Gst.IteratorResult.DONE:break
        if status==Gst.IteratorResult.RESYNC:
            resyncs+=1;assert resyncs<=2;iterator.resync();continue
        assert status==Gst.IteratorResult.OK
        factory=element.get_factory()
        if factory is None:continue
        name=factory.get_name()
        if name not in ('videoconvert','videoscale'):continue
        pads={}
        for label in ('sink','src'):
            caps=element.get_static_pad(label).get_current_caps()
            assert caps is not None and not caps.is_empty()
            pads[label]=caps.to_string()
        assert name not in result
        result[name]=pads
    assert set(result)=={'videoconvert','videoscale'}
    return result

'''+code[end:]
replace("                    result=compare(images['original'],images['candidate'])\n                    results.append(dict(size=[width,height],format=format,pattern=label,**result))",
    "                    assert all((image['width'],image['height'],image['format'])==(width,height,format) for image in images.values())\n                    result=compare(images['original'],images['candidate'])\n                    layouts={name:{key:image[key] for key in ('caps','row_stride','plane_offset')} for name,image in images.items()}\n                    results.append(dict(size=[width,height],format=format,pattern=label,layouts=layouts,negotiated={name:negotiated(pipes[name][0]) for name in CHAINS},**result))")
replace("                    for index in range(1,5):push(source,sink,pixels,index)\n                    wall=time.perf_counter();cpu=time.process_time()",
    "                    for index in range(1,5):warmed=push(source,sink,pixels,index)\n                    info=packed(warmed)\n                    assert (info['width'],info['height'],info['format'])==(width,height,'BGRx')\n                    actual_caps=negotiated(graph)\n                    wall=time.perf_counter();cpu=time.process_time()")
replace("                        'process_cpu_ms':cpu_ms,'wall_ms':wall_ms,'cpu_ms_per_frame':cpu_ms/frames,",
    "                        'negotiated':actual_caps,'process_cpu_ms':cpu_ms,'wall_ms':wall_ms,'cpu_ms_per_frame':cpu_ms/frames,")
replace("def main():\n    parser=argparse.ArgumentParser()",
    "def main():\n    global DEADLINE\n    parser=argparse.ArgumentParser()")
replace("    parser.add_argument('--formats',default='BGR,RGB,BGRx,RGBx,BGRA')\n    args=parser.parse_args()",
    "    parser.add_argument('--formats',default='BGR,RGB,BGRx,RGBx,BGRA')\n    parser.add_argument('--deadline-s',type=float,default=60)\n    args=parser.parse_args()\n    assert 5<=args.deadline_s<=180\n    DEADLINE=time.monotonic()+args.deadline_s")
replace("    raw,summary=performance(sizes,cases['color_bars'],args.frames,args.rounds)",
    "    if not equal:\n        print(json.dumps({'status':'PIXEL_EQUIVALENCE_FAILED_DO_NOT_DEPLOY','strict_visible_pixels_and_alpha_equal':False,'comparisons':comparisons,'performance_skipped':True}))\n        raise SystemExit(2)\n    raw,summary=performance(sizes,cases['color_bars'],args.frames,args.rounds)")
replace("        'source_dimensions':[WIDTH,HEIGHT],'input_color_format':'BGR',",
    "        'reviewed_production_original_sha256':'6e697c16f7ae264dff56b6b35f38da4b531ea13026b69a7c8bdbfb1960a6afcd',\n        'reviewed_production_candidate_sha256':'022098636a41b35bc17929da1cbef0f05e5c257640f9b64a8504c1b4a13e7127',\n        'compared_chains':CHAINS,'source_dimensions':[WIDTH,HEIGHT],'input_color_format':'BGR',")
compile(code,'<hardened-gst-benchmark>','exec')
destination=HERE/'gst_synthetic_compare_hardened.py'
destination.write_text(code,encoding='utf-8')
manifest={'source_sha256':hashlib.sha256(raw).hexdigest(),
    'hardened_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
    'hardened_sha256_lf':hashlib.sha256(code.encode()).hexdigest(),
    'network_or_board_execution':False,
    'changes':['actual VideoMeta stride/offset when present','exact requested format/dimensions',
        'all pushed frame offset/PTS checked','negotiated converter/scaler pad caps recorded',
        'global deadline bounds each pull','pixel mismatch skips perf and exits 2']}
(HERE/'GST_BENCHMARK_HARDENING.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest))
