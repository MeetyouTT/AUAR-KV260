from common import *
name='auar_wide_source_routed.dcp'
d=OUT/name; temp=OUT/(name+'.partial')
r=load(ROOT/'build/reports/clean_directory_validation.json')
expected=r['routed_checkpoint_sha256']
source='/home/ghmd/aura-pan-wide-20261028/implementation/source_routed.dcp'
if not d.is_file() or sha(d)!=expected:
    subprocess.run(['scp','-q','aura-ubuntu:'+source,str(temp)],check=True)
    assert sha(temp)==expected
    with zipfile.ZipFile(temp)as z:
        assert z.testzip() is None and 'dcp.xml' in [x.rsplit('/',1)[-1] for x in z.namelist()],z.namelist()[:10]
    temp.replace(d)
save(QA/'routed_checkpoint.json',dict(name=name,bytes=d.stat().st_size,sha256=expected,original_path=source,archive_crc='PASS',fresh_export='PASS',firmware_files_byte_identical=r['firmware_files_byte_identical']))
print(d.name,d.stat().st_size,expected)
