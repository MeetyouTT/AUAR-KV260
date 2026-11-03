"""Pure completion/counter checks for a deliberate physical cold-boot test."""
def validate_checkpoint(document, before, *, current_boot, source_pid, source_birth_ticks,
                        source_process_alive, lock_free, unit):
    if document.get('schema')!='aura-native-protection-checkpoint-2' or \
            document.get('scope')!='final_quiescent_before_native_owner_close':
        raise ValueError('Exact sealed native checkpoint required')
    seed,aux=document['seed'],document['auxiliary']
    if seed['boot_id']!=current_boot or seed['source_pid']!=source_pid or \
            seed['source_birth_ticks']!=source_birth_ticks or seed['checkpoint_kind']!=1:
        raise ValueError('Checkpoint source differs from the stopped owner')
    if seed['fenced'] or aux['fenced'] or aux['active'] or aux['primary_waiting'] or any(aux['pending_result_tokens']):
        raise ValueError('Native completion is unconfirmed or a result is pending')
    if source_process_alive or not lock_free:
        raise ValueError('The native owner has not released its process and lock')
    if unit.get('MainPID')!='0' or unit.get('ExecMainStatus')!='0' or unit.get('Result')!='success':
        raise ValueError('Native service did not stop normally')
    if seed['primary_calls']<before['primary_calls'] or seed['primary_period_overruns']<before['primary_period_overruns']:
        raise ValueError('Primary counters decreased during shutdown')
    for index,task in ((1,'yunet'),(2,'sface')):
        previous=before['optional'][task]
        if seed['admissions'][index]<previous['calls'] or seed['overruns'][index]<previous['overruns']:
            raise ValueError('Optional counters decreased during shutdown')
    if aux['sface_counters']['completed']<before['sface_completed']:
        raise ValueError('SFace completion history decreased')
    return True
