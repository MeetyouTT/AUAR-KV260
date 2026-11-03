"""Repair public-stage layout only, preserving all frozen worker/source/test bytes."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import shutil

H = Path(__file__).resolve().parent
D = H / 'candidate_m03_v90_stage'
NESTED = 'tree/a/b/c/d/review_m03_win_inference/test_delete_boundaries.py'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


old_raw = (D / 'STAGING_MANIFEST.json').read_bytes()
assert sha(old_raw) == '58d1803a3e8820412f5923978202bb8c7ef46f2d9e7c14e27b328c187c6b2220'
old = json.loads(old_raw)
files = {}
for key, row in old['files'].items():
    raw = Path(row['source']).read_bytes()
    assert sha(raw) == row['sha256'] and len(raw) == row['bytes'], key
    relative = NESTED if key == 'test_delete_boundaries.py' else key
    target = D / relative
    if target.exists():
        assert target.read_bytes() == raw, relative
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    files[relative] = dict(source=str(target), sha256=row['sha256'], bytes=len(raw))

stage = PurePosixPath('/home/root/aura-public-feature-validation-20261031/m03-v90-58d1803a3e882041')
flat = stage / 'test_delete_boundaries.py'
flat_collab = flat.parent.parent
assert len(flat_collab.parents) == 3
review = stage / NESTED
collab = review.parent.parent
project = collab.parents[4]
assert project == stage
local_collab = (D / NESTED).parent.parent
assert local_collab.parents[4] == D
dump(D / 'PATH_LAYOUT_V2_PROOF.json', dict(
    schema='aura.m03-v90.public-stage-layout-proof.v2',
    flat_original_review=str(flat), flat_COLLAB=str(flat_collab),
    flat_COLLAB_parent_count=len(flat_collab.parents),
    flat_failure='PROJECT=COLLAB.parents[4] raises IndexError before test discovery',
    corrected_original_review=str(review), corrected_COLLAB=str(collab),
    corrected_PROJECT=str(project), PROJECT_is_public_stage=True,
    original_review_sha256=files[NESTED]['sha256'],
    original_review_bytes_unchanged=True, worker_bytes_unchanged=True,
    test_assertions_unchanged=True, source_verification_unchanged=True,
    local_PROJECT=str(local_collab.parents[4]),
    independent3_top_level_executed=False,
    actual_first_ARM_receipt='actual_arm_1793497883540736200.json',
    actual_first_ARM_status='RUNNING_WITHOUT_TESTS_NOT_A_PASS',
    first_ARM_stderr_not_available_in_this_receipt=True,
))

old_cli = D / 'ROOT_RUN.txt'
archive = D / 'ROOT_RUN.flat_layout_original.txt'
if not archive.exists():
    shutil.copyfile(old_cli, archive)

cli = '''v90 ARM公开8例：布局V2修正。只调整原4例文件的stage位置。

首版flat路径遗漏原review顶层的PROJECT=COLLAB.parents[4]约定。
首个ARM回执actual_arm_1793497883540736200.json停于RUNNING、没有tests，不能算通过；
已确认完整379源与3候选模块加载。原回执、原STAGING_MANIFEST.json及首版说明
ROOT_RUN.flat_layout_original.txt均保留，V2不覆盖旧证据。

最小布局（R=生产根；S=任意绝对公开stage目录）：
S/arm_public_worker.py
S/SOURCE_MANIFEST.json
S/source_mapping.v90.json
S/after/board/runtime/board_business.py
S/after/board/runtime/history_delete.py
S/after/tools/production_memory_presentation.py
S/test_independent_boundaries.py
S/worker.py
S/tree/a/b/c/d/review_m03_win_inference/test_delete_boundaries.py

最后一项必须按这个相对路径复制原字节，SHA仍为
7528a035ae301b3bf0d3bb0747cb52c322f82b5a1c236102ba5d47915e0c008b。
tree/a/b/c/d共5层，使HERE为review目录，COLLAB=S/tree/a/b/c/d，
PROJECT=COLLAB.parents[4]=S；推导路径留在公开stage内。
其余8项相对位置与SHA不变。无需复制343源快照、模型或环境。
文件及SHA见STAGING_LAYOUT_V2.json，路径推导见PATH_LAYOUT_V2_PROOF.json。

原worker fdd4fcc2...完全不改；仍先校验当前boot、startup90f6、manifest6d03、
mapping df6b、全部379组件、候选3源及两份测试SHA，再导入任何应用模块。
没有改四项测试断言、伪造__file__、跳过源验证或改生产源。
独立3例只执行原函数体AST，顶层路径逻辑不执行，因此留在flat位置。

命令（ROOT_SLOT是root对独立进程的协调标记，NEW_RESULT.json必须不存在）：
python3 -B S/arm_public_worker.py --runtime-root R/runtime/aura --startup-config R/startup/config.json --candidate-root S/after --mapping S/source_mapping.v90.json --candidate-manifest S/SOURCE_MANIFEST.json --candidate-manifest-sha256 cd462e0e26e5d41291afea66b8e598b7fcece0560ebe56257b2f79a132e7f820 --original-review S/tree/a/b/c/d/review_m03_win_inference/test_delete_boundaries.py --independent-tests S/test_independent_boundaries.py --public-worker S/worker.py --root-coordinated-slot ROOT_SLOT --output S/NEW_RESULT.json

root wrapper应等待该进程真正退出，保存exitcode和独立stdout/stderr，
再核对最终JSON status/tests/failures/errors及临时库/线程清理结果。
RUNNING中间JSON或仅wrapper提交成功都不能算通过。
可先--check-only另用新输出，但CHECKED_ONLY也不是8例通过。

真实UI可保持可见，无需关闭、暂停监听、mic-off或设备/服务停机。
生产文件仅只读校验；用例全为独立进程合成Store和公开fixture，数据库在自建
/dev/shm目录，不获取生产writer lease、不打开真实私库、模型或物理设备。
模拟ACK/播放消费不能作为物理听音或真人日期删除验收。

布局V2本地复验结果见LOCAL_LAYOUT_V2.json；实际ARM结果由root另存。
候选尚未部署，r2/newboot冻结包保持原样。
'''
(D / 'ROOT_RUN_LAYOUT_V2.txt').write_bytes(cli.encode('utf-8'))
old_cli.write_bytes(cli.encode('utf-8'))
proofs = {name: sha((D / name).read_bytes()) for name in (
    'STAGING_MANIFEST.json', 'ROOT_RUN.flat_layout_original.txt',
    'PATH_LAYOUT_V2_PROOF.json', 'ROOT_RUN_LAYOUT_V2.txt')}
dump(D / 'STAGING_LAYOUT_V2.json', dict(
    schema='aura.m03-v90.public-stage-layout.v2',
    status='LAYOUT_CORRECTED_AWAITING_LOCAL_AND_ROOT_REPLAY',
    supersedes_only_flat_review_destination_and_CLI=True,
    original_stage_manifest_sha256=sha(old_raw),
    files=files, file_count=len(files),
    original_review_relative_path=NESTED,
    worker_or_product_sources_changed=False, original4_test_bytes_changed=False,
    full379_source_verification_preserved=True,
    UI_close_required=False, pause_mic_off_or_device_stop_required=False,
    first_ARM_result='RUNNING_NO_TESTS_NOT_A_PASS',
    CLI='ROOT_RUN_LAYOUT_V2.txt', proof_sha256=proofs,
))
print(json.dumps(dict(files=len(files), layout='V2', PROJECT=str(project),
    manifest_sha256=sha((D / 'STAGING_LAYOUT_V2.json').read_bytes())), ensure_ascii=False))
