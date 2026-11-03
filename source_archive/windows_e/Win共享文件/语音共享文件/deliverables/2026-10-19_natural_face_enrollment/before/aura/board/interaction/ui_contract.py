"""Validated display/operation adapter for I03/I04/I05/I07, not a model protocol.

All times here are milliseconds from THIS board's monotonic clock. No device,
camera, database or register is opened by this module.
"""
import copy
import math
import time

PROTOCOL = 'aura-ui-1'
MODULE_STATES = {
    'interaction': ('UNKNOWN', 'IDLE', 'LISTENING', 'PROCESSING', 'SPEAKING', 'CANCELLED', 'ERROR'),
    'camera': ('UNKNOWN', 'READY', 'LOST', 'ERROR'),
    'vision': ('UNKNOWN', 'READY', 'DEGRADED', 'ERROR'),
    'npu': ('UNKNOWN', 'READY', 'DEGRADED', 'ERROR'),
    'pl': ('UNKNOWN', 'READY', 'DEGRADED', 'FAULT'),
    'target': ('UNKNOWN', 'NONE', 'CANDIDATE', 'CONFIRMED', 'LOST', 'AMBIGUOUS'),
    'identity': ('UNKNOWN', 'KNOWN', 'ENROLLING', 'DELETED', 'ERROR'),
    'motion': ('UNKNOWN', 'DISARMED', 'NEEDS_REFERENCE', 'ARMED', 'TRACKING', 'AT_LIMIT', 'FAULT'),
    'host': ('UNKNOWN', 'OFFLINE', 'CONNECTING', 'READY', 'DEGRADED', 'FAILED'),
    'audio': ('UNKNOWN', 'READY', 'RECORDING', 'PLAYING', 'UNAVAILABLE', 'ERROR'),
}
ACTIONS = ('record_start', 'record_stop', 'cancel', 'ask_frame', 'target_select',
           'identity_enroll', 'identity_delete', 'motion_disarm', 'identity_sample_start', 'identity_sample_cancel')
STATE_TEXT = {
    'UNKNOWN': '状态未知', 'IDLE': '待机', 'LISTENING': '正在聆听',
    'PROCESSING': '正在思考', 'SPEAKING': '正在播报', 'CANCELLED': '已取消',
    'ERROR': '异常', 'READY': '就绪', 'LOST': '已失联', 'DEGRADED': '部分可用',
    'NONE': '未选择', 'CANDIDATE': '候选对象', 'CONFIRMED': '已锁定',
    'AMBIGUOUS': '存在歧义', 'KNOWN': '已识别', 'ENROLLING': '正在登记',
    'DELETED': '已删除', 'DISARMED': '已禁能', 'NEEDS_REFERENCE': '等待参考确认',
    'ARMED': '已使能', 'TRACKING': '正在随动', 'AT_LIMIT': '到达指令边界',
    'FAULT': '故障', 'OFFLINE': '未连接', 'CONNECTING': '正在连接',
    'FAILED': '不可用', 'RECORDING': '正在录音', 'PLAYING': '正在播放',
    'UNAVAILABLE': '不可用',
}


def display_state(module, state):
    if state is None:
        return '待接入'
    if module == 'identity' and state == 'UNKNOWN':
        return '未识别'
    return STATE_TEXT.get(state, '状态未知')


def millis():
    return int(time.monotonic() * 1000)


def integer(value, minimum=0, maximum=2**53-1):
    return type(value) is int and minimum <= value <= maximum


def text(value, limit=160, empty=True):
    return (isinstance(value, str) and len(value) <= limit
            and (empty or bool(value.strip())) and '\x00' not in value)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def target_key(value):
    require(isinstance(value, dict) and set(value) == {'camera_epoch', 'track_id', 'track_generation'},
            '目标必须携带相机与轨迹代次')
    require(text(value['camera_epoch'], 96, False) and integer(value['track_id'], 1)
            and integer(value['track_generation'], 1), '目标生命周期无效')
    return copy.deepcopy(value)


