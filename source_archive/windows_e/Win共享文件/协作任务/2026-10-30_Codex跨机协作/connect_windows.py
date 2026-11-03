"""Register the prepared Ubuntu SSH host, then perform read-only checks.

Run with the current Windows user's permission to edit ~/.ssh. The input JSON
contains connection metadata only. Never execute commands supplied by that JSON.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parent
SSH_ROOT = Path.home() / ".ssh"
ALIAS = "aura-ubuntu"
STATUS = ROOT / "windows-connection.json"


def run(args: list[str], *, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, shell=False, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def write_status(state: dict) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    temporary = STATUS.with_name(STATUS.name + ".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, STATUS)
    print(json.dumps(state, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', help='User-confirmed current Ubuntu IPv4 after changing networks')
    args = parser.parse_args()
    state = {
        "schema_version": 1,
        "status": "WAITING_FOR_UBUNTU_REGISTRATION",
        "ssh_alias": ALIAS,
        "ssh_config_modified": False,
        "host_fingerprint_verified": False,
        "remote_ssh_verified": False,
        "app_remote_project_verified": False,
        "blockers": [],
    }
    registration = ROOT / "ubuntu-registration.json"
    if not registration.exists():
        state["blockers"].append("Ubuntu has not published ubuntu-registration.json yet.")
        write_status(state)
        return 3
    try:
        data = json.loads(registration.read_text(encoding="utf-8-sig"))
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported Ubuntu registration schema.")
        if data.get("ready") is not True and not (args.host and data.get("local_preparation_complete") is True):
            raise ValueError("Ubuntu registration is not ready; inspect its blockers or provide its user-confirmed current address after local preparation.")
        host = str(ipaddress.IPv4Address(args.host or data["host"]))
        state.update({"registration_host": data["host"], "registration_ready": data.get("ready"),
                      "host_source": "user_confirmed_argument" if args.host else "ubuntu-registration.json"})
        if host == "192.168.50.2" or ipaddress.ip_address(host).is_unspecified or ipaddress.ip_address(host).is_multicast:
            raise ValueError("Use the Ubuntu development host, not the KV260 or an unspecified/multicast address.")
        port = data["port"]
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("Invalid SSH port.")
        user = data["user"]
        if not isinstance(user, str) or not re.fullmatch(r"[a-z_][a-z0-9_.-]*\$?", user) or user == "root":
            raise ValueError("Use a non-root Ubuntu development account.")
        project = data["project_path"]
        if not isinstance(project, str) or not project.startswith("/") or any(ord(c) < 32 for c in project):
            raise ValueError("Invalid remote project path.")
        fingerprint = data["ssh_host_key_sha256"]
        if not isinstance(fingerprint, str) or not re.fullmatch(r"SHA256:[A-Za-z0-9+/]{43}=?", fingerprint):
            raise ValueError("An ED25519 host-key SHA256 fingerprint is required.")
        key = SSH_ROOT / "aura_codex_ubuntu_ed25519"
        if not key.is_file() or not key.with_suffix(".pub").is_file():
            raise ValueError("Run prepare_windows.ps1 before registering Ubuntu.")
        tools = {name: shutil.which(name) for name in ("ssh.exe", "ssh-keyscan.exe", "ssh-keygen.exe")}
        if not all(tools.values()):
            raise ValueError("Windows OpenSSH tools are missing.")

        config = SSH_ROOT / "config"
        old_config = config.read_bytes() if config.exists() else b""
        config_text = old_config.decode("utf-8-sig")
        for line in config_text.splitlines():
            tokens = line.split()
            if tokens and tokens[0].lower() == "host" and ALIAS in tokens[1:]:
                if "# BEGIN AURA CODEX UBUNTU" not in config_text:
                    raise ValueError("SSH alias aura-ubuntu already exists outside the managed block; inspect it first.")

        scan = run([tools["ssh-keyscan.exe"], "-T", "5", "-p", str(port), "-t", "ed25519", host], timeout=12)
        host_lines = [line for line in scan.stdout.splitlines() if line.strip() and not line.startswith("#")]
        if scan.returncode != 0 or not host_lines:
            raise ValueError("Ubuntu SSH host-key scan failed: " + scan.stderr.strip()[:600])
        candidate = ROOT / "ubuntu-host-key.candidate"
        candidate_bytes = ("\n".join(sorted(set(host_lines))) + "\n").encode("ascii")
        candidate.write_bytes(candidate_bytes)
        checked = run([tools["ssh-keygen.exe"], "-lf", str(candidate)])
        matches = re.findall(r"SHA256:[A-Za-z0-9+/]+={0,2}", checked.stdout)
        if checked.returncode != 0 or not matches or any(item != fingerprint for item in matches):
            raise ValueError("SSH host fingerprint does not match the Ubuntu registration; no SSH configuration changed.")
        state["host_fingerprint_verified"] = True

        known_hosts = SSH_ROOT / "aura_codex_ubuntu_known_hosts"
        if known_hosts.exists() and known_hosts.read_bytes() != candidate_bytes:
            raise ValueError("Dedicated known-hosts entry differs. Inspect the change instead of replacing it.")
        if not known_hosts.exists():
            with known_hosts.open("xb") as handle:
                handle.write(candidate_bytes)

        block = (
            "# BEGIN AURA CODEX UBUNTU\n"
            f"Host {ALIAS}\n"
            f"    HostName {host}\n"
            f"    Port {port}\n"
            f"    User {user}\n"
            "    IdentityFile ~/.ssh/aura_codex_ubuntu_ed25519\n"
            "    IdentitiesOnly yes\n"
            "    BatchMode yes\n"
            "    StrictHostKeyChecking yes\n"
            "    UserKnownHostsFile ~/.ssh/aura_codex_ubuntu_known_hosts\n"
            "    ConnectTimeout 10\n"
            "    ServerAliveInterval 30\n"
            "    ServerAliveCountMax 3\n"
            "# END AURA CODEX UBUNTU\n"
        )
        if "# BEGIN AURA CODEX UBUNTU" in config_text:
            if config_text.count("# BEGIN AURA CODEX UBUNTU") != 1 or config_text.count("# END AURA CODEX UBUNTU") != 1:
                raise ValueError("Unexpected managed SSH blocks; inspect the config.")
            current = config_text.split("# BEGIN AURA CODEX UBUNTU", 1)[1].split("# END AURA CODEX UBUNTU", 1)[0]
            if ("# BEGIN AURA CODEX UBUNTU" + current + "# END AURA CODEX UBUNTU\n").replace("\r\n", "\n") != block:
                raise ValueError("Existing managed SSH host differs; review before updating it.")
        else:
            if (config.read_bytes() if config.exists() else b"") != old_config:
                raise ValueError("SSH config changed while preparing; rerun after reviewing it.")
            if old_config:
                backup = SSH_ROOT / ("config.aura-before-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".bak")
                with backup.open("xb") as handle:
                    handle.write(old_config)
            with config.open("ab") as handle:
                handle.write((b"\n" if old_config and not old_config.endswith(b"\n") else b"") + block.encode("ascii"))
            state["ssh_config_modified"] = True

        resolved = run([tools["ssh.exe"], "-G", ALIAS])
        options = dict(line.split(" ", 1) for line in resolved.stdout.splitlines() if " " in line)
        if resolved.returncode != 0 or options.get("hostname") != host or options.get("user") != user or options.get("port") != str(port):
            raise ValueError("Resolved SSH settings differ; an existing config rule may take precedence.")
        state.update({"status": "SSH_CONFIGURED", "host": host, "port": port, "user": user, "project_path": project})
        checks = []
        commands = [
            ("codex_path", "command -v codex"),
            ("codex_version", "codex --version"),
            ("codex_authenticated", "codex login status >/dev/null 2>&1"),
            ("project_exists", "test -d " + shlex.quote(project)),
        ]
        for name, command in commands:
            result = run([tools["ssh.exe"], "-T", ALIAS, command], timeout=30)
            checks.append({"name": name, "exit_code": result.returncode, "stdout": result.stdout.strip()[:1000], "stderr": result.stderr.strip()[:1000]})
            if result.returncode != 0:
                state["checks"] = checks
                raise ValueError("Read-only SSH check failed: " + name)
        state["checks"] = checks
        state["remote_ssh_verified"] = True
        state["status"] = "SSH_VERIFIED_WAITING_FOR_APP_CONNECTION"
        state["blockers"] = ["Add aura-ubuntu in app Settings > Connections > SSH, then choose the verified project folder."]
        write_status(state)
        return 0
    except (KeyError, ValueError, OSError, subprocess.TimeoutExpired) as error:
        state["status"] = "CONNECTION_NOT_VERIFIED"
        state["blockers"].append(str(error))
        write_status(state)
        return 1


if __name__ == "__main__":
    sys.exit(main())
