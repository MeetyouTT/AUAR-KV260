"""Read-only motion preflight. Never opens registers or enables actuation."""
import argparse
import json
from pathlib import Path


def assess(manual_config, calibration, *, boot_id, fdt_sha256, manual_state, firmware=None):
    blockers=[]
    if not boot_id or manual_config.get('boot_id')!=boot_id:blockers.append('BOOT_MISMATCH')
    if not fdt_sha256 or manual_config.get('fdt_sha256')!=fdt_sha256:blockers.append('FDT_MISMATCH')
    if firmware!='aura-visual-servo-b4096-v1.bit.bin':blockers.append('JOINT_FIRMWARE_REQUIRED')
    if manual_state.get('state')!='READY':blockers.append('MANUAL_BACKEND_NOT_READY')
    if calibration.get('verified') is not True:blockers.append('MECHANICS_NOT_VERIFIED')
    if not boot_id or calibration.get('boot_id')!=boot_id:blockers.append('CALIBRATION_BOOT_MISMATCH')
    if not calibration.get('setup_id') or not calibration.get('evidence'):blockers.append('MISSING_SETUP_EVIDENCE')
    pulse=calibration.get('reference_us')
    if type(pulse) is not int or not 1400<=pulse<=1600:blockers.append('REFERENCE_NOT_MEASURED')
    polarity=calibration.get('polarity')
    if type(polarity) is not int or polarity not in (-1,1):blockers.append('POLARITY_NOT_MEASURED')
    if type(calibration.get('camera_moves_with_axis')) is not bool:blockers.append('CAMERA_MOUNT_UNKNOWN')
    return {'state':'BLOCKED' if blockers else 'PREFLIGHT_ONLY','blockers':blockers,
            'physical_actuation_performed':False,'automatic_following_authorized':False,
            'note':'Passing preflight does not establish limit, load, STOP or following accuracy.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('manual-config','calibration','manual-state'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--boot-id',required=True);p.add_argument('--fdt-sha256',required=True)
    p.add_argument('--firmware',required=True)
    a=p.parse_args()
    load=lambda path:json.loads(path.read_text(encoding='utf-8-sig'))
    print(json.dumps(assess(load(a.manual_config),load(a.calibration),boot_id=a.boot_id,
          fdt_sha256=a.fdt_sha256,manual_state=load(a.manual_state),firmware=a.firmware),indent=2))

if __name__=='__main__':main()
