"""Export noncredential Codex/SSH configuration, without changing the live install."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tomllib

PACKAGE = Path(__file__).resolve().parents[1]
SOURCE = Path('C:/Users/35870/.codex')
OUT = PACKAGE/'codex/configuration'
OUT.mkdir(parents=True, exist_ok=True)
changes = []
SECRET_KEY = re.compile(r'(?i)(?:password|passwd|access.?token|refresh.?token|id.?token|bearer|client.?secret|authorization|cookie|api.?key|private.?key)')
PEM = re.compile(r'-----BEGIN (?:[A-Z ]+)?PRIVATE KEY-----.*?-----END (?:[A-Z ]+)?PRIVATE KEY-----', re.S)
TOKEN = re.compile(r'\b(?:sk-[A-Za-z0-9_-]{16,}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,})\b')


def clean_string(value, label):
    for pattern in (PEM, TOKEN, re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/-]{12,}=*')):
        value, count = pattern.subn('[REDACTED_REAUTHENTICATE]', value)
        if count:
            changes.append(dict(path=label, count=count))
    return value


def scrub(value, label='root'):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            where = label+'.'+key
            public_reference = re.search(r'(?i)(?:path|file|env|name|variable)$', key)
            if SECRET_KEY.search(key) and not public_reference and item:
                result[key] = '[REDACTED_REAUTHENTICATE]'
                changes.append(dict(path=where, count=1))
            else:
                result[key] = scrub(item, where)
        return result
    if isinstance(value, list):
        return [scrub(item, label+'[]') for item in value]
    if isinstance(value, str):
        return clean_string(value, label)
    return value


def toml_value(value):
    if isinstance(value, bool): return 'true' if value else 'false'
    if isinstance(value, str): return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (int, float)): return str(value)
    if isinstance(value, list): return '['+', '.join(map(toml_value, value))+']'
    if isinstance(value, dict):
        return '{ '+', '.join(json.dumps(k, ensure_ascii=False)+' = '+toml_value(v) for k,v in value.items())+' }'
    raise ValueError('Unsupported TOML value type: '+type(value).__name__)


def write_toml(path, value):
    text = '# Migration reference; merge after checking paths and signing in on the new host.\n'
    text += '\n'.join(json.dumps(key, ensure_ascii=False)+' = '+toml_value(item) for key,item in value.items())+'\n'
    assert tomllib.loads(text) == value
    path.write_text(text, encoding='utf-8')


cfg_raw = (SOURCE/'config.toml').read_bytes()
config = scrub(tomllib.loads(cfg_raw.decode('utf-8')))
write_toml(OUT/'config.sanitized.toml', config)
(OUT/'config.sanitized.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
portable = json.loads(json.dumps(config).replace('C:\\\\Users\\\\35870', '__USERPROFILE__').replace('C:/Users/35870','__USERPROFILE__'))
write_toml(OUT/'config.portable.template.toml', portable)

global_raw = (SOURCE/'.codex-global-state.json').read_bytes()
state = json.loads(global_raw)
keep = ('codex-managed-remote-connections', 'selected-remote-host-id',
        'remote-connection-auto-connect-by-host-id', 'local-projects', 'project-order')
settings = {key:state[key] for key in keep if key in state}
atoms = state.get('electron-persisted-atom-state', {})
settings['relevant_atom_settings_reference_only'] = {key:item for key,item in atoms.items()
    if key in ('mcp-global-entrypoints-v2', 'agent-mode-by-host-id',
               'preferred-non-full-access-agent-mode-by-host-id', 'composer-auto-context-enabled')}
settings = scrub(settings)
(OUT/'desktop_remote_settings.reference.json').write_text(json.dumps(settings,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

ssh_source = Path('C:/Users/35870/.ssh')
ssh_out = PACKAGE/'codex/ssh'
ssh_out.mkdir(parents=True, exist_ok=True)
copied_public = []
for name in ('config', 'known_hosts', 'aura_codex_ubuntu_known_hosts', 'aura_codex_ubuntu_ed25519.pub'):
    path = ssh_source/name
    if path.is_file() and not path.is_symlink():
        raw = path.read_bytes()
        assert b'PRIVATE KEY' not in raw
        text = clean_string(raw.decode('utf-8'), 'ssh.'+name)
        (ssh_out/(name+'.reference' if name=='config' else name)).write_text(text,encoding='utf-8')
        copied_public.append(name)
board_key = Path('C:/Users/35870/.codex/visualizations/2026/10/09/01a12110-3ba4-7651-b3d7-2e6560916eb6/board-access-20261018/id_ed25519')
if board_key.with_suffix('.pub').is_file():
    raw = board_key.with_suffix('.pub').read_bytes()
    assert raw.startswith(b'ssh-ed25519 ') and b'PRIVATE KEY' not in raw
    (ssh_out/'old_board_key.pub').write_bytes(raw)
    copied_public.append('old_board_key.pub')
template = '''# New keys are generated in the new Windows user's .ssh directory.
# Merge this block; do not overwrite unrelated SSH hosts.
Host aura-ubuntu
    HostName 192.168.137.141
    User ghmd
    Port 22
    IdentityFile ~/.ssh/aura_5090_ubuntu_ed25519
    UserKnownHostsFile ~/.ssh/aura_migration_known_hosts
    IdentitiesOnly yes
    StrictHostKeyChecking yes
    ConnectTimeout 10
    ServerAliveInterval 30
    ServerAliveCountMax 3

Host aura-kv260
    HostName 192.168.50.2
    User root
    Port 22
    IdentityFile ~/.ssh/aura_5090_board_ed25519
    UserKnownHostsFile ~/.ssh/aura_migration_known_hosts
    IdentitiesOnly yes
    StrictHostKeyChecking yes
    ConnectTimeout 10
'''
(ssh_out/'config.5090.template').write_text(template,encoding='utf-8')
known = set()
for name in ('known_hosts','aura_codex_ubuntu_known_hosts'):
    path=ssh_out/name
    if path.exists(): known.update(line.strip() for line in path.read_text('utf-8').splitlines() if line.strip())
(ssh_out/'aura_migration_known_hosts').write_text('\n'.join(sorted(known))+'\n',encoding='utf-8')

plugins = dict(enabled_configuration=config.get('plugins',{}),marketplaces=config.get('marketplaces',{}),
               mcp_servers=config.get('mcp_servers',{}),
               reinstall_using_new_codex_plugin_manager=True,oauth_reauthentication_required=True,
               installed_cache_is_not_a_portable_runtime=True)
(OUT/'plugins_and_mcp.json').write_text(json.dumps(plugins,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

files=[]
for folder in (OUT,ssh_out):
    for path in sorted(folder.rglob('*')):
        if path.is_file():
            raw=path.read_bytes()
            assert not PEM.search(raw.decode('utf-8')) and not TOKEN.search(raw.decode('utf-8'))
            files.append(dict(path=str(path.relative_to(PACKAGE)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
report = dict(schema='aura-codex-noncredential-export-1',status='EXPORTED_REFERENCE_AND_PORTABLE_TEMPLATES',
    source_config_sha256=hashlib.sha256(cfg_raw).hexdigest(),
    source_global_state_sha256=hashlib.sha256(global_raw).hexdigest(),
    project_global_configuration_exported=True,ssh_public_files=copied_public,
    exported_private_keys=False,exported_auth_json=False,exported_browser_or_security_store=False,
    redactions=changes,files=files,live_codex_or_ssh_configuration_modified=False,
    docs=['https://learn.chatgpt.com/docs/config-file/config-basic','https://learn.chatgpt.com/docs/remote-connections#connect-to-an-ssh-host'])
(PACKAGE/'codex/CONFIG_EXPORT_MANIFEST.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=report['status'],files=len(files),redactions=len(changes),private_credentials_copied=False)))
