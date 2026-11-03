"""Create a separate narrowly reviewed NumPy metadata parser variant."""
import ast
import hashlib
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE_SHA='e7df025b3ae21ea0a82d16976bae5d767083aa424343cd1de32b817345c9324d'
HELPER='''def numpy_version_metadata(spec,files):
    """Static data only: never import/exec NumPy or Versioneer source."""
    expected=spec['version'];need(expected=='1.21.2','original_numpy_1212_required')
    version_path=join(spec['root'],'version.py')
    raw=files.read(version_path,65536,canonical=True)
    module=ast.parse(raw.decode('utf-8'))
    assignments={}
    for node in module.body:
        if isinstance(node,ast.Assign):targets=node.targets;value=node.value
        elif isinstance(node,ast.AnnAssign):targets=[node.target];value=node.value
        else:continue
        for target in targets:
            if isinstance(target,ast.Name) and target.id in ('version','full_version'):
                need(target.id not in assignments,'ambiguous_numpy_version_assignment')
                assignments[target.id]=value
    literal=assignments.get('version')
    if isinstance(literal,ast.Constant) and isinstance(literal.value,str):
        need(literal.value==expected,'numpy_version_metadata_changed')
        if 'full_version' in assignments:
            full=assignments['full_version']
            need(isinstance(full,ast.Constant) and full.value==expected,'conflicting_numpy_full_version')
        return {'kind':'static_literal','version':expected,'sources':{version_path:digest(raw)}}
    # This is the exact already-running board vendor wrapper, not a generic
    # permission to resolve arbitrary imports, calls or dynamic expressions.
    need(spec['root']=='/usr/lib/python3.9/site-packages/numpy'
         and digest(raw)=='f89c73ddd072eb0eb166095f2b8238bfb0a7baec6f1a63545e8e42ad55ba2314',
         'unreviewed_numpy_versioneer_wrapper')
    source_path=join(spec['root'],'_version.py')
    source=files.read(source_path,65536,canonical=True)
    need(digest(source)=='db1df0c97f67f72e474f2dbd77e4a2b049727c20e556fd1c24e988d41dbf3841',
         'reviewed_numpy_versioneer_source_changed')
    body=ast.parse(source.decode('utf-8')).body
    need(len(body)==3 and isinstance(body[0],ast.Import)
         and [(a.name,a.asname) for a in body[0].names]==[('json',None)]
         and isinstance(body[1],ast.Assign) and len(body[1].targets)==1
         and isinstance(body[1].targets[0],ast.Name) and body[1].targets[0].id=='version_json'
         and isinstance(body[1].value,ast.Constant) and isinstance(body[1].value.value,str),
         'numpy_versioneer_static_literal_required')
    expected_function=ast.parse('def get_versions():\\n    return json.loads(version_json)\\n').body[0]
    need(ast.dump(body[2],include_attributes=False)==ast.dump(expected_function,include_attributes=False),
         'numpy_versioneer_dynamic_function_refused')
    info=parse(body[1].value.value.encode('utf-8'))
    need(info.get('version')==expected and info.get('dirty') is False and info.get('error') is None,
         'numpy_versioneer_version_not_exact_1212')
    pkg_path=str(PurePosixPath(spec['root']).parent/'numpy-1.21.2-py3.9.egg-info/PKG-INFO')
    pkg=files.read(pkg_path,65536,canonical=True)
    need(digest(pkg)=='c29a04ebcd5571a84b995ceb79ab86f89bde0f8a0b5413c81c357ab72ed15352',
         'reviewed_numpy_egg_metadata_changed')
    metadata=BytesParser().parsebytes(pkg)
    need(metadata.get_all('Name')==['numpy'] and metadata.get_all('Version')==[expected],
         'numpy_versioneer_egg_version_mismatch')
    return {'kind':'reviewed_static_versioneer_and_egg','version':expected,
            'sources':{version_path:digest(raw),source_path:digest(source),pkg_path:digest(pkg)}}


'''


def build():
    original=(HERE/'assemble.py').read_bytes()
    if hashlib.sha256(original).hexdigest()!=BASE_SHA:raise ValueError('Exact e7df source required')
    text=original.decode('utf-8')
    result=text.replace('import argparse\n','import argparse\nimport ast\nfrom email.parser import BytesParser\n',1)
    start=result.index("    if kind=='numpy':\n",result.index('def dependency('))
    end=result.index('    else:\n',start)
    old=result[start:end]
    result=result[:start]+"    version_evidence=None\n    if kind=='numpy':\n        version_evidence=numpy_version_metadata(spec,files)\n"+result[end:]
    old_return="    return {'kind':kind,'version':version,'root':spec['root'],'files':tree,'tree_sha256':digest(encoded(tree))}\n"
    new_return="    result={'kind':kind,'version':version,'root':spec['root'],'files':tree,'tree_sha256':digest(encoded(tree))}\n    if version_evidence is not None:result['version_metadata']=version_evidence\n    return result\n"
    if result.count(old_return)!=1:raise ValueError('Exact dependency return required')
    result=result.replace(old_return,new_return,1).replace('def dependency(spec,files):\n',HELPER+'def dependency(spec,files):\n',1)
    ast.parse(result,feature_version=(3,9))
    # Exact reconstruction proves every unrelated assembler byte is retained.
    recovered=result.replace(HELPER,'',1).replace('import argparse\nimport ast\nfrom email.parser import BytesParser\n','import argparse\n',1)
    recovered=recovered.replace("    version_evidence=None\n    if kind=='numpy':\n        version_evidence=numpy_version_metadata(spec,files)\n",old,1).replace(new_return,old_return,1)
    if recovered.encode()!=original:raise ValueError('Unrelated source bytes changed')
    target=HERE/'assemble_v2.py'
    with target.open('xb') as out:out.write(result.encode())
    return hashlib.sha256(result.encode()).hexdigest()


if __name__=='__main__':print(build())
