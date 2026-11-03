#!/bin/sh
# Run in an already trusted root terminal on the KV260.
# Contains only this Windows host's PUBLIC key; preserves existing keys.
set -eu
if [ "$(id -u)" != 0 ]; then
    printf '%s\n' 'Run this script as root on the KV260.' >&2
    exit 1
fi
key='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPod6SZHW0m4uGiBUSaeJQ1S20cV6VDSLkOAJaFwZs5Q aura-5090-board'
umask 077
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
authorized="$HOME/.ssh/authorized_keys"
if [ -f "$authorized" ]; then
    if grep -Fqx "$key" "$authorized"; then
        printf '%s\n' 'AURA_5090_PUBLIC_KEY_ALREADY_AUTHORIZED'
        exit 0
    fi
    cp -p "$authorized" "$authorized.before-aura-5090-$(date -u +%Y%m%dT%H%M%SZ)-$$"
fi
printf '\n%s\n' "$key" >> "$authorized"
chmod 600 "$authorized"
printf '%s\n' 'AURA_5090_PUBLIC_KEY_AUTHORIZED'
