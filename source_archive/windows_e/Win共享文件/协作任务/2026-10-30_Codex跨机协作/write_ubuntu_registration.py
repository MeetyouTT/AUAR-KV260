"""Publish observed, non-secret Ubuntu SSH metadata with an atomic rename."""
import datetime
import json
import os
from pathlib import Path
import re

root = Path(__file__).resolve().parent
def instant(text):
    # PowerShell round-trip timestamps have 7 fractional digits; Python 3.8
    # accepts microseconds. Keep the timezone and truncate only sub-microseconds.
    normalized = re.sub(r'(\.\d{6})\d+(?=Z|[+-]\d\d:\d\d|$)',r'\1',text)
    result = datetime.datetime.fromisoformat(normalized.replace('Z','+00:00'))
    assert result.tzinfo is not None
    return result

project = Path('/home/ghmd/Win共享文件/语音共享文件')
codex = Path('/home/ghmd/.local/bin/codex')
assert project.is_dir() and codex.is_file()
local = json.loads((root/'ubuntu-local-ssh-verification.json').read_text())
assert local['status'] == 'PASS_LOCAL_SSH'
# The user accepted the local SSH checks. Reuse that evidence rather than
# reinstalling, logging in again, or touching any authentication files.
existing = json.loads((root/'ubuntu-registration.json').read_text())
fingerprint = existing['ssh_host_key_sha256']
assert re.fullmatch(r'SHA256:[A-Za-z0-9+/]{43}',fingerprint)
assert fingerprint == 'SHA256:tNZ7GjGBvS/wQDcvA2omrWvQAKLYIaR4/a2WaBf/Mrs'
checks = {item['name']:item for item in local['checks']}
version = checks['codex_version']['stdout'].removeprefix('codex-cli ') if hasattr(str,'removeprefix') else checks['codex_version']['stdout'].replace('codex-cli ','',1)
value = dict(
    schema_version=1,host='172.23.242.132',port=22,user='ghmd',
    project_path=str(project),codex_path=str(codex),codex_version=version,
    ssh_host_key_sha256=fingerprint,ready=False,
    blockers=[
        'Windows reports no SSH banner after the service was started; the reported route traverses singbox_tun.',
        'A timestamped Windows TCP probe correlated with the Ubuntu inbound/return capture is still required to locate the loss.'
    ],
    candidate_addresses=['172.23.242.132'],
    candidate_address_details=[dict(host='172.23.242.132',interface='wlp0s20f3',
                                   prefix_length=16,assigned_on_ubuntu=True,
                                   windows_reachability='UNVERIFIED')],
    source_path=str(project/'aura'),
    ssh_service=dict(installed=True,enabled=True,active=True,port=22,
                     pubkey_authentication=True,root_password_login=False,
                     config_syntax_valid=True),
    public_key_fingerprint='SHA256:2e0xLhkeWwz48xIv0QqIfeTNeXoEX6sgjt2yo5ftvlc',
    authorized_keys_mode='0600',ssh_directory_mode='0700',
    local_ssh_verified=True,ssh_command_shell_codex_verified=True,
    login_shell_codex_verified=True,codex_authenticated=True,
    windows_ssh_verified=False,app_remote_project_verified=False,
    local_preparation_complete=True,
    windows_network=dict(interface='WLAN',ipv4='10.148.20.87',prefix_length=17,
                         gateway='10.148.0.1',reported_ubuntu_route_interface='singbox_tun',
                         source='user_report'),
    ubuntu_return_route='10.148.20.87 via 172.23.0.1 dev wlp0s20f3 src 172.23.242.132',
    ubuntu_firewall=dict(ufw_active=False,input_policy='ACCEPT',modified=False),
    app_server_lan_listener_created=False,app_server_started=False,
    credentials_or_private_keys_shared=False,
    board_modified_in_this_connection_task=False,
    working_roles=dict(ubuntu='board compilation and deployment',
                       windows='27B, OmniVoice and interface integration',
                       final_target='business processing and memory storage on the board; migration is not performed by this connection task'),
    official_documentation='https://learn.chatgpt.com/docs/remote-connections#connect-to-an-ssh-host',
    updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
observation_path = root/'ubuntu-tcp22-observation-latest.json'
if observation_path.exists():
    observation = json.loads(observation_path.read_text())
    value['network_observation'] = {key:observation.get(key) for key in (
        'status','capture_started_utc','finished_utc','packet_count','inbound_syn_count',
        'outbound_syn_ack_count','inbound_ack_count','outbound_rst_count',
        'window_attempt_overlap_confirmed','interpretation','output_directory')}
    value['network_observation']['capture_scope'] = 'all Ubuntu interfaces, IPv4 TCP/22 for 172.23.242.132; no payload log'
    value['network_observation']['capture_time_semantics'] = 'capture_started_utc is when the listening indication was processed; raw packet headers carry their own timestamps'
    value['network_observation']['rp_filter'] = observation['after']['reverse_path_filter'] if 'after' in observation else observation['before']['reverse_path_filter']
    value['network_observation']['routes_modified'] = False
probe_path = root/'windows-tcp22-probe.json'
if probe_path.exists():
    probe = json.loads(probe_path.read_text(encoding='utf-8-sig'))
    assert probe.get('ubuntu_host') == value['host'] and probe.get('port') == value['port']
    value['windows_tcp_probe'] = {key:probe.get(key) for key in ('status','started_utc','finished_utc','route','attempts')}
    if observation_path.exists() and observation.get('finished_utc'):
        start = instant(observation['capture_started_utc'])
        end = instant(observation['finished_utc'])
        overlap = [attempt.get('index') for attempt in probe.get('attempts',[])
                   if attempt.get('started_utc') and attempt.get('finished_utc')
                   and start <= instant(attempt['started_utc'])
                   and instant(attempt['finished_utc']) <= end]
        value['network_observation']['window_attempt_overlap_confirmed'] = bool(overlap)
        value['network_observation']['fully_covered_windows_attempt_indices'] = overlap
        if overlap and observation.get('inbound_syn_count') == 0:
            value['blockers'] = [
                'No SSH SYN was observed at Ubuntu during the timestamp-correlated Windows attempt(s).',
                'Windows TUN forwarding versus upstream network loss still requires Windows-side egress evidence; Ubuntu emitted no SYN-ACK without an incoming SYN.'
            ]
    # A TCP accept alone may be provided locally by a TUN proxy. Require the
    # remote SSH banner before accepting this address for the next SSH phase.
    after_local_check = instant(probe['finished_utc']) >= instant(local['updated_at'])
    banner_received = after_local_check and any(attempt.get('connected') is True and
                          str(attempt.get('banner','')).startswith('SSH-')
                          for attempt in probe.get('attempts',[]))
    if banner_received:
        value['ready'] = True
        value['blockers'] = []
        value['candidate_address_details'][0]['windows_reachability'] = 'SSH_BANNER_RECEIVED'
        value['windows_tcp_banner_verified'] = True
        value['readiness_scope'] = 'Ubuntu prepared and address reachable; Windows host-key verification/authentication and app connection remain separate checks'
value['blocker_scope'] = 'SSH_TCP_NETWORK_PATH_ONLY'
value['local_verification_repeated'] = False
value['board_r3_ubuntu_acceptance'] = 'USER_CONFIRMED_ACCEPTED; NOT_REDEPLOYED'
value['excluded_project_issue'] = 'Windows voice GPU admission shortage is separate from SSH; resource protections were not changed'
paired_path = root/'ubuntu-tcp22-paired-analysis.json'
if paired_path.exists():
    paired = json.loads(paired_path.read_text())
    if paired.get('capture_directory') == value.get('network_observation',{}).get('output_directory'):
        value['paired_network_analysis'] = {key:paired.get(key) for key in (
            'capture_started_utc','capture_finished_utc','windows_attempt_overlap_confirmed',
            'total_captured_packets','total_tcp22_packets','non_ssh_traffic','capture_statistics','conclusion')}
        value['paired_network_analysis']['evidence_file'] = str(paired_path)
        value['windows_network']['observed_probe_source_addresses'] = sorted(set(
            attempt['windows_source_address'] for attempt in paired.get('attempts',[])))
target = root/'ubuntu-registration.json'
temporary = target.with_suffix('.json.tmp')
with temporary.open('w',encoding='utf-8') as stream:
    json.dump(value,stream,ensure_ascii=False,indent=2)
    stream.write('\n')
    stream.flush()
    os.fsync(stream.fileno())
os.replace(str(temporary),str(target))
print(json.dumps(dict(file=str(target),ready=value['ready'],host=value['host'],
                      user=value['user'],port=value['port'],blockers=value['blockers']),ensure_ascii=False))
