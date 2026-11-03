"""One explicitly authorized maintenance release of the closed session's 27B.

Retains the daemon and all historical session/failed-LAN records. No CLI,
force-stop, model replacement, lock clearing, board access or LAN changes.
"""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
OUT=HERE.parent
ROOT=OUT.parents[1]
HOST=ROOT/'deliverables/2026-10-30_board_owner/integration/production_model_host'
RUNTIME=ROOT/'deliverables/2026-10-18_board_dialogue/model_host'
SESSION='49a75a6f8e3c41f2bddde01bed1cbf45'
sys.path[:0]=[str(HOST),str(ROOT/'aura'),str(ROOT/'deliverables/2026-10-18_board_dialogue')]
import manage
import production_runtime as runtime
from project_ollama import inspect_ownership
from tools.model_inference_host import WindowsTtsProcessProbe
from tools.service_instance_lock import ServiceInstanceLock


def read(path):return json.loads(Path(path).read_bytes())
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def observe():
    latest,state=manage.latest()
    old=read(OUT/'parallel_lan/transactions/547dcb18385242fba3f991e4b9a5983e/latest.original_bytes.json')
    if (latest!=old or latest.get('session_id')!=SESSION or state.get('session_id')!=SESSION
            or state.get('status')!='CLOSED' or state.get('server_closed') is not True
            or state.get('owned_tts_closed') is not True or state.get('owns_fixed_model') is not True
            or state.get('last_control',{}).get('status')!='ACCEPTED'
            or state.get('last_control',{}).get('action')!='stop'):
        raise RuntimeError('Original closed session/ownership proof differs')
    settings,_=manage.config()
    if settings['host']!='127.0.0.1' or settings['allowed_peers']!=['127.0.0.1']:
        raise RuntimeError('Loopback configuration changed')
    source="[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);$rows=@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object {$_.LocalPort -in @(8792,8797)} | Select-Object LocalAddress,LocalPort,OwningProcess);ConvertTo-Json -InputObject $rows -Compress"
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',source],
        capture_output=True,timeout=8,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError('Cannot prove absence of voice listeners')
    listeners=json.loads(result.stdout.decode('utf-8-sig'))
    if listeners:raise RuntimeError('Voice listener appeared; maintenance release refused')
    tts=WindowsTtsProcessProbe().read(deadline=time.monotonic()+10)
    if tts.get('available') is not True or tts.get('logical_workers')!=0:
        raise RuntimeError('TTS workers are present or unknown; maintenance release refused')
    owner=inspect_ownership();expected=state['fixed_daemon_owner']
    if owner.get('pid')!=31632 or any(owner.get(k)!=expected.get(k)
            for k in ('pid','creation_utc','executable','command_line','listeners')):
        raise RuntimeError('Exact project daemon changed; maintenance release refused')
    models=runtime.ollama_json('GET','/api/ps')['models']
    if (len(models)!=1 or models[0].get('name')!=runtime.MODEL
            or models[0].get('context_length')!=2048
            or models[0].get('details',{}).get('quantization_level')!='IQ4_XS'):
        raise RuntimeError('Unique original 27B/2048 residency differs')
    return state,dict(observed_utc=utc(),closed_session_sha256=hashlib.sha256(
        (HOST/'sessions'/SESSION/'status.json').read_bytes()).hexdigest(),
        latest=latest,closed_state=state,voice_listeners=listeners,tts_probe=tts,
        daemon_owner=owner,residency=models)


def main():
    receipt=HERE/'controlled_release_receipt.json'
    if receipt.exists():raise RuntimeError('Maintenance receipt already exists; no duplicate release attempted')
    state,before=observe()
    report=dict(schema='aura-closed-session-maintenance-release-1',status='PRECHECKED',
        original_session=SESSION,failed_lan_transaction='547dcb18385242fba3f991e4b9a5983e',
        authorization='Explicit parent task authorization: once release only this closed session owned fixed27B under lifetime lock, then normal TTS-first loopback start',
        before=before,daemon_stopped=False,unrelated_models_stopped=False,
        forced_action=False,lock_or_control_cleared=False,historical_records_modified=False)
    with ServiceInstanceLock(RUNTIME/'voice8792.instance.lock') as lock:
        state,under_lock=observe()
        if under_lock['closed_session_sha256']!=before['closed_session_sha256']:
            raise RuntimeError('Original closed session record changed during maintenance admission')
        report.update(status='VALIDATED_UNDER_ORIGINAL_LIFETIME_LOCK',under_lock=under_lock,
            original_lifetime_lock_held=lock.held)
        runtime.write_json(receipt,report)
        if runtime.require_owned_model(state) is not True:
            raise RuntimeError('Original owned model is not resident')
        released=runtime.release_owned_model(state)
        after=runtime.ollama_json('GET','/api/ps')['models']
        current=inspect_ownership()
        if (released.get('released') is not True or after
                or any(current.get(k)!=under_lock['daemon_owner'].get(k)
                    for k in ('pid','creation_utc','executable','command_line','listeners'))):
            raise RuntimeError('Controlled release result is not proven')
        if hashlib.sha256((HOST/'sessions'/SESSION/'status.json').read_bytes()).hexdigest()!=before['closed_session_sha256']:
            raise RuntimeError('Original closed session record changed unexpectedly')
        report.update(status='COMPLETED',completed_utc=utc(),release=released,
            residency_after=after,daemon_owner_after=current,
            original_closed_record_unchanged=True)
        runtime.write_json(receipt,report)
    print(json.dumps(dict(status=report['status'],receipt=str(receipt),release=report['release'],
        daemon_pid=report['daemon_owner_after']['pid'])))


if __name__=='__main__':main()
