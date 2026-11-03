"""Assemble from the frozen 55-test transport and explicit frozen dependencies."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;BASE=H.parent;ANON=BASE.parent/'2026-10-29_anonymous_identity_binding'
C=H/'candidate'
for name in ('board/runtime/audio/channel_jobs.py','board/runtime/audio/voice_channel.py','common/speaker_visual.py'):
 p=C/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((BASE/'candidate'/name).read_bytes())
for name in ('common/binding_intent.py','tools/enrollment_receipts.py'):
 p=C/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ANON/'candidate'/name).read_bytes())

path=C/'board/runtime/audio/channel_jobs.py';s=path.read_text(encoding='utf-8')
s=s.replace('import hashlib\n','import hashlib\nfrom contextlib import nullcontext\n',1)
s=s.replace("        self.identity_flow=VoiceEnrollment(boot_id,self._identity_snapshot,self._identity_command,simple=True)",
'''        from board.runtime.audio.face_gallery_readback import FaceGalleryReadback
        from board.runtime.audio.face_binding_bridge import FaceBindingBridge
        self.face_readback=FaceGalleryReadback.configured()
        self.face_binding=FaceBindingBridge(self._identity_snapshot,self._identity_command,self.face_readback)
        self.identity_flow=VoiceEnrollment(boot_id,self.face_binding.snapshot,self.face_binding.command,simple=True)''',1)
needle='    def _record_voice_route(self,meta,header,reply_code=\'\'):'
addition='''    def _face_gallery(self,meta):
        # Private SQLite readback is on this network worker, never GTK/capture.
        reader=getattr(self,'face_readback',None)
        if reader is None:return None
        try:
            snapshot=self.identity_snapshot() if self.identity_snapshot else None
            return reader.read(meta,snapshot)
        except (OSError,ValueError,KeyError,TypeError):return None

    def _face_reply(self,channel,meta,token,reply,exchange,*,sequence=None,final=True):
        receipt=None
        if exchange is not None and final:
            try:receipt=exchange.receipt(reply,self.face_binding.original_snapshot)
            except (OSError,ValueError,KeyError,TypeError):receipt=None
        kwargs=dict(sequence=sequence,final=final)
        if receipt is not None:kwargs['binding_receipt']=receipt
        channel.identity_result(meta,token,reply,**kwargs)

'''
assert needle in s;s=s.replace(needle,addition+needle,1)
old="""                            reply=self.identity_flow.handle(header['text'],start_owner,is_current=current)
"""
new="""                            from common.binding_intent import face_enrollment_text
                            binding_request=header.get('binding_request');exchange=None
                            board_text=header['text']
                            if binding_request is not None:
                                exchange=self.face_binding.exchange(meta,binding_request,start_owner,header['text'],current)
                                board_text=exchange.request['board_text']
                            # Narrow normalization stays inside the original
                            # authorized identity branch. Transcript is unchanged.
                            board_text=face_enrollment_text(board_text,active=self.identity_flow.public()['active'])
                            with self.face_binding.scope(exchange) if exchange is not None else nullcontext():
                                reply=self.identity_flow.handle(board_text,start_owner,is_current=current)
"""
assert old in s;s=s.replace(old,new,1)
old="""                                def emit(value,final,channel=channel,meta=meta,token=token,sequence=sequence,current=current):
                                    if not current():raise InterruptedError('Stale sampling guidance')
                                    channel.identity_result(meta,token,value,sequence=sequence[0],final=final)
                                    sequence[0]+=1
                                emit(reply,False)
                                threading.Thread(target=self.identity_flow.guide,args=(emit,),
                                    kwargs={'is_current':current},name='identity-sampling-guide',daemon=True).start()
                            else:channel.identity_result(meta,header['identity_request'],reply)
"""
new="""                                def emit(value,final,channel=channel,meta=meta,token=token,sequence=sequence,current=current,exchange=exchange):
                                    if not current():raise InterruptedError('Stale sampling guidance')
                                    self._face_reply(channel,meta,token,value,exchange,sequence=sequence[0],final=final)
                                    sequence[0]+=1
                                emit(reply,False)
                                def guide(exchange=exchange,emit=emit,current=current):
                                    with self.face_binding.scope(exchange) if exchange is not None else nullcontext():
                                        self.identity_flow.guide(emit,is_current=current)
                                threading.Thread(target=guide,name='identity-sampling-guide',daemon=True).start()
                            else:self._face_reply(channel,meta,header['identity_request'],reply,exchange)
