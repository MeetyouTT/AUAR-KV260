"""Explicit root candidate launch; inspect by default. No service stop/kill."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import restore_original_ui as control


def launch(policy,receipt,receipt_sha,*,execute=False):
    fd=control.lock()
    try:
        control.inactive(policy)
        control.close_receipt(receipt,receipt_sha,policy['old_child'])
        control.candidate_tree_gone()
        descriptor=control.load(control.TARGET+'/launch.json')
        control.need(control.digest(control.encoded(descriptor))==policy['launch_canonical_sha256'],'launch_descriptor_changed')
        manifest=control.load(control.TARGET+'/assembly_manifest.json')
        control.need(manifest['inspection_sha256']==policy['inspection_sha256'] and manifest['data_origin']=='synthetic','wrong_synthetic_assembly')
        control.need(len(manifest['candidate_files'])==356,'candidate_file_map_changed')
        for relative,row in manifest['candidate_files'].items():
            path=Path(control.TARGET)/relative
            control.need(path.is_relative_to(control.TARGET) and '..' not in path.parts,'candidate_path_escape')
            control.need(control.digest(control.read(path,33554432))==row['sha256'],'candidate_component_changed')
        control.need(descriptor['single_publisher_lock']==control.LOCK and descriptor['original_service']==control.UNIT
                     and descriptor['microphone_initially_enabled'] is False and descriptor['following_initially_enabled'] is False,
                     'candidate_launch_protection_changed')
        result=dict(status='READY_TO_LAUNCH_ONE_SYNTHETIC_GUI',target=control.TARGET,files=356,original_unit_inactive=True)
        if not execute:return result
        environment=dict(descriptor['environment'],PATH='/usr/bin:/bin',LANG='C.UTF-8')
        for key in descriptor['inherit_only_if_already_authorized']:
            control.need(key in ('XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS'),'unreviewed_environment_inheritance')
            if key in os.environ:environment[key]=os.environ[key]
        log_path=control.CONTROL+'/candidate_gui.log'
        log_fd=os.open(log_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(log_fd,'wb') as log:
            child=subprocess.Popen(descriptor['command'],cwd=control.TARGET+'/runtime/aura',env=environment,
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(fd,))
        deadline=time.monotonic()+3;owner=None
        while time.monotonic()<deadline:
            owner=control.process(child.pid)
            if owner:break
            time.sleep(.02)
        control.need(owner is not None and owner['argv']==descriptor['command'],'candidate_actual_owner_unavailable')
        control.save(control.CONTROL+'/candidate_owner.json',dict(owner=owner,target=control.TARGET,
            argv_sha256=owner['cmdline_sha256'],lock_inherited_fd=fd,source_inspection=policy['inspection_sha256']))
        # Never LOCK_UN here: the inherited open-file description must keep
        # the same flock until the candidate GUI naturally exits.
        os.close(fd);fd=None
        result.update(status='CANDIDATE_OWNED_GUI_STARTED_NOT_YET_ACCEPTED',owner=owner,log_path=log_path,
                      lock_lifetime='inherited FD held by GUI; released only on normal process exit')
        return result
    finally:
        if fd is not None:os.close(fd)
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy',required=True);parser.add_argument('--policy-sha256',required=True)
    parser.add_argument('--original-close-receipt',required=True);parser.add_argument('--receipt-sha256',required=True)
    parser.add_argument('--launch',action='store_true');args=parser.parse_args()
    try:
        control.need(os.name=='posix' and os.geteuid()==0,'actual_root_posix_only')
        result=launch(control.read_policy(args.policy,args.policy_sha256),args.original_close_receipt,args.receipt_sha256,execute=args.launch)
        print(json.dumps(result));return 0
    except Exception as exc:
        print(json.dumps(dict(status='REFUSED_NO_FORCE',error=type(exc).__name__+': '+str(exc),forced_action=False)))
        return 2
if __name__=='__main__':raise SystemExit(main())
