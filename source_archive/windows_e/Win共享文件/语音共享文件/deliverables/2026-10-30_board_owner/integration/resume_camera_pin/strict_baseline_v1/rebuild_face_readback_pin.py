"""Read-only fresh camera-owner proof; optionally create one private candidate.

Never opens a gallery database, camera, model runner, GPIO or network connection.
The old source pins and INT8 identity/model/gallery selection remain mandatory.
Only an identical generated runtime config may move to its fresh boot/PID path.
Nothing is installed, reloaded, overwritten or enabled by this script.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess


ENTRY = '/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/face-source-v17/entry.py'
ENTRY_SHA256 = 'f26be22cb640bf44a1bd81b66bb3fa014f5b847b13320781836bf3f173387623'
UNIT = 'aura-camera-ui.service'
FIELDS = {'version','enabled','board_boot_id','camera_pid','camera_start_ticks','camera_cmdline_sha256',
          'camera_config','identity_config','source_sha256','database','model_id','dimension','model_sha256','result_ttl_ms','backend'}


class PinRejected(ValueError):
    def __init__(self,code,fields=()):
        self.code,self.fields = code,list(fields)
        super().__init__(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')


def path(value):
    if (not isinstance(value,str) or not value.startswith('/') or '..' in PurePosixPath(value).parts
            or any(ord(c)<32 for c in value)):
        raise PinRejected('INVALID_SOURCE_PATH')
    return PurePosixPath(value)


def differences(old,new,prefix='',maximum=32):
    """Only old schema field names; never print source values/new arbitrary keys."""
    if not isinstance(old,dict) or not isinstance(new,dict):
        return [prefix or '<root>'] if old != new else []
    result = []
    for key in sorted(old):
        label = prefix+'.'+key if prefix else key
        if key not in new:
            result.append(label)
        elif old[key] != new[key]:
            result.extend(differences(old[key],new[key],label,maximum) if label.count('.') < 5 else [label])
        if len(result)>=maximum:
            return result[:maximum]
    if set(new)-set(old):
        result.append((prefix+'.' if prefix else '')+'<additional_fields>')
    return result[:maximum]


class LiveReader:
    def read(self,name,maximum=2*1024*1024):
        with Path(name).open('rb') as stream:
            raw = stream.read(maximum+1)
        if len(raw)>maximum:
            raise PinRejected('SOURCE_METADATA_TOO_LARGE')
        return raw
    def hash(self,name):
        result = hashlib.sha256()
        with Path(name).open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):
                result.update(chunk)
        return result.hexdigest()
    def boot(self):
        return self.read('/proc/sys/kernel/random/boot_id',256).decode('ascii').strip()
    def unit(self):
        properties = ('MainPID','ActiveState','SubState','ExecStart','ControlGroup')
        output = subprocess.check_output(['systemctl','--no-pager','show',UNIT]+[
            item for key in properties for item in ('-p',key)],text=True,timeout=5)
        return dict(line.split('=',1) for line in output.splitlines() if '=' in line)
    def process(self,pid):
        root = Path('/proc')/str(pid)
        command = self.read(str(root/'cmdline'),16384)
        process_stat = self.read(str(root/'stat'),16384).decode('utf-8')
        fields = process_stat.rsplit(')',1)[1].split()
        if not process_stat.startswith(str(pid)+' (') or len(fields)<20 or fields[0] in ('Z','X'):
            raise PinRejected('CAMERA_PROCESS_NOT_LIVE')
        argv = command.rstrip(b'\x00').decode('utf-8').split('\x00')
        return dict(pid=pid,start_ticks=fields[19],cmdline_sha256=digest(command),argv=argv,
                    executable=str((root/'exe').resolve(strict=True)),
                    argv_executable=str(Path(argv[0]).resolve(strict=True)),
                    cgroups=[line.split(':',2)[2] for line in self.read(str(root/'cgroup'),16384).decode().splitlines() if line.count(':')>=2])


def read_json(reader,name):
    try:
        value = json.loads(reader.read(str(name)).decode('utf-8'))
    except (ValueError,UnicodeError):
        raise PinRejected('INVALID_SOURCE_JSON') from None
    if not isinstance(value,dict):
        raise PinRejected('INVALID_SOURCE_JSON')
    return value


def observed_owner(reader,expected_boot,expected_pid,entry):
    boot = reader.boot(); unit = reader.unit()
    if boot != expected_boot:
        raise PinRejected('FRESH_BOOT_MISMATCH')
    if (unit.get('MainPID') != str(expected_pid) or unit.get('ActiveState') != 'active'
            or unit.get('SubState') != 'running' or unit.get('ControlGroup') != '/system.slice/'+UNIT):
        raise PinRejected('SYSTEMD_CAMERA_OWNER_MISMATCH')
    process = reader.process(expected_pid)
    if (process.get('pid') != expected_pid or process.get('argv') != ['/usr/bin/python3','-B',entry]
            or process.get('executable') != process.get('argv_executable')
            or unit['ControlGroup'] not in process.get('cgroups',[]) or not re.fullmatch(r'[0-9]+',process.get('start_ticks',''))):
        raise PinRejected('PROC_CAMERA_OWNER_MISMATCH')
    # Both selected next start and actually running argv must identify this entry.
    command = unit.get('ExecStart','')
    match = re.search(r'argv\[\]=([^;]+)\s*;',command)
    if match is None or match[1].strip().split() != ['/usr/bin/python3','-B',entry]:
        raise PinRejected('SYSTEMD_EXECSTART_DIFFERS_FROM_PROC')
    return dict(board_boot_id=boot,camera_pid=expected_pid,camera_start_ticks=process['start_ticks'],
                camera_cmdline_sha256=process['cmdline_sha256'])


def build_candidate(config,reader,*,expected_boot,expected_pid,entry=ENTRY,entry_sha256=ENTRY_SHA256):
    if set(config) != FIELDS or config.get('version') != 1 or config.get('enabled') is not True:
        raise PinRejected('UNSUPPORTED_READBACK_SCHEMA')
    if not re.fullmatch(r'[0-9a-f-]{36}',expected_boot or '') or type(expected_pid) is not int or expected_pid<1:
        raise PinRejected('EXPLICIT_FRESH_OWNER_REQUIRED')
    pins = config.get('source_sha256')
    if (not isinstance(pins,dict) or not pins or len(pins)>128 or pins.get(entry) != entry_sha256
            or any(not isinstance(value,str) or not re.fullmatch(r'[0-9a-f]{64}',value) for value in pins.values())):
        raise PinRejected('ORIGINAL_ENTRY_PIN_REQUIRED')
    path(entry)
    for name,expected in pins.items():
        source = path(name)
        if source.suffix not in ('.json','.py') or '.local' in source.parts or str(source) == config['database']:
            raise PinRejected('UNSAFE_ORIGINAL_SOURCE_PIN')
        if reader.hash(name) != expected:
            raise PinRejected('ORIGINAL_SOURCE_SHA_MISMATCH')
    first = observed_owner(reader,expected_boot,expected_pid,entry)
    if (first['board_boot_id'] == config['board_boot_id'] and first['camera_pid'] == config['camera_pid']
            and first['camera_start_ticks'] != config['camera_start_ticks']):
        raise PinRejected('OLD_PID_REUSED')
    ops = path(entry).parents[2]
    selected = [ops/'meta.json',ops/'native_entry.py',ops/'native_entry_pan_face_v5.py',
                ops/'pan-face-edge-v5/native-operator-v1/native_entry_operator.py']
    if any(str(name) not in pins for name in selected):
        raise PinRejected('NATIVE_LAUNCH_CHAIN_NOT_PINNED')
    meta = read_json(reader,selected[0])
    if meta.get('root') != str(ops):
        raise PinRejected('NATIVE_LAUNCH_ROOT_CHANGED')
    candidate_config = str(path(meta.get('candidate_config')))
    ui_source = str(path(meta.get('candidate_root'))/'aura/board/vision/ui_camera_service.py')
    if candidate_config not in pins or pins.get(ui_source) != meta.get('candidate_ui_sha256'):
        raise PinRejected('CAMERA_SELECTION_SOURCE_CHANGED')
    old_runtime = str(path(config['camera_config']))
    if old_runtime not in pins or config['identity_config'] not in pins:
        raise PinRejected('CONFIG_CHAIN_NOT_PINNED')
    # This exact deterministic path is created by the pinned native_entry.py.
    current_runtime = str(ops/('native-run-'+expected_boot+'-'+str(expected_pid))/'config.json')
    old_camera = read_json(reader,old_runtime); camera = read_json(reader,current_runtime)
    old_hash,new_hash = pins[old_runtime],reader.hash(current_runtime)
    if new_hash != old_hash:
        raise PinRejected('GENERATED_CAMERA_CONFIG_BYTES_CHANGED',differences(old_camera,camera))
    identity_path = str(path(config['identity_config']))
    if camera.get('identity') != {'enabled':True,'config':identity_path}:
        raise PinRejected('ACTUAL_IDENTITY_SELECTION_CHANGED')
    identity = read_json(reader,identity_path)
    backend = identity.get('feature_backend',{})
    if (identity.get('schema_version') != 'aura-camera-identity-1' or identity.get('database') != config['database']
            or identity.get('model_id') != config['model_id'] or identity.get('result_ttl_ms') != config['result_ttl_ms']
            or backend.get('kind') != 'dpu_sface' or backend.get('model_sha256') != config['model_sha256']
            or config['dimension'] != 128 or config['backend'] != 'DPU_SFACE_INT8'
            or config['model_id'] != 'sface-int8-'+config['model_sha256'][:16]):
        raise PinRejected('ORIGINAL_INT8_IDENTITY_CHAIN_CHANGED')
    path(config['database'])  # Compare metadata only. Never stat/open/hash the DB.
    model_proofs = {}
    for name,section in (('feature',backend),('face',identity.get('face_backend',{}))):
        if not section:
            continue
        for filename,hash_key in (('model','model_sha256'),('manifest','manifest_sha256')):
            target = str(path(section.get(filename))); expected = section.get(hash_key)
            if (target == config['database'] or not isinstance(expected,str) or not re.fullmatch(r'[0-9a-f]{64}',expected)
                    or PurePosixPath(target).suffix not in ('.json','.xmodel') or reader.hash(target) != expected):
                raise PinRejected('ACTUAL_DPU_MODEL_SHA_MISMATCH')
            model_proofs[name+'_'+hash_key] = expected
    second = observed_owner(reader,expected_boot,expected_pid,entry)
    if second != first:
        raise PinRejected('CAMERA_PROCESS_REUSED_DURING_PROBE')
    if any(reader.hash(name) != value for name,value in pins.items()) or reader.hash(current_runtime) != new_hash:
        raise PinRejected('SOURCE_CHANGED_DURING_PROBE')
    for name,section in (('feature',backend),('face',identity.get('face_backend',{}))):
        if section and any(reader.hash(str(path(section[key]))) != section[hash_key] for key,hash_key in
                           (('model','model_sha256'),('manifest','manifest_sha256'))):
            raise PinRejected('DPU_MODEL_CHANGED_DURING_PROBE')
    candidate = copy.deepcopy(config); candidate.update(first)
    candidate['camera_config'] = current_runtime
    candidate['source_sha256'][current_runtime] = new_hash  # Preserve every original pin.
    changes = [key for key in config if candidate[key] != config[key]]
    observation = dict(owner=first,entry_sha256=entry_sha256,camera_config_sha256=new_hash,
                       identity_config_sha256=pins[identity_path],model_sha256=model_proofs,
                       original_source_pins_sha256=digest(canonical(pins)),database_path_sha256=digest(config['database'].encode()))
    report = dict(ready=True,status='PIN_CANDIDATE_READY_NOT_INSTALLED',owner=first,
        observation_sha256=digest(canonical(observation)),candidate_sha256=digest(candidate_bytes(candidate)),
        original_pin_count=len(pins),candidate_pin_count=len(candidate['source_sha256']),changed_fields=changes,
        camera_config_relocated=current_runtime != old_runtime,camera_config_sha256=new_hash,
        identity_config_sha256=pins[identity_path],model_proofs=model_proofs,database_opened=False,
        native_runner_loaded=False,model_or_mechanical_config_changed=False,windows_payload_sent=False,written=False)
    if current_runtime != old_runtime:
        report['added_source_pin'] = dict(path=current_runtime,sha256=new_hash)
    return candidate,report


def candidate_bytes(candidate):
    return (json.dumps(candidate,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')


def write_new_candidate(candidate,report,*,private_root,output,expected_observation_sha256):
    if expected_observation_sha256 != report.get('observation_sha256'):
        raise PinRejected('REVIEWED_OBSERVATION_TOKEN_MISMATCH')
    if os.name != 'posix':
        raise PinRejected('WRITE_REQUIRES_ACTUAL_POSIX_BOARD')
    if not Path(private_root).is_absolute() or not Path(output).is_absolute():
        raise PinRejected('WRITE_REQUIRES_ABSOLUTE_PRIVATE_PATHS')
    root = Path(private_root).absolute(); destination = Path(output).absolute()
    if (root.resolve() != root or destination.resolve() != destination or root not in destination.parents
            or destination.suffix != '.json' or any(part.casefold() == 'win共享文件' for part in destination.parts)):
        raise PinRejected('WRITE_REQUIRES_NEW_PRIVATE_CANDIDATE')
    info = root.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise PinRejected('CANDIDATE_ROOT_NOT_PRIVATE')
    parent = destination.parent
    parent_info = parent.stat()
    if parent_info.st_uid != os.getuid() or parent_info.st_mode & 0o077:
        raise PinRejected('CANDIDATE_PARENT_NOT_PRIVATE')
    if destination.exists() or destination == Path(candidate['camera_config']) or str(destination) in candidate['source_sha256']:
        raise PinRejected('CANDIDATE_OVERWRITE_REFUSED')
    raw = candidate_bytes(candidate)
    fd = os.open(str(destination),os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return dict(report,written=True,candidate_sha256=digest(raw))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-config',required=True)
    parser.add_argument('--expected-boot-id',required=True)
    parser.add_argument('--expected-pid',type=int,required=True)
    parser.add_argument('--write',action='store_true')
    parser.add_argument('--private-root')
    parser.add_argument('--output')
    parser.add_argument('--expected-observation-sha256')
    args = parser.parse_args()
    try:
        reader = LiveReader()
        config = read_json(reader,args.old_config)
        candidate,report = build_candidate(config,reader,expected_boot=args.expected_boot_id,expected_pid=args.expected_pid)
        if args.write:
            if not args.private_root or not args.output or not args.expected_observation_sha256:
                raise PinRejected('WRITE_REQUIRES_PRIVATE_PATH_AND_REVIEW_TOKEN')
            report = write_new_candidate(candidate,report,private_root=args.private_root,output=args.output,
                                         expected_observation_sha256=args.expected_observation_sha256)
    except PinRejected as exc:
        report = dict(ready=False,status=exc.code,different_fields=exc.fields,written=False,database_opened=False)
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):
        report = dict(ready=False,status='SOURCE_OR_OWNER_PROBE_UNAVAILABLE',written=False,database_opened=False)
    print(json.dumps(report,sort_keys=True))


if __name__ == '__main__':
    main()
