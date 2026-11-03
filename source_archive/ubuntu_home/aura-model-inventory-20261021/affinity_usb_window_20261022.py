import json,subprocess,time,urllib.request
from pathlib import Path
def journal(args):
 return subprocess.check_output(['journalctl','-k']+args+['--no-pager'],timeout=8).decode()
def rows(raw):return [json.loads(x) for x in raw.splitlines() if x.strip()]
cursor=next(x.split(': ',1)[1] for x in journal(['-n','0','--show-cursor']).splitlines() if x.startswith('-- cursor: '))
started=time.monotonic();time.sleep(5)
data=rows(journal(['--after-cursor='+cursor,'-n','5000','-o','json']))
warning=[x for x in data if "WARN: HC couldn't access mem fast enough" in x.get('MESSAGE','')]
recent=rows(journal(['-n','5000','-o','json']));recentwarning=[x for x in recent if "WARN: HC couldn't access mem fast enough" in x.get('MESSAGE','')]
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as f:h=json.load(f)
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
alsa={}
for p in Path('/proc/asound').glob('card*/pcm*p/sub0/status'):
 lines=p.read_text().splitlines();alsa[str(p)]={x.split(':',1)[0]:x.split(':',1)[1].strip() for x in lines if ':' in x and x.split(':',1)[0] in ('state','owner_pid')}
print(json.dumps({'read_only':True,'window_start_mono':started,'window_end_mono':time.monotonic(),'new_matching_warnings':len(warning),'journal_rows':len(data),'window_at_limit':len(data)==5000,'first_new_warning_mono_us':warning[0].get('__MONOTONIC_TIMESTAMP') if warning else None,'last_new_warning_mono_us':warning[-1].get('__MONOTONIC_TIMESTAMP') if warning else None,'last_retained_warning_mono_us':recentwarning[-1].get('__MONOTONIC_TIMESTAMP') if recentwarning else None,'recent_first_mono_us':recent[0].get('__MONOTONIC_TIMESTAMP') if recent else None,'camera_pid':h['pid'],'face_targets':h.get('identity',{}).get('face_targets'),'schedule':h.get('dpu_schedule'),'ui':{k:u.get(k) for k in ('phase','playing','paused','audio_output_state')},'alsa_playback':alsa,'journald':subprocess.check_output(['systemctl','show','systemd-journald.service','-p','MainPID','-p','NRestarts','-p','ActiveState'],timeout=3).decode().strip()}))
