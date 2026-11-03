"""Bounded synthetic Gst comparison. No camera, screen, models, files or frames exported.

ROOT schedules this on the board. Example:
python3 -B - --frames 30 --rounds 2 --sizes 568x300,587x440
Input arrives through stdin when executed with the existing strict SSH helper.
"""
import argparse
import hashlib
import json
import os
import statistics
import time

os.environ['GST_REGISTRY_UPDATE'] = 'no'
import gi
gi.require_version('Gst','1.0')
gi.require_version('GstVideo','1.0')
from gi.repository import Gst, GstVideo
Gst.init(None)

WIDTH, HEIGHT = 640, 480
PIXELS = WIDTH*HEIGHT*3
CHAINS = {'original':'videoconvert ! videoscale', 'candidate':'videoscale ! videoconvert'}

def patterns():
    bars = ((17,33,219),(211,57,29),(71,203,91),(255,255,255),(0,0,0),(53,169,241),(123,67,199),(227,181,13))
    row = b''.join(bytes(pixel)*(WIDTH//len(bars)) for pixel in bars)
    check_a=(bytes((11,97,241))*16+bytes((223,59,17))*16)*(WIDTH//32)
    check_b=(bytes((223,59,17))*16+bytes((11,97,241))*16)*(WIDTH//32)
    return {'black':bytes(PIXELS),'white':b'\xff'*PIXELS,
            'color_bars':row*HEIGHT,
            'sharp_grid':b''.join(check_a if (y//16)%2==0 else check_b for y in range(HEIGHT))}

def pipeline(chain,width,height,format):
    description = ('appsrc name=input is-live=true format=time block=false max-bytes=921600 '
        'caps="video/x-raw,format=BGR,width=640,height=480,framerate=0/1,pixel-aspect-ratio=1/1" ! '
        'queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream ! '
        +CHAINS[chain]+' ! video/x-raw,format='+format+',width='+str(width)+',height='+str(height)+
        ',pixel-aspect-ratio=1/1 ! appsink name=output sync=false async=false max-buffers=1 drop=false')
    graph=Gst.parse_launch(description)
    if graph.set_state(Gst.State.PLAYING)==Gst.StateChangeReturn.FAILURE:
        graph.set_state(Gst.State.NULL)
        raise RuntimeError('Cannot start synthetic pipeline')
    return graph,graph.get_by_name('input'),graph.get_by_name('output')

def push(source,sink,pixels,index):
    buffer=Gst.Buffer.new_allocate(None,len(pixels),None)
    buffer.fill(0,pixels);buffer.offset=index;buffer.pts=index*Gst.MSECOND
    assert source.emit('push-buffer',buffer)==Gst.FlowReturn.OK
    sample=sink.emit('try-pull-sample',3*Gst.SECOND)
    if sample is None:raise RuntimeError('Synthetic output timed out')
    return sample

def packed(sample):
    info=GstVideo.VideoInfo.new_from_caps(sample.get_caps()) if hasattr(GstVideo.VideoInfo,'new_from_caps') else GstVideo.VideoInfo()
    if not hasattr(GstVideo.VideoInfo,'new_from_caps'):assert info.from_caps(sample.get_caps())
    buffer=sample.get_buffer();ok,mapping=buffer.map(Gst.MapFlags.READ)
    assert ok
    try:
        raw=bytes(mapping.data)
        bpp=3 if info.finfo.name in ('BGR','RGB') else 4
        assert len(raw)>=info.size
        visible=b''.join(raw[y*info.stride[0]:y*info.stride[0]+info.width*bpp] for y in range(info.height))
        return {'width':info.width,'height':info.height,'format':info.finfo.name,'bpp':bpp,
                'data':visible,'offset':buffer.offset,'pts':buffer.pts}
    finally:buffer.unmap(mapping)

def error(left,right):
    assert len(left)==len(right)
    if left==right:return {'maximum':0,'mean':0.0,'differing_bytes':0}
    values=[abs(a-b) for a,b in zip(left,right)]
    return {'maximum':max(values),'mean':sum(values)/len(values),'differing_bytes':sum(v!=0 for v in values)}

def compare(left,right):
    assert (left['width'],left['height'],left['format'],left['offset'],left['pts'])==(right['width'],right['height'],right['format'],right['offset'],right['pts'])
    assert left['bpp']==right['bpp']
    if left['bpp']==3:
        result={'visible':error(left['data'],right['data']),'alpha':None,'x_padding_equal':None}
    else:
        a,b=left['data'],right['data']
        channels=[error(a[index::4],b[index::4]) for index in range(3)]
        result={'visible':{'maximum':max(c['maximum'] for c in channels),
            'mean':sum(c['mean'] for c in channels)/3,'differing_bytes':sum(c['differing_bytes'] for c in channels)},
            'alpha':error(a[3::4],b[3::4]) if left['format']=='BGRA' else None,
            'x_padding_equal':a[3::4]==b[3::4] if left['format'].endswith('x') else None}
    # First/last rows exercise scale borders and letterbox output.
    stride=left['width']*left['bpp']
    a=left['data'][:stride]+left['data'][-stride:]
    b=right['data'][:stride]+right['data'][-stride:]
    if left['format'].endswith('x'):
        channels=[error(a[index::4],b[index::4]) for index in range(3)]
        result['top_bottom_rows']={'maximum':max(c['maximum'] for c in channels),
            'mean':sum(c['mean'] for c in channels)/3,'differing_bytes':sum(c['differing_bytes'] for c in channels)}
    else:result['top_bottom_rows']=error(a,b)
    return result

def equivalence(sizes,formats,cases):
    results=[]
    for width,height in sizes:
        for format in formats:
            pipes={}
            try:
                for name in CHAINS:pipes[name]=pipeline(name,width,height,format)
                for index,(label,pixels) in enumerate(cases.items(),1):
                    images={name:packed(push(source,sink,pixels,index)) for name,(_,source,sink) in pipes.items()}
                    result=compare(images['original'],images['candidate'])
                    results.append(dict(size=[width,height],format=format,pattern=label,**result))
            finally:
                for graph,_,_ in pipes.values():graph.set_state(Gst.State.NULL)
    return results

def performance(sizes,pixels,frames,rounds):
    results=[]
    for width,height in sizes:
        for round_number in range(rounds):
            order=('original','candidate') if round_number%2==0 else ('candidate','original')
            for name in order:
                graph,source,sink=pipeline(name,width,height,'BGRx')
                try:
                    for index in range(1,5):push(source,sink,pixels,index)
                    wall=time.perf_counter();cpu=time.process_time()
                    for index in range(5,frames+5):push(source,sink,pixels,index)
                    cpu_ms=(time.process_time()-cpu)*1000
                    wall_ms=(time.perf_counter()-wall)*1000
                    results.append({'size':[width,height],'round':round_number+1,'chain':name,'frames':frames,
                        'process_cpu_ms':cpu_ms,'wall_ms':wall_ms,'cpu_ms_per_frame':cpu_ms/frames,
                        'wall_ms_per_frame':wall_ms/frames})
                finally:graph.set_state(Gst.State.NULL)
    summaries=[]
    for size in sizes:
        rows={name:[r['cpu_ms_per_frame'] for r in results if tuple(r['size'])==size and r['chain']==name] for name in CHAINS}
        a,b=statistics.median(rows['original']),statistics.median(rows['candidate'])
        summaries.append({'size':list(size),'original_cpu_ms_per_frame_median':a,
                          'candidate_cpu_ms_per_frame_median':b,'candidate_cpu_reduction_percent':(a-b)/a*100})
    return results,summaries

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--frames',type=int,default=30)
    parser.add_argument('--rounds',type=int,default=2)
    parser.add_argument('--sizes',default='568x300,587x440,640x480')
    parser.add_argument('--formats',default='BGR,RGB,BGRx,RGBx,BGRA')
    args=parser.parse_args()
    assert 10<=args.frames<=120 and 1<=args.rounds<=4
    sizes=[tuple(map(int,part.split('x'))) for part in args.sizes.split(',')]
    assert sizes and len(sizes)<=4 and all(32<=w<=960 and 32<=h<=720 for w,h in sizes)
    formats=args.formats.split(',');assert formats and set(formats)<={'BGR','RGB','BGRx','RGBx','BGRA'}
    cases=patterns();assert all(len(pixels)==PIXELS for pixels in cases.values())
    started=time.monotonic()
    comparisons=equivalence(sizes,formats,cases)
    equal=all(r['visible']['maximum']==0 and (r['alpha'] is None or r['alpha']['maximum']==0) for r in comparisons)
    raw,summary=performance(sizes,cases['color_bars'],args.frames,args.rounds)
    print(json.dumps({'status':'SYNTHETIC_COMPARE_PASS' if equal else 'PIXEL_EQUIVALENCE_FAILED_DO_NOT_DEPLOY',
        'gst_version':Gst.version_string(),'duration_s':time.monotonic()-started,
        'strict_visible_pixels_and_alpha_equal':equal,'comparisons':comparisons,
        'performance':raw,'performance_summary':summary,
        'comparison_scope':'Synthetic appsrc through original convert/scale elements into appsink; X11 sink and live-source timing require subsequent actual GUI verification.',
        'source_dimensions':[WIDTH,HEIGHT],'input_color_format':'BGR',
        'no_camera_screen_models_database_or_motion':True,'images_or_audio_exported':False}))

if __name__=='__main__':main()
