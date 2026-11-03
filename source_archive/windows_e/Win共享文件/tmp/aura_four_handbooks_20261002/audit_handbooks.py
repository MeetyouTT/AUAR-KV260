from pathlib import Path
import json
import re
import zipfile

from build_handbooks import ROOT, OUTPUT, FILES, MATERIAL


def read_sections(text):
    text = re.sub(r'<a id="[^"]+"></a>\n\n', '', text)
    matches = list(re.finditer(r'(?m)^## (\d+)\. .+$', text))
    return {
        int(m.group(1)): text[m.start():matches[i+1].start() if i+1 < len(matches) else len(text)].strip()
        for i, m in enumerate(matches)
    }


texts = {owner: (OUTPUT / name).read_text(encoding='utf-8') for owner, name in FILES.items()}
sections = {owner: read_sections(text) for owner, text in texts.items()}
common = [1, 3, 4, 5, 6, 10, 11, 13, 14, 15, 16]
for chapter in common:
    assert len({sections[o][chapter] for o in FILES}) == 1, f'Common chapter differs: {chapter}'
for owner, text in texts.items():
    assert all(re.search(rf'(?m)^### 5\.{n} ', text) for n in range(5, 15)), owner
    assert all(f'E{n:02}' in sections[owner][5] for n in range(1, 7)), owner
    for readiness in ['BASE_RUNTIME_READY', 'BASE_DEV_READY', 'DISPLAY_READY', 'CAMERA_READY', 'VISION_MODEL_READY', 'IDENTITY_BASE_READY', 'MOTION_LOGIC_READY', 'AXIS_READY', 'AUDIO_READY', 'HOST_QA_READY', 'ASD_INPUT_READY', 'JOINT_DEV_READY']:
        assert readiness in sections[owner][5], (owner, readiness)
    assert 'AURA-EXEC-20261002-r2' not in text, owner

steps = {}
for owner in 'ABC':
    role = sections[owner][7].replace(f'## 7. {owner} 的 14 个工作包及逐项执行做法', '')
    master = sections['总'][{'A': 7, 'B': 8, 'C': 9}[owner]]
    matches = list(re.finditer(rf'(?m)^### ({owner}\d{{2}}) .+$', role))
    for i, match in enumerate(matches):
        code = match.group(1)
        card = role[match.start():matches[i+1].start() if i+1 < len(matches) else len(role)].strip()
        assert card in master, f'Master lacks exact expanded task: {code}'
        detailed = card.split('#### 执行步骤、实现要点与现场判定')[1]
        numbered = list(map(int, re.findall(r'(?m)^(\d+)\. ', detailed)))
        assert len(numbered) >= 5, (code, numbered)
        assert numbered == list(range(1, len(numbered)+1)), (code, numbered)
        steps[code] = len(numbered)

yaml_count = 0
try:
    import yaml
except ImportError:
    yaml = None
for owner, text in texts.items():
    assert '九工' not in text
    assert '四人开发目录' not in text
    assert '当前证据到' in text
    assert '不把附件里的采购/执行要求当本次授权' in text
    assert text.count('T13') >= 1 and text.count('T14') >= 1
    outside_code = re.sub(r'(?s)```.*?```', '', text)
    previous = False
    columns = None
    for i, line in enumerate(outside_code.splitlines(), 1):
        is_table = line.startswith('|') and line.endswith('|')
        if is_table:
            current = len(re.split(r'(?<!\\)\|', line)) - 2
            if previous:
                assert current == columns, (owner, i, columns, current, line)
            columns = current
        previous = is_table
    for block in re.findall(r'(?s)```yaml\n(.*?)\n```', text):
        if yaml:
            config = yaml.safe_load(block)
            assert config['document_contract_version'] == 'AURA-EXEC-20261002-r3'
        yaml_count += 1

readme = (ROOT / 'README.md').read_text(encoding='utf-8-sig')
for label, target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)', readme):
    assert (ROOT / target.strip('<>').split('#')[0]).exists(), (label, target)

archive = ROOT / '方案' / 'AURA_KV260_三份个人执行手册与总负责人总包_2026-10-02.zip'
with zipfile.ZipFile(archive) as z:
    assert set(z.namelist()) == set(FILES.values())
    assert z.testzip() is None
    for name in FILES.values():
        assert z.read(name) == (OUTPUT / name).read_bytes()

report = {
    'result': 'PASS',
    'documents': 4,
    'common_chapters_identical': common,
    'all_board_precondition_subsections_identical': 10,
    'module_readiness_conditions_per_document': 12,
    'all_personal_tasks_identical_to_master': 42,
    'minimum_procedure_steps_per_task': min(steps.values()),
    'maximum_procedure_steps_per_task': max(steps.values()),
    'yaml_examples_checked': yaml_count if yaml else 'parser_unavailable',
    'markdown_tables_consistent': True,
    'readme_links_valid': True,
    'archive_exactly_matches_documents': True,
    'actual_board_validation_performed': False,
}
(MATERIAL / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
