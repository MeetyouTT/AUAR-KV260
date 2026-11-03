"""Run unchanged independent cases onv3, redirect only their output directory.

Original review source/assertions and negative evidence are never overwritten.
"""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.argv.append('--candidate-v3')
import run_candidate_tests  # Exact local v16+v3 package overlay; no test run on import.
import pytest


def main():
    source=HERE/'independent_review_v2/test_review_edges.py'
    original=[source,*[HERE/'independent_review_v2'/name for name in (
        'edges_final.xml','replay_expired.json','replay_revision.json','unmatched_query.json')]]
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in original if p.exists()}
    destination=HERE/'candidate_v3/independent_edge_metadata'
    destination.mkdir(exist_ok=True)
    class OutputOnly:
        def pytest_collection_modifyitems(self,items):
            for item in items:
                if Path(item.module.__file__).resolve()==source.resolve():
                    item.module.HERE=destination  # FEATURE and all assertions stay original.
    result=pytest.main([str(source),'-q','-p','no:cacheprovider','--import-mode=importlib',
        '--basetemp='+str(HERE/'v3_independent_test_work'),
        '--junitxml='+str(HERE/'candidate_v3/INDEPENDENT_REPLAY.xml')],plugins=[OutputOnly()])
    unchanged=all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in hashes.items())
    receipt=dict(schema='aura.v3-independent-case-replay.v1',exit_code=result,
        original_review_files_unchanged=unchanged,original_file_sha256=hashes,
        output_only_redirection=str(destination),assertions_or_source_modified=False,
        level='code_or_fake_verified',models_or_hardware_called=False)
    (HERE/'candidate_v3/INDEPENDENT_REPLAY.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False))
    raise SystemExit(result if unchanged else 1)


if __name__=='__main__':main()
