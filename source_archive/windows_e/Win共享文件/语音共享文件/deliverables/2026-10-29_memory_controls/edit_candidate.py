"""Edit frozen candidate only; leave the loaded r2 service and board untouched."""
import hashlib,json,shutil
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';C=H/'candidate_source'
plan=json.loads((H/'source_plan.json').read_text(encoding='utf-8'))
assert plan['status']=='CANDIDATE_BUILD'
name='tools/voice_channel_source.py'
for base in ('before','candidate_source'):shutil.copy2(A/name,H/base/name)
plan['files'][name]={'before':hashlib.sha256((A/name).read_bytes()).hexdigest()}
def edit(name,old,new):
    path=C/name;text=path.read_text(encoding='utf-8');assert text.count(old)==1,(name,old)
    path.write_text(text.replace(old,new,1),encoding='utf-8')
edit('common/conversation_store.py',"db.execute('PRAGMA foreign_keys=ON')","db.execute('PRAGMA foreign_keys=ON')\n        db.execute('PRAGMA recursive_triggers=OFF')")
edit('common/conversation_context.py',"'source_turns': [item['seq'] for item in notes],","'source_turns': [item['seq'] for item in notes],\n                     'recent_source_turns': ([r['seq'] for r in recent[-sum(m['role']=='user' for m in selected):]] if selected else []),")
edit('common/timeline_conversations.py','from common.timeline import event_id,select,sql_topic','from common.timeline import event_id,select,sql_topic\nfrom common.memory_controls import MemoryControlsMixin,install as install_controls,resolve_digest_sources')
edit('common/timeline_conversations.py','class TimelineConversationStore(ProfileConversationStore):','class TimelineConversationStore(MemoryControlsMixin,ProfileConversationStore):')
edit('common/timeline_conversations.py','            install(db)\n','            install(db)\n            install_controls(db)\n')
edit('common/timeline_conversations.py',"        from common.timeline_summaries import DigestWorker\n","        from common.timeline_summaries import DigestWorker\n        self.memory_zone=zone\n")
edit('common/timeline_conversations.py',"            base={'conversation_id':r['conversation_id'],","            base={'source_seq':r['seq'],'conversation_id':r['conversation_id'],")
edit('common/timeline_conversations.py','                return rows\n','                return resolve_digest_sources(db,rows)\n')
edit('common/timeline_conversations.py','timeline_source=\'authoritative_archive\',timeline_playback_time=True,',"timeline_source='authoritative_archive',timeline_playback_time=True,\n                    fact_revision_history=1,confirmed_transcript_deletion=1,conversation_source_dependencies=1,")
edit('tools/board_model_host.py','            return build_context(MODEL,records,text,reasoning=reasoning,memories=facts)',
     "            result=build_context(MODEL,records,text,reasoning=reasoning,memories=facts)\n            if hasattr(self.conversations,'attach_sources'):\n                metrics=result[1]\n                sources=metrics['source_turns']+metrics.get('recent_source_turns',[])+metrics['explicit_fact_sources']\n                self.conversations.attach_sources(meta,sources,**profile_options(pid))\n            return result")
edit('tools/memory_timeline_host.py','    picked=select(rows,q,limit=8)\n',
     "    picked=select(rows,q,limit=8)\n    if cid and hasattr(store,'attach_sources'):\n        sources=[]\n        for row in picked:\n            if row.get('source_seq') is not None:sources.append(row['source_seq'])\n            sources+=row.get('source_seqs',[])\n        with turn_profile(models,meta) as pid:store.attach_sources(meta,sources,**profile_options(pid))\n")
edit('tools/voice_channel_source.py',"        durable=models.conversation_context(meta,model_text,reasoning=plan['mode']=='reasoning')",
     "        durable=(None if memory_reply is not None else models.conversation_context(meta,model_text,reasoning=plan['mode']=='reasoning'))")
edit('common/voice_service_capabilities.py',"SERVICE_REVISION = 'voice-timeline-20261028-r2'","SERVICE_REVISION = 'voice-memory-controls-20261029-r3'")
edit('common/voice_service_capabilities.py',"'background_memory_digests':1}","'background_memory_digests':1,'confirmed_transcript_deletion':1,'fact_revision_history':1}")
edit('common/voice_service_capabilities.py',"SOURCE_FILES = (\n","SOURCE_FILES = (\n    'common/memory_controls.py',\n")
for name,entry in plan['files'].items():entry['candidate']=hashlib.sha256((C/name).read_bytes()).hexdigest()
plan['status']='CANDIDATE_IMPLEMENTED'
(H/'source_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'candidate_files':len(plan['files']),'production_source_changed':False,'board_migration':False}))
