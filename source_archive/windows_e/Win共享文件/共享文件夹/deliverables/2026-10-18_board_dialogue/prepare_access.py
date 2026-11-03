"""Create a host-local key; only the public key enters the shared project."""
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
LOCAL=Path('C:/Users/35870/.codex/visualizations/2026/10/09/01a12110-3ba4-7651-b3d7-2e6560916eb6/board-access-20261018')
LOCAL.mkdir(parents=True,exist_ok=True)
key=LOCAL/'id_ed25519'
if not key.exists():
    subprocess.run(['C:/Windows/System32/OpenSSH/ssh-keygen.exe','-q','-t','ed25519','-N','',
                    '-C','aura-windows-20261018','-f',str(key)],check=True)
public=key.with_suffix('.pub').read_text(encoding='utf-8').strip()
(HERE/'board_access.pub').write_text(public+'\n',encoding='ascii')
# Idempotent append; existing board keys remain intact. Run as root on the board.
command="mkdir -p /home/root/.ssh && chmod 700 /home/root/.ssh && touch /home/root/.ssh/authorized_keys && chmod 600 /home/root/.ssh/authorized_keys && (grep -qxF '"+public+"' /home/root/.ssh/authorized_keys || { echo; echo '"+public+"'; } >> /home/root/.ssh/authorized_keys) && echo AURA_KEY_READY"
(HERE/'authorize_windows_on_board.sh').write_text(command+'\n',encoding='ascii')
print(command)
