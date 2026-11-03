"""Run public fake tests using the existing project test dependencies."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, r'C:\Users\35870\.codex\scratch\feature_trigger_collaboration\test_dependencies')
import pytest

raise SystemExit(pytest.main(sys.argv[1:] or [str(HERE/'tests/test_two_field.py'),
    '-q', '-p', 'no:cacheprovider', '--import-mode=importlib',
    '--basetemp='+str(HERE/'tmp_tests'), '--junitxml='+str(HERE/'TESTS.xml')]))
