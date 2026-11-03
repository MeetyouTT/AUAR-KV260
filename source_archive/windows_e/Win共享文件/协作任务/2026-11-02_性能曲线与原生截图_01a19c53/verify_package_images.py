from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from hashlib import sha256
from PIL import Image,ImageChops
import json,csv

ROOT=Path(__file__).resolve().parent

def main():
    figures=sorted((ROOT/'性能曲线').glob('*'))
    shots=sorted((ROOT/'原生截图').glob('*.png'))
    assert len([p for p in figures if p.suffix=='.png'])==11
    assert len([p for p in figures if p.suffix=='.svg'])==11
    assert len(shots)==8
    for path in [*shots,*[p for p in figures if p.suffix=='.png']]:
        with Image.open(path) as im:im.verify()
    proof={}
    for full,detail in [('02_xsim_native_wave','02b_xsim_wave_detail'),('03_vivado_timing','03b_vivado_timing_summary_detail'),('04_vivado_resources','04b_vivado_resource_table_and_chart')]:
        meta=json.loads((ROOT/'原生截图'/(detail+'.json')).read_text(encoding='utf-8'))
        x,y,w,h=meta['window_region']
        original=Image.open(ROOT/'原生截图'/(full+'.png')).convert('RGB').crop((x,y,x+w,y+h))
        actual=Image.open(ROOT/'原生截图'/(detail+'.png')).convert('RGB')
        same=ImageChops.difference(original,actual).getbbox() is None
        assert same,(full,detail,'region pixels differ from full capture')
        proof[detail]={'matches_full_capture_pixels':same,'region':[x,y,w,h]}
    rows=list(csv.DictReader((ROOT/'数据'/'DPU视觉_360个原始采样点.csv').open(encoding='utf-8-sig')))
    pairs=list(csv.DictReader((ROOT/'数据'/'SFace_1000对公开测试_逐对分数.csv').open(encoding='utf-8-sig')))
    assert len(rows)==360 and len(pairs)==1000 and rows[0]['cpu_percent']==''
    assert sum(int(r['fp32_correct']) for r in pairs)==988
    assert sum(int(r['int8_simulation_correct']) for r in pairs)==988
    metrics=json.loads((ROOT/'数据'/'计算结果.json').read_text(encoding='utf-8'))
    mean=sum(float(r['yunet_latest_full_path_ms']) for r in rows)/len(rows)
    assert abs(mean-metrics['board_observation']['snapshot_latency_mean_ms'])<1e-10
    status=(ROOT/'原生截图'/'report_gui_status.txt').read_text(encoding='utf-8')
    assert 'GUI_REPORTS_READY' in status and 'FAILED' not in status
    result={'performance_png':11,'performance_svg':11,'actual_ubuntu_screenshots':8,
            'board_observation_points':360,'public_test_pairs':1000,'source_statistics_recomputed_and_checked':True,
            'native_detail_pixel_integrity':proof,'vivado_gui_reports_ready':True,
            'new_model_inference':False,'board_accessed':False,
            'visual_review':'Eight newly generated curves reviewed; native wave, timing, resource images reviewed; three reused figures were previously reviewed.'}
    (ROOT/'图片交付验证.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    files=[*figures,*shots,*sorted((ROOT/'原生截图').glob('*.json')),ROOT/'原生截图'/'report_gui_status.txt',
           *sorted((ROOT/'数据').glob('*')),ROOT/'曲线来源与图注.json',ROOT/'UBUNTU_CURVE_RUN_RECEIPT.json',
           ROOT/'图片索引与图注.txt',ROOT/'图片交付验证.json',ROOT/'generate_curves.py',ROOT/'run_ubuntu_curves.py']
    assert len(files)==len(set(files))
    manifest=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha256(p.read_bytes()).hexdigest()} for p in files]
    manifest_bytes=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')
    (ROOT/'图片文件清单_SHA256.json').write_bytes(manifest_bytes)
    target=ROOT/'性能曲线与原生截图_可插入报告.zip'
    with ZipFile(target,'w',ZIP_DEFLATED,compresslevel=8) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
        z.writestr('图片文件清单_SHA256.json',manifest_bytes)
    with ZipFile(target) as z:
        assert z.testzip() is None
        for r in manifest:assert sha256(z.read(r['path'])).hexdigest()==r['sha256']
        count=len(z.namelist())
    receipt={'zip':str(target),'bytes':target.stat().st_size,'files':count,'sha256':sha256(target.read_bytes()).hexdigest(),'crc_and_all_entry_hashes_checked':True,**result}
    (ROOT/'IMAGE_PACKAGE_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
