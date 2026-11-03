#!/usr/bin/env python3
"""Add fully executed kernel/ZOCL reproduction to a new payload; preserve sealed v1."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=ROOT/'payload'
TARGET=ROOT/'payload_v2'
WORK=Path('/home/ghmd/kv260-runtime-reproduce-20261003c')
CROSS='/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def write(path,value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def main():
    states={phase:json.loads((WORK/'logs'/('zocl_'+phase)/'status.json').read_text())
            for phase in ['prepare','kernel','module']}
    if not all(v['passed'] for v in states.values()):
        raise RuntimeError('Kernel/ZOCL phases not complete')
    subprocess.run(['sha256sum','-c','--quiet',str(ORIGINAL/'SHA256SUMS')],cwd=str(ORIGINAL),check=True)
    if TARGET.exists():raise RuntimeError('Preserving existing v2')
    shutil.copytree(ORIGINAL,TARGET)
    # Keep the previous index as a historical input, rather than claim it covers v2.
    (TARGET/'SHA256SUMS').rename(TARGET/'evidence/v1_payload.sha256')
    for phase in states:
        source=WORK/'logs'/('zocl_'+phase)
        target=TARGET/'evidence/reproduction/c'/source.name
        shutil.copytree(source,target)
    shutil.copytree(WORK/'artifacts/zocl',TARGET/'host_rebuild/zocl')
    inputs=TARGET/'evidence/reproduction/c/kernel_inputs'
    inputs.mkdir()
    shutil.copy2(WORK/'build/kernel/.config',inputs/'resolved.config')
    shutil.copy2(WORK/'build/kernel/Module.symvers',inputs/'module.symvers')
    module=TARGET/'host_rebuild/zocl/zocl.ko'
    metadata={}
    for name in ['vermagic','srcversion','license']:
        metadata[name]=subprocess.check_output(['/sbin/modinfo','-F',name,str(module)],text=True).strip()
    (TARGET/'evidence/new_zocl_modinfo.log').write_text(
        subprocess.check_output(['/sbin/modinfo',str(module)],text=True))
    (TARGET/'evidence/new_zocl_undefined_symbols.log').write_text(
        subprocess.check_output([CROSS+'nm','-u',str(module)],text=True))
    versions=json.loads((TARGET/'config/source_lock.json').read_text())
    if versions['kernel_release'] not in metadata['vermagic']:
        raise RuntimeError('New ZOCL release mismatch')
    if metadata['srcversion']!=versions['candidate_zocl_srcversion']:
        raise RuntimeError('New ZOCL source version differs from reviewed candidate')
    previous_symvers='6e582b60f2a379055924117f930e5ca0fac44c98d56f3b374dc3ce278da7b8ed'
    symbol_versions=sha(WORK/'build/kernel/Module.symvers')
    new={str(p.relative_to(TARGET)):{'bytes':p.stat().st_size,'sha256':sha(p),'board_verified_this_run':False}
         for p in sorted((TARGET/'host_rebuild/zocl').iterdir()) if p.is_file()}
    summary=json.loads((TARGET/'evidence/verification_summary.json').read_text())
    summary.update(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   new_zocl_full_build_executed=True,new_kernel_full_build_executed=True,
                   kernel_jobs=8,zocl_prepare_and_module_jobs=4,
                   new_kernel_symvers_sha256=symbol_versions,
                   kernel_symvers_matches_prior=symbol_versions==previous_symvers,
                   new_zocl_metadata=metadata,new_zocl_artifacts=new,
                   new_zocl_matches_tested_input=sha(module)==versions['board_tested_binaries']['zocl.ko']['sha256'])
    summary['limitations']=[v for v in summary['limitations'] if
                            v!='New kernel/ZOCL wrapper not exercised through a complete build']
    summary['new_zocl_board_verified_this_run']=False
    summary['new_build_diagnostics']={
        phase:{'warning_lines':[line for path in (WORK/'logs'/('zocl_'+phase)).glob('*.log')
                                for line in path.read_text(errors='replace').splitlines() if 'warning:' in line.lower()]}
        for phase in states}
    write(TARGET/'evidence/verification_summary.json',summary)
    new_report=(
        '# 完整内核与 ZOCL 入口复验\n\n'
        '本次在独立工作区执行 prepare、kernel、module 三阶段并通过。'
        '完整 vmlinux/modules/Module.symvers 和新 ZOCL 均生成；没有安装或加载新内核/模块。\n\n'
        '内核并行 8；准备与模块编译并行 4。配置仅 CONFIG_CC_VERSION_TEXT 的 .real 文本差异；'
        'release 与原镜像匹配。上游源码与原封存证据保留。\n\n'
        '- 新模块 SHA-256：'+sha(module)+'\n'
        '- 新模块 srcversion：'+metadata['srcversion']+'\n'
        '- 新模块 vermagic：'+metadata['vermagic']+'\n'
        '- Kernel Module.symvers SHA-256：'+symbol_versions+'\n'
        '- 与旧内核符号表一致：'+str(symbol_versions==previous_symvers)+'\n'
        '- 与已板测修复模块逐字节一致：'+str(summary['new_zocl_matches_tested_input'])+'\n\n'
        '完整原始日志在 [evidence/reproduction/c](../evidence/reproduction/c/)。'
        '新模块属于本次主机输出；本次没有新的板测。启用仍使用 tested_inputs/ 中已板测输入，'
        '不要用编译成功替代实时预检和同图复验。\n')
    (TARGET/'docs/kernel_zocl_validation.md').write_text(new_report)
    doc=TARGET/'docs/reproducibility.md'
    text=doc.read_text()
    text=text.replace('**本次没有执行这三个 ZOCL 编译阶段。** 旧阶段完整执行并通过；新脚本完成语法和入口检查，移植入口还需在新工作区完整运行以验收。新模块生成后应重新审阅 modinfo、符号与板端结果，不能仅凭 vermagic 相同安装。',
        '**这三个 ZOCL 编译阶段已在本次独立工作区完整执行并通过。** 配置、Module.symvers、新模块 metadata/哈希及完整日志见 [kernel_zocl_validation.md](kernel_zocl_validation.md)。它仍不是陌生主机从零安装或本次板端加载验收。')
    doc.write_text(text)
    doc.write_text(doc.read_text()+
        '\n本包为完整主机复验后的 v2。evidence/v1_payload.sha256 是旧 v1 的输入索引，'
        '其相对路径属于封存 v1；请使用本包根目录的 SHA256SUMS 校验 v2。\n')
    doc=TARGET/'README.md'
    text=doc.read_text().replace('本次未重新构建完整内核或 ZOCL，尚未在陌生环境从零安装 SDK 复现；ZOCL 新入口仅完成语法与入口审阅，完整旧构建日志和模块证据保留。',
        '本次完整内核/ZOCL 新入口已在独立目录执行通过，见 [docs/kernel_zocl_validation.md](docs/kernel_zocl_validation.md)。尚未在陌生环境从零安装 SDK 复现；原构建与新构建日志均保留。')
    doc.write_text(text)
    doc=TARGET/'docs/collaboration_log.md'
    doc.write_text(doc.read_text()+
        '\n## 后续主机完整复验\n\n新的 ZOCL 复现入口在独立目录完成匹配内核准备、'
        '完整内核/模块依赖构建和 ZOCL 编译三阶段。先前注明的待执行项据实际日志更新；'
        '封存 v1 包保留。没有新增板端切换或推理成绩。\n')
    paths=[str(p.relative_to(TARGET)) for p in TARGET.rglob('*')]
    with tarfile.open(TARGET/'sources/xrt_baseline.tar.gz','r:gz') as packed:
        paths+=['xrt_archive/'+m.name for m in packed.getmembers()]
    invalid=[p for p in paths if any(not re.fullmatch(r'[A-Za-z0-9_.-]+',part) for part in Path(p).parts)]
    naming=json.loads((TARGET/'evidence/naming_review.json').read_text())
    naming.update(invalid_paths=invalid,english_ascii_paths_passed=not invalid,
                  uppercase_path_count=sum(any(c.isupper() for c in p) for p in paths))
    write(TARGET/'evidence/naming_review.json',naming)
    if invalid:raise RuntimeError('Unexpected v2 filename')
    broken=[]
    docs=[TARGET/'README.md',TARGET/'skill/README.md']
    docs+=list((TARGET/'docs').glob('*.md'))+list((TARGET/'skill/kv260-runtime-review').rglob('*.md'))
    for doc in docs:
        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)',doc.read_text()):
            if not link.startswith(('http://','https://','#')) and not (doc.parent/link.split('#')[0]).exists():
                broken.append({'document':str(doc.relative_to(TARGET)),'target':link})
    write(TARGET/'evidence/link_review.json',{'passed':not broken,'broken':broken})
    if broken:raise RuntimeError('Broken v2 links')
    files=[p for p in sorted(TARGET.rglob('*')) if p.is_file()]
    index=TARGET/'SHA256SUMS'
    index.write_text(''.join('{}  {}\n'.format(sha(p),p.relative_to(TARGET)) for p in files))
    subprocess.run(['sha256sum','-c','--quiet',str(index)],cwd=str(TARGET),check=True)
    archive=ROOT/'release/kv260_runtime_annex_verified_20261003.tar.gz'
    if archive.exists():raise RuntimeError('Preserving existing archive')
    with tarfile.open(archive,'w:gz') as packed:
        for path in sorted(TARGET.rglob('*')):
            if path.is_file():
                packed.add(path,arcname='kv260-runtime-annex/'+str(path.relative_to(TARGET)),recursive=False)
    with tarfile.open(archive,'r:gz') as packed:
        members={m.name:hashlib.sha256(packed.extractfile(m).read()).hexdigest() for m in packed.getmembers()}
    expected={'kv260-runtime-annex/'+str(p.relative_to(TARGET)):sha(p)
              for p in TARGET.rglob('*') if p.is_file()}
    if members!=expected:raise RuntimeError('v2 archive member mismatch')
    receipt={'passed':True,'payload_files_indexed':len(files),'archive_members_verified':len(members),
             'archive':str(archive),'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,
             'new_zocl':summary['new_zocl_artifacts'],'new_zocl_matches_tested_input':summary['new_zocl_matches_tested_input'],
             'kernel_symvers_matches_prior':summary['kernel_symvers_matches_prior'],
             'board_access':False}
    write(ROOT/'evidence/package_verified_v2.json',receipt)
    print(json.dumps(receipt))


if __name__=='__main__':
    main()
