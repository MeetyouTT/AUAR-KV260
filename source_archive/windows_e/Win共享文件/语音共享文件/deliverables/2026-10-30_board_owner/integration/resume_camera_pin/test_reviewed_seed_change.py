"""Synthetic metadata-only proof; no device/runner/SQLite/systemd calls."""
import copy
import json
from pathlib import PurePosixPath

import pytest

import rebuild_face_readback_pin as pin
from test_rebuild_face_readback_pin import fixture, FixtureReader, OLD_BOOT, NEW_BOOT


def encode(value):
    return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()


class ReviewedReader(FixtureReader):
    def __init__(self,files):
        super().__init__(files)
        self.not_private=set();self.mapped=set();self.after_second=None
    def private_metadata(self,name):
        return name not in self.not_private
    def monotonic_ns(self): return 60_000_000_000
    def clock_ticks(self): return 100
    def mapped_file(self,pid,name): return name in self.mapped
    def python_paths(self,root):
        prefix=root+'/'
        return {name[len(prefix):] for name in self.files if name.startswith(prefix) and name.endswith('.py')}
    def process(self,pid):
        value=super().process(pid)
        if self.process_calls==2 and self.after_second:
            self.after_second()
        return value


def reviewed_fixture(monkeypatch):
    config,original,current,_=fixture()
    files=original.files
    ops=PurePosixPath(pin.ENTRY).parents[2]
    operator=ops/'pan-face-edge-v5/native-operator-v1'
    meta=json.loads(files[str(ops/'meta.json')])
    source_manifest=str(PurePosixPath(meta['candidate_root'])/'native-source.json')
    source={'schema':'aura-native-python-source-2','files':{
        'board/vision/ui_camera_service.py':meta['candidate_ui_sha256']}}
    files[source_manifest]=encode(source)
    old_library='/public/original-native.so';files[old_library]=b'public old native fixture, not an ELF runner'
    library=str(operator/'libaura_native_operator.so');files[library]=b'public current native fixture, not an ELF runner'
    recovery=str(operator/'identity_recovery.py');files[recovery]=b'public reviewed source only'
    unit_path=str(operator/'source-manifest.json');files[unit_path]=encode({'unit':'public synthetic ABI-v2 source manifest'})
    old_unit=pin.digest(b'public predecessor unit')
    unit=pin.digest(files[unit_path])
    settings_path=str(operator/'settings.json')
    settings={'schema':'aura-explicit-native-operator-request-1','request_boot_id':OLD_BOOT,
        'predecessor_unit_sha256':old_unit,'unit_sha256':unit,
        'old_library':old_library,'old_library_sha256':pin.digest(files[old_library]),
        'library':library,'library_sha256':pin.digest(files[library]),
        'constraints':{'hardcap_ms':30,'guard_ms':5,'request_only_once_this_boot':True}}
    files[settings_path]=encode(settings)
    operator_manifest_path=str(operator/'runtime-manifest.json')
    operator_files={name:pin.digest(files[name]) for name in (settings_path,recovery,unit_path,library,
        str(operator/'native_entry_operator.py'),str(ops/'native_entry_pan_face_v5.py'))}
    files[operator_manifest_path]=encode({'schema':'aura-native-operator-runtime-1','files':operator_files})
    anchors={'runtime_manifest':pin.digest(files[operator_manifest_path]),'settings':pin.digest(files[settings_path]),
        'identity_recovery':pin.digest(files[recovery]),'predecessor_unit':old_unit,'unit':unit,'library':pin.digest(files[library])}
    monkeypatch.setattr(pin,'REVIEWED_OPERATOR',anchors)
    directory='/public/kernel-history';checkpoint='/public/state/native-checkpoint.json'
    document={'schema':'aura-native-protection-checkpoint-2','scope':'final_quiescent_before_native_owner_close',
        'source_unit_sha256':unit,'seed':{'abi_version':2,'struct_size':520,'checkpoint_kind':1,'fenced':0,
            'purpose':'final_quiescent_business_checkpoint','boot_id':OLD_BOOT,'source_pid':1333,
            'source_birth_ticks':2232,'captured_mono_ns':9999999999,'source_manifest_sha256':pin.digest(files[source_manifest]),
            'primary_calls':91,'primary_period_overruns':7,'last_primary_ns':1_000_000_000,
            'admissions':[90,15,8],'completed':[90,15,8],'native_failures':[0,0,0],
            'not_submitted':[1,0,0],'overruns':[0,0,0],'disabled':[0,0,0],
            'reserved2':0,'reserved3':0,'reserved_bytes':'',
            'recovery':[dict(enabled=1,phase=0,reason=0,probe_successes=0,attempt_count=0,
                history_opaque=0,opaque_attempt_count=0,cooldown_until_ns=0,fault_primary_calls=0,
                fault_primary_overruns=0,faults=0,attempts=0,recoveries=0,observed_ns=1_000_000_000,
                attempt_times_ns=[0,0],reserved=0) for _ in range(2)]},
        'auxiliary':{'active':0,'fenced':0,'primary_waiting':0,'pending_result_tokens':[0,0,0]},
        'previous_kernel_history':{'preserved':'fixture history is never rewritten or reset'}}
    files[checkpoint]=encode(document);seed_hash=pin.digest(files[checkpoint])
    old_camera=json.loads(files[config['camera_config']])
    old_camera['native_execution']={'library':old_library,'library_sha256':pin.digest(files[old_library]),
        'seed':{'path':checkpoint,'sha256':'0'*64},'source_manifest':source_manifest,
        'source_manifest_sha256':pin.digest(files[source_manifest]),'source_unit_sha256':old_unit,
        'checkpoint_output':checkpoint,'allow_new_kernel_boot':True,'allow_legacy_new_kernel_boot':True,
        'new_boot_marker_directory':directory}
    camera=copy.deepcopy(old_camera);camera['native_execution']['seed']['sha256']=seed_hash
    files[config['camera_config']]=encode(old_camera);files[meta['candidate_config']]=encode(old_camera)
    files[current]=encode(camera)
    for name in config['source_sha256']:
        config['source_sha256'][name]=pin.digest(files[name])
    archive_path=directory+'/archive/'+NEW_BOOT+'-'+seed_hash+'.json'
    archive={'schema':'aura-native-previous-kernel-archive-1','current_boot':NEW_BOOT,'source_boot':OLD_BOOT,
        'source_checkpoint_sha256':seed_hash,'source_checkpoint_path':checkpoint,
        'source_manifest_sha256':pin.digest(files[source_manifest]),'history_is_lower_bound':False,
        'unknown_tail':False,'checkpoint':copy.deepcopy(document)}
    files[archive_path]=encode(archive)
    marker_path=directory+'/kernel-boot-'+NEW_BOOT+'.consumed'
    files[marker_path]=encode({'schema':'aura-native-current-kernel-consumption-1','boot':NEW_BOOT,
        'source_checkpoint_sha256':seed_hash,'archive_path':archive_path,'archive_sha256':pin.digest(files[archive_path]),
        'captured_mono_ns':40_000_000_000})
    reader=ReviewedReader(files);reader.mapped.add(library)
    return config,reader,dict(current=current,checkpoint=checkpoint,seed_hash=seed_hash,
        runtime_hash=pin.digest(files[current]),marker=marker_path,archive=archive_path,
        settings=settings_path,operator_manifest=operator_manifest_path,library=library,recovery=recovery,
        source_manifest=source_manifest)


