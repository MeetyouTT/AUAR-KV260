import json
from pathlib import Path
p=Path('/home/root/aura-audio-recovery-20261023/c58c50eeb1c7cae5/result.json')
d=json.loads(p.read_text()) if p.exists() else {}
out={k:d.get(k) for k in ('phase','complete','error','restore_error','warning_recovered_in_short_sample',
                          'guard_timer_active','ui_before','ui_after','units_after','preference_sha_before','preference_sha_after')}
for phase in ('before','stopped','after'):
    s=d.get(phase,{})
    out[phase]={k:s.get(k) for k in ('seconds','cpu_pct_board','xhci_warning_count','journal_query_complete',
                                  'playback_pcm_status','camera')}
print(json.dumps(out,separators=(',',':')))
