"""Explicit local person-count questions; no image or additional model.

Public device observations stay in their configured device scope. The raw ASR
question remains only in the private channel's RAM transcript. A canonical
device_event represents this query, rather than pretending to be a verbatim
user statement. Answers carry same-device event/summary dependencies and use
the original TTS/player complete receipt. Conversation/profile recall never
receives copies of these answers.
"""
import re
import threading

from board.runtime.board_dialogue import SourcedBoardReply,StaleGeneration
from board.runtime.character import CHARACTER_NAME
from common.timeline import query as timeline_query
from common.visual_question import requested as legacy_visual_requested


ANSWER_TOPIC = '视觉查询答复'
OBSERVATION_TOPIC = '视觉'
_PAST = re.compile(r'刚才|刚刚|之前|先前|上次|上一次|昨天|前天|今早|今天|昨晚|上周|本周|这周|最近|过去|回忆|历史|还记得|时间轴|视觉记忆|画面记忆|一直|分钟前|小时前|秒前|去年|今年|上个月|这个月|上月|上星期|大前天|前几天|前些天|那天|当天|上午|下午|晚上|凌晨|近(?:\d+|[一二两三四五六七八九十]{1,3})(?:分钟|小时|天)|\d{4}年|\d{1,2}月|\d{4}[-年]\d{1,2}[-月]\d{1,2}')
_COUNT = re.compile(r'几(?:个)?人|多少(?:个)?人|人数|人体目标|有人吗|有没有人|是否有人|人多不多|无人|没人')
_UNSUPPORTED = re.compile(r'物品|杯子|手机|颜色|手里|拿的|这是什么|这个是什么|这东西|是谁|谁在|叫什么|认识|身份|人名|图片|图中|照片|相片|视频')


def requested(text):
    if not isinstance(text,str) or not 1 <= len(text) <= 4096:
        return False
    if re.search(r'记住|更正|修改|忘记|删除|清除|取消|确认',text):
        return False
    if re.search(r'(?:我|你|我们).{0,4}(?:说|聊|谈|提到).{0,10}(?:看到|看见|人数|几个人)',text):
        return False  # A query of the conversation is not camera evidence.
    strong = bool(re.search(r'镜头|画面|摄像头|视觉|观察记录',text))
    if not strong and re.search(r'项目|参加|参与|名单|成员|朋友|家庭',text):
        return False
    plain = re.sub(r'^\s*'+re.escape(CHARACTER_NAME)+r'[\s，,：:]*','',text)
    standalone = re.fullmatch(r'(?:现在|刚才|刚刚|之前|先前|昨天|前天|这里).{0,4}'
        r'(?:几(?:个)?人|多少(?:个)?人|人数|有人吗|有没有人|没人吗)[呢啊吗？?！!。]*',plain)
    seen_question = re.search(r'(?:看到|看见).{0,6}(?:几(?:个)?人|多少(?:个)?人|人数|人体目标|什么|啥|谁|人吗|有没有人)',text)
    return bool(legacy_visual_requested(text) or re.search(r'这个是什么|这件是什么',text) or
        strong and re.search(r'几|多少|人|什么|啥|谁|吗|记录|回忆',text) or seen_question or standalone)


def _kind(text):
    if _UNSUPPORTED.search(text):
        return 'unsupported_visual'
    if not _COUNT.search(text) and not re.search(r'看到了?什么|看见了?什么|画面.{0,3}(?:什么|啥)',text):
        return 'unsupported_visual'
    return 'historical_person_count' if _PAST.search(text) else 'current_person_count'


def _valid_count(values,allow_fixture):
    count = values.get('people_count')
    return (values.get('source') == 'camera_observed'
        and values.get('evidence') == 'visual_observation'
        and values.get('source_kind') in (('actual','fixture') if allow_fixture else ('actual',))
        and type(count) is int and 0 <= count <= 1000
        and values.get('event_kind') == ('person_count_observed' if count else 'no_person_detected'))


