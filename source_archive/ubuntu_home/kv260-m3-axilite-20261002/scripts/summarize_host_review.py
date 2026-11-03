#!/usr/bin/env python3
"""Summarize real routed reports and generated metadata, without board operations."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import csv
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
POST = ROOT / "evidence/postroute"
SD = ROOT / "src/kv260/overlays/examples/benchmark/binary_container_1/sd_card"


def json_read(path):
    return json.loads(path.read_text())


def timing_summary():
    lines = (POST / "timing_summary.rpt").read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if "WNS(ns)" in line)
    row = next(line.split() for line in lines[start + 1:start + 7]
               if len(line.split()) == 12 and re.match(r"^[+-]?\d+\.\d+$", line.split()[0]))
    names = ["wns_ns", "tns_ns", "setup_failing_endpoints", "setup_total_endpoints",
             "whs_ns", "ths_ns", "hold_failing_endpoints", "hold_total_endpoints",
             "wpws_ns", "tpws_ns", "pulse_failing_endpoints", "pulse_total_endpoints"]
    summary = {name: (float(value) if i % 4 < 2 else int(value))
               for i, (name, value) in enumerate(zip(names, row))}
    counts = {name: int(value) for name, value in re.findall(
        r"checking (\w+) \((\d+)\)", (POST / "check_timing.rpt").read_text())}
    internal_coverage = all(counts.get(name) == 0 for name in
                            ["no_clock", "unconstrained_internal_endpoints"])
    covered_pass = all(summary[name] >= 0 for name in ["wns_ns", "whs_ns", "wpws_ns"]) and all(
        summary[name] == 0 for name in ["setup_failing_endpoints", "hold_failing_endpoints", "pulse_failing_endpoints"])
    return {"summary": summary, "check_timing_counts": counts,
            "covered_paths_pass": covered_pass,
            "internal_clock_and_constraint_coverage_pass": internal_coverage,
            "complete_io_delay_coverage": counts["no_input_delay"] == counts["no_output_delay"] == 0}


def resources():
    desired = {"CLB LUTs", "CLB Registers", "CLB", "Block RAM Tile", "URAM", "DSPs"}
    values = {}
    for line in (POST / "utilization.rpt").read_text().splitlines():
        cells = [value.strip() for value in line.split("|")]
        if len(cells) >= 7:
            name = cells[1].rstrip("*")
            if name in desired:
                values[name] = {"used": float(cells[2].replace(",", "")),
                                "available": float(cells[5].replace(",", "")),
                                "percent": float(cells[6])}
    if set(values) != desired:
        raise ValueError("Incomplete resource table")
    return values


def drc_summary():
    with (POST / "drc_objects.tsv").open() as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    checks = Counter()
    severities = Counter()
    for row in rows:
        check = re.match(r"([A-Z]+-\d+)", row["NAME"])
        if check is None:
            raise ValueError("Unknown DRC object name: " + row["NAME"])
        checks[check.group(1)] += 1
        severities[row["SEVERITY"]] += 1
    return {"total": len(rows), "check_counts": dict(sorted(checks.items())),
            "severity_counts": dict(severities), "actual_HDPR_5_count": checks["HDPR-5"]}


def metadata():
    hwh = ET.parse(SD / "kv260_ispMipiRx_vcu_DP.hwh").getroot()
    modules = list(hwh.iter("MODULE"))
    dpu = [node for node in modules if node.get("INSTANCE") == "DPUCZDX8G_1"]
    m3 = [node for node in modules if node.get("INSTANCE") == "aura_m3_regs_0"]
    if len(dpu) != 1 or len(m3) != 1:
        raise ValueError("Expected one DPU module and one M3 module")
    parameters = {node.get("NAME"): node.get("VALUE") for node in dpu[0].iter("PARAMETER")}
    dpu_ranges = [dict(node.attrib) for node in hwh.iter("MEMRANGE") if node.get("INSTANCE") == "DPUCZDX8G_1"]
    m3_ranges = [dict(node.attrib) for node in hwh.iter("MEMRANGE") if node.get("INSTANCE") == "aura_m3_regs_0"]
    expected_ranges = {"DPUCZDX8G_1": (0xA0010000, 0xA0010FFF), "aura_m3_regs_0": (0x80080000, 0x80080FFF)}
    ranges_pass = all(any(int(row["BASEVALUE"], 0) == base and int(row["HIGHVALUE"], 0) == high
                         for row in ranges) for ranges, (base, high) in
                      [(dpu_ranges, expected_ranges["DPUCZDX8G_1"]), (m3_ranges, expected_ranges["aura_m3_regs_0"])])
    arch = json_read(SD / "arch.json")
    arch_pass = int(arch["fingerprint"], 0) == 0x101000056010407
    core_pass = int(parameters["SYS_IP_VER"], 0) == 0x41 and int(parameters["SAVE_ARGMAX_ENA"], 0) == 1
    source_header = (ROOT / "rtl/m3_build_id.vh").read_bytes()
    packaged_header = (ROOT / "ip_repo/aura_m3_regs/src/m3_build_id.vh").read_bytes()
    header_pass = source_header == packaged_header
    inventory = (POST / "inventory.txt").read_text()
    hierarchy = re.search(r"^M3_HIERARCHY=(.+)$", inventory, re.MULTILINE)
    layout = json_read(ROOT / "evidence/xclbin_IP_LAYOUT.json")["ip_layout"]
    layout_pass = (int(layout["m_count"]) == 1 and len(layout["m_ip_data"]) == 1
                   and int(layout["m_ip_data"][0]["m_base_address"], 0) == 0xA0010000
                   and layout["m_ip_data"][0]["m_name"] == "DPUCZDX8G:DPUCZDX8G_1")
    parent = ROOT.parent / "kv260-dpu41-control-20261001"
    parent_hwh = ET.parse(parent / SD.relative_to(ROOT) / "kv260_ispMipiRx_vcu_DP.hwh").getroot()
    parent_dpu = next(node for node in parent_hwh.iter("MODULE")
                      if node.get("INSTANCE") == "DPUCZDX8G_1")
    parent_parameters = {node.get("NAME"): node.get("VALUE")
                         for node in parent_dpu.iter("PARAMETER")}
    parameters_match = parameters == parent_parameters
    connections = json_read(ROOT / "evidence/xclbin_CONNECTIVITY.json")
    connections_pass = connections == json_read(parent / "evidence/xclbin_CONNECTIVITY.json")
    topology = json_read(ROOT / "evidence/xclbin_MEM_TOPOLOGY.json")
    topology_pass = topology == json_read(ROOT / "evidence/validated_parent_MEM_TOPOLOGY.json")
    return {"arch": arch, "dpu_parameters_checked": {key: parameters[key] for key in
            ["SYS_IP_VER", "SAVE_ARGMAX_ENA", "ARCH_PP", "ARCH_ICP", "ARCH_OCP"]},
            "dpu_parameter_count": len(parameters),
            "all_dpu_parameters_match_validated_parent": parameters_match,
            "dpu_memory_ranges": dpu_ranges, "m3_memory_ranges": m3_ranges,
            "address_ranges_pass": ranges_pass, "architecture_matches_validated_model": arch_pass,
            "dpu_version_and_argmax_pass": core_pass,
            "packaged_build_id_header_matches": header_pass,
            "xclbin_ip_layout": layout, "xclbin_layout_pass": layout_pass,
            "xclbin_connectivity_matches_validated_parent": connections_pass,
            "xclbin_memory_topology_matches_validated_parent": topology_pass,
            "m3_hierarchy_retained": hierarchy is not None,
            "host_metadata_pass": all([ranges_pass, arch_pass, core_pass, header_pass,
                                        hierarchy is not None, layout_pass, connections_pass,
                                        topology_pass, parameters_match])}


def route_status():
    text = (POST / "route_status.rpt").read_text()
    values = {}
    for label in ["routable nets", "fully routed nets", "nets with routing errors"]:
        match = re.search(r"# of " + re.escape(label) + r"\.+\s*:\s*(\d+)", text)
        if match is None:
            raise ValueError("Missing route count: " + label)
        values[label] = int(match.group(1))
    values["pass"] = values["nets with routing errors"] == 0 and values["routable nets"] == values["fully routed nets"]
    return values


def endpoint_clocks():
    with (POST / "endpoint_clocks.tsv").open() as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    expected = {"DPU_ACLK": ("clk_300M_", 1000 / 300),
                "DPU_2X": ("clk_600M_", 1000 / 600),
                "M3_ACLK": ("clk_100M_", 10.0)}
    passed = len(rows) == 3 and {row["ENDPOINT"] for row in rows} == set(expected)
    for row in rows:
        prefix, period = expected[row["ENDPOINT"]]
        row["period_matches_nominal"] = abs(float(row["PERIOD_NS"]) - period) < 0.001
        row["expected_clock_connected"] = row["CLOCK"].startswith(prefix)
        passed = passed and row["period_matches_nominal"] and row["expected_clock_connected"]
    return {"endpoints": rows, "nominal_clocks_and_connections_pass": passed}


def main():
    timing = timing_summary()
    drc = drc_summary()
    hardware = metadata()
    route = route_status()
    clocks = endpoint_clocks()
    integrity = json_read(ROOT / "evidence/input_integrity_audit.json")
    blocking_drc = sum(count for severity, count in drc["severity_counts"].items()
                       if severity.casefold().replace("_", " ") in
                       {"error", "fatal", "critical warning", "criticalwarning"})
    summary = {"reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
               "scope": "Host-side build review; no board inference or register access performed",
               "build_identity": json_read(ROOT / "evidence/build_identity.json"),
               "timing": timing, "resources": resources(), "drc": drc,
               "metadata": hardware, "routing": route,
               "endpoint_clocks": clocks,
               "source_and_validated_parent_integrity_pass": integrity["pass"],
               "covered_timing_and_metadata_gate_pass": all([
                   timing["covered_paths_pass"],
                   timing["internal_clock_and_constraint_coverage_pass"],
                   hardware["host_metadata_pass"], route["pass"], blocking_drc == 0,
                   integrity["pass"], clocks["nominal_clocks_and_connections_pass"]]),
               "complete_io_constraint_coverage_pass": timing["complete_io_delay_coverage"],
               "board_coexistence_validation": "not_performed",
               "axi_protocol_simulation": "not_performed"}
    path = ROOT / "evidence/host_review_summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print("Covered timing/metadata gate:", summary["covered_timing_and_metadata_gate_pass"])
    print("Complete I/O coverage:", summary["complete_io_constraint_coverage_pass"])
    print("Timing:", timing["summary"])
    print("DRC:", drc)
    print("Board coexistence:", summary["board_coexistence_validation"])
    if not summary["covered_timing_and_metadata_gate_pass"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