def validate_snapshot(value, boot_id, now_ms):
    require(isinstance(value, dict), '服务状态必须为对象')
    required = {'protocol_version', 'board_boot_id', 'service_epoch', 'sequence',
                'observed_mono_ms', 'ttl_ms', 'source_kind', 'context', 'modules', 'capabilities'}
    require(required <= set(value) and not set(value)-required-{'preview'}, '服务状态字段不完整或未知')
    require(value['protocol_version'] == PROTOCOL, '界面接口版本不匹配')
    require(value['board_boot_id'] == boot_id, '状态属于另一次板卡启动')
    require(text(value['service_epoch'], 96, False), '缺少服务代次')
    require(integer(value['sequence'], 1), '状态序号无效')
    stamp, ttl = value['observed_mono_ms'], value['ttl_ms']
    require(integer(stamp) and integer(ttl, 100, 5000), '状态时间或有效期无效')
    require(stamp <= now_ms + 100 and now_ms < stamp + ttl, '服务状态已过期或不属于板端时钟')
    require(value['source_kind'] in ('actual', 'fixture'), '必须注明真实或测试数据')
    context = value['context']
    require(isinstance(context, dict) and set(context) == {'session_id', 'request_id', 'generation'},
            '交互归属字段不完整')
    require(text(context['session_id'], 96, False) and text(context['request_id'], 96)
            and integer(context['generation']), '交互归属无效')
    caps = value['capabilities']
    require(isinstance(caps, dict) and not set(caps)-set(ACTIONS)
            and all(type(v) is bool for v in caps.values()), '能力列表无效')
    modules = value['modules']
    require(isinstance(modules, dict) and not set(modules)-set(MODULE_STATES), '未知状态模块')
    for name, module in modules.items():
        require(isinstance(module, dict) and module.get('state') in MODULE_STATES[name]
                and text(module.get('detail', '')), '模块状态无效：'+name)
    interaction = modules.get('interaction', {})
    transport = modules.get('camera',{}).get('preview_transport')
    require(transport in (None,'aura-local-bgr-1'), '未知本机预览传输版本')
    require(text(interaction.get('transcript', ''), 2000) and text(interaction.get('reply', ''), 8000),
            '字幕长度无效')
    timings = interaction.get('timings_ms', {})
    require(isinstance(timings, dict) and not set(timings)-{'asr', 'vlm', 'tts', 'first_audio'}
            and all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 3600000
                    for v in timings.values()), '推理耗时无效')
    vision = modules.get('vision', {})
    require(integer(vision.get('people_count', 0), 0, 1000), '人数无效')
    target = modules.get('target', {})
    if target.get('selected') is not None:
        target_key(target['selected'])
    tracks = target.get('tracks', [])
    require(isinstance(tracks, list) and len(tracks) <= 16, '目标列表过长')
    keys = set()
    for row in tracks:
        require(isinstance(row, dict) and set(row) == {'key', 'label'}, '目标条目无效')
        key = target_key(row['key'])
        require(text(row['label'], 48, False), '目标名称无效')
        encoded = tuple(key[k] for k in ('camera_epoch', 'track_id', 'track_generation'))
        require(encoded not in keys, '目标生命周期重复')
        keys.add(encoded)
    identity = modules.get('identity', {})
    sampling=identity.get('enrollment_sampling')
    if sampling is not None:
        require(isinstance(sampling,dict) and set(sampling)=={'session_id','stage','counts','total','total_required','detail'},
                '采样状态字段无效')
        require(text(sampling['session_id'],96) and sampling['stage'] in ('idle','front','left','right','validate','ready','failed')
                and text(sampling['detail'],160) and sampling['total_required']==15,'采样阶段无效')
        counts=sampling['counts']
        require(isinstance(counts,dict) and set(counts)=={'front','left','right','validate'}
                and all(integer(counts[k],0,n) for k,n in (('front',4),('left',3),('right',3),('validate',5)))
                and integer(sampling['total'],0,15) and sampling['total']==sum(counts.values()),'采样数量无效')
    if identity.get('target_kind') is not None:
        require(identity['target_kind']=='face' and integer(identity.get('face_count'),0,16), '人脸目标类型或数量无效')
        faces=identity.get('face_targets')
        require(isinstance(faces,list) and len(faces)<=16, '人脸目标列表无效')
        face_keys=[]
        for row in faces:
            require(isinstance(row,dict) and set(row)=={'key','label'} and text(row['label'],48,False), '人脸目标条目无效')
            key=target_key(row['key']);require(key not in face_keys,'人脸轨迹重复');face_keys.append(key)
        selected_face=identity.get('face_target')
        require(selected_face is None or target_key(selected_face) in face_keys, '当前人脸目标已失效')
    face = identity.get('face_preview')
    if face is not None:
        require(isinstance(face,dict) and set(face)=={'target','frame_id','captured_mono_ms','ttl_ms'},
                '人脸预览字段无效')
        key=target_key(face['target'])
        selected=identity.get('face_target') if identity.get('target_kind')=='face' else target.get('selected')
        require(key==selected and integer(face['frame_id'],1)
                and integer(face['captured_mono_ms']) and face['captured_mono_ms']<=now_ms+100
                and integer(face['ttl_ms'],100,5000), '人脸预览归属或期限无效')
    for name in ('person_id', 'display_name'):
        require(text(identity.get(name, ''), 96), '身份字段无效')
    require(integer(identity.get('db_version', 0)), '身份库版本无效')
    people = identity.get('people', [])
    require(isinstance(people, list) and len(people) <= 32, '身份列表过长')
    ids = set()
    for row in people:
        require(isinstance(row, dict) and set(row) == {'person_id', 'display_name'}
                and text(row['person_id'], 96, False) and text(row['display_name'], 48, False),
                '身份条目无效')
        require(row['person_id'] not in ids, '身份 ID 重复')
        ids.add(row['person_id'])
    preview = value.get('preview')
    if preview is not None:
        require(isinstance(preview, dict) and set(preview) == {'camera_epoch', 'frame_id', 'captured_mono_ms'},
                '画面引用无效')
        require(text(preview['camera_epoch'], 96, False) and integer(preview['frame_id'], 1)
                and integer(preview['captured_mono_ms']) and preview['captured_mono_ms'] <= now_ms+100,
                '画面时间或编号无效')
    return copy.deepcopy(value)


