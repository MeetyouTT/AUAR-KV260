import bootstrap
import hashlib,json,os,subprocess,types
from pathlib import Path
import pytest

H=Path(__file__).resolve().parent;P=H.parents[2]
UUID='GPU-00000000-0000-0000-0000-000000000001'

@pytest.fixture
def launcher(tmp_path,monkeypatch):
    candidate=H/'candidate/deliverables/2026-10-18_board_dialogue/project_ollama.py'
    m=types.ModuleType('candidate_project_ollama');m.__file__=str(P/'deliverables/2026-10-18_board_dialogue/project_ollama.py')
    exec(compile(candidate.read_text(encoding='utf-8'),str(candidate),'exec'),m.__dict__)
    m.ROOT=tmp_path/'project';m.HERE=tmp_path/'stage';m.ROOT.mkdir();m.HERE.mkdir()
    m.STORAGE={'ollama_directory':'D:/AIModels/Ollama-AURA'}
    executable=tmp_path/'ollama.exe';executable.write_bytes(b'public mocked executable identity')
    m.executable=str(executable.resolve());m.shutil=types.SimpleNamespace(which=lambda name:m.executable)
    m.client_version='0.40.13';m.gpus=UUID+', 16311';m.commands=[];m.children=[]
    def run(command,**options):
        m.commands.append((command,options))
        if command==[m.executable,'--version']:
            return types.SimpleNamespace(returncode=0,stdout='ollama version is '+m.client_version,stderr='')
        if command[0]=='nvidia-smi':return types.SimpleNamespace(returncode=0,stdout=m.gpus,stderr='')
        pytest.fail('Unexpected subprocess '+repr(command))
    def popen(command,**options):
        m.children.append((command,options));return types.SimpleNamespace(pid=3210,poll=lambda:None)
    m.subprocess=types.SimpleNamespace(run=run,Popen=popen,CREATE_NO_WINDOW=0x08000000)
    m.read_version=lambda:'0.40.13'
    m.actual_inspector=m.inspect_ownership
    m.owner={'pid':3210,'creation_utc':'2026-10-30T00:00:00.0000000Z','executable':m.executable,
      'command_line':subprocess.list2cmdline([m.executable,'serve']),'parent_pid':3200,
      'listeners':[{'LocalAddress':'127.0.0.1','LocalPort':11435,'OwningProcess':3210}]}
    m.inspect_ownership=lambda:dict(m.owner)
    m.port_available=lambda:True
    m.time=types.SimpleNamespace(sleep=lambda seconds:None)
    for key in ('CUDA_VISIBLE_DEVICES','LLAMA_ARG_FIT','LLAMA_ARG_FIT_TARGET'):
        monkeypatch.delenv(key,raising=False)
    return m

def configure(m,**changes):
    value=dict(schema_version=1,fit_target_mib=512,calibration_id='synthetic-test-only-not-a-production-budget',
               gpu_uuid=UUID,ollama_version='0.40.13')
    value.update(changes);path=m.ROOT/'aura/config/ollama_runtime.local.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8');return value

def test_healthy_without_new_configuration_is_reused_without_any_subprocess(launcher):
    m=launcher;result=m.ensure()
    assert result['status']=='REUSED' and not result['needs_controlled_restart']
    assert result['launch_environment_applied'] is None and m.commands==[] and m.children==[]

@pytest.mark.parametrize('change',[{'fit_target_mib':True},{'fit_target_mib':0},{'fit_target_mib':-1},
 {'fit_target_mib':1.5},{'calibration_id':''},{'gpu_uuid':'0'},{'ollama_version':'latest'},{'unknown_option':1}])
def test_invalid_or_unsourced_configuration_never_launches_or_replaces_healthy_daemon(launcher,change):
    m=launcher;configure(m,**change)
    with pytest.raises(ValueError):m.ensure()
    assert not m.children

def test_new_config_on_healthy_daemon_is_explicitly_pending_controlled_restart(launcher):
    m=launcher;configure(m);result=m.ensure()
    assert result['status']=='REUSED' and result['needs_controlled_restart'] is True
    assert result['launch_environment_applied'] is None and not result['effective_runner_budget_verified']
    assert result['ownership']['creation_utc']==m.owner['creation_utc'] and not m.children

def test_matching_creation_record_can_be_reused_but_is_not_current_environment_verification(launcher):
    m=launcher;configure(m);policy=m.load_runtime_policy();bindings=m.verify_policy_bindings(policy,m.executable,m.project_environment(policy),running_version='0.40.13')
    prior={'ownership':m.owner,'runtime_policy':policy,'bindings':bindings}
    (m.HERE/'project_ollama_process.json').write_text(json.dumps(prior),encoding='utf-8')
    result=m.ensure()
    assert result['policy_recorded_for_current_process_creation'] is True and not result['needs_controlled_restart']
    assert result['launch_environment_applied'] is None and not result['effective_runner_budget_verified']

