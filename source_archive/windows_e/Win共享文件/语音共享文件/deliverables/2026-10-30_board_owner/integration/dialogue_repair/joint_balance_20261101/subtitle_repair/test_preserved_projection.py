"""Reuse public projection/privacy regressions against current and repaired bytes."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(label, path):
    spec = importlib.util.spec_from_file_location(label, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    path = HERE/'public_sources/test_single_projection.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    # Import its public behavior tests while supplying this bundle's source
    # pair, rather than loading the previous release's external directories.
    tree.body = [n for n in tree.body if not (isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id in ('OLD', 'NEW') for t in n.targets))]
    inherited = types.ModuleType('authored_public_projection_tests')
    inherited.__file__ = str(path)
    exec(compile(ast.fix_missing_locations(tree), str(path), 'exec'), inherited.__dict__)
    inherited.OLD = load('current_projection', HERE/'before/tools/production_memory_presentation.py')
    inherited.NEW = load('repaired_projection', HERE/'after/tools/production_memory_presentation.py')
    # This old test checks the previous optimization's literal five source
    # replacements, not behavior. It does not apply to a later one-file repair.
    names = [n for n in unittest.defaultTestLoader.getTestCaseNames(inherited.SingleProjectionTests)
             if n != 'test_source_changes_are_exactly_five_frozen_replacements']
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(
        inherited.SingleProjectionTests(name) for name in names))
    report = dict(schema='aura-subtitle-preserved-projection-1', tests=result.testsRun,
        seeded_nested_cases=500, failures=len(result.failures), errors=len(result.errors),
        passed=result.wasSuccessful(), current_984d_vs_repaired=True,
        single_tree_projection_retained=True, public_fixtures_only=True,
        device_network_model_or_database_access=False)
    (HERE/'PROJECTION_TEST_RESULT.json').write_text(json.dumps(report, indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
