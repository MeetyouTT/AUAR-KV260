from pathlib import Path
import collections
import datetime as dt
import hashlib
import json
import posixpath
import re
import sqlite3
import statistics
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from build_documents import blocks, clean
from collect_evidence import OUT, WORK, public_text
from audit_history import user_text

sha=lambda b:hashlib.sha256(b).hexdigest()
flat=lambda s:re.sub(r'\s+','',clean(s))


def main():
    checks=[];metrics=[]
    def check(name,condition,detail=None):
        checks.append({'check':name,'passed':bool(condition),'detail':detail})
    rs=[json.loads(l) for l in (OUT/'conversations_full.jsonl').open()]
    h=sqlite3.connect('file:/home/ghmd/.codex/thread_history_1.sqlite?mode=ro',uri=True)
    for r in rs:
        row=h.execute('select item_json from thread_items where thread_id=? and turn_id=? and item_id=?',(r['thread_id'],r['turn_id'],r['item_id'])).fetchone()
        check('source_message_json_'+r['item_id'],row is not None and sha(row[0].encode())==r['source_item_json_sha256'])
        ob=json.loads(row[0]);text=user_text(ob) if r['role']=='user' else ob.get('text','')
        expected=public_text(text)
        if r['selection_id']=='q21':expected=re.sub(r'34BZNXC|JoneNik\S*','[设备名已脱敏]',expected)
        check('source_and_export_text_'+r['item_id'],sha(text.encode())==r['source_text_sha256'] and expected==r['text'] and sha(r['text'].encode())==r['export_text_sha256'])
    check('message_counts',len(rs)==67 and len({r['selection_id'] for r in rs})==22 and len({r['item_id'] for r in rs})==67)
    idx=json.loads((OUT/'source_index.json').read_text());entries=idx['entries']
    for e in entries:
        path=Path(e['source_path'])
        if e.get('archive_member'):
            with zipfile.ZipFile(path) as z:b=z.read(e['archive_member'])
        else:b=path.read_bytes()
        check('source_sha_'+e['evidence_id'],sha(b)==e['source_sha256'])
        if e.get('snapshot'):
            check('snapshot_sha_'+e['evidence_id'],sha((OUT/e['snapshot']).read_bytes())==e['snapshot_sha256'])
    check('source_counts',len(entries)==74 and sum(bool(e.get('snapshot')) for e in entries)==36 and idx['historical_index_verified']==38 and idx['historical_mismatches']==0)
    mainmd=(OUT/'ai_collaboration_record.md').read_text()
    check('ten_engineering_cases',len(re.findall(r'^## \d+\. C\d{2}：',mainmd,re.M))==10)
    corpus='\n'.join(r['text'] for r in rs)+'\n'+'\n'.join((OUT/e['snapshot']).read_text() for e in entries if e.get('snapshot'))
    quotes=[re.sub(r'^> ?', '',l) for l in mainmd.splitlines() if l.startswith('>')]
    for i,q in enumerate(quotes,1):check('main_quote_'+str(i),flat(q) in flat(corpus),{'quote':q})
    root=Path('/home/ghmd/auar-scheme-a-9a4f-20261103-01a1a08b/auar_xuefei/report/evidence')
    hp=root/'hardware_results.json';hw=json.loads(hp.read_text())
    check('fresh_hardware_metrics',hw['timing']['WNS_ns']==.002 and hw['timing']['WHS_ns']==.01 and hw['timing']['TNS_ns']==0 and hw['timing']['THS_ns']==0 and hw['implementation']['drc_errors']==0 and hw['route']['fully routed nets']==199333 and hw['route']['nets with routing errors']==0 and not hw['implementation']['board_verified'])
    metrics.append({'source':str(hp),'sha256':sha(hp.read_bytes()),'scope':'saved build result, no new synthesis or board execution','values':{k:hw[k] for k in ['implementation','timing','route','utilization']}})
    rp=root/'rtl_xsim.json';rtl=json.loads(rp.read_text())
    check('saved_rtl_result',len(rtl['tests'])==4 and sum(len(t['stages']) for t in rtl['tests'])==12 and all(s['exit_code']==0 for t in rtl['tests'] for s in t['stages']) and not rtl['board_verified'])
    metrics.append({'source':str(rp),'sha256':sha(rp.read_bytes()),'tests':4,'stages':12,'scope':'saved XSim result, not rerun'})
    def source_json(eid):
        e=next(e for e in entries if e['evidence_id']==eid)
        return json.loads(Path(e['source_path']).read_text())
    sf=source_json('E09');a=sf['models']['fp32']['held_out_at_train_selected_threshold'];b=sf['models']['int8_simulation']['held_out_at_train_selected_threshold']
    check('sface_quality_numbers',a['accuracy']==b['accuracy']==.988 and a['false_accepts']==0 and b['false_accepts']==1 and a['false_rejects']==12 and b['false_rejects']==11)
    yn=source_json('E10')['thresholds']['0.6'];check('yunet_agreement_numbers',yn['counts']['matched_iou_ge_05']==316 and yn['counts']['reference_faces']==322 and round(100*316/322,2)==98.14)
    pair=source_json('E17');medians={}
    for variant in ['current','compact']:
        xs=[x for x in pair['cases'] if x['variant']==variant]
        medians[variant]={key:round(statistics.median(x[key] for x in xs),2) for key in ['first_reply_ms','speech_ready_ms','total_ms']}
        check('llm_medians_'+variant,len(xs)==4 and medians[variant]==pair['summary'][variant])
    metrics.append({'evidence_id':'E17','recomputed_medians':medians,'scope':'read saved cases only, no new inference'})
    jr=ET.parse(next(e['source_path'] for e in entries if e['evidence_id']=='E19')).getroot()
    suites=[x for x in jr.iter('testsuite')]
    check('saved_junit_result',sum(int(x.attrib.get('tests',0)) for x in suites)==637 and sum(int(x.attrib.get('failures',0))+int(x.attrib.get('errors',0)) for x in suites)==0)
    gpu=source_json('E20');check('saved_gpu_free_memory',gpu['observed_min_free_mib']==1656 and not gpu['physical_playback'])
    pynq=source_json('E30');check('pynq_validation_scope',pynq['unit_tests']['tests']==15 and pynq['total_simulated_cases']==73 and not pynq['pynq_runtime_verified'] and not pynq['board_verified'] and not pynq['cross_board_verified'] and not pynq['non_author_reuse_verified'])
    retention=source_json('E23');check('retention_scope',retention['status']=='STORAGE_PASS_RECALL_PENDING' and retention['baseline_body_rows']==[1,1] and retention['after_body_rows']==[0,0] and not retention['actual_prompt_retrieval_observed'])
    for folder,name,expected_size in [('AUAR_方案A源码交付_9a4f_20261103','auar_xuefei_source.rar',44475833),('AUAR_上板资料扩充_9a4f_20261103','auar_xuefei_board_enhanced.rar',56970807)]:
        p=Path('/home/ghmd/下载')/folder/name;receipt=json.loads((p.parent/'archive_verification.json').read_text())
        expected_sha=receipt.get('sha256') or receipt.get('archive',{}).get('sha256')
        check('rar_identity_'+name,p.stat().st_size==expected_size and sha(p.read_bytes())==expected_sha)
    doc=OUT/'ai_collaboration_record.docx'
    with zipfile.ZipFile(doc) as z:
        check('docx_crc',z.testzip() is None)
        names=set(z.namelist())
        for n in sorted(names):
            if n.endswith('.xml') or n.endswith('.rels'):ET.fromstring(z.read(n))
        document=ET.fromstring(z.read('word/document.xml'))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        actual=''.join(x.text or '' for x in document.findall('.//w:t',ns))
        wanted=''.join(''.join(clean(c) for row in v for c in row) if t=='table' else clean(v) for t,v in blocks(mainmd) if t!='pagebreak')
        check('docx_body_text',flat(actual)==flat(wanted))
        styles=ET.fromstring(z.read('word/styles.xml'))
        check('docx_no_duplicate_paragraph_properties',all(len([x for x in p if x.tag.endswith('}spacing')])<=1 for p in styles.findall('.//w:pPr',ns)))
        relns={'p':'http://schemas.openxmlformats.org/package/2006/relationships'}
        targets=[]
        for rel in ET.fromstring(z.read('word/_rels/document.xml.rels')).findall('p:Relationship',relns):
            targets.append(posixpath.normpath('word/'+rel.attrib['Target']))
        check('docx_relationship_targets',all(t in names for t in targets))
    pdfs=[]
    for name,expected_pages in [('ai_collaboration_record.pdf',15),('conversation_records.pdf',23)]:
        p=OUT/name
        res=subprocess.run(['pdftotext','-layout',str(p),'-'],capture_output=True,text=True,check=True)
        text=res.stdout;pages=[x for x in text.split('\f') if x.strip()]
        check('pdf_page_count_'+name,len(pages)==expected_pages,{'pages':len(pages)})
        check('pdf_no_empty_or_replacement_'+name,all(len(x.strip())>40 for x in pages) and '\ufffd' not in text)
        bbox=subprocess.run(['pdftotext','-bbox',str(p),'-'],capture_output=True,text=True,check=True)
        dom=ET.fromstring(bbox.stdout);bad=[]
        for word in dom.iter():
            if word.tag.endswith('}word') or word.tag=='word':
                x0,y0,x1,y1=[float(word.attrib[k]) for k in ['xMin','yMin','xMax','yMax']]
                if x0<35 or y0<20 or x1>560 or y1>825:bad.append([x0,y0,x1,y1])
        check('pdf_text_bounds_'+name,not bad,{'out_of_bounds_words':len(bad)})
        if name.startswith('ai_'):
            # -layout interleaves adjacent table columns; raw stream order keeps
            # complete cell paragraphs contiguous for lossless coverage checks.
            raw_text=subprocess.run(['pdftotext','-raw',str(p),'-'],capture_output=True,text=True,check=True).stdout
            missing=[]
            for typ,val in blocks(mainmd):
                if typ=='pagebreak':continue
                pieces=[c for row in val for c in row] if typ=='table' else [val]
                for x in pieces:
                    if flat(x) not in flat(raw_text):missing.append(x[:100])
            check('main_pdf_text_coverage',not missing,{'missing_blocks':missing})
        else:check('all_question_ids_in_pdf',all('Q%02d'%i in text for i in range(1,23)))
        pdfs.append({'path':name,'pages':len(pages),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())})
    scanpaths=[p for p in OUT.rglob('*') if p.is_file() and p.suffix in ['.md','.json','.jsonl','.csv','.txt','.xml']]
    suspected=[]
    for p in scanpaths:
        s=p.read_text(encoding='utf-8-sig')
        for pat in [r'\bsk-[A-Za-z0-9_-]{20,}',r'\bghp_[A-Za-z0-9]{20,}',r'\bgithub_pat_[A-Za-z0-9_]{20,}']:
            if re.search(pat,s):suspected.append(str(p.relative_to(OUT)))
    check('no_obvious_credentials',not suspected,{'suspected_files':suspected})
    check('no_private_database_or_media_files',not any(p.suffix.lower() in ['.sqlite','.db','.wav','.mp3','.pcm','.jpg','.jpeg'] for p in OUT.rglob('*') if p.is_file()))
    check('english_output_names',all(re.fullmatch(r'[a-z0-9_.-]+',p.name) for p in OUT.rglob('*')))
    result={'schema':'auar-ai-collaboration-validation-v1','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'PASS' if all(x['passed'] for x in checks) else 'FAIL','checks_total':len(checks),'checks_passed':sum(x['passed'] for x in checks),'source_entries':len(entries),'standalone_snapshots':36,'historical_expected_sha_matches':38,'original_database_messages_verified':len(rs),'conversation_selections':22,'engineering_cases':10,'pdfs':pdfs,'metric_rechecks':metrics,'docx_office_opened':False,'visual_review':{'method':'Poppler page renders and contact-sheet layout inspection, plus full text readback and bounding-box checks','main_pages_inspected':15,'transcript_pages_inspected':23},'new_engineering_or_model_or_board_tests':False,'checks':checks}
    (OUT/'checks/validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ['checks','metric_rechecks']},ensure_ascii=False))
    for x in checks:
        if not x['passed']:print('FAIL',json.dumps(x,ensure_ascii=False))
    if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
