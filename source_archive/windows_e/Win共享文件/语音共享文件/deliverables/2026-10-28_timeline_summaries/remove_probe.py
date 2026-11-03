"""Production-view helper: remove only this acceptance's single-frame probe."""
import hashlib,json,sys,time
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A))
from common.timeline_config import load_config
from common.timeline_observations import TimelineObservationStore
probe=json.loads((H/'live_summary_acceptance.json').read_text(encoding='utf-8'))
row=probe['probe_event'];report={'status':'STARTING'}
try:
    config=load_config(A/'config/timeline_memory.json')
    store=TimelineObservationStore(Path.home()/'AppData/Local/Aura/device-memory/observations.sqlite3',
        device_id=config['device_id'],history_days=config['visual_history_days'],history_limit=config['visual_event_limit'])
    with store.lock:
        data=store.db.execute('SELECT boot,epoch,first_frame,last_frame,first_received,last_received,summary FROM visual_timeline WHERE id=? AND device=?',
                             (row['event_id'],config['device_id'])).fetchone()
        assert data and data[:2]==(probe['board_boot'],probe['submission']['epoch'])
        assert data[2]==data[3]==probe['submission']['frame_id'] and data[4]==data[5]==row['received']
        assert hashlib.sha256(data[6].encode()).hexdigest()==row['summary_sha256']
        at=data[4]
        matches=store.db.execute('SELECT id FROM visual_timeline WHERE device=? AND first_received<=? AND last_received>=?',
            (config['device_id'],at+.00001,at-.00001)).fetchall()
        assert matches==[(row['event_id'],)],'Probe is no longer an isolated event; do not delete other records'
        revision_before=store.generation(probe['board_boot'])
        removed=store.forget_timeline({'start':at-.00001,'end':at+.00001,'topic':'','error':None})
        assert removed==1 and not store.db.execute('SELECT 1 FROM visual_timeline WHERE id=?',(row['event_id'],)).fetchone()
        report={'status':'PASS','removed_only_probe':True,'event_id':row['event_id'],'deleted_events':removed,
                'revision_before':revision_before,'revision_after':store.generation(probe['board_boot'])}
    store.close()
except Exception as exc:report={'status':'FAIL','error':type(exc).__name__+': '+str(exc)}
(H/'probe_removed.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
