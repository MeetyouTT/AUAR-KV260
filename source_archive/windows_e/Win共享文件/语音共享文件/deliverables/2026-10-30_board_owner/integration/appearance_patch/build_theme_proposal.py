"""Local-only theme proposal over the CURRENT formal304-pin production.

Outputs stay beside this script. No board, native renderer, service, model,
database or production file is read/written. Root is the only publisher.
"""
import ast
import copy
import difflib
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
INTEGRATION=HERE.parent
PROJECT=HERE.parents[3]
CURRENT=INTEGRATION/'formal_character_switch/actual_completed.json'
GTK=INTEGRATION/'formal_switch/overlay/aura/tools/board_avatar_gtk.py'
TOKENS=PROJECT/'aura/ui/ui_tokens.json'
GTK_SHA='2cad2f43ab811ca0ca14975ff81f831ac4fa7bba889d33fef683669721b937a4'
TOKENS_SHA='fa59f73b3582280514d7a9a2efde91ab486c1dfe08e42f88c378e8a327a7262a'
STARTUP_SHA='91dbe7229cf0e11afdcfa6ca5aca657dd7f95a2adfa9b3764a0df0d793f050e2'

# Proposal only. Panel cream remains identical to the unchanged native EGL
# clear colour; changing that colour needs root's renderer/theme coordination.
PROPOSED={
    'bg':'#F4EFF1',
    'panel_bg':'#FCFCF3',
    'panel_border':'#D8CDD3',
    'accent':'#873A4D',
    'accent_dark':'#303950',
    'warning':'#915600',
    'error':'#C62828',
    'success':'#2E7D32',
    'privacy_mask':'#E9E3E7',
    'text_primary':'#282C3C',
    'text_secondary':'#5E5B6A',
}
CSS={
    'button:disabled {color:#91969b;background:#ebede8;}':
    'button:disabled {color:#6B6672;background:#ECE8EA;}',
    'button.primary:disabled {background:#e4e8e3;color:#91969b;}':
    'button.primary:disabled {background:#ECE8EA;color:#6B6672;}',
    'button.nav:hover {background:#e9f2f6;}':
    'button.nav:hover {background:#EEE5E9;}',
    'button.primary:disabled label {color:#91969b;}':
    'button.primary:disabled label {color:#6B6672;}',
    'button.quiet {background:transparent;border-color:transparent;box-shadow:none;color:#8b969b;':
    'button.quiet {background:transparent;border-color:transparent;box-shadow:none;color:#6B6473;',
}


def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()


def luminance(value):
    rgb=[int(value[i:i+2],16)/255 for i in (1,3,5)]
    linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    return sum(v*w for v,w in zip(linear,(.2126,.7152,.0722)))


def contrast(a,b):
    light,dark=sorted((luminance(a),luminance(b)),reverse=True)
    return (light+.05)/(dark+.05)


def apply_css(source):
    for old,new in CSS.items():
        if source.count(old)!=1:raise ValueError('Current GTK colour integration point changed: '+old)
        source=source.replace(old,new,1)
    return source