def test_reused_pid_with_new_creation_time_does_not_claim_previous_env_application(launcher):
    m=launcher;configure(m);policy=m.load_runtime_policy();bindings=m.verify_policy_bindings(policy,m.executable,m.project_environment(policy))
    old=dict(m.owner,creation_utc='different-previous-process')
    (m.HERE/'project_ollama_process.json').write_text(json.dumps({'ownership':old,'runtime_policy':policy,'bindings':bindings}))
    result=m.ensure();assert result['needs_controlled_restart'] and result['policy_recorded_for_current_process_creation'] is False
    assert not m.children

@pytest.mark.parametrize('which',['running_version','installed_version','gpu','multiple_gpu','capacity','hidden_gpu','fit_disabled'])
def test_binding_mismatches_never_launch_or_kill_existing_process(launcher,monkeypatch,which):
    m=launcher;configure(m)
    if which=='running_version':m.read_version=lambda:'0.40.12'
    if which=='installed_version':m.client_version='0.40.12'
    if which=='gpu':m.gpus='GPU-00000000-0000-0000-0000-000000000099,16311'
    if which=='multiple_gpu':m.gpus+='\nGPU-00000000-0000-0000-0000-000000000099,16311'
    if which=='capacity':configure(m,fit_target_mib=20000)
    if which=='hidden_gpu':monkeypatch.setenv('CUDA_VISIBLE_DEVICES','-1')
    if which=='fit_disabled':monkeypatch.setenv('LLAMA_ARG_FIT','off')
    with pytest.raises((ValueError,RuntimeError)):m.ensure()
    assert not m.children

def test_new_child_gets_only_project_fit_override_and_original_model_flags(launcher,monkeypatch):
    m=launcher;configure(m);versions=iter([None,'0.40.13']);m.read_version=lambda:next(versions)
    monkeypatch.setenv('SYNTHETIC_PRIVATE_ENV','not-to-be-written-in-report');before=dict(os.environ)
    result=m.ensure();assert result['status']=='STARTED' and result['launch_environment_applied']
    assert os.environ==before and len(m.children)==1
    command,options=m.children[0];env=options['env']
    assert command==[m.executable,'serve'] and env['LLAMA_ARG_FIT_TARGET']=='512'
    assert env['OLLAMA_HOST']=='127.0.0.1:11435' and env['OLLAMA_MODELS']=='D:/AIModels/Ollama-AURA'
    assert env['OLLAMA_NUM_PARALLEL']=='1' and env['OLLAMA_MAX_LOADED_MODELS']=='1' and env['OLLAMA_CONTEXT_LENGTH']=='2048' and env['OLLAMA_NO_CLOUD']=='1'
    record=json.loads((m.HERE/'project_ollama_process.json').read_text())
    assert record['ownership']['pid']==3210 and record['bindings']['executable_sha256']==hashlib.sha256(Path(m.executable).read_bytes()).hexdigest()
    assert not record['effective_runner_budget_verified'] and 'not-to-be-written' not in json.dumps(record)

def test_no_config_preserves_original_creation_environment_and_reuses_no_global_mutation(launcher):
    m=launcher;versions=iter([None,'0.40.13']);m.read_version=lambda:next(versions)
    result=m.ensure();env=m.children[0][1]['env']
    assert result['status']=='STARTED' and not result['runtime_policy_requested'] and 'LLAMA_ARG_FIT_TARGET' not in env
    assert not m.commands

def test_occupied_port_after_unready_health_does_not_spawn_or_replace(launcher):
    m=launcher;m.read_version=lambda:None;m.port_available=lambda:False
    with pytest.raises(RuntimeError,match='occupied'):m.ensure()
    assert not m.children

def test_new_ready_endpoint_must_belong_to_the_newly_created_exact_process(launcher):
    m=launcher;versions=iter([None,'0.40.13']);m.read_version=lambda:next(versions);m.owner['pid']=9999
    with pytest.raises(RuntimeError,match='another process'):m.ensure()
    assert len(m.children)==1 and not any('kill' in str(command).lower() or 'stop-process' in str(command).lower() for command,_ in m.commands)

@pytest.mark.parametrize('changed',[{'creation_utc':''},{'executable':None},
 {'listeners':[{'LocalAddress':'0.0.0.0','LocalPort':11435,'OwningProcess':3210}]},
 {'listeners':[{'LocalAddress':'127.0.0.1','LocalPort':11434,'OwningProcess':3210}]}])
def test_read_only_ownership_inspector_rejects_incomplete_or_wrong_listener(launcher,changed):
    m=launcher;value=dict(m.owner,**changed)
    def run(command,**options):
        assert command[0]=='powershell.exe' and 'Get-NetTCPConnection' in command[-1]
        assert 'Stop-Process' not in command[-1] and 'Terminate' not in command[-1]
        return types.SimpleNamespace(returncode=0,stdout=json.dumps(value).encode('utf-8'))
    m.subprocess.run=run
    with pytest.raises(RuntimeError):m.actual_inspector()
