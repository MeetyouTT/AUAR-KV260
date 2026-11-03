"""Root-only ARM public temporary-store proof; never a deployment tool.

Verify exact saved newboot startup, boot and every379 live component BEFORE
loading the three-file overlay in THIS process. Original independent4 plus
independent3 test bodies and one paired-route/full-ACK/UI-hook smoke run with
public temporary SQLite and RAM PCM. No camera/mic/models/player/private DB.
"""
import argparse
import ast
from datetime import datetime
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

STARTUP='90f6c6c40f6501362aa77483235a7260a212de6e3357615311bdaa5cc193ebbe'
SOURCE_MANIFEST='6d03c1d7aa95a9c5615f540606699f67c4ee7a44be1e50dcb2983c6c555e3637'
MAPPING='df6b26927ad60d6d3513429c697d70bd15c84cfdca6d16c5527e9992cb7b04e2'
BOOT='bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
REVIEW4='7528a035ae301b3bf0d3bb0747cb52c322f82b5a1c236102ba5d47915e0c008b'
REVIEW3='94410be3389a0d0d2f1e3658484b4def8b06fd98e62ef63c355309ac71cb4a6b'
PUBLIC_WORKER='7d5ff31d1f56cb567fd630c35056a1a33f9d239f520ad92975f47e10149153df'
FILES={'board/runtime/board_business.py','board/runtime/history_delete.py','tools/production_memory_presentation.py'}


def sha(raw):return hashlib.sha256(raw).hexdigest()
def need(ok,code):
    if not ok:raise ValueError(code)
def save(path,value):
    temp=path.with_name(path.name+'.tmp');temp.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'));os.replace(temp,path)
def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class PublicBridge:
    def __init__(self):self.lock=threading.RLock();self.state=dict(reply='公开旧显示')
    def publish(self,state,frame):self.state=state
class PublicVisual:
    def __init__(self):
        self.stream=None;self.pending=self.ready=self.audio_waiting=None
        self.reply='公开旧显示';self.turns=[];self.log=[];self.phase='IDLE'
        self.core=NS(reply_text='公开旧显示');self.output=NS(active=False,paused=False)
    def channel_event(self,header,pcm,owner,feedback_assets,requested_at):
        if header['kind']=='start':self.stream=dict(owner=owner)
class PublicRecording:
    def __init__(self):self.controller=PublicVisual();self.transcription=dict(state='ANSWERED',text='公开旧显示')
    def tick(self):return None
    def public(self):return dict(reply=self.controller.reply,local_transcription=dict(self.transcription))