def _historical_counts(items,allow_fixture):
    counts,events,summaries = [],set(),set()
    for item in items:
        if not isinstance(item,dict):
            continue
        if item.get('source') == 'camera_observed':
            meta = item.get('metadata')
            if not isinstance(meta,dict):
                continue
            values = dict(source='camera_observed',evidence=meta.get('evidence'))
            for claim in meta.get('claims',[]):
                if isinstance(claim,dict) and set(claim) == {'field','value'}:
                    values[claim['field']] = claim['value']
            if _valid_count(values,allow_fixture) and isinstance(item.get('event_id'),str):
                counts.append(values['people_count']);events.add(item['event_id'])
        elif item.get('source') == 'timeline_summary' and isinstance(item.get('summary_id'),str):
            groups = {}
            for claim in item.get('claims',[]):
                if (isinstance(claim,dict) and set(claim) == {'event_id','field','value'}
                        and isinstance(claim['event_id'],str)):
                    groups.setdefault(claim['event_id'],{})[claim['field']] = claim['value']
            selected = [values['people_count'] for values in groups.values()
                        if _valid_count(values,allow_fixture)]
            if selected:
                counts.extend(selected);summaries.add(item['summary_id'])
    return counts,tuple(sorted(events)),tuple(sorted(summaries))


def historical_reply(result,*,allow_fixture=False):
    if not isinstance(result,dict) or not isinstance(result.get('items'),list) or not isinstance(result.get('status'),dict):
        raise ValueError('Visual history must include its bounded recall status')
    counts,events,summaries = _historical_counts(result['items'],allow_fixture)
    status = result['status']
    if counts:
        a,b = min(counts),max(counts)
        text = ('所选观察记录检测到%d个人体目标。' % a if a == b
                else '所选观察记录的目标数为%d至%d。' % (a,b))
    elif not result['items']:
        text = '这段未检索到有效人数记录，不等于当时没人。'
    else:
        text = '所选记录没有可核实的人体目标计数。'
    notes = []
    if status.get('result_limited') is True:
        notes.append('结果限量')
    if status.get('boundary_incomplete') is True:
        notes.append('跨界摘要未列')
    if summaries or status.get('boundary_incomplete') is True:
        notes.append('摘要细节不可还原')
    if notes:
        text += '；'.join(notes)+'。'
    if len(text)>48:
        raise ValueError('Local visual reply exceeds the original 48-character bound')
    return SourcedBoardReply(text,source_event_ids=events,summary_ids=summaries,
                              provenance_complete=True)


