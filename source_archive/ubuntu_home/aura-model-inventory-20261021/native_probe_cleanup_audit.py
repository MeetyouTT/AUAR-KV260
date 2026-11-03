import json,subprocess,time
from pathlib import Path
t=Path('/sys/kernel/tracing')
events=[line for line in (t/'uprobe_events').read_text().splitlines() if any(p in line for p in ('aura_iso_','aura_vart_'))]
instances=[p.name for p in (t/'instances').iterdir() if p.name.startswith(('aura_iso_','aura_vart_'))]
units=['aura-uprobe-cleanup-'+p+'.timer' for p in ('6781bbb12d73edb2','e977c9df9c2d3bcb','9c8f8702f68a4d24')]
units+=['aura-vart-phase-0b69843e8b7c38fa.service','aura-vart-phase-cleanup-0b69843e8b7c38fa.timer']
states={unit:subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','--value'],text=True).strip() for unit in units}
print(json.dumps({'read_only':True,'snapshot_mono_ns':time.monotonic_ns(),'own_uprobe_events_remaining':events,
 'own_instances_remaining':instances,'unit_states':states,'passed':not events and not instances and all(x in ('inactive','failed') for x in states.values()),
 'preflight_rejection_is_not_successful_observation':True}))
