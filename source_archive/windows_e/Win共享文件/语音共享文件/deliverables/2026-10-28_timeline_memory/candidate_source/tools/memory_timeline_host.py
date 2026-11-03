"""Compose scoped archive/visual events without blocking ordinary voice on errors."""
import http.client,sqlite3,time
from common.timeline import query,historical,context_message,select,DEFAULT_ZONE
from tools.profile_control import turn_profile,profile_options

def use_visual_revision(models,meta,revision):
    if type(revision) is not int or revision<0:raise ValueError('Invalid visual revision')
    turns=getattr(models,'timeline_turns',None)
    if turns is None:turns={};models.timeline_turns=turns
    prior=turns.get(meta['request_id'])
    if prior and prior['revision']!=revision:raise ValueError('Visual memory changed during recall')
    turns[meta['request_id']]={'context':dict(meta),'revision':revision,'checked':time.monotonic()}
    while len(turns)>64:turns.pop(next(iter(turns)))
    store=getattr(models,'conversations',None)
    if meta['request_id'] in getattr(models,'conversation_turns',{}) and hasattr(store,'attach_visual'):
        store.attach_visual(meta,revision)

def sync_visual_archive(models,meta):
    store=getattr(models,'conversations',None)
    if not hasattr(store,'has_visual_dependencies') or not store.has_visual_dependencies():return
    from tools.device_client import call
    try:
        result=call('/v1/memory/revision',{'boot':meta['board_boot_id']},timeout=.06)
        revision=result['revision']
        if result.get('version')!=1 or type(revision) is not int or revision<0:raise ValueError('Invalid revision')
    except (OSError,ValueError,KeyError,http.client.HTTPException):revision=None
    store.invalidate_visual(revision)

def live_context(models,meta,text):
    """Read a live-cache revision atomically with its sources; missing hub is optional."""
    from tools.device_client import call
    from common.device_memory import context_message as live_message
    try:
        value=call('/v1/memory/recall',{'boot':meta['board_boot_id'],'history':False})
        rows=value.get('observations',[])
        if rows:
            use_visual_revision(models,meta,value['revision'])
            return live_message(rows)
    except PermissionError:raise
    except (OSError,ValueError,KeyError,http.client.HTTPException):pass
    return None

def memory_context(models,meta,text,*,max_bytes=2600):
    if not historical(text):return None
    q=query(text,now=time.time(),zone=getattr(models,'timeline_zone',DEFAULT_ZONE))
    rows=[];errors=[]
    cid=getattr(models,'conversation_turns',{}).get(meta['request_id'])
    store=getattr(models,'conversations',None)
    if cid and hasattr(store,'timeline_events'):
        try:
            with turn_profile(models,meta) as pid:
                rows+=store.timeline_events(cid,q,exclude=meta['request_id'],**profile_options(pid))
        except PermissionError:raise
        except (sqlite3.Error,TimeoutError,OSError):errors.append('conversation_unavailable')
        # Authorization failures must still reject the turn, not fall back to a guest scope.
    from tools.device_client import call
    try:
        value=call('/v1/memory/timeline',{'text':text,'boot':meta['board_boot_id']},timeout=.25)
        if value.get('version')!=1:raise ValueError('Unsupported timeline service')
        rows+=value['events']
        if value['events']:use_visual_revision(models,meta,value['revision'])
    except PermissionError:raise
    except (OSError,ValueError,KeyError,http.client.HTTPException):errors.append('visual_unavailable')
    picked=select(rows,q,limit=8)
    return context_message(picked,q,max_bytes=max_bytes,status=','.join(errors) if errors else 'ok')

def validate_visual_memory(models,meta,*,force=False):
    stamp=getattr(models,'timeline_turns',{}).get(meta['request_id'])
    if stamp is None:return
    if stamp['context']!=meta:raise ValueError('Timeline belongs to another request')
    if not force and time.monotonic()-stamp['checked']<.5:return
    from tools.device_client import call
    try:value=call('/v1/memory/revision',{'boot':meta['board_boot_id']},timeout=.06)
    except (OSError,ValueError,http.client.HTTPException):raise ValueError('Timeline revision could not be checked')
    if value.get('version')!=1 or value.get('revision')!=stamp['revision']:raise ValueError('Visual memory changed; obsolete output')
    stamp['checked']=time.monotonic()