class LocalVisualQueries:
    requested = staticmethod(requested)
    matches = staticmethod(requested)

    def __init__(self,store,visual_worker,timeline,*,zone='America/Los_Angeles',limit=20):
        if (store is not visual_worker.store or timeline is not visual_worker.timeline
                or visual_worker.scope.get('kind') != 'device'
                or store.clock != timeline.event_time):
            raise ValueError('Use only the configured shared public device observation scope')
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError('Bound local visual recall to 1-20 items')
        self.store,self.worker,self.timeline,self.clock = store,visual_worker,timeline,timeline.monotonic
        self.scope,self.zone,self.limit = dict(visual_worker.scope),zone,limit
        self.allow_fixture = bool(getattr(visual_worker.collector,'allow_fixture',False))
        self.lock = threading.Lock()
        self.queries = 0
        self.last_kind,self.last_status = '',{}

    def public(self):
        with self.lock:
            return dict(enabled=True,scope_kind='device',queries=self.queries,
                last_kind=self.last_kind,last_recall_status=dict(self.last_status),
                images_used=False,additional_model=False,private_transcripts_stored=False)

    def _range(self,text,now):
        text = text.replace('刚刚','刚才')
        shorts = list(re.finditer(r'(?:最近|过去|近)(\d+|[一二两三四五六七八九十]{1,3})(分钟|小时)',text))
        if shorts:
            if len(shorts) != 1 or re.search(r'昨天|前天|今天|上周|本周|这周|去年|今年|上个月|这个月|上月|上星期|大前天|前几天|那天|当天|分钟前|小时前|秒前|上午|下午|晚上|凌晨|\d{4}[-年]',text):
                return {'error':'ambiguous_time_range'}
            short = shorts[0]
            numeral = short[1]
            if numeral.isascii() and numeral.isdigit():
                amount = int(numeral)
            else:
                digits = dict(zip('一二两三四五六七八九',(1,2,2,3,4,5,6,7,8,9)))
                if '十' in numeral:
                    a,b = numeral.split('十',1)
                    if (a and a not in digits) or (b and b not in digits):
                        return {'error':'unsupported_time_range'}
                    amount = (digits.get(a,1)*10)+digits.get(b,0)
                else:
                    amount = digits.get(numeral,0)
            amount *= 60 if short[2] == '小时' else 1
            if not 1 <= amount <= 24*60:
                return {'error':'unsupported_time_range'}
            return dict(start=max(0.,now-amount*60),end=now,error=None)
        if re.search(r'分钟|小时|秒前|前几天|前些天|那天|当天|今年|这个月|(?:过去|(?<!最)近).{0,8}天|最近[一二两三四五六七八九十]+天|(?:\d{1,2}|[一二两三四五六七八九十]{1,3})[点时:]',text):
            return {'error':'unsupported_time_range'}
        if re.search(r'\d{4}年|\d{1,2}月',text) and not re.search(r'\d{4}[-年]\d{1,2}[-月]\d{1,2}',text):
            return {'error':'unsupported_time_range'}
        selected = timeline_query(text,now=now,zone=self.zone)
        if selected['start'] is None and not selected['error']:
            if re.search(r'上次|上一次',text):
                return dict(start=None,end=now,limit=1,error=None)
            if not re.search(r'历史|时间轴|视觉记忆|画面记忆',text):
                return {'error':'time_range_required'}
        return dict(start=selected['start'],end=selected['end'],error=selected['error'])

    def __call__(self,text,*,job,controller,is_current,cancel_event,reply_sink=None):
        if not requested(text):
            raise ValueError('No explicit visual question')
        def current():
            if not is_current() or cancel_event.is_set():
                raise StaleGeneration('Visual reply no longer owns its input')
            if self.clock() >= job.deadline:
                raise TimeoutError('Original visual query deadline expired')
            self.store.check_scope(job.scope)  # Live original profile grant, no DB/fact read.
        current()
        kind = _kind(text)
        now = self.timeline.event_time()
        selected = self._range(text,now) if kind == 'historical_person_count' else None
        normalized = '设备查询意图（规范化）：'+{
            'current_person_count':'查询镜头当前人体目标数量。',
            'historical_person_count':'查询镜头人体目标数量历史。',
            'unsupported_visual':'查询超出人体目标计数范围的画面信息。'}[kind]
        claims = [{'field':'input_representation','value':'normalized_visual_query'},
                  {'field':'query_kind','value':kind}]
        if selected and not selected.get('error'):
            claims.extend([{'field':'query_start_utc','value':selected['start'] or 0.},
                           {'field':'query_end_utc','value':selected['end']}])
        def reply():
            current()
            status = {}
            if kind == 'unsupported_visual':
                value = SourcedBoardReply('我目前仅记录镜头人体目标数量，无法判断物品、颜色或身份。')
            elif kind == 'current_person_count':
                source = self.worker.record_current_observation()
                if source is None:
                    value = SourcedBoardReply('现在无法取得新鲜、稳定的人数观察，暂时不能判断。')
                else:
                    count = source['count']
                    value = SourcedBoardReply(
                        '这次画面取样稳定检测到%d个人体目标。' % count if count else
                        '这次画面取样未检测到人体目标，不能据此断定没人。',
                        source_event_ids=(source['event_id'],))
            elif selected.get('error'):
                value = SourcedBoardReply('请明确要查询的单日或最近多少分钟的视觉记录。')
                status = {'range_rejected':True}
            else:
                result = self.store.history_with_status(self.scope,topic=OBSERVATION_TOPIC,
                    start=selected['start'],end=selected['end'],limit=min(self.limit,selected.get('limit',self.limit)))
                value = historical_reply(result,allow_fixture=self.allow_fixture)
                status = {key:result['status'].get(key) for key in (
                    'returned_count','matching_count','result_limited','boundary_incomplete',
                    'boundary_omitted_summaries','summary_details_recoverable','absence_proven')}
            current()
            if len(value.text)>48:
                raise ValueError('Local visual reply exceeds the original bound')
            with self.lock:
                self.queries += 1
                self.last_kind,self.last_status = kind,status
            return value
        budget = int((job.deadline-self.clock())*1000)
        if budget<1:
            raise TimeoutError('Original visual reply deadline expired')
        return controller.prepare_local_reply(normalized,reply,scope=self.scope,
            session_id=job.meta['session_id'],generation=job.meta['generation'],budget_ms=budget,
            turn_id=job.meta['request_id'],cancel_event=cancel_event,topic=ANSWER_TOPIC,
            input_source='device_event',metadata=dict(evidence='device_confirmed',claims=claims))
