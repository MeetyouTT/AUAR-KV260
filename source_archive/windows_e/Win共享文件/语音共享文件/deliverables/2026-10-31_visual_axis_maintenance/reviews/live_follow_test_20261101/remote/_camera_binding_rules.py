"""Pure same-boot producer renewal; gallery, model and all old source pins are preserved."""
import copy

READBACK_FIELDS={'version','enabled','board_boot_id','camera_pid','camera_start_ticks',
    'camera_cmdline_sha256','camera_config','identity_config','source_sha256','database',
    'model_id','dimension','model_sha256','result_ttl_ms','backend'}

def binding_candidate(baseline,old_runtime,new_runtime,*,boot,old_pid,old_birth,new_pid,new_birth,
                      command_sha,new_runtime_path,new_runtime_sha,checkpoint_sha,model_id):
    def need(value,reason):
        if not value:raise ValueError(reason)
    need(set(baseline)==READBACK_FIELDS and baseline['version']==1 and baseline['enabled'] is True,
         'original complete enabled readback required')
    need(baseline['board_boot_id']==boot and baseline['camera_pid']==old_pid
         and str(baseline['camera_start_ticks'])==str(old_birth)
         and baseline['camera_cmdline_sha256']==command_sha,'original owner binding mismatch')
    need(type(new_pid) is int and new_pid>1 and new_pid!=old_pid,'distinct current producer required')
    need(baseline['dimension']==128 and baseline['backend']=='DPU_SFACE_INT8'
         and baseline['model_id']==model_id,'original model and backend required')
    need(old_runtime['identity']['config']==new_runtime['identity']['config']==baseline['identity_config'],
         'identity configuration changed')
    old=copy.deepcopy(old_runtime);new=copy.deepcopy(new_runtime)
    old['native_execution'].pop('seed');seed=new['native_execution'].pop('seed')
    need(old==new,'runtime change beyond the exact checkpoint pointer')
    need(seed['sha256']==checkpoint_sha and seed['path']==new_runtime['native_execution']['checkpoint_output'],
         'exact freshly consumed checkpoint pointer required')
    need(new_runtime_path not in baseline['source_sha256'],'new runtime source pin already present')
    result=copy.deepcopy(baseline)
    result.update(camera_pid=new_pid,camera_start_ticks=str(new_birth) if isinstance(baseline['camera_start_ticks'],str) else new_birth,
                  camera_cmdline_sha256=command_sha,camera_config=new_runtime_path)
    result['source_sha256'][new_runtime_path]=new_runtime_sha
    need(len(result['source_sha256'])==len(baseline['source_sha256'])+1,'exact one-pin extension required')
    return result
