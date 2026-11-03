"""Local fake tracefs checks: no /sys writes, no board, no DPU."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "trace_isolated.py"
spec = importlib.util.spec_from_file_location("isolated_review_target", SOURCE)
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)


class IsolatedReview(unittest.TestCase):
    def test_kernel_zero_padded_offset_matches(self):
        self.assertTrue(target.same_target("/owned/fixture.so:0x0000000000000510", "/owned/fixture.so:0x510"))
        self.assertFalse(target.same_target("/foreign/fixture.so:0x510", "/owned/fixture.so:0x510"))
        self.assertFalse(target.same_target("/owned/fixture.so:0x511", "/owned/fixture.so:0x510"))
        self.assertFalse(target.same_target("/owned/fixture.so:0x510(0x20)", "/owned/fixture.so:0x510"))

    def test_append_preserves_existing_definitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "events"
            p.write_text("p:foreign/existing /foreign/a.so:0x10\n")
            target.write(p, "p:owned/new /owned/b.so:0x20", True)
            self.assertEqual(p.read_text(), "p:foreign/existing /foreign/a.so:0x10\np:owned/new /owned/b.so:0x20\n")

    def test_append_uses_no_seek_no_truncate_and_closes(self):
        command = "p:owned/new /owned/b.so:0x20"
        raw = (command + "\n").encode()
        with patch.object(target.os, "open", return_value=987) as opened, \
             patch.object(target.os, "write", return_value=len(raw)) as wrote, \
             patch.object(target.os, "close") as closed, \
             patch.object(target.os, "lseek", side_effect=AssertionError("tracefs must not seek")):
            target.write(Path("/fake/uprobe_events"), command, True)
        flags = opened.call_args.args[1]
        self.assertTrue(flags & os.O_APPEND)
        self.assertTrue(flags & os.O_CLOEXEC)
        self.assertFalse(flags & os.O_TRUNC)
        self.assertFalse(flags & os.O_CREAT)
        wrote.assert_called_once_with(987, raw)
        closed.assert_called_once_with(987)

    def test_partial_tracefs_command_fails_and_closes_without_replaying(self):
        with patch.object(target.os, "open", return_value=987), \
             patch.object(target.os, "write", return_value=2) as wrote, \
             patch.object(target.os, "close") as closed:
            with self.assertRaisesRegex(RuntimeError, "Partial tracefs command write"):
                target.write(Path("/fake/uprobe_events"), "p:owned/new /owned/b.so:0x20", True)
        self.assertEqual(wrote.call_count, 1)
        closed.assert_called_once_with(987)

    def fake_cleanup(self, changed=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            group = target.GROUP
            name = target.NAMES[0]
            expected = "/owned/fixture.so:0x510"
            actual = "/owned/fixture.so:0x0000000000000511" if changed else "/owned/fixture.so:0x0000000000000510"
            lines = ["p:foreign/existing /foreign/a.so:0x10", "p:" + group + "/" + name + " " + actual]
            meta = {"source_sha256": target.sha(SOURCE), "group": group,
                    "boot": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                    "event_targets": {name: expected}}
            (root / "ownership.json").write_text(json.dumps(meta))
            writes = []

            def fake_write(path, value, append=False):
                writes.append((str(path), value, append))
                self.assertEqual(path, target.TRACE / "uprobe_events")
                self.assertTrue(append)
                self.assertTrue(value.startswith("-:" + group + "/"))
                remove = value[2:]
                lines[:] = [line for line in lines if line.split()[0].split(":", 1)[1] != remove]

            with patch.object(target, "ROOT", root), patch.object(target, "INSTANCE", root / "missing-instance"), \
                 patch.object(target, "definitions", lambda: list(lines)), patch.object(target, "write", fake_write):
                result = target.cleanup()
            return result, lines, writes

    def test_cleanup_deletes_only_matching_owned_definition(self):
        result, lines, writes = self.fake_cleanup()
        self.assertTrue(result["passed"])
        self.assertEqual(lines, ["p:foreign/existing /foreign/a.so:0x10"])
        self.assertEqual(len(writes), 1)

    def test_cleanup_retains_changed_target(self):
        result, lines, writes = self.fake_cleanup(changed=True)
        self.assertFalse(result["passed"])
        self.assertEqual(len(lines), 2)
        self.assertEqual(writes, [])

    def parse_using_actual_run_statements(self, line):
        run = next(n for n in ast.parse(SOURCE.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "run")
        protected = next(n for n in run.body if isinstance(n, ast.Try))
        start = next(i for i, n in enumerate(protected.body)
                     if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "pattern" for t in n.targets))
        end = next(i for i, n in enumerate(protected.body)
                   if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ordered" for t in n.targets))
        code = compile(ast.fix_missing_locations(ast.Module(body=protected.body[start:end], type_ignores=[])), str(SOURCE), "exec")
        context = dict(target.__dict__, trace=line)
        exec(code, context)
        return context["events"]

    def test_microsecond_trace_is_scaled_without_invented_precision(self):
        events = self.parse_using_actual_run_statements(" worker-123 [001] .... 123.456789: native_enter: (0x1234)")
        self.assertEqual(events, [[123456789000, "native_enter"]])

    def test_nanosecond_trace_group_prefix(self):
        events = self.parse_using_actual_run_statements(" worker-123 [001] .... 123.456789123: " + target.GROUP + ":native_return: (0x1234)")
        self.assertEqual(events, [[123456789123, "native_return"]])


if __name__ == "__main__":
    print("Reviewed source SHA256:", hashlib.sha256(SOURCE.read_bytes()).hexdigest(), flush=True)
    unittest.main(verbosity=2)
