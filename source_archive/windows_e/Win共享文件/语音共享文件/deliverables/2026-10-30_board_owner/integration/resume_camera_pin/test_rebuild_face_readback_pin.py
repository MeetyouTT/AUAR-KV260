"""Small synthetic filesystem/proc fixtures. No board, gallery or model access."""
import copy
import json
from pathlib import PurePosixPath

import pytest

from rebuild_face_readback_pin import (ENTRY, UNIT, PinRejected, build_candidate, digest,
                                      differences, write_new_candidate)


OLD_BOOT = '605eaf50-c66a-4559-bfc9-5ae177e0f305'
NEW_BOOT = '8100a7fd-0c6a-46c4-82b8-f874988a1521'


class FixtureReader:
    def __init__(self,files,boot=NEW_BOOT):
        self.files,self.current_boot = files,boot
        self.reads = []; self.process_calls = 0; self.reuse = False; self.selected_entry = ENTRY
    def read(self,name,maximum=2*1024*1024):
        assert not name.endswith('.sqlite3'), 'Fixture must never read a gallery'
        self.reads.append(name)
        return self.files[name]
    def hash(self,name):
        return digest(self.read(name))
    def boot(self):
        return self.current_boot
    def unit(self):
        return dict(MainPID='1334',ActiveState='active',SubState='running',ControlGroup='/system.slice/'+UNIT,
                    ExecStart='{ path=/usr/bin/python3 ; argv[]=/usr/bin/python3 -B '+self.selected_entry+' ; ignore_errors=no ; }')
    def process(self,pid):
        self.process_calls += 1
        return dict(pid=1334,start_ticks='9999' if self.reuse and self.process_calls>1 else '3210',
                    cmdline_sha256=digest(('/usr/bin/python3\0-B\0'+ENTRY+'\0').encode()),
                    argv=['/usr/bin/python3','-B',ENTRY],executable='/usr/bin/python3.9',
                    argv_executable='/usr/bin/python3.9',cgroups=['/system.slice/'+UNIT])


def fixture():
    ops = PurePosixPath(ENTRY).parents[2]
    identity_path = '/public/board_identity.json'
    database = '/home/root/.local/share/aura/DO_NOT_OPEN_SYNTHETIC.sqlite3'
    model = '/public/sface-public.xmodel'; manifest = '/public/sface-manifest.json'
    model_bytes = b'public synthetic model bytes, not weights'
    model_sha = digest(model_bytes)
    identity = dict(schema_version='aura-camera-identity-1',database=database,
        model_id='sface-int8-'+model_sha[:16],result_ttl_ms=3000,threshold=.5,
        feature_backend=dict(kind='dpu_sface',model=model,model_sha256=model_sha,
                             manifest=manifest,manifest_sha256=digest(b'{}')))
    camera = dict(identity={'enabled':True,'config':identity_path},
                  native_execution={'seed':{'sha256':'0'*64}},capture_fps=30)
    encode = lambda value:json.dumps(value,sort_keys=True).encode()
    candidate = '/public/candidate'
    meta = dict(root=str(ops),candidate_root=candidate,candidate_config=candidate+'/camera.json',
                candidate_ui_sha256=digest(b'public camera source'))
    old_runtime = str(ops/('native-run-'+OLD_BOOT+'-1333')/'config.json')
    new_runtime = str(ops/('native-run-'+NEW_BOOT+'-1334')/'config.json')
    files = {ENTRY:b'public pinned launcher',str(ops/'meta.json'):encode(meta),
             str(ops/'native_entry.py'):b'public pinned native entry',
             str(ops/'native_entry_pan_face_v5.py'):b'public pinned face entry',
             str(ops/'pan-face-edge-v5/native-operator-v1/native_entry_operator.py'):b'public operator entry',
             candidate+'/camera.json':encode(camera),candidate+'/aura/board/vision/ui_camera_service.py':b'public camera source',
             old_runtime:encode(camera),identity_path:encode(identity),model:model_bytes,manifest:b'{}'}
    pins = {name:digest(raw) for name,raw in files.items() if name not in (model,manifest)}
    files[new_runtime] = encode(camera)
    config = dict(version=1,enabled=True,board_boot_id=OLD_BOOT,camera_pid=1333,camera_start_ticks='2232',
        camera_cmdline_sha256='a'*64,camera_config=old_runtime,identity_config=identity_path,
        source_sha256=pins,database=database,model_id=identity['model_id'],dimension=128,
        model_sha256=model_sha,result_ttl_ms=3000,backend='DPU_SFACE_INT8')
    return config,FixtureReader(files),new_runtime,model


