from common import *
import tempfile
with tempfile.TemporaryDirectory(prefix='stage_check_',dir=QA) as tmp:
    r=subprocess.run([sys.executable,'-B',str(ROOT/'board/scripts/stage.py'),'--audio',str(OUT/'auar_board_audio_dependencies.zip'),'--out',str(Path(tmp)/'board_fs')],capture_output=True)
    (QA/'windows_stage_with_audio.txt').write_bytes(r.stdout+r.stderr)
    print(r.returncode,(r.stdout+r.stderr).decode(errors='replace')[-480:])
    if r.returncode:sys.exit(r.returncode)
    rf=Path(tmp)/'board_fs'
    sources=load(ROOT/'models/board_audio_dependencies.json')
    paths=load(ROOT/'src/software/config/board_avatar_gtk.json')['board_business']
    groups={'asr':paths['asr_directory'],'frontend':paths['frontend_directory'],'speaker':paths['speaker']['model_directory'],'wheels_arm64':'/opt/auar/wheels'}
    for f in sources:
        group,name=f['path'].split('/',1);target=rf/groups[group].lstrip('/')/name
        assert sha(target)==f['sha256'],name
    save(QA/'audio_stage_verification.json',{'result':'PASS','audio_files_matched':len(sources),'rootfs_files':sum(p.is_file() for p in rf.rglob('*')),'live_device_access':False})
# The skill bundle preserves the documented relative paths. Includes samples only.
pack=OUT/'auar_skills.zip'
with zipfile.ZipFile(pack,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7)as z:
    for p in sorted((ROOT/'skill').rglob('*')):
        if p.is_file():z.write(p,p.relative_to(ROOT))
with zipfile.ZipFile(pack)as z:
    assert z.testzip() is None
    for n in z.namelist():
        assert hashlib.sha256(z.read(n)).hexdigest()==sha(ROOT/n)
save(QA/'skills_archive.json',{'status':'PASS','bytes':pack.stat().st_size,'sha256':sha(pack),'scope':'three project skills and optional generic PYNQ supplement'})
