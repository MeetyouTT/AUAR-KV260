import http.client as http_client
import json, traceback
try:
    """Actual production model, five invented turns, temporary isolated memory only."""
    import hashlib, http.client, json, sys, tempfile, time, traceback, uuid
    from pathlib import Path
    
    STARTUP=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
    assert hashlib.sha256(STARTUP.read_bytes()).hexdigest()=='69080f9877565d346329c8c3004071102349ca9f7d6779819004cf8ca405dfe3'
    cfg=json.loads(STARTUP.read_bytes()); aura=Path(cfg['runtime'])/'aura';sys.path.insert(0,str(aura))
    from common.board_memory import BoardMemoryStore
    from common.character_profile import selected_profile
    from common.model_inference_wire import Owner, validate_request, validate_response, decode_audio
    from board.runtime.board_memory_policy import BoardContextBuilder, message_cost
    from board.runtime.board_dialogue import validate_model_reply, address_reply, dialogue_thinking_test_options
    from board.runtime.compact_request_adapter import CompactRequestAdapter
    
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    assert dialogue_thinking_test_options(boot)=={} and not Path('/run/aura-dialogue-thinking-test.json').exists()
    session='public-five-round-'+uuid.uuid4().hex
    scope=dict(kind='conversation',id=session);source='conversation:'+session
    questions=['我养的小猫叫团团，它最喜欢蓝色。请记着，陪我聊几句。',
               '今天天气很好，陪我轻松聊聊。', '我准备下午去公园散步。',
               '走路累了可以怎么放松？', '第一轮我告诉你的宠物名字和喜欢的颜色是什么？']
    trace=[]; rows=[]; stage='HEALTH'; result={}
    
    def http(method,path,payload=None):
        c=http_client.HTTPConnection('192.168.50.1',8797,timeout=65)
        try:
            c.request(method,path,json.dumps(payload,ensure_ascii=False).encode() if payload else None,{'Content-Type':'application/json'})
            r=c.getresponse();raw=r.read(12000001); assert len(raw)<=12000000
            return r.status,json.loads(raw)
        finally:c.close()
    
    class Transport:
        def request(self,kind,payload,*,deadline,cancelled):
            assert not cancelled() and time.monotonic()<deadline
            validate_request(kind,payload);start=time.monotonic()
            code,value=http('POST','/v1/inference/'+kind,payload)
            row=dict(kind=kind,generation=payload['generation'],http_status=code,ok=value.get('ok'),
                     error_code=(value.get('error') or {}).get('code'),seconds=round(time.monotonic()-start,3),
                     output_format=payload.get('options',{}).get('output_format','json'),
                     think=payload.get('options',{}).get('think',False))
            trace.append(row)
            assert code==200 and value.get('ok'),row
            return validate_response(value,Owner.from_dict(payload),kind)
    
    try:
        code,health=http('GET','/health');assert code==200 and health['ok']
        assert not health['active'] and not health['pending'] and health['backend']['context_limit']==4096
        mode=json.loads((aura/'config/board_avatar_gtk.json').read_bytes())['board_business'].get('dialogue_output_format','json')
        prompt=selected_profile().persona_full_prompt
        b=BoardContextBuilder(prompt,context_limit=4096)
        t=Transport();client=t
        if mode!='json':
            client=CompactRequestAdapter(t,system_prompt=prompt,capabilities=dict(
                format_contract_version=health['backend']['format_contract_version'],output_formats=health['backend']['output_formats']),mode=mode)
        with tempfile.TemporaryDirectory(prefix='aura-public-five-round-') as temp:
            db=Path(temp)/'public.sqlite3';store=BoardMemoryStore(db,data_origin='board')
            for generation,question in enumerate(questions,1):
                stage='ROUND_'+str(generation)
                turn=session+'-'+str(generation)
                store.begin_turn(scope,turn,question,generation=generation,metadata={'source_id':source})
                context=store.context(scope,context_source_id=source)
                context['conversation_address']=dict(display_name='测试甲',face=dict(state='NO_FACE',display_name=None,face_count=0))
                messages=b(context,question)
                if generation==5:
                    assert all(dict(role='user',content=q) in messages for q in questions[:4])
                    assert '团团' not in question and '蓝色' not in question
                    assert b.metrics['prior_user_turns_included']==4 and b.metrics['five_turn_window_complete']
                payload=dict(protocol_version=1,request_id='public-llm-'+uuid.uuid4().hex,board_boot_id=boot,session_id=session,
                             generation=generation,budget_ms=60000,task='dialogue',messages=messages,options={})
                response=client.request('llm',payload,deadline=time.monotonic()+60,cancelled=lambda:False)
                reply=address_reply(validate_model_reply(response['result']['text'],question),'测试甲')
                row=dict(round=generation,question=question,reply=reply.text,context_metrics=dict(b.metrics),
                         prior_assistant_turns=sum(m['role']=='assistant' for m in messages),valid_named_reply='测试甲' in reply.text)
                rows.append(row)
                store.generated(turn,reply.text,generation=generation)
                # Public test fixture receipt only; never claims physical speaker playback.
                store.bind_audio_receipt(turn,generation=generation,playback_token=turn,sha256='a'*64,samples=240)
                store.ack_played(turn,generation=generation,playback_token=turn,sha256='a'*64,samples=240)
            assert '团团' in rows[4]['reply'] and '蓝色' in rows[4]['reply'], 'fifth_round_recall_failed'
            stage='TTS_PUBLIC_FIFTH_REPLY'
            audio=t.request('tts',dict(protocol_version=1,request_id='public-tts-'+uuid.uuid4().hex,board_boot_id=boot,
                session_id=session,generation=5,budget_ms=60000,text=rows[4]['reply']),deadline=time.monotonic()+60,cancelled=lambda:False)
            pcm,rate=decode_audio(audio['result']['audio']);assert pcm and rate==24000 and len(pcm)%2==0
            reopened=BoardMemoryStore(db,data_origin='board')
            assert len(reopened.context(scope,context_source_id=source)['messages'])==10
            result=dict(status='FIVE_ROUND_MODEL_RECALL_AND_TTS_PASSED',first_turn_recalled_on_fifth=True,
                pet_name_correct=True,color_correct=True,store_reopen_preserved_all_five=True,tts_samples=len(pcm)//2,
                tts_sample_rate=rate,output_adapter=mode,context_limit=4096)
    except Exception as error:
        result=dict(status='PUBLIC_FIVE_ROUND_CHECK_FAILED',stage=stage,error_type=type(error).__name__,
            error_code=str(error)[:180],traceback_lines=traceback.format_exc().splitlines()[-5:])
    code,health_after=http('GET','/health')
    result.update(schema='aura-public-five-round-check-1',rounds=rows,trace=trace,stage=stage,
        model_active_after=health_after.get('active'),model_pending_after=health_after.get('pending'),
        public_inputs_only=True,private_store_reads=0,microphone_enable_calls=0,real_recording_requests=0,
        speaker_playback_calls=0,fixture_acknowledgements_only=True,axis_camera_or_DFX_commands=0)
    print(json.dumps(result,ensure_ascii=False))
    
except BaseException as error:
    print(json.dumps(dict(status='PUBLIC_PROBE_PREPARATION_ERROR',error_type=type(error).__name__,detail=str(error)[:150],traceback_lines=traceback.format_exc().splitlines()[-7:])))
