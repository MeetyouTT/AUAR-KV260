"""Independent-PL-clock comparison of the first changed emitted pulse."""
import json
from test_hardware_slew import scene


rows=[]
for hardware in (False,True):
    f=scene(hardware=hardware,reference=1400)
    f.feed([.86]*10)
    changed=[r for r in f.device.frames if r['width']!=r['before']]
    first=f.device.commands[0] if f.device.commands else None
    rows.append(dict(mode='FPGA_FRAME_SLEW' if hardware else 'PS_RUCKIG_SMALL_STEPS',
        first_changed_pulse_ms=round((changed[0]['now']-10.)*1000,3) if changed else None,
        first_commit_ms=round((first['now']-10.)*1000,3) if first else None,
        first_target_register_us=first['target'] if first else None,
        emitted_width_after_800ms=f.device.pulse,
        commands=len(f.device.commands),arms=f.device.arms,
        maximum_emitted_step_us=max([abs(r['width']-r['before']) for r in f.device.frames] or [0]),
        original_deadlines_preserved=all(c['deadline']<=c['stamp']+c['freshness_s'] for c in f.device.commands)))
    f.session.close()
print(json.dumps(dict(scope='synthetic real session plus independent-clock fake PL; not measured electrical or mechanical response',
                      face_source_interval_ms=80,source_age_ms=60,rows=rows,motor_commands_sent=0)))