def build(config,reader):
    return build_candidate(config,reader,expected_boot=NEW_BOOT,expected_pid=1334,
                           entry_sha256=config['source_sha256'][ENTRY])


def test_identical_runtime_relocation_keeps_all_old_pins_and_never_opens_gallery():
    config,reader,new_runtime,_ = fixture(); before = copy.deepcopy(config)
    candidate,report = build(config,reader)
    assert report['ready'] and report['camera_config_relocated'] and report['written'] is False
    assert config == before and candidate['camera_pid'] == 1334 and candidate['camera_start_ticks'] == '3210'
    assert candidate['camera_config'] == new_runtime
    assert all(candidate['source_sha256'][name] == value for name,value in config['source_sha256'].items())
    assert candidate['source_sha256'][new_runtime] == config['source_sha256'][config['camera_config']]
    assert candidate['database'] == config['database'] and candidate['model_id'] == config['model_id']
    assert config['database'] not in reader.reads and report['database_opened'] is False


def test_modified_original_entry_source_refuses_refresh():
    config,reader,_,_ = fixture(); reader.files[ENTRY] += b'changed'
    with pytest.raises(PinRejected,match='ORIGINAL_SOURCE_SHA_MISMATCH'):
        build(config,reader)


def test_actual_model_bytes_changed_refuses_refresh_without_loading_runner():
    config,reader,_,model = fixture(); reader.files[model] += b'changed'
    with pytest.raises(PinRejected,match='ACTUAL_DPU_MODEL_SHA_MISMATCH'):
        build(config,reader)


def test_reused_pid_between_observations_is_rejected():
    config,reader,_,_ = fixture(); reader.reuse = True
    with pytest.raises(PinRejected,match='CAMERA_PROCESS_REUSED_DURING_PROBE'):
        build(config,reader)


def test_old_same_boot_pid_reuse_is_not_silently_rebased():
    config,reader,_,_ = fixture(); config.update(board_boot_id=NEW_BOOT,camera_pid=1334)
    with pytest.raises(PinRejected,match='OLD_PID_REUSED'):
        build(config,reader)


def test_pending_systemd_entry_must_match_the_actual_running_process():
    config,reader,_,_ = fixture(); reader.selected_entry = '/public/different-entry.py'
    with pytest.raises(PinRejected,match='SYSTEMD_EXECSTART_DIFFERS_FROM_PROC'):
        build(config,reader)


def test_changed_runtime_bytes_report_only_redacted_field_names():
    config,reader,new_runtime,_ = fixture()
    camera = json.loads(reader.files[new_runtime]); camera['native_execution']['seed']['sha256'] = 'PRIVATE_VALUE_NOT_TO_PRINT'
    camera['PRIVATE_UNTRUSTED_KEY'] = 'PRIVATE_VALUE_NOT_TO_PRINT'
    reader.files[new_runtime] = json.dumps(camera).encode()
    with pytest.raises(PinRejected) as failure:
        build(config,reader)
    assert failure.value.code == 'GENERATED_CAMERA_CONFIG_BYTES_CHANGED'
    assert failure.value.fields == ['native_execution.seed.sha256','<additional_fields>']
    assert 'PRIVATE_' not in json.dumps(failure.value.fields)


def test_review_token_does_not_accept_a_different_process_observation(tmp_path):
    config,reader,_,_ = fixture(); candidate,report = build(config,reader)
    with pytest.raises(PinRejected,match='REVIEWED_OBSERVATION_TOKEN_MISMATCH'):
        write_new_candidate(candidate,report,private_root=tmp_path,output=tmp_path/'candidate.json',
                            expected_observation_sha256='0'*64)
    assert list(tmp_path.iterdir()) == []
