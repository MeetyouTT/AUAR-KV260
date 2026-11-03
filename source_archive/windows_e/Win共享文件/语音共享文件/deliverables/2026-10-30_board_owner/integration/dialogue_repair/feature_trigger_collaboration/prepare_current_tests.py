"""Adapt archived test input names to the explicitly selected current persona.

Only public fixture text changes; no assertion, threshold, target freshness,
consent, provenance or receipt condition is modified.
"""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[4]


def main():
    out={}
    for name in ('test_board_dialogue_jobs.py','test_spoken_identity_query.py'):
        source=PROJECT/'aura/tests/framework'/name
        raw=source.read_bytes();text=raw.decode('utf-8')
        replacements={}
        for old in ('汐蓝','夕蓝','西蓝','西兰'):
            replacements[old]=text.count(old)
            text=text.replace(old,'雪妃')
        destination=HERE/'tests/current_profile'/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(text,encoding='utf-8',newline='')
        out[name]=dict(source=str(source),source_sha256=hashlib.sha256(raw).hexdigest(),
            adapted_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
            literal_replacements_to_current_character=replacements,assertions_changed=False)
    (HERE/'CURRENT_TEST_ADAPTATIONS.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(current_persona_fixture_copies=len(out),assertions_changed=False)))


if __name__=='__main__':
    main()
