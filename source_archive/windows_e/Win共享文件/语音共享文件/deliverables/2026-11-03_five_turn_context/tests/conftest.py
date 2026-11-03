"""Resolve deployed candidate modules first, original host-only helpers second."""
from pathlib import Path
import os
import sys

TASK = Path(__file__).resolve().parents[1]
PROJECT = TASK.parents[1] / 'aura'
sys.path.insert(0, os.environ.get('AURA_CONTEXT_RUNTIME', str(TASK/'candidate_runtime')))
for name in ('tools', 'common'):
    module = __import__(name)
    module.__path__.append(str(PROJECT/name))
