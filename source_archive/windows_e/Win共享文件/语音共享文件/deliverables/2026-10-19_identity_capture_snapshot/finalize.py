"""Finalize actual photo evidence without rewriting frozen source snapshots."""
import base64
import json
from pathlib import Path
import re
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
prior=HERE.parent/'2026-10-19_enrollment_photo_archive'
review=json.loads((HERE/'photo_review.json').read_text(encoding='utf-8'))
assert review['status']=='PASS_REAL_ENROLLMENT_FACE_PHOTOS_SAVED_AND_EXPORTED'
folder=Path(review['folder']);m=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
sys.path.insert(0,str(prior))
from export_latest import save_review
names=[r['filename'] for r in m['images']]+[m['selected']['filename']]
save_review({'manifest':m,'files':{n:base64.b64encode((folder/n).read_bytes()).decode() for n in names}},folder.parent)
for directory in (HERE,prior):
    path=directory/'verification_summary.json';s=json.loads(path.read_text(encoding='utf-8'))
    s.update(status='REAL_ENROLLMENT_COMMITTED_AND_FACE_PHOTOS_SAVED_EXPORTED',
        actual_new_user_photos_captured=True,actual_user_photos_available=True,
        live_user_new_enrollment_passed=True,user_confirmed_enrollment_completed=True,
        registered_audio_complete=review['board']['registered_audio_complete'],
        saved_sample_photo_count=review['image_count'],photo_session_id=review['session_id'],
        latest_database=review['board']['database'],photo_review=str(HERE/'photo_review.json'),
        gallery=review['gallery'],all_photos_preview=str(folder/'照片预览.md'),
        assistant_actual_photo_visual_review_passed=True,human_reentry_recognition_tested=False,
        later_identity_query_code='identity_unknown',later_identity_query_generation=6,
        stable_person_recognition_accepted=False)
    path.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
marker='actual-enrollment-photos-20261019'
def note(path,body):
    raw=path.read_text(encoding='utf-8')
    raw=re.sub(r'<!-- '+marker+r' -->.*?<!-- /'+marker+r' -->\s*','',raw,flags=re.S)
    path.write_text('<!-- '+marker+' -->\n'+body+'\n<!-- /'+marker+' -->\n\n'+raw,encoding='utf-8')
proof=('**本轮真实登记及照片保存已完成。** 用户确认“已经完成登记”，正式COMMITTED，原身份1条/单模板保留，库修订14→15，registered完整播放；真实保存25张112×112采样图（13采集、7质量拒绝、5最终独立验证）及selected.png原样副本。模板帧7828，验证8025/8036/8051/8065/8080，分数0.813952～0.897079且逐帧≥0.80。板卡目录0700/文件0600，电脑原PNG逐张解码、尺寸/SHA核对通过。'
       '已目视检查实际正脸模板、转头拒绝图及两张验证图；裁剪中心为人脸，眼镜存在屏幕反光，不据此断言全部识别失败的原因。'
       f'全部照片及标注：[照片预览]({(folder/"照片预览.md").as_posix()})、[离线总览]({Path(review["gallery"]).as_posix()})。'
       '用户第6代身份查询仍identity_unknown并完整播放；未做离场重返或不同人验证，不把登记/保存成功当识别稳定性已通过。以下较早“照片待采集”是加载时记录，最新以本段及photo_review.json为准。')
for directory in (HERE,prior):note(directory/'README.md',proof)
note(ROOT/'AGENTS.md',f'- 2026-10-19存图版+入口快照修复已取得真人登记证据：用户“已经完成登记”，COMMITTED/registered完整播放，库1身份/1模板修订14→15；25张实际112×112采样图+selected副本已保存在板端及电脑`身份登记照片/{review["session_id"]}/`，13采集/7质量拒绝/5最终验证，SHA/解码/板端0700/0600通过。UI28f2候选、相机6f1候选，0.80/0.1及原模型保持。照片已可展示，勿再说本轮没有照片或待采样；不能补造历史照片。后续第6代“我是谁”查询仍identity_unknown/完整播放，离场重返与识别稳定性未通过，不将登记成功当识别修复完成。最新证据`deliverables/2026-10-19_identity_capture_snapshot/photo_review.json`及verification_summary.json，实际照片不打包入源码ZIP；未来登记继续留存仅人脸，失败/取消留档。LLM数据D盘。')
note(ROOT/'README.md',f'> **2026-10-19 本轮真实登记照片已保存：** 25张人脸采样图，含最终模板和5张验证图，正式登记修订15及成功播报已确认。[全部照片](身份登记照片/{review["session_id"]}/照片预览.md)，[实际证据](deliverables/2026-10-19_identity_capture_snapshot/photo_review.json)。后续身份查询仍UNKNOWN，识别稳定性未验收。')
analysis=ROOT.parent/'语言模型分析'
for name in ('身份登记人脸照片保存与查看_20261019.md','语音登记入口快照修复_20261019.md'):
    note(analysis/name,proof)
note(analysis/'README.md','[本轮真实登记照片与证据](../语音共享文件/deliverables/2026-10-19_identity_capture_snapshot/README.md)：25张实际人脸图已保存、COMMITTED/成功播报通过；后续身份查询仍UNKNOWN，识别稳定性未通过。')
print(json.dumps({'status':'REAL_FACE_PHOTOS_READY_FOR_USER_REVIEW','count':len(m['images']),
    'preview':str(folder/'照片预览.md'),'database':review['board']['database']},ensure_ascii=False))
