"""Reproducible local source merge; no app/model/DB/device construction."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'resume_yuki_business_candidate_v2/candidate/aura'
FRESH=HERE/'fresh/aura'
DEST=HERE/'candidate/aura'


def digest(raw):return hashlib.sha256(raw).hexdigest()
def replace_once(text,old,new):
    if text.count(old)!=1:raise ValueError('Expected exactly one source insertion: '+old[:65])
    return text.replace(old,new)
def source_node(text,name,cls=None):
    tree=ast.parse(text)
    body=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name==cls).body if cls else tree.body
    node=next(x for x in body if isinstance(x,(ast.FunctionDef,ast.ClassDef)) and x.name==name)
    return ast.get_source_segment(text,node)


def gtk():
    text=(BASE/'tools/board_avatar_gtk.py').read_text(encoding='utf8')
    actual=(FRESH/'tools/board_avatar_gtk.py').read_text(encoding='utf8')
    for name in ('build_window','refresh_runtime','refresh_settings'):
        text=replace_once(text,source_node(text,name,'BoardAvatarStage'),source_node(actual,name,'BoardAvatarStage'))
    text=replace_once(text,source_node(text,'main'),source_node(actual,'main'))
    for old,new in (
        ('self.root = Path(root).resolve(strict=True)',"self.root = Path(config['formal_stage_root']).resolve(strict=True)"),
        ("self.rect = avatar_board.contain_rect(464, 480, self.geometry['w'], self.geometry['h'])", "self.rect = dict(x=0, y=0, w=self.geometry['w'], h=self.geometry['h'])"),
        ('from tools.yuki_business_candidate import prepare_pair','from tools.formal_yuki import prepare_pair'),
        ("SettingsStore(settings_file or AURA.parent/'avatar_user_settings.json')","SettingsStore(settings_file or Path(config['formal_settings_paths']['user']))"),
        ("TranscriptionStore(AURA.parent/'avatar_transcription_settings.json')","TranscriptionStore(Path(config['formal_settings_paths']['transcription']))"),
        ("TranscriptionStore(AURA.parent/'avatar_conversation_settings.json')","TranscriptionStore(Path(config['formal_settings_paths']['conversation']))"),
        ("ConnectionStore(AURA.parent/'avatar_service_settings.json', defaults['connection'])","ConnectionStore(Path(config['formal_settings_paths']['service']), defaults['connection'])"),
        ('from tools.yuki_business_gui import prepare_board_business','from tools.production_board_business_gui import prepare_board_business'),
        ('from tools.yuki_business_candidate import create_native_core','from tools.formal_yuki import create_native_core'),
        ('from tools.yuki_business_candidate import native_controller_type','from tools.formal_yuki import native_controller_type'),
        ('from tools.native_yuki_candidate import prepare_portrait','from tools.formal_native_yuki import prepare_portrait'),
        ('from tools.native_yuki_candidate import display_status','from tools.formal_native_yuki import display_status')):
        text=replace_once(text,old,new)
    text=replace_once(text,'            recording=recording_type(visual_controller,transcriber=self.transcriber,**recording_options)',
        '            from tools.formal_yuki import paired_recording_type\n'
        '            recording_type=paired_recording_type(recording_type,self.character_pair)\n'
        '            recording=recording_type(visual_controller,transcriber=self.transcriber,**recording_options)')
    text=replace_once(text,"        kind = data['type']",
        "        kind = data['type']\n"
        "        from tools.production_business_ui import guard_legacy_configuration\n"
        "        guard_legacy_configuration(self, data)")
    text=replace_once(text,'            self.refresh_runtime(state,settings_text)',
        '            self.refresh_runtime(state,settings_text)\n'
        '            from tools.production_business_ui import project_business_ui\n'
        '            project_business_ui(self,state)')
    text=replace_once(text,"            state['diagnostic_job']=dict(self.diagnostic_job) if self.diagnostic_job else None\n            self.bridge.publish(state,packet['jpeg'])",
        "            state['diagnostic_job']=dict(self.diagnostic_job) if self.diagnostic_job else None\n"
        "            if self.board_business is not None:\n"
        "                state['board_business']=self.board_business.runtime.public()\n"
        "            self.bridge.publish(state,packet['jpeg'])")
    return text.encode()


def formal_pair():
    text=(FRESH/'tools/formal_yuki.py').read_text(encoding='utf8')
    text=replace_once(text,"    if config.get('board_business', {}).get('enabled'):\n        raise PairRejected('Formal image-only overlay must retain the original legacy business')",
        "    business = config.get('board_business', {})\n"
        "    if business.get('enabled') is not True or business.get('data_origin') != 'board':\n"
        "        raise PairRejected('Formal board business requires explicit migrated board storage')")
    return text.encode()


def main():
    snapshot=json.loads((HERE/'current_formal_snapshot.json').read_text(encoding='utf8'))
    if snapshot['startup_sha256']!='4c78824ba9c1c04bb95389a49b64215a7f624a323becae637bc8d4e7c4db4d7e':raise ValueError('Current appearance basis changed')
    files={};providers={}
    for path in FRESH.rglob('*'):
        if path.is_file():
            relative=path.relative_to(FRESH).as_posix();raw=path.read_bytes()
            if digest(raw)!=snapshot['files'][relative]['sha256']:raise ValueError('Fresh snapshot source changed')
            files[relative]=raw;providers[relative]='actual-current4c788'
    for path in BASE.rglob('*'):
        if path.is_file():
            relative=path.relative_to(BASE).as_posix()
            if relative not in files or relative=='tools/profile_selection_ui.py':
                files[relative]=path.read_bytes();providers[relative]='frozen-business-v2-2c25'
    files['tools/board_avatar_gtk.py']=gtk();providers['tools/board_avatar_gtk.py']='business-v2-plus-current-theme-rect-settings-pair'
    files['tools/formal_yuki.py']=formal_pair();providers['tools/formal_yuki.py']='current-formal-pair-explicit-board-business'
    for path in (HERE/'production_modules').rglob('*'):
        if path.is_file():
            relative=path.relative_to(HERE/'production_modules').as_posix();files[relative]=path.read_bytes();providers[relative]='production-receipt-retention-bridge'
    for relative,raw in sorted(files.items()):
        if relative.endswith('.py'):ast.parse(raw,feature_version=(3,9))
        path=DEST/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    rows={k:{'sha256':digest(v),'bytes':len(v),'provider':providers[k]} for k,v in sorted(files.items())}
    before=snapshot['files'];changes={k:{'before':before[k]['sha256'],'after':rows[k]['sha256']} for k in before if before[k]['sha256']!=rows[k]['sha256']}
    value={'schema':'aura.production-business.source-merge.v1','status':'PREPARATION_NOT_DEPLOYED','basis_startup_sha256':snapshot['startup_sha256'],
        'basis_component_count':304,'files':rows,'changes':changes,'new_files':sorted(set(rows)-set(before)),
        'native_library_sha256':rows['tools/libaura_yuki.so']['sha256'],'theme_tokens_sha256':rows['ui/ui_tokens.json']['sha256'],
        'source_models_devices_or_databases_opened':False}
    (HERE/'candidate_manifest.json').write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'files':len(rows),'changed_current':len(changes),'new':len(value['new_files']),
                     'library':value['native_library_sha256'],'theme':value['theme_tokens_sha256']}))


if __name__=='__main__':main()