def build(config,reader,details,**changes):
    values=dict(expected_boot=NEW_BOOT,expected_pid=1334,entry_sha256=config['source_sha256'][pin.ENTRY],
        expected_current_runtime_sha256=details['runtime_hash'],expected_current_seed_sha256=details['seed_hash'])
    values.update(changes)
    return pin.build_candidate(config,reader,**values)


def test_default_still_refuses_the_actual_single_seed_field_change(monkeypatch):
    config,reader,d=reviewed_fixture(monkeypatch)
    with pytest.raises(pin.PinRejected,match='GENERATED_CAMERA_CONFIG_BYTES_CHANGED'):
        build(config,reader,d,expected_current_runtime_sha256=None,expected_current_seed_sha256=None)


def test_reviewed_pair_proves_sealed_history_and_only_adds_new_metadata_pins(monkeypatch):
    config,reader,d=reviewed_fixture(monkeypatch); before=copy.deepcopy(reader.files); old=copy.deepcopy(config)
    candidate,report=build(config,reader,d)
    assert report['ready'] and not report['written']
    assert all(candidate['source_sha256'][name]==sha for name,sha in old['source_sha256'].items())
    assert candidate['camera_config']==d['current']
    assert candidate['source_sha256'][d['current']]==d['runtime_hash']
    assert candidate['identity_config']==old['identity_config'] and candidate['database']==old['database']
    review=report['reviewed_seed_change']
    assert review['existing_boot_consumption_verified'] and review['operator_library_mapped']
    assert not review['operator_request_executed'] and not review['counters_or_recovery_state_modified']
    assert not review['hardware_or_mechanical_readiness_asserted']
    assert config==old and reader.files==before
    assert d['checkpoint'] not in candidate['source_sha256']  # Mutable future checkpoint is never made an inherited static pin.
    assert old['database'] not in reader.reads
    assert not any('fpga' in name or 'firmware' in name for name in reader.reads)


@pytest.mark.parametrize('field',['expected_current_runtime_sha256','expected_current_seed_sha256'])
def test_both_explicit_review_hashes_are_required(monkeypatch,field):
    config,reader,d=reviewed_fixture(monkeypatch)
    with pytest.raises(pin.PinRejected,match='PAIR_REQUIRED'):
        build(config,reader,d,**{field:None})
    assert not reader.reads


@pytest.mark.parametrize('field',['expected_current_runtime_sha256','expected_current_seed_sha256'])
def test_review_values_must_match_actual_current_bytes(monkeypatch,field):
    config,reader,d=reviewed_fixture(monkeypatch)
    with pytest.raises(pin.PinRejected,match='SHA_MISMATCH'):
        build(config,reader,d,**{field:'f'*64})


