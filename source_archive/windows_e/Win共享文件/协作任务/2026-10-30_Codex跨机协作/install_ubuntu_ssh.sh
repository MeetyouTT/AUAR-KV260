#!/bin/bash
# Run through the Ubuntu administrator authorization dialog or sudo locally.
# Installs only OpenSSH Server and its dependencies. Does not contact the board.
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
    printf '%s\n' 'Administrator authorization is required.' >&2
    exit 1
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get -o Dpkg::Options::=--force-confold --no-install-recommends install -y openssh-server
/usr/sbin/sshd -t
root_login=$(/usr/sbin/sshd -T -C user=root,host=localhost,addr=127.0.0.1 | awk '$1 == "permitrootlogin" {print $2}')
case "$root_login" in
    no|prohibit-password|without-password|forced-commands-only) ;;
    *) printf '%s\n' 'Root password login would be allowed; preserve config for manual review.' >&2; exit 1 ;;
esac
systemctl enable --now ssh.service
systemctl show ssh.service -p LoadState -p ActiveState -p SubState -p UnitFileState
/usr/bin/ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
printf '%s\n' 'SSH_INSTALL_AND_START_COMPLETE'