"""
assert old in s;s=s.replace(old,new,1)
old="""                    if options.get('conversation') is not None:options['speaker_visual']=self._speaker_visual(meta)
                    result=channel.exchange"""
new="""                    if options.get('conversation') is not None:
                        options['speaker_visual']=self._speaker_visual(meta)
                        packet=self._face_gallery(meta)
                        if packet is not None:
                            try:
                                if channel.submit_face_gallery(meta,packet,is_current=current):options['face_gallery']=packet
                            except (OSError,ValueError,RuntimeError):pass  # Ordinary voice stays available.
                    result=channel.exchange"""
assert old in s;s=s.replace(old,new,1);path.write_text(s,encoding='utf-8',newline='\n')

path=C/'board/runtime/audio/voice_channel.py';s=path.read_text(encoding='utf-8')
s=s.replace('wake_entry=False,speaker_visual=None):','wake_entry=False,speaker_visual=None,face_gallery=None):',1)
needle='            if profile_token is not None:'
addition="""            if face_gallery is not None:
                from common.face_binding_wire import encode_gallery_header
                headers['X-Aura-Face-Gallery']=encode_gallery_header(face_gallery,meta)
"""
assert needle in s;s=s.replace(needle,addition+needle,1)
needle='                state.accept(header, payload)'
addition="""                if 'binding_request' in header:
                    if header.get('kind')!='transcript' or 'identity_request' not in header:
                        raise ValueError('Binding metadata requires the original identity token')
                    from common.face_binding_wire import validate_binding_request
                    validate_binding_request(header['binding_request'],meta)
"""
assert needle in s;s=s.replace(needle,addition+needle,1)
s=s.replace('def identity_result(self,meta,token,reply,*,sequence=None,final=True):','def identity_result(self,meta,token,reply,*,sequence=None,final=True,binding_receipt=None):',1)
needle="            if sequence is not None:body.update(sequence=sequence,final=final)"
addition="""            if binding_receipt is not None:
                if final is not True or reply['code'] not in ('registered','already_known'):
                    raise ValueError('Face receipt requires final original success result')
                from common.face_binding_wire import canonical
                if len(canonical(binding_receipt))<=4096:body['binding_receipt']=binding_receipt
"""
assert needle in s;s=s.replace(needle,addition+needle,1)
needle="            connection.request('POST','/v1/voice/identity/result',json.dumps(body).encode(),{'Content-Type':'application/json'})"
replacement="""            raw_body=json.dumps(body).encode()
            if len(raw_body)>4096 and 'binding_receipt' in body:
                # Retain the original result but provide no commit proof. The
                # host must keep unified binding incomplete, never truncate it.
                body.pop('binding_receipt');raw_body=json.dumps(body).encode()
            if len(raw_body)>4096:raise ValueError('Original identity result exceeds bound')
            connection.request('POST','/v1/voice/identity/result',raw_body,{'Content-Type':'application/json'})"""
assert needle in s;s=s.replace(needle,replacement,1)
addition="""
    def submit_face_gallery(self,meta,packet,*,is_current=lambda:True):
        from common.face_binding_wire import canonical,validate_packet,packet_sha256
        packet=validate_packet(packet,meta);digest=packet_sha256(packet)
        if not is_current():raise InterruptedError('Stale face gallery metadata')
        connection=http.client.HTTPConnection(self.host,self.port,timeout=.4)
        try:
            body=canonical(dict(context=meta,packet=packet))
            if len(body)>24576:return False
            connection.request('POST','/v1/voice/identity/gallery',body,{'Content-Type':'application/json'})
            response=connection.getresponse();raw=response.read(4097)
            if (response.status!=200 or len(raw)>4096):return False
            result=json.loads(raw)
            if not is_current():raise InterruptedError('Expired face gallery metadata')
            return result=={'accepted':True,'packet_sha256':digest}
        finally:connection.close()
"""
s+=addition;path.write_text(s,encoding='utf-8',newline='\n')

index=json.loads((H/'camera_source_index.json').read_text());entry=json.loads((H/'camera_entry.json').read_text())['camera']
process=json.loads((H/'camera_process_metadata.json').read_text());boot=json.loads((H/'board_preflight.json').read_text())['boot']
cfg='/home/root/aura-native-live-20261024/ops/be72669aa53de735/native-run-'+boot+'-'+str(process['pid'])+'/config.json'
camera=json.loads((H/'camera_source'/index[cfg]['local_name']).read_text());identity_path=camera['identity']['config']
identity=json.loads((H/'camera_source'/index[identity_path]['local_name']).read_text())
pins={name:v['sha256'] for name,v in index.items() if name!= '/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/face_source.py'}
pins.update({name:v['sha256'] for name,v in entry['sources'].items()})
readback=dict(version=1,enabled=True,board_boot_id=boot,camera_pid=process['pid'],camera_start_ticks=process['start_ticks'],
    camera_cmdline_sha256=process['cmdline_sha256'],camera_config=cfg,identity_config=identity_path,
    source_sha256=pins,database=identity['database'],model_id=identity['model_id'],dimension=128,
    model_sha256=identity['feature_backend']['model_sha256'],result_ttl_ms=identity['result_ttl_ms'],backend='DPU_SFACE_INT8')
path=C/'config/face_gallery_readback.local.json';path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps(readback,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'candidate_files':len(list(C.rglob('*.py')))+1,'identity_config_sha256':index[identity_path]['sha256'],
 'camera_runtime_config_sha256':index[cfg]['sha256'],'no_deployment':True}))