def test_additional_camera_field_change_is_never_hidden_by_review(monkeypatch):
    config,reader,d=reviewed_fixture(monkeypatch)
    camera=json.loads(reader.files[d['current']]);camera['capture_fps']=1
    reader.files[d['current']]=encode(camera);d['runtime_hash']=pin.digest(reader.files[d['current']])
    with pytest.raises(pin.PinRejected,match='NOT_EXACT_SEED_SHA'):
        build(config,reader,d)


def test_changed_identity_or_any_original_pin_remains_a_hard_failure(monkeypatch):
    config,reader,d=reviewed_fixture(monkeypatch)
    identity=json.loads(reader.files[config['identity_config']]);identity['threshold']=0.
    reader.files[config['identity_config']]=encode(identity)
    with pytest.raises(pin.PinRejected,match='ORIGINAL_SOURCE_SHA_MISMATCH'):
        build(config,reader,d)


@pytest.mark.parametrize('name',['checkpoint','marker','archive'])
def test_protected_history_metadata_must_remain_private(monkeypatch,name):
    config,reader,d=reviewed_fixture(monkeypatch);reader.not_private.add(d[name])
    with pytest.raises(pin.PinRejected,match='METADATA_NOT_PRIVATE'):
        build(config,reader,d)


@pytest.mark.parametrize('name',['settings','operator_manifest','library','recovery'])
def test_existing_operator_chain_cannot_be_replaced_even_with_the_pair(monkeypatch,name):
    config,reader,d=reviewed_fixture(monkeypatch);reader.files[d[name]]+=b'changed'
    with pytest.raises(pin.PinRejected):
        build(config,reader,d)


def test_operator_library_must_belong_to_the_actual_camera_process(monkeypatch):
    config,reader,d=reviewed_fixture(monkeypatch);reader.mapped.clear()
    with pytest.raises(pin.PinRejected,match='NOT_MAPPED_BY_CAMERA'):
        build(config,reader,d)


def test_new_boot_marker_cannot_predate_this_actual_camera_owner(monkeypatch):
    config,reader,d=reviewed_fixture(monkeypatch)
    marker=json.loads(reader.files[d['marker']]);marker['captured_mono_ns']=1
    reader.files[d['marker']]=encode(marker)
    with pytest.raises(pin.PinRejected,match='PREDATES_CURRENT_OWNER'):
        build(config,reader,d)


def test_archived_counter_history_must_equal_the_entire_reviewed_checkpoint(monkeypatch):
    config,reader,d=reviewed_fixture(monkeypatch)
    archive=json.loads(reader.files[d['archive']]);archive['checkpoint']['seed']['primary_calls']=0
    reader.files[d['archive']]=encode(archive)
    marker=json.loads(reader.files[d['marker']]);marker['archive_sha256']=pin.digest(reader.files[d['archive']])
    reader.files[d['marker']]=encode(marker)
    with pytest.raises(pin.PinRejected,match='ARCHIVE_BINDING_MISMATCH'):
        build(config,reader,d)


def test_source_proof_is_rechecked_after_the_second_pid_observation(monkeypatch):
    config,reader,d=reviewed_fixture(monkeypatch)
    reader.after_second=lambda:reader.files.__setitem__(d['settings'],reader.files[d['settings']]+b'changed')
    with pytest.raises(pin.PinRejected,match='PROOF_CHANGED_DURING_PROBE'):
        build(config,reader,d)


def test_added_native_python_file_changes_the_full_source_closure(monkeypatch):
    config,reader,d=reviewed_fixture(monkeypatch)
    root=str(PurePosixPath(d['source_manifest']).parent/'aura')
    reader.files[root+'/unreviewed.py']=b'unknown source'
    with pytest.raises(pin.PinRejected,match='SOURCE_CLOSURE_CHANGED'):
        build(config,reader,d)


@pytest.mark.parametrize('field,value,code',[
    ('fenced',1,'NOT_SEALED_QUIESCENT'), ('abi_version',3,'NOT_SEALED_QUIESCENT'),
    ('purpose','isolated_model_equivalence','NOT_SEALED_QUIESCENT'),
    ('boot_id',NEW_BOOT,'PREDECESSOR_OWNER_MISMATCH'),
    ('source_pid',999,'PREDECESSOR_OWNER_MISMATCH'),
    ('source_birth_ticks',999,'PREDECESSOR_OWNER_MISMATCH'),
    ('source_manifest_sha256','f'*64,'SOURCE_MANIFEST_MISMATCH'),
])
def test_reviewed_hashes_never_make_an_unsealed_or_foreign_seed_acceptable(monkeypatch,field,value,code):
    config,reader,d=reviewed_fixture(monkeypatch)
    document=json.loads(reader.files[d['checkpoint']]);document['seed'][field]=value
    reader.files[d['checkpoint']]=encode(document);d['seed_hash']=pin.digest(reader.files[d['checkpoint']])
    camera=json.loads(reader.files[d['current']]);camera['native_execution']['seed']['sha256']=d['seed_hash']
    reader.files[d['current']]=encode(camera);d['runtime_hash']=pin.digest(reader.files[d['current']])
    with pytest.raises(pin.PinRejected,match=code):
        build(config,reader,d)