def main():
    current=json.loads(CURRENT.read_bytes())
    if (current['root']!='/home/root/aura-character-xuefei-20261030/f94fca2c94288acb'
            or current['startup_sha256']!=STARTUP_SHA or current['component_pins']!=304
            or current['source_manifest_sha256']!='bfdc28c79eff58e4ae6cc35df889f99232b4fdd64263dab5377a1b108c3fe7a0'):
        raise ValueError('The CURRENT formal production metadata changed; rebase instead of using old c413')
    old_gtk=GTK.read_bytes();old_tokens=TOKENS.read_bytes()
    if sha(old_gtk)!=GTK_SHA or sha(old_tokens)!=TOKENS_SHA:
        raise ValueError('Current formal theme source pin mismatch')
    tokens=json.loads(old_tokens);candidate=copy.deepcopy(tokens)
    candidate['colors'].update(PROPOSED)
    assert candidate['colors']['box']==tokens['colors']['box']
    assert candidate['colors']['zone']==tokens['colors']['zone']
    assert {k:v for k,v in candidate.items() if k!='colors'}=={k:v for k,v in tokens.items() if k!='colors'}
    css=apply_css(old_gtk.decode())
    ast.parse(css,feature_version=(3,9))
    # CSS exists only inside one string. Its Python AST must otherwise stay
    # identical, so no handler/controller/permission/timing/layout can change.
    before=ast.parse(old_gtk);after=ast.parse(css)
    for tree in (before,after):
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str):
                for old,new in CSS.items():node.value=node.value.replace(new,old)
    assert ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False)
    output=HERE/'proposed_overlay/aura'
    (output/'ui').mkdir(parents=True,exist_ok=True);(output/'tools').mkdir(parents=True,exist_ok=True)
    token_text=old_tokens.decode()
    for name,color in PROPOSED.items():
        old=json.dumps(name)+': '+json.dumps(tokens['colors'][name])
        new=json.dumps(name)+': '+json.dumps(color)
        if token_text.count(old)!=1:raise ValueError('Current colour token integration point changed: '+name)
        token_text=token_text.replace(old,new,1)
    new_tokens=token_text.encode();new_gtk=css.encode()
    assert json.loads(new_tokens)==candidate
    (output/'ui/ui_tokens.json').write_bytes(new_tokens)
    (output/'tools/board_avatar_gtk.py').write_bytes(new_gtk)
    patch=''
    for name,a,b in (('aura/ui/ui_tokens.json',old_tokens,new_tokens),('aura/tools/board_avatar_gtk.py',old_gtk,new_gtk)):
        patch+=''.join(difflib.unified_diff(a.decode().replace('\r\n','\n').splitlines(True),
            b.decode().replace('\r\n','\n').splitlines(True),fromfile='a/'+name,tofile='b/'+name))
    (HERE/'theme.proposed.patch').write_bytes(patch.encode())
    checks=[]
    pairs=[('primary_on_panel',PROPOSED['text_primary'],PROPOSED['panel_bg']),
        ('primary_on_card',PROPOSED['text_primary'],PROPOSED['bg']),
        ('secondary_on_panel',PROPOSED['text_secondary'],PROPOSED['panel_bg']),
        ('secondary_on_card',PROPOSED['text_secondary'],PROPOSED['bg']),
        ('selected_white_on_wine','#FFFFFF',PROPOSED['accent']),
        ('title_on_panel',PROPOSED['accent_dark'],PROPOSED['panel_bg']),
        ('warning_on_panel',PROPOSED['warning'],PROPOSED['panel_bg']),
        ('error_on_panel',PROPOSED['error'],PROPOSED['panel_bg']),
        ('success_on_panel',PROPOSED['success'],PROPOSED['panel_bg']),
        ('quiet_on_panel','#6B6473',PROPOSED['panel_bg']),
        ('disabled_text','#6B6672','#ECE8EA')]
    pairs.extend((name+'_on_card',PROPOSED[name],PROPOSED['bg']) for name in ('warning','error','success'))
    for name,fg,bg in pairs:
        ratio=contrast(fg,bg);assert ratio>=4.5,(name,ratio)
        checks.append(dict(name=name,foreground=fg,background=bg,contrast=round(ratio,2)))
    result=dict(schema='aura.appearance.theme_proposal.v1',status='ROOT_PALETTE_CONFIRMED_SOURCE_READY_NOT_PUBLISHED',
        base_root=current['root'],base_startup_sha256=STARTUP_SHA,base_component_pins=304,
        base_source_manifest_sha256=current['source_manifest_sha256'],
        files={'aura/ui/ui_tokens.json':dict(before_sha256=TOKENS_SHA,proposed_sha256=sha(new_tokens)),
               'aura/tools/board_avatar_gtk.py':dict(before_sha256=GTK_SHA,proposed_sha256=sha(new_gtk))},
        palette=PROPOSED,css_substitutions=CSS,contrast_checks=checks,
        warning_semantics='amber preserved; darkened for small text',error_success_preserved=True,
        vision_box_zone_preserved=True,panel_native_clear_unchanged=True,
        layout_geometry_handlers_timing_unchanged=True,new_dependencies=[],
        device_service_database_model_calls=False,performance_test=False,publisher='root_only')
    (HERE/'theme_proposal.json').write_bytes(encoded(result))
    with zipfile.ZipFile(HERE/'xuefei_theme.overlay.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in result['files']:
            info=zipfile.ZipInfo(relative,(2026,10,30,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,(HERE/'proposed_overlay'/relative).read_bytes())
    print(json.dumps(dict(status=result['status'],files=2,contrast_min=min(row['contrast'] for row in checks),
        manifest_sha256=sha((HERE/'theme_proposal.json').read_bytes()),
        source_zip_sha256=sha((HERE/'xuefei_theme.overlay.zip').read_bytes())),sort_keys=True))


if __name__=='__main__':main()
