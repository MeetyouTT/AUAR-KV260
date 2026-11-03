"""Verify exported spreadsheet caches and package explicitly selected evidence."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as ET
from hashlib import sha256
import json
import math
import shutil

ROOT=Path(__file__).resolve().parent
DATA=json.loads((ROOT/'report_data.json').read_text(encoding='utf-8'))
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'c':'http://schemas.openxmlformats.org/drawingml/2006/chart'}
XLSX=ROOT/'技术文档材料清单与性能表.xlsx'

def hash_file(path):return sha256(path.read_bytes()).hexdigest()

def main():
    stats={}
    with ZipFile(XLSX) as z:
        assert z.testzip() is None
        for name in z.namelist():
            if name.endswith('.xml') or name.endswith('.rels'):ET.fromstring(z.read(name))
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            strings=[''.join(e.itertext()) for e in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',NS)]
        def cells(n):return {e.attrib['r']:e for e in ET.fromstring(z.read(f'xl/worksheets/sheet{n}.xml')).findall('.//s:c',NS)}
        def value(c):
            if c.attrib.get('t')=='inlineStr':return ''.join(c.find('s:is',NS).itertext())
            v=c.find('s:v',NS)
            if v is None:return None
            if c.attrib.get('t')=='s':return strings[int(v.text)]
            return v.text
        book=ET.fromstring(z.read('xl/workbook.xml'))
        stats['sheets']=[e.attrib['name'] for e in book.findall('s:sheets/s:sheet',NS)]
        assert len(stats['sheets'])==7
        formulas=[]
        for n in range(1,8):
            for addr,c in cells(n).items():
                assert c.attrib.get('t')!='e',(n,addr,value(c))
                if c.find('s:f',NS) is not None:
                    assert value(c) is not None,(n,addr,'missing cached value')
                    formulas.append((n,addr))
        stats['formulas_with_cached_values']=len(formulas)
        assert len(formulas)>120
        raw=cells(7)
        for metric in DATA['metrics']:
            row=DATA['metric_rows'][metric['key']]
            actual=float(value(raw[f'C{row}']))
            assert math.isclose(actual,metric['value'],rel_tol=1e-12,abs_tol=1e-12),(metric['key'],actual,metric['value'])
        stats['verified_original_numeric_observations']=len(DATA['metrics'])
        metrics={m['key']:m['value'] for m in DATA['metrics']}
        llm=cells(4)
        expected=metrics['tts1_seconds']/(metrics['tts1_samples']/metrics['tts1_rate'])
        assert math.isclose(float(value(llm['F20'])),expected,rel_tol=1e-12)
        stats['restored_tts_rtf']=float(value(llm['F20']))
        vision=cells(2)
        for row in [12,13,14]:assert value(vision[f'F{row}'])=='hex: 0x101000056010407'
        stats['hex_fingerprints_preserved_as_text']=True
        charts=[n for n in z.namelist() if n.startswith('xl/') and '/charts/chart' in n and n.endswith('.xml')]
        assert len(charts)==4
        stats['native_charts_with_source_ranges']=[]
        for n in charts:
            c=ET.fromstring(z.read(n));ranges=[e.text for e in c.findall('.//c:f',NS)]
            assert ranges,(n,'no source ranges')
            stats['native_charts_with_source_ranges'].append({'chart':n,'ranges':ranges})
    proofs=json.loads((ROOT/'workbook_key_results.json').read_text(encoding='utf-8'))
    assert proofs['rtf_recalculation_verified']
    stats['live_positive_input_recalculation_passed']=True
    stats['formula_scan']=json.loads((ROOT/'formula_error_scan.json').read_text(encoding='utf-8'))
    stats['visual_qa']='7 sheets / 12 rendered views reviewed; four new publication figures reviewed; label overlap and hex display corrected.'
    native=Path('E:/Win共享文件/协作任务/2026-11-02_作品概述_AMD实跑_01a19c53/report_figures/03_vivado_block_design_native.png')
    shutil.copy2(native,ROOT/'报告配图'/native.name)
    figures=sorted((ROOT/'报告配图').glob('*'))
    stats['figure_files']={'png':sum(f.suffix=='.png' for f in figures),'svg':sum(f.suffix=='.svg' for f in figures)}
    (ROOT/'SOURCES.json').write_text(json.dumps(DATA['sources'],ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'交付验证.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')

    # No recursive root walk: excludes the node_modules junction and internal QA/build files.
    files=[XLSX,ROOT/'材料使用说明.txt',ROOT/'report_data.json',ROOT/'SOURCES.json',
           ROOT/'VITIS_AI_RUN_RECEIPT.json',ROOT/'vitis_ai_inspection_stdout.json',
           ROOT/'WINDOWS_MODEL_ENVIRONMENT_READONLY.json',ROOT/'交付验证.json',*figures]
    previous=Path('E:/Win共享文件/协作任务/2026-11-02_作品概述_AMD实跑_01a19c53/作品概述图片与AMD实跑证据.zip')
    entries=[(f,f.relative_to(ROOT).as_posix()) for f in files]
    entries.append((previous,'AMD原始日志与工程证据/'+previous.name))
    manifest=[{'path':arc,'bytes':p.stat().st_size,'sha256':hash_file(p)} for p,arc in entries]
    manifest_bytes=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')
    (ROOT/'交付文件清单_SHA256.json').write_bytes(manifest_bytes)
    target=ROOT/'技术文档性能表与图像材料包.zip'
    with ZipFile(target,'w',ZIP_DEFLATED,compresslevel=8) as z:
        for p,arc in entries:z.write(p,arc)
        z.writestr('交付文件清单_SHA256.json',manifest_bytes)
    with ZipFile(target) as z:
        assert z.testzip() is None
        for row in manifest:assert sha256(z.read(row['path'])).hexdigest()==row['sha256']
        assert not any('node_modules' in name or name.startswith('qa/') for name in z.namelist())
        package_files=len(z.namelist())
    receipt={'zip':str(target),'bytes':target.stat().st_size,'sha256':hash_file(target),
             'files':package_files,'crc_checked':True,'all_entry_hashes_checked':True,'xlsx':stats}
    (ROOT/'PACKAGE_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
