"""Wired device observations and CPU voice templates; no actuator endpoints."""
import argparse,base64,json,os,threading,time,sqlite3
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from common.device_memory import ObservationStore
from common.visual_question import validate_jpeg
from tools.visual_question_host import LocalVisualQuestion

class Hub:
    def __init__(self,root,model_directory,calibration=None,timeline=None,*,anonymous_config=None,encoder_factory=None,private_root_validator=None):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.timeline=timeline
        if timeline:
            from common.timeline_observations import TimelineObservationStore
            self.observations=TimelineObservationStore(self.root/'observations.sqlite3',device_id=timeline['device_id'],
                history_days=timeline['visual_history_days'],history_limit=timeline['visual_event_limit'])
            self.observations.start_summaries(zone=timeline['timezone'])
        else:self.observations=ObservationStore(self.root/'observations.sqlite3')
        self.visual=LocalVisualQuestion();self.visual_lock=threading.Lock()
        self.speaker_pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='speaker-cpu')
        self.speaker_gate=threading.Lock();self.speaker=None;self.speaker_error='initializing'
        self.binding=None;self.binding_error='disabled'
        from tools.speaker_turns import SpeakerTurns
        self.speaker_turns=SpeakerTurns(self)
        self.visual_error='';self.last_visual=None;self.last_frame={}
        def initialize():
            try:
                from tools.speaker_device import SpeakerDevice
                if encoder_factory is None:
                    import torch
                    from common.speaker_identity import EcapaEncoder
                    torch.set_num_threads(2);encoder=EcapaEncoder(model_directory)
                else:encoder=encoder_factory(model_directory)
                self.speaker=SpeakerDevice(encoder,self.root/'speakers.sqlite3',calibration=calibration)
                self.speaker_error=''
                if anonymous_config and anonymous_config.get('enabled') is True:
                    try:
                        from tools.binding_hub_runtime import BindingHubRuntime
                        options={} if private_root_validator is None else {'validate_root':private_root_validator}
                        self.binding=BindingHubRuntime(self,anonymous_config,**options);self.binding_error=''
                    except Exception as exc:self.binding_error=type(exc).__name__+': '+str(exc)[:160]
            except Exception as exc:self.speaker_error=type(exc).__name__+': '+str(exc)[:160]
        self.speaker_pool.submit(initialize)
    def observe(self,value):
        if set(value)!={'frame','jpeg_base64'}:raise ValueError('Unexpected observation fields')
        jpeg=base64.b64decode(value['jpeg_base64'],validate=True);frame=value['frame'];validate_jpeg(frame,jpeg)
        if not self.visual_lock.acquire(False):return {'accepted':False,'reason':'busy'}
        key=(frame['board_boot_id'],frame['camera_epoch'])
        if frame['frame_id']<=self.last_frame.get(key,-1):self.visual_lock.release();raise ValueError('Replayed visual frame')
        self.last_frame[key]=frame['frame_id']
        while len(self.last_frame)>8:self.last_frame.pop(next(iter(self.last_frame)))
        received=time.time();generation=self.observations.generation(frame['board_boot_id'])
        def summarize():
            try:
                reply=self.visual.answer('用一句简短中文描述当前可见的物体、位置与动作。不要识别身份，不推测画外内容。',
                    frame,jpeg,deadline=time.monotonic()+12,cancelled=threading.Event())
                self.observations.add(frame,reply['reply_text'],received,generation=generation)
                self.last_visual=time.time();self.visual_error=''
            except Exception as exc:self.visual_error=type(exc).__name__+': '+str(exc)[:100]
            finally:self.visual_lock.release()
        threading.Thread(target=summarize,name='bounded-camera-observation',daemon=True).start()
        return {'accepted':True,'image_persisted':False}
    def speaker_call(self,method,*args):
        if self.speaker is None:raise ValueError('Speaker model unavailable: '+self.speaker_error)
        if not self.speaker_gate.acquire(False):raise ValueError('Speaker worker busy')
        future=self.speaker_pool.submit(self._speaker_method,method,args)
        future.add_done_callback(lambda _:self.speaker_gate.release())
        return future.result(timeout=12)
    def _speaker_method(self,method,args):
        value=getattr(self.speaker,method)(*args)
        if method=='turn' and getattr(self,'binding',None) is not None:self.binding.after_original_voice_turn(args[0],args[1])
        return value
    def binding_call(self,path,value):
        if self.binding is None:raise ValueError('Binding runtime unavailable')
        if not self.speaker_gate.acquire(False):raise ValueError('Speaker worker busy')
        from tools.binding_dispatch import dispatch
        job={'value':value,'cancelled':False}
        def run():
            if job['cancelled']:raise InterruptedError('Binding request expired')
            body=job['value'];job['value']=None
            try:return dispatch(self.binding,path,body)
            finally:
                if isinstance(body,dict) and 'pcm' in body:body['pcm']=None
        try:future=self.speaker_pool.submit(run)
        except Exception:self.speaker_gate.release();raise
        future.add_done_callback(lambda _:self.speaker_gate.release())
        try:return future.result(timeout=12)
        finally:
            job['cancelled']=True
            body=job['value'];job['value']=None
            if isinstance(body,dict) and 'pcm' in body:body['pcm']=None
            future.cancel()
    def analysis_submit(self,meta,pcm,cid,visual):
        value=self.binding.precomputed_analysis(meta,cid,visual) if self.binding is not None else None
        if value is not None:
            # Preserve normal result/cancel receipt ownership without a CPU job.
            from common.asr_wire import context
            meta=context(meta,pcm);service=self.speaker_turns;key=service.key(meta)
            with service.lock:
                service._expire();old=service.rows.get(key)
                if old is not None:return service._row(meta,cid)['value']
                actor=service.actor(meta);previous=service.latest.get(actor)
                if previous is not None and meta['generation']<=previous[0]:raise ValueError('Stale or reused speaker generation')
                service.latest[actor]=(meta['generation'],meta['request_id']);service.latest.move_to_end(actor)
                while len(service.latest)>32:
                    removed,_=service.latest.popitem(last=False);service.streaks.pop(removed,None)
                if value['voice'] is None:service.streaks.pop(actor,None)
                now=service.clock()
                while len(service.rows)>=service.max_rows:
                    removed,_=service.rows.popitem(last=False);service._release_pending(removed)
                service.rows[key]=dict(meta=meta,cid=cid,visual=value['visual'],value=value,deadline=now,remove_at=now+service.result_lifetime)
                return value
        return self.speaker_turns.submit(meta,pcm,cid,visual)
    def health(self):
        return {'version':1,'revision':'device-timeline-v2' if self.timeline else 'device-skills-v1','pid':os.getpid(),'speaker_ready':self.speaker is not None,'speaker_error':self.speaker_error,
            'visual_error':self.visual_error,'last_visual_unix':self.last_visual,'image_persisted':False,
            'observation_retention_seconds':86400,'observation_limit':1000,
            'speaker_calibrated':bool(self.speaker and self.speaker.calibrated),'automatic_profile_access':False,
            'speaker_turn_attribution':self.speaker_turns.health(),
            'anonymous_binding':{'version':1,'enabled':self.binding is not None,'error':self.binding_error,'automatic_profile_access':False},
            'motion_control':False,'timeline':self.observations.timeline_health() if self.timeline else {'version':0}}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass  # Never log bodies, names, images or PCM.
    def reply(self,code,value):
        raw=json.dumps(value,ensure_ascii=False).encode()
        self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
    def allowed(self):return self.client_address[0] in ('127.0.0.1','192.168.50.1','192.168.50.2') and not self.headers.get('Origin')
    def do_GET(self):
        if not self.allowed():self.reply(403,{'error':'Wired device access only'});return
        self.reply(200,self.server.hub.health()) if self.path=='/health' else self.reply(404,{'error':'Unknown route'})
    def do_POST(self):
        if not self.allowed():self.reply(403,{'error':'Wired device access only'});return
        self.connection.settimeout(4)
        try:
            if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length',[]))!=1:raise ValueError('Bounded body required')
            size=int(self.headers['Content-Length'])
            if not 1<=size<=900000 or self.headers.get('Content-Type')!='application/json':raise ValueError('Invalid body')
            v=json.loads(self.rfile.read(size));hub=self.server.hub
            if self.path.startswith('/v1/binding/'):
                if self.client_address[0]!='127.0.0.1':raise ValueError('Binding requires loopback model adapter')
                out=hub.binding_call(self.path,v)
            elif self.path=='/v1/observations':out=hub.observe(v)
            elif self.path in ('/v1/memory/timeline','/v1/memory/timeline/forget','/v1/memory/revision'):
                if not hub.timeline:raise ValueError('Timeline not configured')
                if self.client_address[0] not in ('127.0.0.1','192.168.50.1'):raise ValueError('Timeline requires local model adapter')
                if not isinstance(v.get('boot'),str) or not 1<=len(v['boot'])<=64:raise ValueError('Invalid boot')
                from common.timeline import query,episode_excerpts
                from common.timeline_summaries import summary_mode
                if self.path.endswith('/revision'):
                    if set(v)!={'boot'}:raise ValueError('Unexpected revision fields')
                    out={'version':1,'revision':hub.observations.generation(v['boot'])}
                else:
                    if set(v)!={'boot','text'}:raise ValueError('Unexpected timeline fields')
                    q=query(v['text'],now=time.time(),zone=hub.timeline['timezone'])
                    # Read sources and their revision atomically, avoiding a forget race.
                    if not hub.observations.lock.acquire(timeout=.03):raise TimeoutError('Timeline busy')
                    try:
                        if self.path.endswith('/forget'):
                            out=({'error':q['error']} if q['error'] else {'deleted_events':hub.observations.forget_timeline(q)})
                        else:
                            mode=summary_mode(v['text'])
                            rows=[]
                            if mode and hasattr(hub.observations,'summary_events'):
                                try:rows=hub.observations.summary_events(q,kind=mode)
                                except (sqlite3.Error,TimeoutError):pass
                            cached=bool(rows)
                            if not rows:rows=hub.observations.timeline_events(q,limit=6)
                            out={'events':rows,'episodes':[] if cached else episode_excerpts(rows,zone=q['zone']),'query':q,'background_digest_used':cached}
                        out.update(version=1,revision=hub.observations.generation(v['boot']))
                    finally:hub.observations.lock.release()
            elif self.path in ('/v1/memory/recall','/v1/memory/forget'):
                if not isinstance(v.get('boot'),str) or not 1<=len(v['boot'])<=64:raise ValueError('Invalid boot')
                if self.path.endswith('/forget'):hub.observations.forget(v['boot']);out={'cleared':True}
                else:
                    with hub.observations.lock:
                        out={'observations':hub.observations.recall(v['boot'],history=v.get('history') is True)}
                        if hub.timeline:out['revision']=hub.observations.generation(v['boot'])
            elif self.path in ('/v1/speaker/analysis/submit','/v1/speaker/analysis/result','/v1/speaker/analysis/cancel'):
                if self.client_address[0] not in ('127.0.0.1','192.168.50.1'):raise ValueError('Speaker attribution requires local model adapter')
                if self.path.endswith('/submit'):
                    if set(v)!={'context','conversation_id','pcm','visual'}:raise ValueError('Unexpected speaker analysis fields')
                    pcm=base64.b64decode(v['pcm'],validate=True)
                    try:out=getattr(hub,'analysis_submit',hub.speaker_turns.submit)(v['context'],pcm,v['conversation_id'],v['visual'])
                    finally:pcm=None;v['pcm']=None
                else:
                    if set(v)!={'context','conversation_id'}:raise ValueError('Unexpected speaker receipt fields')
                    method=hub.speaker_turns.cancel if self.path.endswith('/cancel') else hub.speaker_turns.result
                    out=method(v['context'],v['conversation_id'])
            elif self.path=='/v1/speaker/state':out=hub.speaker_call('state',v['context'])
            elif self.path=='/v1/speaker/turn':
                if not isinstance(v['text'],str) or len(v['text'])>2000:raise ValueError('Invalid text')
                pcm=base64.b64decode(v['pcm'],validate=True)
                from common.asr_wire import context
                context(v['context'],pcm)
                out={'reply':hub.speaker_call('turn',v['context'],v['text'],pcm)}
            else:self.reply(404,{'error':'Unknown route'});return
            self.reply(200,out)
        except sqlite3.Error:self.reply(503,{'error':'Device memory temporarily unavailable'})
        except (OSError,ValueError,TypeError,KeyError,TimeoutError):self.reply(400,{'error':'Device request rejected or unavailable'})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--speaker-model',type=Path,required=True);parser.add_argument('--calibration',type=Path)
    parser.add_argument('--listen',default='192.168.50.1');args=parser.parse_args()
    if args.listen not in ('127.0.0.1','192.168.50.1'):raise ValueError('Use the wired/local address')
    c=json.loads(args.calibration.read_text()) if args.calibration and args.calibration.exists() else None
    server=ThreadingHTTPServer((args.listen,8812),Handler);server.daemon_threads=True
    from common.timeline_config import load_config
    timeline=load_config(Path(__file__).resolve().parents[1]/'config/timeline_memory.json')
    anonymous_path=Path(__file__).resolve().parents[1]/'config/anonymous_identity.local.json'
    anonymous=json.loads(anonymous_path.read_text(encoding='utf-8')) if anonymous_path.exists() else None
    server.hub=Hub(args.root,args.speaker_model,c,timeline=timeline,anonymous_config=anonymous)
    # Also expose loopback for the host's model-side adapter; never all interfaces.
    if args.listen!='127.0.0.1':
        local=ThreadingHTTPServer(('127.0.0.1',8812),Handler);local.daemon_threads=True;local.hub=server.hub
        threading.Thread(target=local.serve_forever,daemon=True).start()
    server.serve_forever()

if __name__=='__main__':main()
