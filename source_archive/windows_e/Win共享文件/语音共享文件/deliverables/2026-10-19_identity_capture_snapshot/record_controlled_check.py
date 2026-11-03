"""Record the failed user-declared frontal check separately from photo saving."""
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
r=json.loads((HERE/'controlled_front_check.json').read_text(encoding='utf-8'))
assert r['sample_count']>0 and r['database_hash_unchanged'] and not r['production_changed']
passed=r['pass_080']==r['sample_count'] and r['production_states'].get('KNOWN',0)>0
assert not passed
text='''# 本人正脸10秒检查：未通过

日期2026-10-19。用户按要求确认刚登记的本人单独、距离与登记接近、正对镜头，并选择“开始检查”。随后板端进行10.09秒只读检查，未重登、未调阈值、未保存新照片。原身份库修订15及哈希保持。

## 实测

- 共取得6份当前实际112×112模型输入，0份达到正式0.80门槛，余弦相似度0.620695～0.643428，中位0.637173。无预览取图或特征服务错误。
- 当前6份彼此相似度0.705348～0.950372，中位0.776804。前三份相邻0.936632/0.950372，后半段较低，不能把整段概括为特征完全稳定。
- 52次生产状态均UNKNOWN；9次有新鲜模型输入、1次有已确认目标但无新鲜模型输入、9次人脸目标未确认、33次未满足单张人脸条件。此脚本没有把最后33次细分为0张/多张，不得声称已证明多个人或确定全是0张。
- 采样到的模型输入源龄429～774ms，低于原3秒TTL；没有证据将这些有效低分归因于结果过期。人脸目标键（含None）共3种，检测/目标连续性也不稳定。

本轮登记选中照片已独立回放，与正式数据库模板余弦相似度1.0；最后5份登记验证图重放仍全部>=0.80。因此登记图片/模板保存一致性已通过，但**登记后的真人正脸识别未通过**。存图/登记成功不能作为识别稳定性验收。

已读核对原YuNetCompat检测、五点几何对齐和Windows RGB SFace输入路径，没有在本轮发现已被复现的新源码缺陷；不能将“检测与对齐仍需排查”写成“对齐错误已确认”。这6份只读诊断没有保留图片或原始关键点，尚不能区分光照/反光/实际头姿、框与关键点漂移及模型匹配能力。也不能据此认为降低门槛就已安全解决误认。

后续先定位检测和当前模型输入变化，区分人脸目标丢失与有效输入低分；转头、离场重返及语音身份回答的稳定性验收暂不继续。保留现有身份及本轮25张登记照片，无需再次录入身份。正式0.80/0.1、原模型、单模板与独立5帧验证保持，未做自动参数或模板更改。

证据：`controlled_front_check.json`、`after_enrollment_scores.json`、`photo_review.json`。本轮只存数值，不导出姓名、身份ID或特征向量。
'''
(HERE/'controlled_front_check_review.md').write_text(text,encoding='utf-8')
for directory in (HERE,HERE.parent/'2026-10-19_enrollment_photo_archive'):
 path=directory/'verification_summary.json';s=json.loads(path.read_text(encoding='utf-8'))
 s.update(controlled_frontal_check_status='FAILED',controlled_frontal_check_passed=False,
  controlled_frontal_sample_count=r['sample_count'],controlled_frontal_pass_080=r['pass_080'],
  controlled_frontal_score_distribution=r['score_distribution'],
  controlled_frontal_production_states=r['production_states'],
  controlled_frontal_evidence=str(HERE/'controlled_front_check.json'),
  stable_person_recognition_accepted=False,actual_user_new_policy_return_recognition_passed=None,
  source_defect_in_detection_or_alignment_confirmed=False,
  user_registration_or_saved_photos_invalidated=False)
 path.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
marker='controlled-frontal-failure-20261019'
def note(path,body):
 raw=path.read_text(encoding='utf-8')
 raw=re.sub(r'<!-- '+marker+r' -->.*?<!-- /'+marker+r' -->\s*','',raw,flags=re.S)
 path.write_text('<!-- '+marker+' -->\n'+body+'\n<!-- /'+marker+' -->\n\n'+raw,encoding='utf-8')
note(ROOT/'AGENTS.md','- 2026-10-19用户“开始检查”后本人正脸10.09秒实测未通过：6份实际模型输入0达0.80，0.620695～0.643428/中位0.637173；52次状态全UNKNOWN，9次新鲜输入、1次无新输入、9次目标未确认、33次非单张脸条件（未细分0/多人，勿推断），目标键含None共3种。源龄429～774ms/无特征请求错；库修订15哈希不变，没存新图。彼此0.705348～0.950372，前3份相邻0.936632/0.950372，勿概括全程稳定。照片/模板一致性和登记成功仍有效，但本人正脸识别失败；检测及裁脸对齐待进一步定位，未确认新源码缺陷、不归因眼镜或用户姿态。未调0.80/0.1、未改模板/模型，不继续要求重登/转头/重返。最新证据deliverables/2026-10-19_identity_capture_snapshot/controlled_front_check_review.md及controlled_front_check.json。')
note(ROOT/'README.md','> **2026-10-19 登记后本人正脸检查未通过：** 10秒6份有效输入最高0.643/门槛0.80，检测目标也不稳定。登记照片与模板已核对一致，照片保存通过；真人识别仍待修复。[本轮数值及定位范围](deliverables/2026-10-19_identity_capture_snapshot/controlled_front_check_review.md)。')
note(HERE/'README.md','> **最新真人结果：正脸识别未通过。** 用户开始检查后10秒取得6份有效输入，0份达到0.80，最高0.643；人脸目标也不稳定。照片保存/模板一致性已通过，不能当作真人识别完成。[本轮结果](controlled_front_check_review.md)。')
analysis=ROOT.parent/'语言模型分析';name='登记后正脸识别实测_20261019.md'
(analysis/name).write_text(text,encoding='utf-8')
note(analysis/'README.md',f'[登记后本人正脸识别实测]({name})：未通过，最高0.643/门槛0.80；登记照片及模板一致，检测/新画面匹配待定位。')
print(json.dumps({'status':'FAILED_CONTROLLED_FRONTAL_RECOGNITION','sample_count':r['sample_count'],
 'pass_080':r['pass_080'],'max_score':r['score_distribution']['max'],
 'registration_and_photo_saving_still_valid':True,'production_changed':False}))
