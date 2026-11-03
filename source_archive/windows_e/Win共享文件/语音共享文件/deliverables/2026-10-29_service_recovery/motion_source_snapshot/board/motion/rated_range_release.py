"""Explicit rated-range authority; preserves hardware identity and STOP checks."""
import hashlib,json
from pathlib import Path

def require(value,message):
    if not value:raise RuntimeError(message+'; no MMIO')

def document(root,item):
    relative=Path(item['file'])
    require(not relative.is_absolute() and '..' not in relative.parts,'Local range evidence required')
    p=Path(root)/relative
    require(p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],'Range evidence changed')
    return json.loads(p.read_text())

def rated_range_bounds(release,config,root):
    require(release.get('status')=='USER_RATED_RANGE_VSRV2'
            and release.get('scope')=='explicit_user_rated_pulse_range'
            and release.get('app')=='aura-visual-servo-b4096-wide-v1'
            and release.get('abi')==2 and release.get('build_id')==0x10282601
            and release.get('boot_id')==config.get('boot_id')
            and [release.get('manual_minimum_us'),release.get('manual_maximum_us')]==[500,2500]
            and [config.get('manual_minimum_us'),config.get('manual_maximum_us')]==[500,2500]
            and config.get('maximum_step_us')==20 and config.get('maximum_duration_s')==2
            and all(release.get(k) is False for k in ['physical_range_verified','mechanical_reference_calibrated','external_waveform_verified']),
            'Exact uncalibrated rated-range scope required')
    a=document(root,release['authorization']);p=document(root,release['platform_proof'])
    require(a.get('schema')=='aura-explicit-rated-range-1' and a.get('boot_id')==config['boot_id']
            and a.get('bounds_us')==[500,2500] and a.get('nominal_center_us')==1500
            and a.get('requested_angles_deg')==[-90,90] and a.get('clearance_confirmed') is True
            and a.get('physical_calibration_claimed') is False and bool(a.get('user_instruction_quote')),
            'Current explicit range instruction required')
    require(p.get('boot_id')==config['boot_id'] and p.get('fdt_sha256')==config['fdt_sha256']
            and p.get('build_id')==0x10282601 and p.get('identity_stop_passed') is True
            and p.get('ARM_sent') is False and p.get('COMMIT_sent') is False,
            'Current wide firmware ID/STOP proof required')
    stop=p['after_stop']
    require(stop.get('flags')==0 and stop.get('lease_left_ms')==0
            and all(type(stop.get(k)) is int and 500<=stop[k]<=2500 for k in ['width_us','target_us','reference_us']),
            'Stopped wide firmware proof required')
    return 500,2500
