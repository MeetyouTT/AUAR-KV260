"""Build one explicit-runtime diagnostic copy from a SHA-pinned parent probe.

The original file is never written. The only replacements are one runtime guard,
four required diagnostic CLI flags, and an origin-proof output field. Every
other byte of normalized original source is retained, including ESRCH fixes.
"""
import argparse
import hashlib
from pathlib import Path


PARENT_SHA256 = 'b53803cab734bb69cd8a62698c92d630ed98d9d0b2cee7ecc9232bcb4a4323a3'
OLD_GUARD = """    if (ort.__version__ != '1.17.3' or sherpa.__version__ != '1.13.8'
            or (fft/'deps').resolve() not in Path(ort.__file__).resolve().parents
            or (asr/'deps').resolve() not in Path(sherpa.__file__).resolve().parents):
        raise ValueError('Require the previously verified isolated ORT/sherpa versions')
"""
NEW_GUARD = """    _SELECTED_RUNTIME_PROOF.update(require_explicit_runtime(args, np, ort, sherpa, fft, asr))
"""
CLI_ANCHOR = "    parser.add_argument('--resources-root', type=Path, required=True)\n"
CLI_EXTRA = """    parser.add_argument('--runtime-private-root', type=Path, required=True)
    parser.add_argument('--runtime-ort-root', type=Path, required=True)
    parser.add_argument('--runtime-ort-version', choices=('1.17.3','1.19.2'), required=True)
    parser.add_argument('--runtime-numpy-root', type=Path, required=True)
"""
OUTPUT_ANCHOR = '    print(json.dumps(value,ensure_ascii=True),flush=True)\n'
OUTPUT_EXTRA = "    value['selected_runtime'] = dict(_SELECTED_RUNTIME_PROOF)\n"


