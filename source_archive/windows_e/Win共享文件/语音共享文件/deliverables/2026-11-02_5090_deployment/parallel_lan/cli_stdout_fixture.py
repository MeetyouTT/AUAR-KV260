"""Exercise the real CLI JSON output with isolated metadata, never live controls."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lan_control as lan


session = "a" * 32
snapshot = dict(
    status="FRESH_IDLE_MODEL_OWNER_CONFIRMED", utc="isolated-fixture",
    session_id=session, configuration_sha256="b" * 64,
    endpoint="http://192.168.50.1:8797", main_owner={"pid": 1},
    tts_owner={"pid": 2}, health={"ok": True, "label": "\u96ea\u5983"},
    tts_ownership={"available": True}, listeners=[], local_acceptance={},
)
adapter = dict(alias="\u4ee5\u592a\u7f51", description="isolated-fixture")
live = SimpleNamespace(adapter=lambda: copy.deepcopy(adapter))
with patch.object(lan, "Live", return_value=live), \
        patch.object(lan, "inspection", return_value=copy.deepcopy(snapshot)), \
        patch.object(sys, "argv", ["lan_control.py", "firewall-guard", "--expected-session", session]):
    lan.main()
