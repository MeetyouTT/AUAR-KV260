from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
root=Path(__file__).resolve().parent.parent;q=root/'verification';folder=Path.home()/'下载/AUAR_方案A源码交付_9a4f_20261103';stage=folder.with_name('.auar-9a4f-verified-01a1a08b')
def note(status,phase,**more):
 p=q/'publication-retry-state.tmp';v=dict(status=status,phase=phase,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**more);p.write_text(json.dumps(v,ensure_ascii=False,indent=2));os.replace(str(p),str(q/'release_state.json'));print(v,flush=True)
try:
 if folder.is_symlink() or not folder.is_dir() or any(folder.iterdir()) or folder.stat().st_uid!=os.getuid() or stage.exists():raise ValueError('Unexpected publication directory state')
 note('RUNNING','reverify_and_publish_final_archive')
 x=Path.home()/'Xilinx_2022.2';rar=Path.home()/'auar-engineering-delivery-XpV7MC/rar-tool/usr/bin/rar'
 args=[sys.executable,'-B',str(root/'operations/final_roundtrip_retry.py'),str(root/'auar_xuefei'),str(q),str(stage),str(rar),str(x/'Vivado/2022.2'),str(x/'Vitis/2022.2')]
 with (q/'final_archive_retry.log').open('xb') as f:p=subprocess.run(args,cwd=str(root),stdout=f,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError('Acceptance retry failed, see final_archive_retry.log')
 rec=json.loads((stage/'archive_verification.json').read_text())
 if hashlib.sha256((stage/rec['archive']).read_bytes()).hexdigest()!=rec['sha256'] or rec['status']!='PASS':raise RuntimeError('Output hash mismatch')
 if folder.is_symlink() or any(folder.iterdir()):raise RuntimeError('Delivery directory changed during validation')
 os.rename(str(stage),str(folder))
 note('PASS','published',path=str(folder),rar_bytes=rec['bytes'],sha256=rec['sha256'])
except Exception as e:
 note('FAIL','publication_retry_action_required',error=str(e));raise