RUNTIME_GUARD = r'''
# Explicit diagnostic-only alternate runtime. Imported module objects are
# captured before the parent's original run_probe can prepend its old deps.
# No sys.modules entry, package version or production source is changed.
REVIEWED_PARENT_SHA256 = 'b53803cab734bb69cd8a62698c92d630ed98d9d0b2cee7ecc9232bcb4a4323a3'
_PRELOADED_NUMPY = sys.modules.get('numpy')
_PRELOADED_ORT = sys.modules.get('onnxruntime')
_SELECTED_RUNTIME_PROOF = {}
_OFFICIAL_WHEELS = {
    'onnxruntime': 'df2a94179a42d530b936f154615b54748239c2908ee44f0d722cb4df10670f68',
    'numpy': 'd5241e0a80d808d70546c697135da2c613f30e28251ff8307eb72ba696945764',
}
_OFFICIAL_NATIVE = {
    'onnxruntime/capi/onnxruntime_pybind11_state.cpython-39-aarch64-linux-gnu.so':
        '4e3e7d9ac54723d6602cf0258041a9ef79bb3c40eb28e9c63d4d105a7d1ce5bc',
    'onnxruntime/capi/libonnxruntime.so.1.19.2':
        '4a8b12f35d553899a064ae577dc6d9be44c47a5ba4530ac0cf2e1454e4567afc',
    'onnxruntime/capi/libonnxruntime_providers_shared.so':
        'd93c6b9016eb23a46b7ace5a6c7d56139fdf11bfe0228e93801de758707dee2b',
    'numpy/core/_multiarray_umath.cpython-39-aarch64-linux-gnu.so':
        '147aff3b8942204bbd523583c39b7e6c5ddd20387afc9126e65183c0c53fc129',
    'numpy/fft/_pocketfft_internal.cpython-39-aarch64-linux-gnu.so':
        '5eb2a64a494acaae6f3363d9c5503b83be907b8dfe640045a944f8c11abb4ad3',
}


def _runtime_sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for raw in iter(lambda: stream.read(1024*1024), b''):
            result.update(raw)
    return result.hexdigest()


def _runtime_root(path):
    value = Path(path)
    if not value.is_absolute() or value.resolve(strict=True) != value or not value.is_dir():
        raise ValueError('Diagnostic runtime roots must be explicit regular absolute directories')
    return value


def _runtime_manifest(root, package, version):
    path = root/'isolation-manifest.json'
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024*1024:
        raise ValueError('Missing bounded private runtime isolation manifest')
    value = json.loads(path.read_text(encoding='utf-8'))
    if (value.get('status') != 'UNPACKED_NOT_IMPORTED' or value.get('package') != package
            or value.get('version') != version
            or value.get('wheel_sha256') != _OFFICIAL_WHEELS[package]):
        raise ValueError('Private runtime manifest differs from the reviewed official wheel')
    return value['wheel_sha256']


def _runtime_native(root, relative):
    path = root/relative
    if path.is_symlink() or path.resolve(strict=True) != path or not path.is_file():
        raise ValueError('Native runtime file must remain inside its regular pinned root')
    actual = _runtime_sha(path)
    if actual != _OFFICIAL_NATIVE[relative]:
        raise ValueError('Official native runtime fingerprint mismatch')
    return actual


def require_explicit_runtime(args, np, ort, sherpa, fft, asr):
    """Fail before loading models unless helper selected the exact paired case."""
    import importlib
    if (os.name != 'posix' or sys.version_info[:2] != (3,9)
            or getattr(sys.flags, 'no_site', 0) != 1):
        raise ValueError('Use the reviewed helper fresh ARM CPython3.9 -S child')
    if (np is not _PRELOADED_NUMPY or ort is not _PRELOADED_ORT
            or np is not sys.modules.get('numpy') or ort is not sys.modules.get('onnxruntime')):
        raise ValueError('Selected NumPy/ORT must already be preloaded without replacement')
    private = _runtime_root(args.runtime_private_root)
    numpy_root = _runtime_root(args.runtime_numpy_root)
    ort_root = _runtime_root(args.runtime_ort_root)
    if (numpy_root != private/'numpy-1.26.4' or np.__version__ != '1.26.4'
            or numpy_root not in Path(np.__file__).resolve(strict=True).parents):
        raise ValueError('Both paired cases require the exact private NumPy1.26.4')
    if args.runtime_ort_version not in ('1.17.3','1.19.2') or ort.__version__ != args.runtime_ort_version:
        raise ValueError('Selected exact ORT diagnostic version mismatch')
    expected_ort = ((fft/'deps').resolve(strict=True) if args.runtime_ort_version == '1.17.3'
                    else private/'onnxruntime-1.19.2')
    if ort_root != expected_ort or ort_root not in Path(ort.__file__).resolve(strict=True).parents:
        raise ValueError('Selected ORT package is outside the exact permitted case root')
    if (sherpa.__version__ != '1.13.8'
            or (asr/'deps').resolve(strict=True) not in Path(sherpa.__file__).resolve(strict=True).parents):
        raise ValueError('Require the unchanged previously verified isolated sherpa1.13.8')
    binding = importlib.import_module('onnxruntime.capi.onnxruntime_pybind11_state')
    numpy_core = importlib.import_module('numpy.core._multiarray_umath')
    numpy_fft = importlib.import_module('numpy.fft._pocketfft_internal')
    binding_file = Path(binding.__file__).resolve(strict=True)
    if ort_root not in binding_file.parents:
        raise ValueError('Loaded ORT binding differs from the selected private core')
    if (Path(numpy_core.__file__).resolve(strict=True) != numpy_root/'numpy/core/_multiarray_umath.cpython-39-aarch64-linux-gnu.so'
            or Path(numpy_fft.__file__).resolve(strict=True) != numpy_root/'numpy/fft/_pocketfft_internal.cpython-39-aarch64-linux-gnu.so'):
        raise ValueError('Loaded NumPy native core/FFT differs from the paired private root')
    native = {}
    wheels = dict(numpy=_runtime_manifest(numpy_root,'numpy','1.26.4'))
    for relative in _OFFICIAL_NATIVE:
        if relative.startswith('numpy/'):
            native[relative] = _runtime_native(numpy_root,relative)
        elif args.runtime_ort_version == '1.19.2':
            native[relative] = _runtime_native(ort_root,relative)
    if args.runtime_ort_version == '1.19.2':
        if binding_file != ort_root/'onnxruntime/capi/onnxruntime_pybind11_state.cpython-39-aarch64-linux-gnu.so':
            raise ValueError('Selected new ORT binding path differs from the official CP39 ARM64 member')
        wheels['onnxruntime'] = _runtime_manifest(ort_root,'onnxruntime','1.19.2')
    providers = ort.get_available_providers()
    if 'CPUExecutionProvider' not in providers:
        raise ValueError('Selected CPU runtime has no CPUExecutionProvider')
    proof = dict(status='EXACT_PRELOADED_RUNTIME_VERIFIED',
        reviewed_parent_sha256=REVIEWED_PARENT_SHA256,
        onnxruntime=ort.__version__,numpy=np.__version__,sherpa_onnx=sherpa.__version__,
        ort_root=str(ort_root),numpy_root=str(numpy_root),private_root=str(private),
        ort_origin=str(Path(ort.__file__).resolve()),numpy_origin=str(Path(np.__file__).resolve()),
        sherpa_origin=str(Path(sherpa.__file__).resolve()),binding_origin=str(binding_file),
        binding_sha256=_runtime_sha(binding_file),official_native_sha256=native,
        official_wheel_sha256=wheels,available_providers=providers,
        fresh_no_site=True,preloaded_modules_retained=True,version_or_module_rewritten=False,
        production_defaults_changed=False)
    print('EXPLICIT_RUNTIME_PROOF '+json.dumps(proof,sort_keys=True),file=sys.stderr,flush=True)
    return proof


'''


def build(source):
    for token in (OLD_GUARD, CLI_ANCHOR, OUTPUT_ANCHOR, 'MODEL_SHA = '):
        if source.count(token) != 1:
            raise ValueError('Reviewed parent diagnostic structure changed')
    result = source.replace(OLD_GUARD,NEW_GUARD)
    result = result.replace(CLI_ANCHOR,CLI_ANCHOR+CLI_EXTRA)
    result = result.replace(OUTPUT_ANCHOR,OUTPUT_EXTRA+OUTPUT_ANCHOR)
    return result.replace('MODEL_SHA = ',RUNTIME_GUARD+'MODEL_SHA = ',1)


def recover_original(source):
    return (source.replace(RUNTIME_GUARD,'',1).replace(NEW_GUARD,OLD_GUARD,1)
        .replace(CLI_ANCHOR+CLI_EXTRA,CLI_ANCHOR,1)
        .replace(OUTPUT_EXTRA+OUTPUT_ANCHOR,OUTPUT_ANCHOR,1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent-probe',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    raw = args.parent_probe.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PARENT_SHA256:
        raise ValueError('Original parent probe differs from the reviewed exact SHA')
    if args.output.resolve() == args.parent_probe.resolve() or args.output.exists():
        raise ValueError('Create a new independent diagnostic copy only')
    original = raw.decode('utf-8').replace('\r\n','\n')
    result = build(original)
    if recover_original(result) != original:
        raise ValueError('Diagnostic transform did not preserve all original source')
    compile(result,str(args.output),'exec')
    args.output.write_text(result,encoding='utf-8',newline='\n')
    print(hashlib.sha256(args.output.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
