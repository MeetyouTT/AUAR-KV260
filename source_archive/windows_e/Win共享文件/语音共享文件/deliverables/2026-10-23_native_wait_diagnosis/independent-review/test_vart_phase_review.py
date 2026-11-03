"""Local-only checks of actual parser AST, exact opcodes and cleanup rebinding."""
import ast
import importlib.util
import json
from pathlib import Path
import re
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "trace_vart.py"
tree = ast.parse(SOURCE.read_text())
names = ("native_enter", "native_return", "restore_enter", "restore_return")
group = "aura_vart_local_fake"
context = {"re": re, "h": SimpleNamespace(NAMES=names, GROUP=group)}
parser_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "parse_trace")
exec(compile(ast.fix_missing_locations(ast.Module(body=[parser_node], type_ignores=[])), str(SOURCE), "exec"), context)
parse = context["parse_trace"]


def line(name, stamp="123.456789", tid=499788, with_group=False):
    return " python3-" + str(tid) + " [001] d... " + stamp + ": " + (group + ":" if with_group else "") + name + ": (0x10a10)"


class PhaseReview(unittest.TestCase):
    def test_complete_cycle_numeric_intervals(self):
        raw = "\n".join(line(n, "123." + f"{456789+i*100:06}") for i, n in enumerate(names))
        events, cycles, incomplete, digits = parse(raw, 499788)
        self.assertEqual((len(events), len(cycles), incomplete, digits), (4, 1, 0, [6]))
        self.assertAlmostEqual(cycles[0]["native_interval_ms"], .1)
        self.assertAlmostEqual(cycles[0]["restore_interval_ms"], .1)

    def test_cross_tid_is_rejected(self):
        with self.assertRaises(AssertionError):
            parse(line("native_enter", tid=499789), 499788)

    def test_group_prefix_nanosecond_and_equal_quantized_stamps(self):
        events, cycles, incomplete, digits = parse("\n".join(line(n, "123.456789123", with_group=True) for n in names), 499788)
        self.assertEqual(digits, [9])
        self.assertEqual(incomplete, 0)
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0]["native_interval_ms"], 0)

    def test_partial_boundaries_are_counted_not_spliced(self):
        raw = [line("restore_return")]
        raw += [line(n) for n in names]
        raw += [line("native_enter"), line("native_return")]
        events, cycles, incomplete, digits = parse("\n".join(raw), 499788)
        self.assertEqual(len(cycles), 1)
        self.assertEqual(incomplete, 2)

    def test_internal_missing_phase_does_not_create_false_cycle(self):
        raw = [line("native_enter"), line("native_return"), line("restore_return")]
        raw += [line(n) for n in names]
        events, cycles, incomplete, digits = parse("\n".join(raw), 499788)
        self.assertEqual(len(cycles), 1)
        self.assertEqual(incomplete, 1)

    def test_backwards_timestamp_rejected(self):
        raw = [line(names[0], "124.000000")] + [line(n, "123.000000") for n in names[1:]]
        with self.assertRaises(AssertionError):
            parse("\n".join(raw), 499788)

    def test_excess_timestamp_precision_rejected(self):
        with self.assertRaises(AssertionError):
            parse(line("native_enter", "123.1234567890"), 499788)

    def test_four_points_match_current_exact_elf(self):
        assignment = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "POINTS" for t in n.targets))
        points = ast.literal_eval(assignment.value)
        self.assertEqual(tuple(points), names)
        elf = (ROOT / "exact-runtime/vart.so").read_bytes()
        for off, word in points.values():
            self.assertEqual(off % 4, 0)
            self.assertEqual(int.from_bytes(elf[off:off+4], "little"), word)

    def test_rebound_cleanup_uses_phase_namespace_and_preserves_fixture(self):
        spec = importlib.util.spec_from_file_location("phase_cleanup_local_test", ROOT / "trace_isolated.py")
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        old_group = helper.GROUP
        with tempfile.TemporaryDirectory() as tmp:
            oldroot, newroot = Path(tmp) / "fixture", Path(tmp) / "phase"
            oldroot.mkdir(); newroot.mkdir()
            sentinel = oldroot / "ownership.json"; sentinel.write_text("fixture sentinel")
            helper.SOURCE = SOURCE; helper.ROOT = newroot; helper.GROUP = group
            helper.INSTANCE = newroot / "missing-instance"
            (newroot / "ownership.json").write_text(json.dumps({"source_sha256": helper.sha(SOURCE), "group": group,
                "boot": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                "event_targets": {"native_enter": "/vart.so:0x10a04"}}))
            defs = ["p:" + old_group + "/native_enter /fixture.so:0x7b0", "p:" + group + "/native_enter /vart.so:0x0000000000010a04"]
            def remove(path, value, append=False):
                self.assertTrue(append)
                self.assertEqual(value, "-:" + group + "/native_enter")
                defs[:] = defs[:1]
            with patch.object(helper, "definitions", lambda: list(defs)), patch.object(helper, "write", remove):
                result = helper.cleanup()
            self.assertTrue(result["passed"])
            self.assertEqual(len(defs), 1)
            self.assertTrue(defs[0].startswith("p:" + old_group + "/"))
            self.assertEqual(sentinel.read_text(), "fixture sentinel")
            self.assertTrue((newroot / "cleanup.json").exists())
            self.assertFalse((oldroot / "cleanup.json").exists())


if __name__ == "__main__":
    import hashlib
    print("Reviewed source SHA256:", hashlib.sha256(SOURCE.read_bytes()).hexdigest(), flush=True)
    unittest.main(verbosity=2)
