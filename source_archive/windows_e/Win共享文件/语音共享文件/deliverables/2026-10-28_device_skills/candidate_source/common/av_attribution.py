"""Bind model scores to a bounded synchronized audio/video window, not a person."""
import math

def window(value,now_ms):
    fields={'board_boot_id','clock_domain','capture_id','turn_generation','camera_epoch','track_id','track_generation','started_ms','ended_ms','deadline_ms','frame_times_ms'}
    if not isinstance(value,dict) or set(value)!=fields:raise ValueError('Invalid AV window')
    for k in ('board_boot_id','clock_domain','capture_id','camera_epoch'):
        if not isinstance(value[k],str) or not 1<=len(value[k])<=96:raise ValueError('Invalid AV owner')
    for k in ('turn_generation','track_id','track_generation','started_ms','ended_ms','deadline_ms'):
        if type(value[k]) is not int or value[k]<(1 if k in ('track_id','track_generation') else 0):raise ValueError('Invalid AV timestamp/track')
    if type(now_ms) is not int or not 0<=value['started_ms']<value['ended_ms']<=now_ms<value['deadline_ms']<=value['ended_ms']+2000:raise ValueError('AV window stale')
    duration=value['ended_ms']-value['started_ms']
    if not 800<=duration<=3000:raise ValueError('AV window duration outside bound')
    times=value['frame_times_ms']
    if not isinstance(times,list) or not 8<=len(times)<=90 or any(type(t) is not int for t in times):raise ValueError('Invalid AV frame times')
    if any(b<=a or b-a>150 for a,b in zip(times,times[1:])):raise ValueError('AV frame gap or reversal')
    if not value['started_ms']<=times[0]<=value['started_ms']+80 or not value['ended_ms']-80<=times[-1]<=value['ended_ms']:raise ValueError('Audio/video coverage differs')
    return dict(value,frame_times_ms=list(times))

def decision(result,current,now_ms,*,calibrated=False,threshold=None,margin=None,cancelled=False):
    def reject(reason):return {'accepted':False,'reason':reason,'personal_memory_allowed':False}
    if cancelled:return reject('CANCELLED')
    if not calibrated:return reject('NOT_FIELD_CALIBRATED')
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in (threshold,margin)) or not 0<=threshold<=1 or not 0<=margin<=1:return reject('INVALID_OPERATING_POINT')
    try:
        expected=window(current,now_ms);actual=window(result['window'],now_ms)
        if actual!=expected:return reject('CONTEXT_MISMATCH')
        rows=result['candidates']
        if not isinstance(rows,list) or not 1<=len(rows)<=8:return reject('INVALID_CANDIDATES')
        keys=set();ranked=[]
        for row in rows:
            if set(row)!= {'track_id','track_generation','score'}:return reject('INVALID_CANDIDATES')
            key=(row['track_id'],row['track_generation']);score=row['score']
            if any(type(k) is not int or k<1 for k in key) or key in keys:return reject('INVALID_CANDIDATES')
            if type(score) not in (int,float) or not math.isfinite(score) or not 0<=score<=1:return reject('INVALID_CANDIDATES')
            keys.add(key);ranked.append((score,key))
        ranked.sort(reverse=True)
        if ranked[0][0]<threshold:return reject('NO_CONFIDENT_SPEAKER')
        if len(ranked)>1 and ranked[0][0]-ranked[1][0]<margin:return reject('AMBIGUOUS')
        if ranked[0][1]!=(current['track_id'],current['track_generation']):return reject('OTHER_TRACK_SPEAKING')
        if result.get('all_visible_tracks_scored') is not True:return reject('INCOMPLETE_SCENE')
        return {'accepted':True,'reason':'CURRENT_AV_WINDOW','target':(current['camera_epoch'],*ranked[0][1]),'personal_memory_allowed':False}
    except (ValueError,KeyError,TypeError):return reject('INVALID_OR_STALE_WINDOW')