def validate_action(action, params, snapshot):
    require(action in ACTIONS and isinstance(params, dict), '未知服务操作')
    require(snapshot is not None and snapshot['capabilities'].get(action) is True, '功能尚未接入或状态已失效')
    modules = snapshot['modules']
    if action in ('target_select', 'identity_enroll','identity_sample_start'):
        required = {'target', 'display_name', 'confirmed'} if action == 'identity_enroll' else {'target'}
        replacement=action in ('identity_enroll','identity_sample_start') and 'replace_person_id' in params
        require(set(params)==required|({'replace_person_id','db_version'} if replacement else set()), '目标操作字段不完整')
        if replacement:
            require(integer(params['db_version']) and params['db_version']==modules.get('identity',{}).get('db_version')
                and params['replace_person_id'] in [r['person_id'] for r in modules.get('identity',{}).get('people',[])],
                '待更新身份已变化')
        key = target_key(params['target'])
        identity=modules.get('identity',{})
        face_mode=action in ('identity_enroll','identity_sample_start') and identity.get('target_kind')=='face'
        targets=identity.get('face_targets',[]) if face_mode else modules.get('target',{}).get('tracks',[])
        require(key in [row['key'] for row in targets], '目标已离开或换代')
        if face_mode:require(key==identity.get('face_target') and identity.get('face_count')==1,'请只保留一个当前人脸目标')
        if action == 'identity_enroll':
            require(params['confirmed'] is True and text(params['display_name'], 48, False), '登记需要确认和名称')
    elif action=='identity_sample_cancel':
        require(set(params)=={'session_id'} and text(params['session_id'],96,False),'采样取消归属无效')
        require(params['session_id']==modules.get('identity',{}).get('enrollment_sampling',{}).get('session_id'),
                '采样已结束或已换代')
    elif action == 'identity_delete':
        require(set(params) == {'person_id', 'db_version', 'confirmed'} and params['confirmed'] is True,
                '删除需要明确确认')
        identity = modules.get('identity', {})
        require(integer(params['db_version']) and params['db_version'] == identity.get('db_version')
                and params['person_id'] in [r['person_id'] for r in identity.get('people', [])],
                '身份已删除或库版本变化')
    else:
        require(not params, '该操作不接受额外参数')
    if action in ('record_start', 'ask_frame'):
        require(modules.get('audio', {}).get('state') not in ('RECORDING', 'PLAYING')
                and modules.get('interaction', {}).get('state') not in ('LISTENING', 'PROCESSING', 'SPEAKING'),
                '当前录放音或交互尚未结束')
    if action == 'record_stop':
        require(modules.get('audio', {}).get('state') == 'RECORDING', '当前没有录音')
    if action == 'ask_frame':
        require(snapshot.get('preview') is not None and modules.get('camera', {}).get('state') == 'READY',
                '当前画面不可用')
    return copy.deepcopy(params)


