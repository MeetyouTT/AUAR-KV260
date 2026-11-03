"""Generated AXI4-Lite driver. No PYNQ import or hardware access at import time."""
import hashlib
from pathlib import Path
import time


CONTRACT = {'schema_version': 1, 'name': 'crc32', 'ip_name': 'checksum_unit_0', 'data_width': 32, 'addr_range': 512, 'metadata_source': 'synthetic_fixture', 'timeout_ms': 100, 'poll_interval_ms': 1, 'registers': [{'name': 'command', 'hwh_name': 'CMD', 'offset': 64, 'width': 32, 'access': 'wo', 'read_effect': 'none'}, {'name': 'status', 'hwh_name': 'STATUS', 'offset': 68, 'width': 32, 'access': 'ro', 'read_effect': 'clear'}, {'name': 'word', 'hwh_name': 'DATA', 'offset': 128, 'width': 32, 'access': 'rw', 'read_effect': 'none'}, {'name': 'digest', 'hwh_name': 'CRC', 'offset': 160, 'width': 32, 'access': 'ro', 'read_effect': 'none'}], 'inputs': ['word'], 'outputs': ['digest'], 'control': {'start': {'register': 'command', 'value': 4}, 'done': {'register': 'status', 'mask': 128, 'value': 128}, 'done_reset': 'on_start'}}
EXPECTED_HWH_SHA256 = '69054b25869810546e01486c9b623fdbcf5c35c13ec238e7cc01b852f8cfab73'
METADATA_STATUS = 'MATCHED'


class ContractDriver:
    def __init__(self, ip, clock=None, sleep=None):
        self.ip = ip
        self.registers = {row["name"]: row for row in CONTRACT["registers"]}
        self.clock = clock or time.monotonic
        self.sleep = sleep or time.sleep

    @staticmethod
    def _word(value):
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError("expected uint32 value")
        return value

    def read_register(self, name):
        reg = self.registers[name]
        if reg["access"] == "wo":
            raise PermissionError("write-only register: " + name)
        return int(self.ip.read(reg["offset"])) & 0xffffffff

    def write_register(self, name, value):
        reg = self.registers[name]
        if reg["access"] == "ro":
            raise PermissionError("read-only register: " + name)
        self.ip.write(reg["offset"], self._word(value))

    def run(self, inputs):
        if not isinstance(inputs, dict) or set(inputs) != set(CONTRACT["inputs"]):
            raise ValueError("input names do not match the contract")
        # Validate every input before the first write.
        values = {name: self._word(inputs[name]) for name in CONTRACT["inputs"]}
        for name, value in values.items():
            self.write_register(name, value)
        control = CONTRACT["control"]
        deadline = self.clock() + CONTRACT["timeout_ms"] / 1000.0
        self.write_register(control["start"]["register"], control["start"]["value"])
        done = control["done"]
        while True:
            status = self.read_register(done["register"])
            remaining = deadline - self.clock()
            if remaining < 0:
                raise TimeoutError("completion was observed after the declared timeout")
            if status & done["mask"] == done["value"]:
                break
            if remaining <= 0:
                raise TimeoutError("IP did not complete within the declared timeout")
            self.sleep(min(CONTRACT["poll_interval_ms"] / 1000.0, remaining))
        return {name: self.read_register(name) for name in CONTRACT["outputs"]}


def open_overlay(bit_path, program=False, accept_incomplete_metadata=False):
    """Open a real PYNQ overlay only when the caller explicitly chooses this path."""
    if CONTRACT["metadata_source"] != "vivado_export":
        raise RuntimeError("real hardware mode requires a contract generated with real Vivado metadata")
    if METADATA_STATUS != "MATCHED" and not accept_incomplete_metadata:
        raise RuntimeError("register metadata is incomplete; review the contract before hardware access")
    bit_path = Path(bit_path).resolve()
    if bit_path.suffix != ".bit" or not bit_path.is_file():
        raise ValueError("provide an existing .bit file")
    hwh_path = bit_path.with_suffix(".hwh")
    if not hwh_path.is_file() or hashlib.sha256(hwh_path.read_bytes()).hexdigest() != EXPECTED_HWH_SHA256:
        raise ValueError("matching HWH must have the same stem and the hash used at generation time")
    from pynq import Overlay
    overlay = Overlay(str(bit_path), download=False)
    if program:
        overlay.download()
    elif not overlay.is_loaded():
        raise RuntimeError("overlay is not loaded; explicit --program is required to load it")
    description = overlay.ip_dict.get(CONTRACT["ip_name"])
    if description is None or int(description.get("addr_range", 0)) < CONTRACT["addr_range"]:
        raise RuntimeError("runtime IP instance/address range does not match the contract")
    ip = overlay
    for name in CONTRACT["ip_name"].split("/"):
        ip = getattr(ip, name)
    return overlay, ContractDriver(ip)