def verify(args):
    need(sys.flags.optimize==0,'assertions_must_not_be_optimized')
    need(args.output.is_absolute() and not args.output.exists(),'fresh_absolute_output_required')
    mapping_raw=args.mapping.read_bytes();need(sha(mapping_raw)==MAPPING,'frozen_mapping_changed')
    mapping=json.loads(mapping_raw)
    need(mapping['startup_sha256']==STARTUP and mapping['source_manifest_sha256']==SOURCE_MANIFEST,'different_release_mapping')
    need(mapping['boot_id']==BOOT and len(mapping['component_pins'])==379,'different_boot_or_count')
    candidate_raw=args.candidate_manifest.read_bytes()
    need(sha(candidate_raw)==args.candidate_manifest_sha256,'candidate_manifest_changed')
    candidate=json.loads(candidate_raw)
    need(candidate['baseline_mapping_sha256']==MAPPING and set(candidate['files'])==FILES,'wrong_overlay_baseline')
    for path,digest in ((args.original_review,REVIEW4),(args.independent_tests,REVIEW3),(args.public_worker,PUBLIC_WORKER)):
        need(not path.is_symlink() and sha(path.read_bytes())==digest,'review_or_public_fixture_changed')
    base=args.runtime_root.resolve(strict=True);after=args.candidate_root.resolve(strict=True)
    need(not base.is_relative_to(after) and not after.is_relative_to(base),'overlay_must_stay_outside_production')
    need({p.relative_to(after).as_posix() for p in after.rglob('*') if p.is_file() or p.is_symlink()}==FILES,'exact_three_file_overlay_required')
    if args.local_replay:
        need(sys.platform!='linux','board_requires_live_checks')
        configs={'config/character_profile.local.json','config/persona.xuefei.candidate.json',
            'config/yuki_pair.formal.json','config/yuki_accepted_prompt.baseline.txt'}
        required={p:s for p,s in mapping['component_pins'].items() if p.endswith('.py') or p in configs}
    else:
        need(sys.platform=='linux' and args.root_coordinated_slot,'root_exclusive_board_slot_required')
        need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'current_boot_changed_rebind_required')
        need(args.startup_config is not None and sha(args.startup_config.read_bytes())==STARTUP,'current_startup_changed_rebind_required')
        need(json.loads(args.startup_config.read_bytes())['component_sha256']==mapping['component_pins'],'live_component_set_changed')
        required=mapping['component_pins']
    for relative,digest in required.items():
        path=base/relative
        need(not path.is_symlink() and path.resolve().is_relative_to(base),'component_path_escape')
        need(sha(path.read_bytes())==digest,'baseline_component_changed:'+relative)
    for relative,row in candidate['files'].items():
        path=after/relative
        need(not path.is_symlink() and path.resolve().is_relative_to(after),'overlay_path_escape')
        need(sha(path.read_bytes())==row['sha256'] and row['before_sha256']==mapping['component_pins'].get(relative),'overlay_source_or_before_changed')
        if row['before_sha256'] is None:need(not (base/relative).exists(),'untracked_runtime_component_already_exists')
    return mapping,candidate,dict(boot_id=BOOT,startup_sha256=STARTUP,source_manifest_sha256=SOURCE_MANIFEST,
        mapping_sha256=MAPPING,components=379,hashed_components=len(required),
        live_all379_checked=not args.local_replay,application_imports_after_verification=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('runtime-root','candidate-root','mapping','candidate-manifest','original-review','independent-tests','public-worker','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--candidate-manifest-sha256',required=True)
    p.add_argument('--startup-config',type=Path)
    p.add_argument('--root-coordinated-slot')
    p.add_argument('--local-replay',action='store_true');p.add_argument('--check-only',action='store_true')
    args=p.parse_args();mapping,candidate,verification=verify(args)
    result=dict(schema='aura.m03-newboot.public-arm-overlay.v1',status='CHECKED_ONLY' if args.check_only else 'RUNNING',
        verification=verification,candidate_manifest_sha256=args.candidate_manifest_sha256,
        worker_sha256=sha(Path(__file__).read_bytes()),host='local_windows' if args.local_replay else 'board',
        coordinated_slot=args.root_coordinated_slot,
        limits=dict(production_source_written=False,production_private_store_opened=False,model_called=False,
            physical_device_opened=False,production_listening_or_owners_changed=False,
            ASR_PCM_TTS_native_ready_and_GUI='explicit_public_fixtures',physical_playback_verified=False,
            public_temporary_profile_grants_only=True),independent_review4_sha256=REVIEW4,
        independent_review3_sha256=REVIEW3,paired_steps=[])
    save(args.output,result)
    if args.check_only:return 0
    sys.dont_write_bytecode=True;sys.path.insert(0,str(args.runtime_root.resolve()))
    for name in ('common','board.runtime','tools'):
        package=importlib.import_module(name)
        package.__path__=[str(args.candidate_root.resolve()/name.replace('.','/'))]+list(package.__path__)
    loaded={}
    for name in ('common.board_memory','common.board_production_bootstrap','board.runtime.board_dialogue',
        'board.runtime.board_business','board.runtime.history_delete','tools.production_memory_presentation'):
        module=importlib.import_module(name);path=Path(module.__file__).resolve()
        loaded[name]=dict(path=str(path),sha256=sha(path.read_bytes()))
    for name,relative in (('board.runtime.board_business','board/runtime/board_business.py'),
        ('board.runtime.history_delete','board/runtime/history_delete.py'),
        ('tools.production_memory_presentation','tools/production_memory_presentation.py')):
        need(loaded[name]['sha256']==candidate['files'][relative]['sha256'],'candidate_module_not_loaded')
    need(loaded['common.board_production_bootstrap']['sha256']==mapping['component_pins']['common/board_production_bootstrap.py'],'cold_bootstrap_not_loaded')
    result['loaded_modules']=loaded;save(args.output,result)
    original=load_module('unchanged_public_counterexamples',args.original_review)
    public=load_module('frozen_public_input_helpers',args.public_worker)
    from common.profile_access import ProfileAccess
    from common.conversation_selection import ConversationSelection
    from board.runtime.board_business import BoardBusinessConfig,create_board_business_runtime
    from tools.yuki_business_candidate import bind_runtime_pair
    from tools import production_memory_presentation as presentation
    # Compile the three independently reviewed test FUNCTION BODIES unchanged.
    # Their only pytest operation is raises(PermissionError); use the standard
    # unittest assertRaises context. setattr uses standard unittest.mock.patch.
    independent=ast.parse(args.independent_tests.read_bytes())
    functions=[n for n in independent.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
    need(len(functions)==3 and all(not n.decorator_list for n in functions),'independent_test_shape_changed')
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(original.DeleteBoundaryReview)
    class Extra(original.DeleteBoundaryReview):pass
    for node in functions:
        namespace=dict(datetime=datetime,ZoneInfo=ZoneInfo,ProfileAccess=ProfileAccess)
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(args.independent_tests),'exec'),namespace)
        function=namespace[node.name]
        def wrapped(self,function=function,namespace=namespace):
            namespace['pytest']=NS(raises=self.assertRaises)
            class Patches:
                def setattr(_,obj,name,value):
                    item=patch.object(obj,name,value);item.start();self.addCleanup(item.stop)
            if 'monkeypatch' in function.__code__.co_varnames[:function.__code__.co_argcount]:function(self,Patches())
            else:function(self)
        setattr(Extra,node.name,wrapped);suite.addTest(Extra(node.name))
    class Paired(unittest.TestCase):
        def test_actual_paired_registration_store_complete_ACK_and_commit_projection(self):
            with tempfile.TemporaryDirectory(prefix='public-paired-') as name:
                root=Path(name);clock=public.Mono();timeline=public.PublicTimeline('public-arm-newboot',clock)
                client=public.SyntheticModelTransport();asr=public.ScriptedAsr();pair=public.public_pair(args.runtime_root.resolve())
                cfg=BoardBusinessConfig(str(root/'business'),(1793300000.,1793500000.))
                bundle=create_board_business_runtime(cfg,'public-arm-newboot',asr=asr,system_prompt=pair.selected_prompt,
                    conversation_selection=ConversationSelection(root/'selection.json'),timeline=timeline,
                    client=client,clock=clock,capture_idle=lambda:True)
                bind_runtime_pair(bundle,pair);bundle.jobs.select_conversation(resume=False)
                # Only the presentation predicate uses a board-shaped proxy.
                # The real Runtime/Store remain SYNTHETIC in this public root.
                rec=PublicRecording();stage=NS(board_business=NS(runtime=NS(config=NS(data_origin='board'),
                    store=bundle.store,jobs=bundle.jobs,_foreground_idle=lambda:False)),bridge=PublicBridge(),
                    controller=NS(read=lambda:dict(state=dict(reply='公开旧显示'))),closed=False)
                life=presentation.bind_presentation(stage,rec,clock=clock);presentation.attach_presentation(stage)
                try:
                    def say(text,n):
                        clock.now+=1.;asr.text=text;pcm=(1000+n).to_bytes(2,'little')*48000
                        meta=bundle.jobs.submit(NS(capture_id='public-arm-'+str(n),audio=NS(sample_count=48000),pcm=pcm))
                        self.assertTrue(bundle.jobs.run_next());rows=[]
                        while True:
                            row=bundle.jobs.poll()
                            if row is None:break
                            rows.append(row)
                        self.assertFalse(any('error' in row for row in rows))
                        complete=next(row['network_complete'] for row in rows if 'network_complete' in row)
                        audio=b''.join(row['pcm'] for row in rows if row.get('channel_event',{}).get('kind')=='audio')
                        self.assertEqual(sha(audio),complete['pcm_sha256']);self.assertEqual(len(audio)//2,complete['sample_count'])
                        with self.assertRaises((ValueError,InterruptedError)):
                            bundle.jobs.acknowledge(meta,dict(complete,sample_count=complete['sample_count']-1))
                        for row in rows:
                            if 'channel_event' in row:rec.controller.channel_event(row['channel_event'],row.get('pcm',b''),meta,{},clock())
                        bundle.jobs.acknowledge(meta,complete);bundle.jobs.drain_actions()
                        self.assertTrue(bundle.jobs.last_ack['committed'])
                        result['paired_steps'].append(dict(step=n,full_ack=True,partial_ack_rejected=True,
                            samples=complete['sample_count'],pcm_sha256=complete['pcm_sha256']))
                    say('雪妃，记住：项目是公开海风',1)
                    scope=dict(kind='conversation',id=bundle.jobs.conversation_selection.active)
                    self.assertEqual(bundle.store.context(scope)['facts'][0]['value'],'公开海风')
                    say('雪妃，删除今天的对话记录',2)
                    self.assertEqual(bundle.store.context(scope)['facts'][0]['value'],'公开海风')
                    notifications=[];original_notify=bundle.store.notify_history_delete_committed
                    def notify(**kwargs):
                        notifications.append(kwargs);return original_notify(**kwargs)
                    bundle.store.notify_history_delete_committed=notify
                    before=life.invalidations;say('雪妃，确认删除记录',3)
                    self.assertEqual(bundle.store.context(scope)['facts'],[])
                    self.assertTrue(all('公开海风' not in row['text'] for row in bundle.store.history(scope)))
                    # Real jobs also invalidate their prior generation on
                    # submit. Count the NEW commit hook itself, not the sum of
                    # that original generation event and the commit event.
                    self.assertEqual(len(notifications),1)
                    self.assertGreater(life.invalidations,before)
                    self.assertIn('已按预览删除',rec.public()['reply'])
                    self.assertNotIn('公开海风',rec.public()['reply']);self.assertEqual(rec.public()['local_transcription']['text'],'')
                    self.assertTrue(all(kind=='tts' for kind,_ in client.calls));self.assertFalse(bundle.access.grants)
                    result['paired_source']='tools.yuki_jobs_candidate._route -> LocalHistoryDelete -> original Store -> bound complete ACK'
                finally:bundle.close()
    suite.addTest(Paired('test_actual_paired_registration_store_complete_ACK_and_commit_projection'))
    old_temp=tempfile.tempdir;threads=set(threading.enumerate());log=io.StringIO()
    parent=None if args.local_replay else '/dev/shm'
    with tempfile.TemporaryDirectory(prefix='aura-public-m03-newboot-',dir=parent) as owned:
        os.chmod(owned,0o700);need(not Path(owned).resolve().is_relative_to(args.runtime_root.resolve()),'temporary_root_inside_production')
        tempfile.tempdir=owned
        try:outcome=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
        finally:tempfile.tempdir=old_temp
    result.update(status='PASS' if outcome.wasSuccessful() else 'FAIL',tests=outcome.testsRun,
        failures=len(outcome.failures),errors=len(outcome.errors),public_test_log=log.getvalue(),
        temporary_stores_removed=not Path(owned).exists(),new_threads_remaining=len(set(threading.enumerate())-threads),
        test_framework='stdlib unittest; original4 unchanged + original3 AST with assertRaises/patch adapter + paired smoke',
        imported_optional_packages=[n for n in ('numpy','onnxruntime','pytest') if n in sys.modules])
    if not result['temporary_stores_removed'] or result['new_threads_remaining']:result['status']='FAIL'
    save(args.output,result)
    print(json.dumps(dict(status=result['status'],tests=result['tests'],failures=result['failures'],errors=result['errors'])))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
