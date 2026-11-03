#!/usr/bin/env python3
import argparse,datetime,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out=ROOT/'evidence'/(stamp+'-joint-fit');out.mkdir()
env=os.environ.copy();env['AURA_ADAPT_OUT']=str(out);env['AURA_ADAPT_ROOT']=str(ROOT)
parser=argparse.ArgumentParser()
parser.add_argument('--resume-spliced',type=Path)
parser.add_argument('--resume-bound',type=Path)
parser.add_argument('--resume-imported',type=Path)
parser.add_argument('--resume-trimmed',type=Path)
parser.add_argument('--resume-optimized',type=Path)
parser.add_argument('--resume-incremental',type=Path)
parser.add_argument('--resume-placed',type=Path)
parser.add_argument('--resume-routed',type=Path,
                    help='Resume joint_preroute_physopt.dcp or a completed joint_routed.dcp')
parser.add_argument('--usb-audio',action='store_true')
parser.add_argument('--audio-stub',type=Path)
parser.add_argument('--incremental',action='store_true')
parser.add_argument('--incremental-reference',type=Path,
                    help='Use a completed joint candidate as the incremental physical reference')
parser.add_argument('--timing-closure',action='store_true',
                    help='Use the official TimingClosure incremental directive instead of RuntimeOptimized')
parser.add_argument('--postroute-refine',choices=['dsp','clock','alternate'],
                    help='Additional documented physical optimization on a resumed routed checkpoint')
args=parser.parse_args()
if args.timing_closure and not args.incremental:
    parser.error('--timing-closure requires --incremental and a fresh reference import')
if args.incremental_reference and not args.incremental:
    parser.error('--incremental-reference requires --incremental')
if args.postroute_refine and not args.resume_routed:
    parser.error('--postroute-refine requires --resume-routed')
if args.postroute_refine:
    env['AURA_ADAPT_POSTROUTE_REFINE']=args.postroute_refine
reference=Path('/home/ghmd/kv260-m3-axilite-20261002/src/kv260/overlays/examples/benchmark/binary_container_1/link/vivado/vpl/prj/prj.runs/impl_1/kv260_ispMipiRx_vcu_DP_wrapper_routed.dcp')
if args.incremental_reference:
    reference=args.incremental_reference.resolve()
    if ROOT not in reference.parents or reference.name!='joint_routed.dcp':
        parser.error('Candidate reference must be this experiment\'s completed joint_routed.dcp')
    reference_status=json.loads((reference.parent/'status.json').read_text())
    if reference_status.get('state')!='finished' or reference_status.get('rc')!=0 or not reference_status.get('usb_audio_profile'):
        parser.error('Candidate reference implementation did not finish successfully')
    if not args.usb_audio:
        parser.error('Candidate reference requires --usb-audio')
    if reference_status.get('source_files_changed_during_run')!=[]:
        parser.error('Candidate reference sources changed during its implementation')
    for name in ['fpga/rtl/motion_fit.sv','fpga/rtl/audio_decerr.sv','fpga/audio_ports.tcl']:
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=reference_status['available_source_sha256'][name]:
            parser.error('Candidate reference hardware source mismatch: '+name)
    if not (reference.parent/'joint_route.rpt').is_file():
        parser.error('Candidate reference lacks its route report')
if args.incremental:
    env['AURA_ADAPT_INCREMENTAL']='1'
    env['AURA_ADAPT_INCREMENTAL_REFERENCE']=str(reference)
    env['AURA_ADAPT_INCREMENTAL_DIRECTIVE']='TimingClosure' if args.timing_closure else 'RuntimeOptimized'
if args.usb_audio:
    env['AURA_ADAPT_USB_AUDIO']='1'
resume_args=[args.resume_spliced,args.resume_bound,args.resume_imported,args.resume_trimmed,args.resume_optimized,args.resume_incremental,args.resume_placed,args.resume_routed]
if sum(value is not None for value in resume_args)>1:
    raise ValueError('Choose one resume phase')
resume=None
stage=None
for name in ['imported','trimmed','optimized','incremental','placed','routed']:
    value=getattr(args,'resume_'+name)
    if value:
        resume=value.resolve();stage=name
if stage:
    expected={'imported':'joint_imported.dcp','trimmed':'joint_trimmed.dcp','optimized':'joint_optimized.dcp',
              'incremental':'joint_incremental.dcp','placed':'joint_placed.dcp','routed':'joint_preroute_physopt.dcp'}[stage]
    accepted=[expected]
    if stage=='routed':
        accepted.append('joint_routed.dcp')
    if ROOT not in resume.parents or resume.name not in accepted:
        raise ValueError('Resume checkpoint must match the requested experiment phase')
    prior=json.loads((resume.parent/'status.json').read_text())
    if resume.name=='joint_routed.dcp':
        if prior.get('state')!='finished' or prior.get('rc')!=0 or prior.get('source_files_changed_during_run')!=[]:
            raise ValueError('Final routed checkpoint must come from a completed immutable implementation')
        for name in ['fpga/rtl/motion_fit.sv','fpga/rtl/audio_decerr.sv','fpga/audio_ports.tcl']:
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=prior['available_source_sha256'][name]:
                raise ValueError('Final routed hardware source mismatch: '+name)
    if not prior.get('usb_audio_profile') or not args.usb_audio:
        raise ValueError('Trimmed implementation requires the verified USB audio profile')
    env.update(AURA_ADAPT_RESUME=str(resume),AURA_ADAPT_BOUND='1',AURA_ADAPT_UNROUTED='1',AURA_ADAPT_STAGE=stage)
    if args.incremental and stage not in ['trimmed','optimized','incremental']:
        parser.error('A fresh incremental reference import requires an optimized or earlier checkpoint')
