"""Validate that camera state is sealed before allowing a cold-boot test."""
def validate_checkpoint(document, before, boot, pid, birth, unit, alive, lock_free):
    if document.get('schema') != 'aura-native-protection-checkpoint-2' or document.get('scope') != 'final_quiescent_before_native_owner_close':
        raise ValueError('Missing sealed native checkpoint')
    s, a = document['seed'], document['auxiliary']
    if (s['boot_id'], s['source_pid'], s['source_birth_ticks'], s['checkpoint_kind']) != (boot, pid, birth, 1):
        raise ValueError('Stale checkpoint owner')
    if s['fenced'] or a['fenced'] or a['active'] or a['primary_waiting'] or any(a['pending_result_tokens']):
        raise ValueError('Unfinished native operation')
    if alive or not lock_free or any(unit.get(k) != v for k, v in [('MainPID','0'),('ExecMainStatus','0'),('Result','success')]):
        raise ValueError('Owner not stopped normally')
    schedule = before['dpu_schedule']
    for k in ['primary_calls','primary_period_overruns']:
        if s[k] < schedule[k]:raise ValueError('Primary history decreased')
    for i, task in [(1,'yunet'),(2,'sface')]:
        if s['admissions'][i] < schedule['optional'][task]['calls'] or s['overruns'][i] < schedule['optional'][task]['overruns']:
            raise ValueError('Optional history decreased')
    if a['sface_counters']['completed'] < before['identity']['feature_inference']['completed']:
        raise ValueError('Identity history decreased')
    return True
