"""Local metadata-only assembly policy builder; never reads model weights."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OWNER = HERE.parents[1]


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(candidate):
    handoff = read(candidate/'HANDOFF.json')
    if handoff.get('candidate_revision')!=2 or handoff.get('status')!='SOURCE_CANDIDATE_V2_FROZEN_NOT_SELECTED':
        raise ValueError('The reviewed frozen revision2 candidate is required')
    public = read(HERE/'actual_public_configuration.json')
    resources = read(HERE/'actual_public_resources.json')['public_resources']
    cues = read(HERE.parent/'resume_runtime/actual_static_cues.json')
    rows = []
    for row in resources:
        if not row['exists']:continue
        relative = row['relative']
        destination = ('stage/'+Path(relative).name if relative.startswith('deliverables/2026-10-06_xilan_live/')
                       else 'runtime/'+relative)
        rows.append({'declared': row['path'], 'source': row['resolved'], 'target': destination,
                     'bytes': row['bytes'], 'sha256': row['sha256']})
        if 'reference_audio' in row:
            rows.append({'declared': str(Path(row['path']).parent/row['reference_audio']).replace('\\','/'),
                         'source': row['reference_audio_resolved'],
                         'target': 'runtime/deliverables/2026-10-06_voice_selected_soft_young/'+row['reference_audio'],
                         'bytes': row['reference_audio_bytes'], 'sha256': row['reference_audio_sha256']})
    root = '/home/root/aura-board-owner-candidate-20261030'
    models = []
    for name, suffix, selected in [('asr', '', {'models/paraformer/model.int8.onnx','models/paraformer/tokens.txt'}),
                                  ('frontend', '', {'models/gtcrn_simple.onnx','models/silero_vad_v5.onnx'})]:
        metadata = read(OWNER/'ubuntu'/ (name+'_asset_manifest.local.json'))
        for item in metadata['entries']:
            if item['name'] in selected:
                models.append({'path': metadata['candidate_root']+'/'+item['name'],
                               'sha256': item['sha256'], 'bytes': item['bytes']})
    speaker = read(OWNER/'speaker/assets_manifest.json')
    for item in speaker['entries']:
        if item['name'] in {'embedding.onnx','frontend.npz','manifest.json'}:
            models.append({'path':root+'/speaker-c695feae5eaf88eb/'+item['name'],
                           'sha256':item['sha256'],'bytes':item['bytes']})
    archive = handoff['artifacts']
    policy = {'schema':'aura-yuki-synthetic-assembly-policy-1',
              'source':{'candidate_revision':2,'archive_sha256':archive['source_zip_sha256'], 'archive_bytes':archive['source_zip_bytes'],
                        'manifest_sha256':archive['source_manifest_sha256'], 'files':archive['candidate_files'],
                        'python_files':archive['python_files']},
              'baseline':{'startup':public['startup']['path'], 'startup_sha256':public['startup']['sha256'],
                          'runtime':public['startup']['content']['runtime'],
                          'gui':public['gui']['path'],'gui_sha256':public['gui']['sha256'],
                          'pins':public['startup']['content']['component_sha256']},
              'public_copies':rows,'models':models,
              'asr_directory':root+'/asr-1.13.8/models/paraformer',
              'frontend_directory':root+'/frontend-b3d06b653876469d/models',
              'speaker_directory':root+'/speaker-c695feae5eaf88eb',
              'speaker_manifest_sha256':'d59b61bd1dfffacabf4927ec55e9469550882ff213c1b5ac5d3b6fa2dd6f77fe',
              'dependencies':[
                  {'kind':'onnxruntime','version':'1.17.3','root':root+'/fft-ee19b936d17aa451/deps'},
                  {'kind':'sherpa-onnx','version':'1.13.8','root':root+'/asr-1.13.8/deps'},
                  {'kind':'webrtcvad-wheels','version':'2.0.14','root':root+'/webrtcvad-wheels-2.0.14-127741474d07c52f/deps'},
                  {'kind':'numpy','version':'1.21.2','root':'/usr/lib/python3.9/site-packages/numpy'}],
              'feedback':{'path':cues['manifest'],'sha256':cues['manifest_sha256']},
              'face_readback':handoff['private_readback_future_parameter']['value'],
              'camera':{'boot':handoff['private_readback_future_parameter']['observed_parent_boot'],
                        'pid':handoff['private_readback_future_parameter']['observed_parent_camera_pid'],
                        'birth':handoff['private_readback_future_parameter']['observed_parent_camera_birth']},
              'target_root_prefix':root+'/yuki-gui-capacity-',
              'source_handoff_sha256':sha(candidate/'HANDOFF.json'),
              'never_copy':['old avatar PNG directories','old cache or business history','private databases',
                            'profile/receipt/authentication keys','venvs','LLM weights','old local preference files']}
    return policy


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    data=build(args.candidate)
    raw=(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    with args.output.open('xb') as stream:stream.write(raw)
    print(json.dumps({'path':str(args.output),'sha256':hashlib.sha256(raw).hexdigest(),
                      'baseline_pins':len(data['baseline']['pins']),'model_files':len(data['models'])}))
