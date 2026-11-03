"""One-time archive of the user-accepted voice baseline; refuses replacement."""
import json
from pathlib import Path
import zipfile
from verify_saved import HERE, ROOT, digest

def main():
    archive = HERE / 'accepted_source.zip'
    if archive.exists():
        raise SystemExit('Accepted archive already exists; keep the approved baseline')
    dialogue = ROOT / 'deliverables/2026-10-11_omnivoice_dialogue'
    selected = ROOT / 'deliverables/2026-10-06_voice_selected_soft_young'
    acceptance = {
        'schema_version': 1, 'date': '2026-10-11', 'status': 'USER_ACCEPTED_VOICE_EFFECT',
        'user_statement': '目前这个语音效果合格，写入项目文件夹中保存，由其他主机进行后续工作',
        'scope': 'Current Xilan voice effect accepted; shared project saved for work on other hosts',
        'character': '汐蓝', 'voice': '柔亮俏皮', 'tts': 'k2-fsa/OmniVoice',
        'model_revision': 'c5fdb5ccb189668d56333f77ba2629f4cd7535f4',
        'reference_sha256': '0d252fc92cfd0002f61d05f107b816d092fd5086a281e98e94d3cdc5ccf66604',
        'parameters': {'num_step': 16, 'speed': 1.0, 'guidance_scale': 2.0, 'denoise': True,
                       'preprocess_prompt': True, 'postprocess_output': True},
        'seed': 8701, 'dtype': 'float16', 'attention': 'sdpa',
        'llm_model': 'qwen3:4b-instruct-2507-q4_K_M',
        'llm_digest': '0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0',
        'llm_profile': {'strict': True, 'fast': True, 'num_ctx': 2048, 'num_predict': 120,
                        'think': False, 'keep_alive': '30m', 'history_rounds': 4},
        'asr': 'sherpa-onnx CPU Paraformer int8, 2 threads',
        'entry': 'deliverables/2026-10-11_omnivoice_dialogue/launch.py',
        'model_files': 'model_files.json', 'source_archive': 'accepted_source.zip',
        'historical_evidence': ['chain_verification.json', 'warm_turns_verification.json', 'regression_fast.log'],
        'not_implied': ['LLM factual-quality approval', 'FPGA deployment approval', 'remote synchronization completed',
                        'automated physical microphone validation'],
        'environment': 'Rebuild per host; exact observed versions in runtime_versions.json',
    }
    (HERE / 'acceptance.json').write_text(json.dumps(acceptance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    sources = set((ROOT / 'aura/tools').glob('*.py'))
    sources.update((ROOT / 'aura/board').rglob('*.py'))
    sources.update((ROOT / 'aura').glob('requirements*.txt'))
    sources.update((ROOT / 'aura/tests').glob('test_*voice*.py'))
    sources.update((ROOT / 'aura/tests').glob('test_realtime*.py'))
    for pattern in ('*.py', '*.json', '*.md', '*.html', '*.js', '*.bat', 'regression*.log'):
        sources.update(dialogue.glob(pattern))
    for path in (selected / 'selection.json', selected / 'reference/soft_young.wav', ROOT / '.cline-handover.md'):
        sources.add(path)
    sources.update(p for p in HERE.iterdir() if p.is_file())
    # Keep launch metadata only as historic machine data, documented as nonportable.
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for source in sorted(sources):
            z.write(source, source.relative_to(ROOT).as_posix())
    standalone = [archive, *[p for p in HERE.iterdir() if p.suffix in {'.json', '.md', '.py', '.txt'}],
                  selected / 'selection.json', selected / 'reference/soft_young.wav']
    standalone.extend((ROOT / 'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14') / name
                      for name in ('model.int8.onnx', 'tokens.txt'))
    rows = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': digest(p)}
            for p in sorted(set(standalone)) if p.name not in {'baseline_files.json', 'model_files.json'}]
    baseline = {'date': '2026-10-11', 'status': 'SAVED', 'archive_entries': len(sources), 'files': rows,
                'note': 'Verify frozen source archive; active source may evolve after this acceptance'}
    (HERE / 'baseline_files.json').write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('SAVED_ACCEPTED_BASELINE', len(sources), 'archive entries')

if __name__ == '__main__':
    main()
