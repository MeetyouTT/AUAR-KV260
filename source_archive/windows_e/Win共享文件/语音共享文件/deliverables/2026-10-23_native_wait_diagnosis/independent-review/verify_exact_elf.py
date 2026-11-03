"""Local-only, deterministic evidence checks; never imports the ARM module."""
import hashlib
import json
import pathlib
import struct

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
elf_path = ROOT / "exact-runtime/vart.so"
elf = elf_path.read_bytes()
expected_sha = "dc6bff9be31b8dc349a72489e06237f8503175805d042025558694823f61de34"
assert len(elf) == 194720
assert hashlib.sha256(elf).hexdigest() == expected_sha
assert elf[:6] == b"\x7fELF\x02\x01"
assert struct.unpack_from("<H", elf, 18)[0] == 183  # EM_AARCH64
phoff = struct.unpack_from("<Q", elf, 32)[0]
phsize, phcount = struct.unpack_from("<HH", elf, 54)
loads = []
for i in range(phcount):
    kind, flags, off, va, pa, filesz, memsz, align = struct.unpack_from("<IIQQQQQQ", elf, phoff + i * phsize)
    if kind == 1:
        loads.append({"offset": off, "virtual_address": va, "file_size": filesz, "flags": flags})
assert loads[0] == {"offset": 0, "virtual_address": 0, "file_size": 0x2d2e5, "flags": 5}
# .text and .rodata file offset equal ELF virtual address in this ELF.
for address, value in [(0x26620, b"execute_async\0"), (0x26630, b"wait\0")]:
    assert elf[address:address + len(value)] == value

ops = {
    0xD4A0: 0xF0000000, 0xD4A4: 0x911BC000,
    0xD4A8: 0xB00000C1, 0xD4AC: 0x91188021,
    0xD4B8: 0xF90002A1, 0xD4C4: 0xF9001AA0,
    0xD5FC: 0x9118C321, 0xD600: 0xD0000002,
    0xD604: 0x91378042, 0xD610: 0xF9000001,
    0xD620: 0xF9001802,
    0x109F0: 0x97FFE0B8, 0x109F8: 0xAA0003F3,
    0x10A04: 0xAA1403E0,
    0x10A08: 0xF9400863, 0x10A0C: 0xD63F0060,
    0x10A10: 0xAA0003F6, 0x10A1C: 0xAA1303E0,
    0x10A20: 0x97FFDEF8, 0x10A44: 0x97FFF8A3,
    0x10A74: 0x97FFF897,
    0xFFDC: 0x12800002, 0xFFEC: 0xF9400C63,
    0xFFF4: 0xD63F0060,
}
for address, opcode in ops.items():
    assert address % 4 == 0 and address < loads[0]["file_size"]
    assert struct.unpack_from("<I", elf, address)[0] == opcode, hex(address)

event_path = ROOT / "event-5788-raw.json"
event = json.loads(event_path.read_text())
t = event["trace"]
left, right = event["left_raw_sample"], event["right_raw_sample"]
assert event["tid"] == t["calling_thread_native_id"] == 499788
assert left[1] < t["execute_start_mono_ns"] < t["execute_return_mono_ns"] < right[0]
assert right[3] - left[3] == 0
assert right[2] - left[2] == 3447954
assert t["execute_return_mono_ns"] - t["execute_start_mono_ns"] == 30167721
assert t["execute_return_thread_cpu_ns"] - t["execute_start_thread_cpu_ns"] == 580727

result = {
    "scope": "LOCAL_STATIC_ANALYSIS_NO_BOARD_NO_INFERENCE_NO_MODULE_IMPORT",
    "elf": {"bytes": len(elf), "sha256": expected_sha,
            "build_id": "e359176b9761d3035b0301d4ec6c48de9a0af577",
            "source_commit_matched": False, "debug_info_matched": False,
            "load_segments": loads},
    "execute_binding": {"name_elf_address": "0x26620", "callback": "0x106f0",
                        "record_name_store": "0xd4b8", "record_callback_store": "0xd4c4",
                        "record_name_offset": 0, "record_callback_offset": 48},
    "execute_normal_path": {
        "save_thread_call": "0x109f0", "save_thread_plt": "0x8cd0",
        "runner_virtual_offset": 16, "runner_virtual_call": "0x10a0c",
        "native_return_instruction": "0x10a10",
        "restore_thread_call": "0x10a20", "restore_thread_plt": "0x8600",
        "after_restore_instruction": "0x10a24",
        "buffer_map_calls_after_restore": ["0x10a44", "0x10a74"],
        "releases_gil_around_runner_virtual_call": True,
        "runtime_duration_of_each_native_subphase_collected": False,
    },
    "wait_binding": {"name_elf_address": "0x26630", "callback": "0xfde0",
                     "record_name_store": "0xd610", "record_callback_store": "0xd620",
                     "runner_virtual_offset": 24, "runner_virtual_call": "0xfff4",
                     "timeout_argument": -1,
                     "explicit_release_around_this_virtual_call_observed": False,
                     "all_possible_overloads_or_transitive_native_code_audited": False},
    "verified_instruction_words": {hex(k): f"{v:08x}" for k, v in ops.items()},
    "event_5788": {
        "tid": event["tid"], "left_raw_sample": left, "right_raw_sample": right,
        "execute_start_ns": t["execute_start_mono_ns"],
        "execute_return_ns": t["execute_return_mono_ns"],
        "execute_wall_ns": 30167721, "execute_thread_cpu_ns": 580727,
        "runqueue_delta_ns": right[3] - left[3],
        "runtime_delta_ns": right[2] - left[2],
        "timeslices_delta": right[4] - left[4],
        "expanded_bracket_ns": right[1] - left[0],
        "snapshot_interval_lower_ns": right[0] - left[1],
        "before_edge_ns": t["execute_start_mono_ns"] - left[0],
        "after_edge_ns": right[1] - t["execute_return_mono_ns"],
        "gil_wait_proven": False, "native_or_driver_wait_excluded": False,
        "observer_cost_gate_passed": False,
    },
    "uprobes_proposed_only": {
        "native_return": "0x10a10", "before_restore_call": "0x10a20",
        "after_restore_call": "0x10a24", "native_entry_optional": "0x10a0c",
        "file_offsets_equal_elf_addresses_for_these_instructions": True,
        "non_branch_native_pre_point": "0x10a04",
        "non_branch_restore_pre_point": "0x10a1c",
        "board_trace_capability_checked_by_root": True,
        "actual_registration_hit_and_cost_verified": False, "enabled": False,
    },
}
(HERE / "exact-elf-evidence.json").write_text(json.dumps(result, indent=2) + "\n")
print("Exact ELF, opcode/name/callback checks and raw event bracket arithmetic: PASS")
