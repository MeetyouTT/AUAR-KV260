"""Explicit native provenance/fresh-runtime checks without importing real ORT."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_diagnostic_copy_preserves_entire_reviewed_parent_source():
    builder = load(ROOT/'build_runtime_probe.py','runtime_probe_builder')
    original = ROOT.parent/'resume_inference/board_audio_pipeline_probe.py'
    raw = original.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == builder.PARENT_SHA256
    source = raw.decode('utf-8').replace('\r\n','\n')
    derived = (ROOT/'board_audio_runtime_probe.py').read_text(encoding='utf-8')
    assert builder.build(source) == derived
    assert builder.recover_original(derived) == source
    # Exact inversion protects original device, model, overflow, threshold,
    # timeouts, scheduler, endpoint and both root-added ESRCH race guards.
    assert 'except (FileNotFoundError, ProcessLookupError):' in derived
    assert 'thread_nice = _nice_counts(ProbeProcessPriority(0)._read())' in derived


def test_official_native_fingerprints_match_offline_asset_manifest():
    module = load(ROOT/'board_audio_runtime_probe.py','runtime_probe_pins')
    assets = json.loads((ROOT.parent/'resume_ort_candidate/official_assets.json').read_text(encoding='utf-8'))
    expected = {item['path']:item['sha256'] for asset in assets['assets'] for item in asset['native_files']}
    assert all(expected[name] == sha for name,sha in module._OFFICIAL_NATIVE.items())
    assert {a['package']:a['sha256'] for a in assets['assets']} == module._OFFICIAL_WHEELS


@pytest.fixture
def runtime_case(tmp_path, monkeypatch):
    module = load(ROOT/'board_audio_runtime_probe.py','explicit_runtime_under_test')
    private = (tmp_path/'private').resolve()
    numpy_root = private/'numpy-1.26.4'
    new_ort = private/'onnxruntime-1.19.2'
    fft,asr = tmp_path/'original-fft',tmp_path/'original-asr'

    def file(path, data=b'synthetic native image'):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data)
        return path

    names = list(module._OFFICIAL_NATIVE)
    natives = {}
    for relative in names:
        target = file((numpy_root if relative.startswith('numpy/') else new_ort)/relative)
        natives[relative] = hashlib.sha256(target.read_bytes()).hexdigest()
    monkeypatch.setattr(module,'_OFFICIAL_NATIVE',natives)
    for package,version,root in (('numpy','1.26.4',numpy_root),('onnxruntime','1.19.2',new_ort)):
        file(root/'isolation-manifest.json',json.dumps(dict(status='UNPACKED_NOT_IMPORTED',
            package=package,version=version,wheel_sha256=module._OFFICIAL_WHEELS[package])).encode())
    np = SimpleNamespace(__version__='1.26.4',__file__=str(file(numpy_root/'numpy/__init__.py',b'')))
    ort = SimpleNamespace(__version__='1.19.2',__file__=str(file(new_ort/'onnxruntime/__init__.py',b'')),
        get_available_providers=lambda:['CPUExecutionProvider'])
    sherpa = SimpleNamespace(__version__='1.13.8',__file__=str(file(asr/'deps/sherpa_onnx/__init__.py',b'')))
    binding = SimpleNamespace(__file__=str(new_ort/names[0]))
    core = SimpleNamespace(__file__=str(numpy_root/'numpy/core/_multiarray_umath.cpython-39-aarch64-linux-gnu.so'))
    fft_native = SimpleNamespace(__file__=str(numpy_root/'numpy/fft/_pocketfft_internal.cpython-39-aarch64-linux-gnu.so'))
    for name,value in [('numpy',np),('onnxruntime',ort),
                       ('onnxruntime.capi.onnxruntime_pybind11_state',binding),
                       ('numpy.core._multiarray_umath',core),('numpy.fft._pocketfft_internal',fft_native)]:
        monkeypatch.setitem(sys.modules,name,value)
    monkeypatch.setattr(module,'_PRELOADED_NUMPY',np)
    monkeypatch.setattr(module,'_PRELOADED_ORT',ort)
    # Only module-local OS/sys wrappers are replaced; pytest's process is intact.
    monkeypatch.setattr(module,'os',SimpleNamespace(name='posix'))
    monkeypatch.setattr(module,'sys',SimpleNamespace(version_info=(3,9,9),
        flags=SimpleNamespace(no_site=1),modules=sys.modules,stderr=sys.stderr))
    args = SimpleNamespace(runtime_private_root=private,runtime_numpy_root=numpy_root,
        runtime_ort_root=new_ort,runtime_ort_version='1.19.2')
    return SimpleNamespace(module=module,args=args,np=np,ort=ort,sherpa=sherpa,fft=fft,asr=asr,
        binding=binding,core=core,native_fft=fft_native,file=file)


def check(case):
    return case.module.require_explicit_runtime(case.args,case.np,case.ort,case.sherpa,case.fft,case.asr)


def test_exact_new_runtime_records_real_origins_without_mutating_modules(runtime_case):
    case = runtime_case
    before = dict(sys.modules)
    proof = check(case)
    assert proof['onnxruntime'] == '1.19.2' and proof['numpy'] == '1.26.4'
    assert proof['official_wheel_sha256'] == case.module._OFFICIAL_WHEELS
    assert proof['official_native_sha256'] == case.module._OFFICIAL_NATIVE
    assert proof['version_or_module_rewritten'] is False
    assert all(sys.modules.get(name) is value for name,value in before.items())


def test_retained_ort_requires_original_fft_deps_with_same_paired_numpy(runtime_case):
    case = runtime_case
    old_root = (case.fft/'deps').resolve()
    case.ort.__version__ = '1.17.3'
    case.ort.__file__ = str(case.file(old_root/'onnxruntime/__init__.py',b''))
    case.binding.__file__ = str(case.file(old_root/'onnxruntime/capi/old_binding.so'))
    case.args.runtime_ort_root,case.args.runtime_ort_version = old_root,'1.17.3'
    proof = check(case)
    assert proof['numpy'] == '1.26.4' and proof['onnxruntime'] == '1.17.3'
    assert 'onnxruntime' not in proof['official_wheel_sha256']
    assert len(proof['official_native_sha256']) == 2


@pytest.mark.parametrize('mutation,match',[
    (lambda c:setattr(c.module.sys.flags,'no_site',0),'fresh ARM'),
    (lambda c:setattr(c.module,'_PRELOADED_ORT',None),'preloaded'),
    (lambda c:setattr(c.np,'__version__','1.21.2'),'NumPy1.26.4'),
    (lambda c:setattr(c.ort,'__version__','1.17.3'),'version mismatch'),
    (lambda c:setattr(c.args,'runtime_ort_version','1.20.0'),'version mismatch'),
    (lambda c:setattr(c.sherpa,'__version__','1.13.7'),'sherpa1.13.8'),
    (lambda c:setattr(c.ort,'get_available_providers',lambda:[]),'CPUExecutionProvider'),
    (lambda c:setattr(c.args,'runtime_private_root',c.args.runtime_numpy_root),'NumPy1.26.4'),
])
def test_runtime_drift_is_refused_before_model_loading(runtime_case,mutation,match):
    mutation(runtime_case)
    with pytest.raises(ValueError,match=match):
        check(runtime_case)


def test_lying_version_cannot_hide_loaded_binding_outside_selected_root(runtime_case):
    case = runtime_case
    case.binding.__file__ = str(case.file(case.fft/'deps/onnxruntime/capi/original.so'))
    with pytest.raises(ValueError,match='binding differs'):
        check(case)


def test_lying_package_cannot_hide_numpy_fft_outside_paired_root(runtime_case):
    case = runtime_case
    case.native_fft.__file__ = str(case.file(case.fft/'deps/numpy/fft/original.so'))
    with pytest.raises(ValueError,match='native core/FFT'):
        check(case)


def test_native_binary_tampering_is_refused(runtime_case):
    case = runtime_case
    Path(case.binding.__file__).write_bytes(b'changed binary')
    with pytest.raises(ValueError,match='fingerprint mismatch'):
        check(case)


def test_wheel_manifest_substitution_is_refused(runtime_case):
    case = runtime_case
    path = case.args.runtime_numpy_root/'isolation-manifest.json'
    value = json.loads(path.read_text())
    value['wheel_sha256'] = '0'*64
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='manifest differs'):
        check(case)
