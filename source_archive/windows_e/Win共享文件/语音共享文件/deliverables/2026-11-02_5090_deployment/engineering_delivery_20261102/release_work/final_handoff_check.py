from common import *
import re
main=load(QA/'release_receipt.json'); skill=load(QA/'standalone_skills_ubuntu.json')
assert main['contents']==1836 and main['bytes']<200000000 and main['rar_test']==main['verify_after_unpack']=='PASS'
for p in ['aura/skill/command_guard_validation/SKILL.md','aura/skill/llm_voice_runtime_optimization/SKILL.md','aura/skill/perception_freshness_benchmark/SKILL.md','先读_交付与核验.txt','SHA256SUMS.txt']:
    assert (OUT/p).is_file(),p
assert load(QA/'skills_archive.json')['sha256']==skill['archive_sha256'] and skill['status']=='PASS'
for line in (OUT/'SHA256SUMS.txt').read_text(encoding='ascii').splitlines():
    h,n=line.split('  ',1);assert sha(OUT/n)==h,n
for n in ['auar_kv260_engineering.rar','auar_board_audio_dependencies.zip','auar_skills.zip','auar_wide_source_routed.dcp']:
    assert n in (OUT/'SHA256SUMS.txt').read_text()
assert all((OUT/'aura'/k).exists() for k in ['data/results/xir_three_models.json','build/reports/clean_directory_validation.json','report/requirements_map.md','report/release_status.md'])
for f,v in [('release_after_read.txt','1835 release files'),('extracted_single_core.txt','pynq_examples 0')]:
    assert v in (QA/f).read_text(encoding='utf8')
print('E: final RAR',main['bytes'],'bytes;',main['contents'],'archive members;',main['sha256'])
print('Audio assets',load(QA/'audio_stage_verification.json')['audio_files_matched'],'skills',len(skill['result']),'DCP',load(QA/'routed_checkpoint.json')['bytes'])
