"""Exact vendor NumPy metadata fixtures; never imports/executes NumPy."""
import builtins
import hashlib
import importlib.util
import json
from pathlib import Path
import types

import pytest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('assemble_numpy_metadata_fixture',HERE/'assemble_v2.py')
assembly=importlib.util.module_from_spec(spec);spec.loader.exec_module(assembly)
WRAPPER=json.loads((HERE/'actual_numpy_version_metadata.json').read_text(encoding='utf-8'))
MORE=json.loads((HERE/'actual_numpy_versioneer_metadata.json').read_text(encoding='utf-8'))['files']
ROOT='/usr/lib/python3.9/site-packages/numpy'


class Files:
    def __init__(self):
        self.data={row['path']:row['content'].encode() for row in [WRAPPER]+MORE}
        assert all(hashlib.sha256(self.data[row['path']]).hexdigest()==row['sha256'] for row in [WRAPPER]+MORE)
    def read(self,name,limit=65536,canonical=False):
        raw=self.data[name];assert len(raw)<=limit;return raw
    def tree(self,root):
        return {name[len(root)+1:]:{'bytes':len(raw),'sha256':assembly.digest(raw)}
                for name,raw in self.data.items() if name.startswith(root+'/')}


def test_actual_vendor_static_versioneer_and_egg_are_exact1212_and_do_not_import_numpy(monkeypatch):
    files=Files();original=builtins.__import__
    def guarded(name,*args,**kwargs):
        assert not name.startswith('numpy'),'NumPy import is forbidden during inspect'
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',guarded)
    result=assembly.dependency({'kind':'numpy','root':ROOT,'version':'1.21.2'},files)
    evidence=result['version_metadata']
    assert result['version']=='1.21.2' and evidence['kind']=='reviewed_static_versioneer_and_egg'
    assert evidence['sources']=={row['path']:row['sha256'] for row in [WRAPPER]+MORE}
    assert any(name.endswith('PKG-INFO') for name in evidence['sources'])


@pytest.mark.parametrize('name', ['version.py','_version.py','PKG-INFO'])
def test_any_reviewed_vendor_metadata_byte_change_refuses(name):
    files=Files();path=next(path for path in files.data if path.endswith('/'+name))
    files.data[path]+=b'\nchanged\n'
    with pytest.raises(assembly.Refused):assembly.numpy_version_metadata({'root':ROOT,'version':'1.21.2'},files)


@pytest.mark.parametrize('name', ['_version.py','PKG-INFO'])
def test_missing_vendor_or_egg_evidence_is_not_a_version_fallback(name):
    files=Files();path=next(path for path in files.data if path.endswith('/'+name));del files.data[path]
    with pytest.raises(KeyError):assembly.numpy_version_metadata({'root':ROOT,'version':'1.21.2'},files)


@pytest.mark.parametrize('value', ['1.21.1','1.21.2rc1','1.21.2+vendor','1.26.4','2.0.0'])
def test_other_requested_version_cannot_be_approved(value):
    with pytest.raises(assembly.Refused):assembly.numpy_version_metadata({'root':ROOT,'version':value},Files())


@pytest.mark.parametrize('text', ["version='1.21.2'\n", "version: str = '1.21.2'\nfull_version: str = '1.21.2'\n"])
def test_exact_literal_metadata_remains_supported_without_execution(text):
    files=Files();files.data[ROOT+'/version.py']=text.encode()
    value=assembly.numpy_version_metadata({'root':ROOT,'version':'1.21.2'},files)
    assert value['kind']=='static_literal' and value['version']=='1.21.2'


@pytest.mark.parametrize('text', [
    "version='1.26.4'\nfull_version='1.21.2'\n",
    "comment=\"version='1.21.2'\"\n",
    "version='1.21.2'\nversion='2.0.0'\n",
    "version=get_versions()['version']\n",
    "version='1.21.2'\nfull_version='1.21.2+vendor'\n",
])
def test_regex_lookalikes_conflicting_or_arbitrary_dynamic_versions_refused(text):
    files=Files();files.data[ROOT+'/version.py']=text.encode()
    with pytest.raises(assembly.Refused):assembly.numpy_version_metadata({'root':ROOT,'version':'1.21.2'},files)


def test_exact_original_e7df_script_and_final_policy_are_unchanged():
    assert hashlib.sha256((HERE/'assemble.py').read_bytes()).hexdigest()=='e7df025b3ae21ea0a82d16976bae5d767083aa424343cd1de32b817345c9324d'
    assert hashlib.sha256((HERE/'assembly_policy.v2.final.json').read_bytes()).hexdigest()=='ffa2f3b1c063c3af51006c622d81684fdeb37cf19d8c7b0ac063325d0581f9ea'
