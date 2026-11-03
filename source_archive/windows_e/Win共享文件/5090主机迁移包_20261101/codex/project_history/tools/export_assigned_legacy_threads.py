"""Supplement only explicit desktop project membership, including the old parent chat."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('project_history_export', HERE/'export_project_history.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
source = Path(r'C:\Users\35870\.codex\.codex-global-state.json')
state = json.loads(source.read_text(encoding='utf-8'))
parents = '01a12110-3ba4-7651-b3d7-2e6560916eb6'
target_projects = {identity for identity, project in state['local-projects'].items()
                   if any(M.belongs(path) for path in project.get('rootPaths', []))}
target_projects.add(state['thread-project-assignments'][parents]['projectId'])
assigned = {identity for identity, value in state['thread-project-assignments'].items()
            if isinstance(value, dict) and value.get('projectId') in target_projects}
prior = json.loads((M.BASE_OUT/'snapshot_complete_v2/EXPORT_MANIFEST.json').read_text(encoding='utf-8'))
already = {row['thread_id'] for row in prior['provenance']}
M.SELECTED_IDS = assigned-already
M.OUT = M.BASE_OUT/'snapshot_project_assignments_v3'
assert parents in M.SELECTED_IDS
M.OUT.mkdir(parents=True, exist_ok=True)
(M.OUT/'PROJECT_SELECTION.json').write_text(json.dumps(dict(
    selected_project_ids=sorted(target_projects), explicit_assigned_thread_count=len(assigned),
    supplement_thread_ids=sorted(M.SELECTED_IDS), source=str(source),
    source_snapshot_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    no_other_projects_or_credentials_exported=True), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(supplement_threads=len(M.SELECTED_IDS)), ensure_ascii=False), flush=True)
M.main()