def identity_completion(result, identity):
    """A transport ACK is not a committed enrollment/deletion."""
    operation = identity.get('last_operation', {})
    if (result.get('accepted') is True and result.get('action') in ('identity_enroll', 'identity_delete')
            and operation.get('command_id') == result.get('command_id')
            and operation.get('action') == result.get('action') and operation.get('state') == 'COMMITTED'
            and integer(operation.get('db_version')) and operation['db_version'] == identity.get('db_version')
            and text(operation.get('detail'), 160, False)):
        return operation['detail']
    return ''


class SnapshotGate:
    """Retain latest state, reject rollback/replayed epochs, expire by source time."""
    def __init__(self, boot_id, clock=millis):
        self.boot_id, self.clock = boot_id, clock
        self.value = None
        self.retired = set()
        self.cancelled_context = None

    def ingest(self, value):
        value = validate_snapshot(value, self.boot_id, self.clock())
        require(value['service_epoch'] not in self.retired, '旧服务代次不可恢复')
        if self.value:
            old = self.value
            if old['service_epoch'] == value['service_epoch']:
                if value['sequence'] == old['sequence'] and value == old:
                    return False
                require(value['sequence'] > old['sequence']
                        and value['observed_mono_ms'] >= old['observed_mono_ms'], '状态序号或时间倒退')
            else:
                require(len(self.retired) < 128, '服务换代过多，请重新连接')
                self.retired.add(old['service_epoch'])
        self.value = value
        return True

    def read(self):
        value = self.value
        if value is None or self.clock() >= value['observed_mono_ms']+value['ttl_ms']:
            return None
        result = copy.deepcopy(value)
        if self.cancelled_context == (value['service_epoch'], value['context']):
            module = result['modules'].setdefault('interaction', {})
            module.update(state='CANCELLED', transcript='', reply='', detail='本轮已取消')
            result['interaction_suppressed'] = True
        return result

    def cancel(self):
        if self.value:
            self.cancelled_context = (self.value['service_epoch'], copy.deepcopy(self.value['context']))


def validate_ack(value, command, now_ms):
    require(now_ms < command['deadline_mono_ms'], '操作回执已超时，结果未知')
    fields = {'protocol_version', 'board_boot_id', 'service_epoch', 'command_id', 'ui_epoch', 'ui_generation',
              'accepted', 'detail'}
    require(isinstance(value, dict) and set(value) == fields and integer(value['ui_generation']), '操作回执字段无效')
    for name in ('protocol_version', 'board_boot_id', 'service_epoch', 'command_id', 'ui_epoch', 'ui_generation'):
        require(value.get(name) == command[name], '操作回执归属不匹配：'+name)
    require(type(value.get('accepted')) is bool and text(value.get('detail', '')), '操作回执内容无效')
    return {'accepted': value['accepted'], 'detail': value.get('detail', '')}
