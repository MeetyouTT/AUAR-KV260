import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from generate import ContractError, check_hwh, generate, read_json, validate_contract, validate_vectors


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.temp = Path(self.temporary.name)
        self.example = ROOT / "examples/adder"
        self.raw = read_json(self.example / "contract.json")
        self.contract = validate_contract(self.raw)

    def driver(self, example=None):
        example = example or self.example
        out = self.temp / example.name
        generate(example / "contract.json", example / "metadata_fixture.hwh", example / "vectors.json", out, example / "mock_ip.py")
        return load(out / "driver.py", example.name + "_driver"), load(out / "mock_ip.py", example.name + "_mock"), out

    def test_contract_rejects_unsupported_protocols_and_widths(self):
        cases = []
        for key, value in (("schema_version", 2), ("data_width", 64), ("ip_name", "bad.name"), ("timeout_ms", 0)):
            row = copy.deepcopy(self.raw)
            row[key] = value
            cases.append(row)
        row = copy.deepcopy(self.raw)
        row["dma"] = True
        cases.append(row)
        row = copy.deepcopy(self.raw)
        row["control"]["done_reset"] = "manual"
        cases.append(row)
        for row in cases:
            with self.subTest(row=row):
                with self.assertRaises(ContractError):
                    validate_contract(row)

    def test_contract_rejects_aliases_alignment_and_access_errors(self):
        mutations = [
            lambda c: c["registers"][2].update(offset=3),
            lambda c: c["registers"][2].update(offset=256),
            lambda c: c["registers"][2].update(offset=4),
            lambda c: c["registers"][2].update(name="status"),
            lambda c: c["registers"][2].update(access="ro"),
            lambda c: c["registers"][4].update(read_effect="clear"),
            lambda c: c["control"]["done"].update(mask=0),
            lambda c: c["control"]["done"].update(value=2),
            lambda c: c["control"]["start"].update(register="lhs"),
        ]
        for i, mutate in enumerate(mutations):
            with self.subTest(mutation=i):
                row = copy.deepcopy(self.raw)
                mutate(row)
                with self.assertRaises(ContractError):
                    validate_contract(row)

    def test_vectors_reject_missing_expected_values_and_invalid_words(self):
        vectors = read_json(self.example / "vectors.json")
        for key, value in (("expected", {"sum": None}), ("inputs", {"lhs": -1, "rhs": 0}), ("inputs", {"lhs": True, "rhs": 0}), ("inputs", {"lhs": 0})):
            with self.subTest(key=key, value=value):
                rows = copy.deepcopy(vectors)
                rows[0][key] = value
                with self.assertRaises(ContractError):
                    validate_vectors(rows, self.contract)

    def test_hwh_conflicts_cannot_be_bypassed_with_incomplete_flag(self):
        original = (self.example / "metadata_fixture.hwh").read_text()
        for before, after in (("VALUE=\"0x10\"", "VALUE=\"0x18\""), ("VALUE=\"read-write\"", "VALUE=\"read-only\""), ("HIGHVALUE=\"0x400000ff\"", "HIGHVALUE=\"0x4000001f\"")):
            with self.subTest(after=after):
                path = self.temp / "bad.hwh"
                path.write_text(original.replace(before, after, 1))
                with self.assertRaises(ContractError):
                    check_hwh(path, self.contract, allow_incomplete=True)

    def test_incomplete_metadata_is_separate_from_a_match(self):
        tree = ET.parse(self.example / "metadata_fixture.hwh")
        for module in tree.getroot().iter("MODULE"):
            module.remove(module.find("REGISTERS"))
        path = self.temp / "incomplete.hwh"
        tree.write(path)
        with self.assertRaisesRegex(ContractError, "incomplete"):
            check_hwh(path, self.contract)
        report = check_hwh(path, self.contract, allow_incomplete=True)
        self.assertEqual(report["status"], "INCOMPLETE")
        self.assertEqual(report["register_count"], 0)
        self.assertFalse(report["hardware_verified"])

    def test_hwh_handles_namespaces_and_rejects_duplicate_ip(self):
        text = (self.example / "metadata_fixture.hwh").read_text()
        path = self.temp / "namespaced.hwh"
        path.write_text(text.replace("<SYSTEM>", '<SYSTEM xmlns="urn:test">'))
        self.assertEqual(check_hwh(path, self.contract)["status"], "MATCHED")
        root = ET.parse(self.example / "metadata_fixture.hwh").getroot()
        modules = root.find("MODULES")
        modules.append(copy.deepcopy(modules[0]))
        ET.ElementTree(root).write(path)
        with self.assertRaisesRegex(ContractError, "exactly one"):
            check_hwh(path, self.contract)

    def test_hwh_rejects_entity_declarations(self):
        path = self.temp / "entity.hwh"
        path.write_text('<!DOCTYPE SYSTEM [<!ENTITY x "hello">]><SYSTEM/>')
        with self.assertRaisesRegex(ContractError, "DTD/entity"):
            check_hwh(path, self.contract)

    def test_generate_refuses_to_overwrite_output(self):
        out = self.temp / "existing"
        out.mkdir()
        (out / "keep.txt").write_text("keep")
        with self.assertRaisesRegex(ContractError, "already exists"):
            generate(self.example / "contract.json", self.example / "metadata_fixture.hwh", self.example / "vectors.json", out)
        self.assertEqual((out / "keep.txt").read_text(), "keep")

    def test_driver_writes_only_declared_inputs_then_start(self):
        module, mock, out = self.driver()
        ip = mock.create_ip(module.CONTRACT)
        driver = module.ContractDriver(ip)
        self.assertEqual(driver.run({"lhs": 17, "rhs": 25}), {"sum": 42})
        self.assertEqual(ip.trace, [("write", 16, 17), ("write", 20, 25), ("write", 0, 1), ("read", 4), ("read", 32)])
        with self.assertRaises(PermissionError):
            driver.write_register("sum", 0)
        with self.assertRaises(PermissionError):
            driver.read_register("command")
        before = list(ip.trace)
        with self.assertRaises(ValueError):
            driver.run({"lhs": 1, "rhs": True})
        self.assertEqual(before, ip.trace)
        report = json.loads((out / "contract_report.json").read_text())
        self.assertFalse(report["board_verified"])

    def test_read_clear_status_is_consumed_once(self):
        module, mock, _ = self.driver(ROOT / "examples/crc32")
        ip = mock.create_ip(module.CONTRACT)
        result = module.ContractDriver(ip).run({"word": 0x12345678})
        self.assertEqual(result, {"digest": 2943190994})
        self.assertEqual(sum(row == ("read", 68) for row in ip.trace), 1)
        self.assertEqual(ip.values[68], 0)

    def test_never_done_times_out(self):
        module, _, _ = self.driver()
        now = [0.0]
        class NeverDone:
            def write(self, offset, value):
                pass
            def read(self, offset):
                return 0
        def sleep(_):
            now[0] += 0.05
        driver = module.ContractDriver(NeverDone(), clock=lambda: now[0], sleep=sleep)
        with self.assertRaises(TimeoutError):
            driver.run({"lhs": 1, "rhs": 2})

    def test_late_completion_does_not_bypass_timeout(self):
        module, _, _ = self.driver()
        now = [0.0]
        class LateDone:
            def write(self, offset, value):
                pass
            def read(self, offset):
                now[0] = 0.2
                return 1
        driver = module.ContractDriver(LateDone(), clock=lambda: now[0], sleep=lambda _: None)
        with self.assertRaises(TimeoutError):
            driver.run({"lhs": 1, "rhs": 2})

    def test_synthetic_examples_cannot_enter_hardware_mode(self):
        module, _, _ = self.driver()
        with self.assertRaisesRegex(RuntimeError, "real Vivado metadata"):
            module.open_overlay(self.temp / "anything.bit", program=True)

    def test_runner_detects_wrong_reference_and_preserves_hardware_status(self):
        _, _, out = self.driver()
        vectors = read_json(out / "vectors.json")
        vectors[1]["expected"]["sum"] = 99
        path = out / "wrong.json"
        path.write_text(json.dumps(vectors))
        report = out / "wrong_report.json"
        result = subprocess.run([sys.executable, "-B", str(out / "test_ip.py"), "--vectors", str(path), "--report", str(report)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(result.returncode, 1)
        data = read_json(report)
        self.assertEqual(data["status"], "FAIL")
        self.assertFalse(data["board_verified"])
        self.assertEqual(data["cases"][1]["actual"], {"sum": 42})
        self.assertEqual(data["cases"][1]["status"], "FAIL")

    def test_runner_rejects_report_overwriting_inputs(self):
        _, _, out = self.driver()
        original = (out / "vectors.json").read_bytes()
        result = subprocess.run([sys.executable, "-B", str(out / "test_ip.py"), "--report", str(out / "vectors.json")], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual((out / "vectors.json").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
