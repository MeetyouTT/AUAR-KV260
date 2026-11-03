"""Candidate first; legacy source classes are test-fixture builders only."""
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'candidate/aura'))
import common
# Offline migration fixtures construct the ORIGINAL legacy schema. These
# constructors are not runtime dependencies and are not copied into production.
common.__path__.append(str(HERE.parents[3]/'aura/common'))
import pytest
raise SystemExit(pytest.main(['-p','no:cacheprovider','-q',str(HERE/'test_production_merge.py'),
    str(HERE/'candidate/aura/tests/framework/test_board_production_migration.py'),
    str(HERE/'candidate/aura/tests/framework/test_board_memory_migration.py'),
    '--junitxml='+str(HERE/'production_integrated_tests.xml')]))
