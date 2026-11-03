import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPAIR=HERE.parent
PROJECT=REPAIR.parents[3]

if __name__=='__main__':
    old=json.loads((REPAIR/'guard_candidate/actual_installed.json').read_text(encoding='utf-8'))
    assert old['startup_sha256']=='698b757a8ede34d52ea1d6ec9894e80ac0ccf793109efb3dc0b06e94800a7f7b'
    pins=[
      ('common/board_memory.py','guard_session_candidate','33cb8cedd191382967884850a31e8d106dc41a20b5deee493e23168c8c13b3b0','6e62b109f429c8b8ebb11b1bcf45258be08f5dd659c778e51bd1d95123ee5735'),
      ('board/runtime/audio/board_dialogue_jobs.py','guard_session_candidate','1536fe63361a9f971a22a0bcfd93145f9f8316607dc7a344b298933f1253672f','71fd1ac8e2ddb2e20eeb572063cc69e370e18f40af4a97fb65e2d8258bae45a0'),
      ('board/runtime/audio/automatic_capture.py','capture_diagnostics_candidate','751a26e70fe79e9371dc50d63a399386e4b5c637d58ca5b8142617d4de7ef4c0','5e7abc5a15840aff51d0471313498a46efc940f16d4bd7ee95fed65f98fdcc0a'),
      ('board/runtime/audio/board_frontend_auto.py','capture_diagnostics_candidate','94400137437292cc3d072b0dc1625818a45c5fbe69c1f055f867fe55793d333a','d81275853699597a5dc92c0651f8ffb8e59f63ece760d2d9d514527078cc6573')]
    sources={}
    for rel,folder,before,pin in pins:
        source=REPAIR/folder/'after'/rel;raw=source.read_bytes();ast.parse(raw,feature_version=(3,9))
        assert hashlib.sha256(raw).hexdigest()==pin
        sources[rel]=dict(source=source.relative_to(PROJECT).as_posix(),sha256=pin,before_sha256=before)
    result=dict(stage='automatic-listening-v7-scoped-audio-check',before_startup_sha256=old['startup_sha256'],
        before_manifest_sha256=old['source_manifest_sha256'],sources=sources,
        business_options=old['business_options'],gui_options=dict(voice_barge_in=False),
        wake_word_required=False,conversation_mode='half_duplex',queue_frames=8,
        model_or_threshold_changes=False,source_only=True,private_data_replayed=False)
    (HERE/'revision.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
