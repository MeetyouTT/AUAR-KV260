"""Compare deterministic reachable traces to the pinned production Python policy.

The harness supplies the same qualified-success filtering and ordinary-admission
precondition as the production scheduler. No model or gate is instantiated.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import subprocess

reference = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_vision_recovery_and_admission/candidate/aura/board/vision/dpu_recovery_policy.py')
spec = importlib.util.spec_from_file_location('production_recovery_reference', reference)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
phases = {'RUNNING': 0, 'COOLDOWN': 1, 'PROBATION': 2, 'LATCHED': 3}
reasons = {None: 0, 'unsafe_or_unknown_completion': 1, 'recovery_budget_exhausted': 2,
           'completed_hardcap_only': 3, 'primary_overrun_after_fault': 4,
           'primary_overrun_during_probation': 5}
second = 10 ** 9


def snapshot(policy, accepted):
    return dict(accepted=accepted, phase=phases[policy.phase], reason=reasons[policy.reason],
                faults=policy.faults, attempts=policy.attempts, recoveries=policy.recoveries,
                probe_successes=policy.probe_successes,
                cooldown_until_ns=round(policy.cooldown_until * second),
                fault_primary_calls=policy.fault_primary_calls,
                fault_primary_overruns=policy.fault_primary_overruns,
                attempt_times=[round(t * second) for t in policy.attempt_times])


comparisons = 0
for seed in range(24):
    rng = random.Random(seed)
    policy = module.YuNetRecoveryPolicy()
    now, calls, overruns = 100 * second, 10, 0
    commands, expected = [], []
    for step in range(160):
        now += rng.choice([0, 1, 1000000, second // 10, second, 10 * second, 600 * second])
        calls += rng.choice([0, 1, 2])
        last = now - rng.choice([0, second // 2, second // 2 + 1])
        if policy.phase == 'RUNNING':
            operation = rng.choice(['F', 'F', 'D', 'S'])
        elif policy.phase == 'COOLDOWN':
            operation = rng.choice(['D', 'A', 'A', 'P'])
        elif policy.phase == 'PROBATION':
            operation = rng.choice(['S', 'S', 'S', 'S', 'F', 'P'])
        else:
            operation = rng.choice(['D', 'S', 'P'])
        if operation == 'F':
            safe = rng.random() < .85
            completed, body, hardcap, guard = (1, 0, 1, 0) if safe else rng.choice([
                (0, 0, 1, 0), (1, 1, 1, 0), (1, 0, 1, 1), (1, 0, 0, 0)])
            commands.append(f'F {now} {completed} {body} {hardcap} {guard} {calls} {overruns} {last} 1')
            policy.fault(now / second, completed=bool(completed), body_failed=bool(body),
                         hardcap=bool(hardcap), guard=bool(guard), primary_calls=calls,
                         primary_overruns=overruns)
            accepted = True
        elif operation in ('D', 'A'):
            commands.append(f'{operation} {now} {calls} {overruns} {last} 1')
            accepted = policy.due(now / second, primary_calls=calls, primary_overruns=overruns,
                                  last_primary=last / second)
            if operation == 'A' and accepted:
                policy.admitted(now / second)
        elif operation == 'P':
            commands.append('P')
            if policy.phase == 'PROBATION':
                calls += 1
                overruns += 1
            accepted = policy.primary_failed()
        else:
            submitted = rng.random() > .1
            completed = submitted and rng.random() > .1
            usable = rng.random() > .1
            status = 0 if rng.random() > .1 else 1
            expires = now + rng.choice([-1, 0, second])
            commands.append(f'S {now} {int(submitted)} {int(completed)} {int(usable)} {status} {expires}')
            before = policy.phase
            if submitted and completed and usable and status == 0 and now < expires:
                policy.success()
            accepted = before == 'PROBATION' and policy.phase == 'RUNNING'
        expected.append(snapshot(policy, accepted))
    run = subprocess.run([str(Path(__file__).resolve().with_name('recovery_trace'))],
                         input='\n'.join(commands) + '\n', text=True, capture_output=True,
                         timeout=5, check=True)
    actual = [json.loads(line) for line in run.stdout.splitlines()]
    assert len(actual) == len(expected)
    for index, (left, right) in enumerate(zip(actual, expected)):
        assert left == right, {'seed': seed, 'step': index, 'command': commands[index],
                               'native': left, 'python': right}
        comparisons += 1
print(json.dumps({'passed': True, 'traces': 24, 'state_comparisons': comparisons,
                  'python_reference_sha256': hashlib.sha256(reference.read_bytes()).hexdigest(),
                  'scope': 'standalone policy parity with scheduler-qualified probes; no gate/VART/DPU'}))
