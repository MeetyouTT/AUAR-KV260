def continuity_reference_stop(release, config, root):
    """User-confirmed continuity is a command reference, not angle calibration."""
    require(release.get('status') == STATUS and release.get('scope') == SCOPE
            and release.get('boot_id') == config.get('boot_id')
            and release.get('manual_motion_enabled') is False
            and release.get('automatic_following_enabled') is False
            and all(release.get(k) is False for k in ('physical_range_verified','mechanical_reference_calibrated','external_waveform_verified'))
            and [release.get('manual_minimum_us'),release.get('manual_maximum_us')] == [1400,1600]
            and [config.get('manual_minimum_us'),config.get('manual_maximum_us')] == [1400,1600]
            and config.get('maximum_step_us') == 20 and config.get('maximum_duration_s') == 2,
            'CONTINUITY_CONNECTION_SCOPE_REQUIRED')
    q=release['qualification'];require(q.get('kind')=='USER_CONFIRMED_CONTINUITY','CONTINUITY_KIND_REQUIRED')
    docs={}
    for key in ('reference','previous_stop'):
        item=q[key];p=Path(item['file'])
        require(not p.is_absolute() and '..' not in p.parts,'LOCAL_EVIDENCE_REQUIRED')
        p=Path(root)/p
        require(p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],'CONTINUITY_EVIDENCE_CHANGED')
        docs[key]=json.loads(p.read_text())
    ref,old=docs['reference'],docs['previous_stop']
    require(ref.get('schema')=='aura-current-boot-continuity-reference-1'
            and ref.get('boot_id')==config['boot_id'] and ref.get('fdt_sha256')==config['fdt_sha256']
            and ref.get('user_confirmed_no_manual_or_powerup_motion') is True
            and ref.get('user_quote')=='都没有，机械朝向保持上次的位置'
            and ref.get('source')=='USER_CONFIRMED_CONTINUITY_FROM_PREVIOUS_STOPPED_COMMAND'
            and ref.get('ARM_sent') is False and ref.get('COMMIT_sent') is False
            and ref.get('mechanical_angle_measured') is False and ref.get('mechanical_zero_calibrated') is False,
            'CURRENT_USER_CONTINUITY_REQUIRED')
    require(old.get('status')=='PASS' and old.get('boot')==ref['predecessor_boot']
            and old.get('automatic_following') is False and old.get('motor_active') is False
            and old.get('pan_us')==ref.get('reference_us')==1400,
            'PREVIOUS_STOPPED_COMMAND_REQUIRED')
    before,defined,final=ref['before'],ref['defined'],ref['stopped_readback']
    require(stopped(before) and stopped(final) and before['width_us']==1500
            and before['ack_seq']==final['ack_seq']==0 and final['epoch']==before['epoch']+1
            and defined['flags']==12 and defined['lease_left_ms']==0 and defined['ack_seq']==0
            and all(defined[k]==final[k]==1400 for k in ('width_us','target_us','reference_us'))
            and all(defined[k]==final[k] for k in ('session','epoch')),
            'REFERENCE_WITHOUT_PWM_PROOF_REQUIRED')
    return final
