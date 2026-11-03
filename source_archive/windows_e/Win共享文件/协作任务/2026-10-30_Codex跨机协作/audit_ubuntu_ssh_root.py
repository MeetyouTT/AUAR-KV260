"""Read only effective SSH policy and firewall; never print host private keys."""
import json
import os
import subprocess

assert os.geteuid() == 0
def run(args):
    result = subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15)
    return dict(exit_code=result.returncode,output=result.stdout.strip())
config = run(['/usr/sbin/sshd','-T','-C','user=ghmd,host=windows-codex,addr=10.148.20.87'])
assert config['exit_code'] == 0
settings = {}
allowed = {'port','listenaddress','pubkeyauthentication','authorizedkeysfile',
           'permitrootlogin','passwordauthentication','kbdinteractiveauthentication',
           'allowtcpforwarding','gatewayports','usepam'}
for line in config['output'].splitlines():
    key,value = line.split(' ',1)
    if key in allowed:
        settings.setdefault(key,[]).append(value)
assert settings['permitrootlogin'][0] in ('no','prohibit-password','without-password','forced-commands-only')
print(json.dumps(dict(status='AUDIT_ONLY',effective_settings=settings,
                     syntax=run(['/usr/sbin/sshd','-t']),
                     firewall=run(['/usr/sbin/ufw','status','verbose']),
                     input_policy=run(['/usr/sbin/iptables','-S','INPUT']),
                     firewall_modified=False,root_password_login_enabled=False)))