elif args.resume_spliced or args.resume_bound:
    resume=(args.resume_spliced or args.resume_bound).resolve()
    expected='joint_unplaced.dcp' if args.resume_bound else 'joint_spliced.dcp'
    if ROOT not in resume.parents or resume.name not in ([expected,'joint_unrouted.dcp'] if args.resume_bound else [expected]):
        raise ValueError('Resume must use this experiment\'s checkpoint')
    env['AURA_ADAPT_RESUME']=str(resume)
    if args.resume_bound:
        env['AURA_ADAPT_BOUND']='1'
    if resume.name=='joint_unrouted.dcp':
        env['AURA_ADAPT_UNROUTED']='1'
audio_stub=None
if args.audio_stub:
    audio_stub=args.audio_stub.resolve()
    if not args.usb_audio or resume is None or resume.name!='joint_unrouted.dcp':
        raise ValueError('Cached audio stub requires the matching unrouted checkpoint and USB audio profile')
    if ROOT not in audio_stub.parents or audio_stub.name!='audio_stub.dcp' or audio_stub.parent!=resume.parent:
        raise ValueError('Audio stub and its original unrouted design must share one evidence directory')
    for name in ['audio_alias_map.tsv','disabled_audio.sv','audio_source_manifest.json']:
        if not (audio_stub.parent/name).is_file():
            raise ValueError('Missing cached audio source evidence: '+name)
    env['AURA_ADAPT_AUDIO_STUB']=str(audio_stub)
source=ROOT/'scripts/fit_checkpoint.tcl'
(out/'fit_checkpoint.tcl').write_bytes(source.read_bytes())
status={'evidence':str(out),'state':'running','script_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'board_modified':False}
status['usb_audio_profile']=args.usb_audio
status['incremental_requested']=args.incremental
status['postroute_refine']=args.postroute_refine
if args.incremental:
    status['incremental_directive']=env['AURA_ADAPT_INCREMENTAL_DIRECTIVE']
    ref_sha=hashlib.sha256(reference.read_bytes()).hexdigest()
    if not args.incremental_reference and ref_sha!='4a564eb33412124544dd942c74ff682ccd529d29e739e41dbce28aa94232face':
        raise ValueError('Original reference checkpoint changed')
    status['incremental_reference']=str(reference)
    status['incremental_reference_sha256']=ref_sha
    status['incremental_reference_kind']='completed_candidate' if args.incremental_reference else 'original_m3'
source_names=['scripts/map_audio_aliases.tcl','scripts/prepare_audio_stub.py',
              'scripts/report_signoff.tcl',
              'fpga/audio_ports.tcl','fpga/rtl/audio_decerr.sv','fpga/rtl/motion_fit.sv']
source_hashes={}
for name in source_names:
    data=(ROOT/name).read_bytes()
    target=out/'source_archive'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(data)
    source_hashes[name]=hashlib.sha256(data).hexdigest()
status['available_source_sha256']=source_hashes
if stage:
    status['resume_stage']=stage
    if stage=='incremental' and not args.incremental:
        status['incremental_inherited']=True
        for name in ['incremental_reference','incremental_reference_sha256','incremental_directive','incremental_reference_kind']:
            if name not in prior:
                continue
            status[name]=prior[name]
if audio_stub:
    status['audio_stub']=str(audio_stub)
    status['audio_stub_sha256']=hashlib.sha256(audio_stub.read_bytes()).hexdigest()
    for name in ['audio_alias_map.tsv','disabled_audio.sv','audio_source_manifest.json']:
        (out/name).write_bytes((audio_stub.parent/name).read_bytes())
if resume:
    status['resume_checkpoint']=str(resume)
    status['resume_sha256']=hashlib.sha256(resume.read_bytes()).hexdigest()
    status['resume_io_bound']=bool(args.resume_bound or stage)
    if args.resume_bound or stage:
        (out/'io_binding.txt').write_bytes((resume.parent/'io_binding.txt').read_bytes())
(out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
(ROOT/'CURRENT_FPGA.json').write_text(json.dumps(status,indent=2)+'\n')
argv=['bash','--noprofile','--norc','-c',
      'source /home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh; exec vivado -mode batch -source "$1" -log "$2" -journal "$3"',
      'aura-joint-fit',str(out/'fit_checkpoint.tcl'),str(out/'vivado.log'),str(out/'vivado.jou')]
print(json.dumps(status),flush=True)
with (out/'console.log').open('wb') as log:
    p=subprocess.Popen(argv,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT)
    status['pid']=p.pid;(out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    (ROOT/'CURRENT_FPGA.json').write_text(json.dumps(status,indent=2)+'\n')
    rc=p.wait()
changed=[name for name,sha in source_hashes.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha]
status['source_files_changed_during_run']=changed
if changed:
    status['vivado_rc']=rc
    rc=2
status.update(state='finished',rc=rc)
(out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
(ROOT/'CURRENT_FPGA.json').write_text(json.dumps(status,indent=2)+'\n')
print(json.dumps(status),flush=True)
raise SystemExit(rc)
