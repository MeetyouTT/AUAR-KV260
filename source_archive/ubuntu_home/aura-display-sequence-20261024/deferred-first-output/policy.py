"""One boot only: test a late first Linux scanout, never a permanent delay."""
def choose_boot(source_boot,current_boot,target_boot):
    if current_boot==source_boot:return 'UNCHANGED_SOURCE_BOOT'
    if target_boot is None:return 'CLAIM_NEW_BOOT'
    if current_boot!=target_boot:return 'UNCHANGED_LATER_BOOT'
    return 'TRIAL_BOOT'


def readiness(*,uptime,elapsed,scanout_active,camera_ready,minimum_uptime=60,maximum_wait=90):
    if scanout_active:return 'INVALID_SCANOUT_ALREADY_ACTIVE'
    if uptime>=minimum_uptime and camera_ready:return 'READY_FOR_FIRST_XSERVER_OUTPUT'
    if elapsed>=maximum_wait:return 'FALLBACK_WAIT_LIMIT'
    return 'WAIT'
