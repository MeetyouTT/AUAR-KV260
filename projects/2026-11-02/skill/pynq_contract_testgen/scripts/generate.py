#!/usr/bin/env python3
"""Generate a PYNQ register driver from an explicit AXI4-Lite contract.

This module uses only the Python standard library and never imports PYNQ.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
WORD_MAX = (1 << 32) - 1
NAME = re.compile(r"[a-z][a-z0-9_]*\Z")
IP_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(/[A-Za-z_][A-Za-z0-9_]*)*\Z")


class ContractError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def number(value, label):
    require(not isinstance(value, bool), label + ": boolean is not an integer")
    try:
        result = int(value, 0) if isinstance(value, str) else value
    except ValueError:
        raise ContractError(label + ": invalid integer")
    require(isinstance(result, int), label + ": expected integer")
    return result


def keys(value, allowed, required, label):
    require(isinstance(value, dict), label + ": expected object")
    require(not (set(value) - set(allowed)), label + ": unsupported fields " + str(sorted(set(value) - set(allowed))))
    require(not (set(required) - set(value)), label + ": missing fields " + str(sorted(set(required) - set(value))))


def read_json(path):
    path = Path(path)
    require(path.stat().st_size <= 1024 * 1024, "JSON input exceeds 1 MiB")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_contract(raw):
    c = json.loads(json.dumps(raw))
    allowed = {"schema_version", "name", "ip_name", "data_width", "addr_range", "registers", "inputs", "outputs", "control", "timeout_ms", "poll_interval_ms", "metadata_source"}
    keys(c, allowed, allowed, "contract")
    require(type(c["schema_version"]) is int and c["schema_version"] == 1, "unsupported schema_version")
    require(isinstance(c["name"], str) and NAME.fullmatch(c["name"]), "name must use lowercase ASCII identifiers")
    require(isinstance(c["ip_name"], str) and IP_NAME.fullmatch(c["ip_name"]), "invalid ip_name")
    require(type(c["data_width"]) is int and c["data_width"] == 32, "only 32-bit AXI4-Lite scalar registers are supported")
    require(c["metadata_source"] in ("synthetic_fixture", "vivado_export", "user_supplied"), "unsupported metadata_source")
    c["addr_range"] = number(c["addr_range"], "addr_range")
    require(4 <= c["addr_range"] <= 2 ** 32 and c["addr_range"] % 4 == 0, "addr_range must be a positive multiple of four")
    for k in ("timeout_ms", "poll_interval_ms"):
        c[k] = number(c[k], k)
    require(1 <= c["timeout_ms"] <= 60000, "timeout_ms must be in 1..60000")
    require(0 <= c["poll_interval_ms"] <= c["timeout_ms"], "invalid poll_interval_ms")
    require(isinstance(c["registers"], list) and 1 <= len(c["registers"]) <= 256, "registers must contain 1..256 entries")
    regs = {}
    offsets = set()
    hwh_names = set()
    for reg in c["registers"]:
        fields = {"name", "hwh_name", "offset", "width", "access", "read_effect"}
        keys(reg, fields, fields - {"hwh_name"}, "register")
        name = reg["name"]
        require(isinstance(name, str) and NAME.fullmatch(name), "invalid register name")
        require(name not in regs, "duplicate register name: " + name)
        reg.setdefault("hwh_name", name)
        require(isinstance(reg["hwh_name"], str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", reg["hwh_name"]), "invalid hwh_name")
        require(reg["hwh_name"] not in hwh_names, "duplicate hwh_name")
        reg["offset"] = number(reg["offset"], name + ".offset")
        require(0 <= reg["offset"] <= c["addr_range"] - 4 and reg["offset"] % 4 == 0, "unaligned or out-of-range register: " + name)
        require(reg["offset"] not in offsets, "duplicate register offset")
        require(type(reg["width"]) is int and reg["width"] == 32, "only full 32-bit registers are supported")
        require(reg["access"] in ("ro", "wo", "rw"), "unsupported access: " + name)
        require(reg["read_effect"] in ("none", "clear"), "unsupported read_effect: " + name)
        regs[name] = reg
        offsets.add(reg["offset"])
        hwh_names.add(reg["hwh_name"])
    for role in ("inputs", "outputs"):
        names = c[role]
        require(isinstance(names, list) and names and all(isinstance(n, str) for n in names), role + ": expected nonempty name list")
        require(len(names) == len(set(names)), role + ": duplicate register")
        for name in names:
            require(name in regs, "unknown " + role + " register: " + name)
            if role == "inputs":
                require(regs[name]["access"] != "ro", "input register is read-only: " + name)
            else:
                require(regs[name]["access"] != "wo" and regs[name]["read_effect"] == "none", "output must be readable without side effects: " + name)
    require(not set(c["inputs"]) & set(c["outputs"]), "input/output aliases are not supported")
    keys(c["control"], {"start", "done", "done_reset"}, {"start", "done", "done_reset"}, "control")
    require(c["control"]["done_reset"] == "on_start", "done must clear on start; other protocols are not supported")
    start, done = c["control"]["start"], c["control"]["done"]
    keys(start, {"register", "value"}, {"register", "value"}, "start")
    keys(done, {"register", "mask", "value"}, {"register", "mask", "value"}, "done")
    for role, obj in (("start", start), ("done", done)):
        require(isinstance(obj["register"], str) and obj["register"] in regs, role + ": unknown register")
        obj["value"] = number(obj["value"], role + ".value")
        require(0 <= obj["value"] <= WORD_MAX, role + ".value is not uint32")
    require(regs[start["register"]]["access"] != "ro", "start register is read-only")
    require(regs[done["register"]]["access"] != "wo", "done register is write-only")
    done["mask"] = number(done["mask"], "done.mask")
    require(0 < done["mask"] <= WORD_MAX and done["value"] & ~done["mask"] == 0, "invalid done mask/value")
    data_names = set(c["inputs"]) | set(c["outputs"])
    require(start["register"] not in data_names and done["register"] not in data_names, "control/data register alias is not supported")
    return c


def validate_vectors(vectors, contract):
    require(isinstance(vectors, list) and 1 <= len(vectors) <= 10000, "vectors must contain 1..10000 cases")
    ids = set()
    for row in vectors:
        keys(row, {"id", "inputs", "expected"}, {"id", "inputs", "expected"}, "vector")
        require(isinstance(row["id"], str) and NAME.fullmatch(row["id"]) and row["id"] not in ids, "invalid or duplicate case id")
        ids.add(row["id"])
        for field, names in (("inputs", contract["inputs"]), ("expected", contract["outputs"])):
            require(isinstance(row[field], dict) and set(row[field]) == set(names), "vector " + row["id"] + ": incorrect " + field + " names")
            for value in row[field].values():
                require(type(value) is int and 0 <= value <= WORD_MAX, "vector values must be uint32")
    return vectors


def tag(element):
    return element.tag.rsplit("}", 1)[-1]


def properties(element):
    result = dict(element.attrib)
    for child in element:
        if tag(child) == "PROPERTY":
            result[child.get("NAME", "")] = child.get("VALUE")
    return result


def check_hwh(path, contract, allow_incomplete=False):
    data = Path(path).read_bytes()
    require(len(data) <= 16 * 1024 * 1024, "HWH input exceeds 16 MiB")
    require(b"<!DOCTYPE" not in data.upper() and b"<!ENTITY" not in data.upper(), "HWH DTD/entity declarations are unsupported")
    root = ET.fromstring(data)
    ip_name = contract["ip_name"]
    modules = [m for m in root.iter() if tag(m) == "MODULE" and (m.get("FULLNAME", "").lstrip("/") == ip_name or ("/" not in ip_name and m.get("INSTANCE") == ip_name))]
    require(len(modules) == 1, "HWH must contain exactly one matching IP instance: " + ip_name)
    module = modules[0]
    missing = []
    ranges = set()
    for entry in root.iter():
        if tag(entry) == "MEMRANGE" and entry.get("INSTANCE", "").lstrip("/") == ip_name:
            if entry.get("BASEVALUE") is None or entry.get("HIGHVALUE") is None:
                missing.append("address window bounds")
                continue
            low = number(entry.get("BASEVALUE"), "HWH base")
            high = number(entry.get("HIGHVALUE"), "HWH high")
            require(0 <= low <= high < 2 ** 64, "invalid HWH address window")
            ranges.add((low, high))
    require(len(ranges) <= 1, "multiple HWH address windows are unsupported")
    if ranges:
        low, high = next(iter(ranges))
        require(high - low + 1 >= contract["addr_range"], "contract exceeds HWH address window")
    else:
        missing.append("IP address window")
    registers = {}
    for item in module.iter():
        if tag(item) == "REGISTER":
            name = item.get("NAME")
            require(name and name not in registers, "duplicate or unnamed HWH register")
            registers[name] = properties(item)
    access = {"read-only": "ro", "write-only": "wo", "read-write": "rw", "ro": "ro", "wo": "wo", "rw": "rw"}
    for reg in contract["registers"]:
        row = registers.get(reg["hwh_name"])
        if row is None:
            missing.append("register " + reg["hwh_name"])
            continue
        for field, expected in (("ADDRESS_OFFSET", reg["offset"]), ("SIZE", 32)):
            if row.get(field) is None:
                missing.append(reg["hwh_name"] + "." + field)
            else:
                require(number(row[field], "HWH " + field) == expected, "HWH " + field + " mismatch: " + reg["hwh_name"])
        if row.get("ACCESS") is None:
            missing.append(reg["hwh_name"] + ".ACCESS")
        else:
            require(access.get(row["ACCESS"].lower()) == reg["access"], "HWH ACCESS mismatch: " + reg["hwh_name"])
    require(allow_incomplete or not missing, "incomplete HWH metadata: " + ", ".join(missing))
    return {"status": "INCOMPLETE" if missing else "MATCHED", "missing": missing,
            "register_count": len(registers), "metadata_source": contract["metadata_source"],
            "semantic_protocol_verified": False, "hardware_verified": False}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def generate(contract_path, hwh_path, vectors_path, output, mock_path=None, allow_incomplete=False):
    contract = validate_contract(read_json(contract_path))
    vectors = validate_vectors(read_json(vectors_path), contract)
    metadata = check_hwh(hwh_path, contract, allow_incomplete)
    template = (ROOT / "templates/driver.py.tmpl").read_text(encoding="utf-8")
    driver = template.replace("__CONTRACT_LITERAL__", repr(contract)).replace("__HWH_SHA_LITERAL__", repr(sha256(hwh_path))).replace("__METADATA_STATUS_LITERAL__", repr(metadata["status"]))
    compile(driver, "driver.py", "exec")
    test = (ROOT / "templates/test_ip.py.tmpl").read_text(encoding="utf-8")
    compile(test, "test_ip.py", "exec")
    mock = Path(mock_path).read_text(encoding="utf-8") if mock_path is not None else None
    if mock is not None:
        compile(mock, "mock_ip.py", "exec")
    report = {"schema_version": 1, "generator_status": "GENERATED", "metadata": metadata,
              "validation_level": "static_contract_and_metadata", "pynq_runtime_verified": False,
              "board_verified": False, "golden_reference_verified": False,
              "inputs": {"contract_sha256": sha256(contract_path), "hwh_sha256": sha256(hwh_path), "vectors_sha256": sha256(vectors_path)},
              "tool_sha256": sha256(__file__), "case_count": len(vectors)}
    if mock_path is not None:
        report["inputs"]["mock_sha256"] = sha256(mock_path)
    output = Path(output)
    require(not output.exists(), "output already exists; choose a new directory: " + str(output))
    output.mkdir(parents=True)
    files = {"driver.py": driver, "test_ip.py": test,
             "contract.json": json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
             "vectors.json": json.dumps(vectors, ensure_ascii=False, indent=2) + "\n",
             "contract_report.json": json.dumps(report, ensure_ascii=False, indent=2) + "\n",
             "quickstart.md": "# Generated PYNQ test skeleton\n\nRun `python3 test_ip.py --mode mock` when a mock_ip.py is provided. This is software simulation only. For PYNQ use real Vivado metadata, a matching bit/HWH pair, and the documented hardware validation procedure. No overlay has been loaded by code generation.\n"}
    if mock is not None:
        files["mock_ip.py"] = mock
    for name, content in files.items():
        (output / name).write_text(content, encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--hwh", required=True, type=Path)
    parser.add_argument("--vectors", required=True, type=Path)
    parser.add_argument("--mock", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--allow-incomplete-metadata", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = generate(args.contract, args.hwh, args.vectors, args.out, args.mock, args.allow_incomplete_metadata)
    except (ValueError, OSError, ET.ParseError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({"status": "GENERATED", "out": str(args.out), "metadata_status": report["metadata"]["status"], "board_verified": False}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
