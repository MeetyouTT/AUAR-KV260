"""Default-off CPU-role experiment for one pinned, isolated camera process."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import threading

from thread_affinity_trial import AffinityTrial, Journal, checked_policy

ALLOWED_ROOT = Path('/home/root/aura-dpu-vision-20261021/affinity-live')
CAMERA_SHA = '1e0e6f0b8881c2d4d4cf81a2527e79d063e673eeba1d069e33bdde2608303005'
ROLE_SOURCES = {
    'camera-detection': ('board/vision/ui_camera_service.py', 'run.<locals>.inference',
        'a55abb900a94096c33e3dd2ecfe895e44b3821ac9eccb892c8c822e73cb017d4'),
    'camera-live-preview': ('board/vision/ui_camera_service.py', 'run.<locals>.preview',
        'a55abb900a94096c33e3dd2ecfe895e44b3821ac9eccb892c8c822e73cb017d4'),
    'camera-face-targets': ('board/identity/face_targets.py', 'FaceTargetService.work',
        'd03e2aee39a43f31705494dd679ad4ce7d9b49ddf7bd1185f5e021cdb8990aa0'),
    'camera-identity': ('board/identity/live.py', 'IdentityService.work',
        '92ff7ea739c92942b37f60158bdbdec517596ce33fcc0113766e8f2a8fff2044'),
    'sface-dpu-shadow': ('board/identity/sface_shadow.py', 'SFaceShadow.work',
        '69ae50d51ec325b79e264dc49f61e70d7d578fb1ed4f43f4fcc32235382059b5'),
    'sface-crop-prepare': ('board/identity/sface_producer.py', 'SFaceProducer.work',
        '663ae00fa98888767959c528c3d479a2ba9952d3975ef1a17b897623b3274a8e'),
}


def target_matches(thread, source):
    target = getattr(thread, '_target', None)
    function = getattr(target, '__func__', target)
    code = getattr(function, '__code__', None)
    if code is None or getattr(function, '__qualname__', None) != source[1]:
        return False
    return Path(code.co_filename).resolve() == source[0]


def launch(argv, *, allowed_root=ALLOWED_ROOT, expected_sha=CAMERA_SHA,
           role_sources=ROLE_SOURCES, record_directory=None, runner=runpy.run_path,
           trial_factory=AffinityTrial, journal_factory=Journal):
    enabled = os.environ.get('AURA_EXPERIMENT_AFFINITY')
    if enabled not in (None, '0', '1'):
        raise ValueError('AURA_EXPERIMENT_AFFINITY accepts only 0 or 1')
    if not argv:
        raise ValueError('Pinned camera entrypoint required')
    target = Path(argv[0])
    if (not target.is_absolute() or target.resolve(strict=True) != target
            or allowed_root.resolve() not in target.parents or target.name != 'board_camera_motion.py'
            or hashlib.sha256(target.read_bytes()).hexdigest() != expected_sha):
        raise ValueError('Camera entrypoint differs from the pinned experiment')
    old_argv = sys.argv
    trial = journal = None
    original_run = threading.Thread.run
    try:
        if enabled == '1':
            if (os.environ.get('AURA_EXPERIMENT_GIL_MS') is not None
                    or abs(sys.getswitchinterval() - .005) > 1e-9):
                raise ValueError('Affinity trial requires the original 5ms GIL setting')
            policy_path = Path(os.environ['AURA_EXPERIMENT_AFFINITY_POLICY'])
            if not policy_path.is_absolute() or policy_path.resolve(strict=True) != policy_path:
                raise ValueError('Explicit absolute nonsymlink policy file required')
            policy_bytes = policy_path.read_bytes()
            policy = json.loads(policy_bytes)
            masks = checked_policy(policy, os.sched_getaffinity(0))
            sources = {}
            aura_root = target.parents[1]
            for role in masks:
                relative, qualname, digest = role_sources[role]
                path = aura_root / relative
                if (path.resolve(strict=True) != path
                        or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
                    raise ValueError('Pinned role source differs: ' + role)
                sources[role] = path, qualname
            journal = journal_factory(record_directory or Path(__file__).parent)
            journal({'event': 'PROCESS_BASELINE', 'pid': os.getpid(),
                     'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                     'allowed_cpus': sorted(os.sched_getaffinity(0)),
                     'gil_seconds': sys.getswitchinterval(), 'target_sha256': expected_sha,
                     'role_source_sha256': {role: role_sources[role][2] for role in masks},
                     'policy_sha256': hashlib.sha256(policy_bytes).hexdigest(),
                     'scope': 'current selected Python threads in this isolated process only'})
            trial = trial_factory(masks, journal)

            def scoped_run(thread):
                name = thread.name
                if name not in role_sources:
                    return original_run(thread)
                if (name not in sources or not target_matches(thread, sources[name])
                        or threading.current_thread() is not thread):
                    trial.reject('Unreviewed thread binding or unexpected configured role: ' + name)
                    return
                with trial.role(name):
                    return original_run(thread)

            threading.Thread.run = scoped_run
        sys.argv = list(argv)
        return runner(str(target), run_name='__main__')
    finally:
        sys.argv = old_argv
        threading.Thread.run = original_run
        try:
            if trial is not None:
                trial.close()
        finally:
            if journal is not None:
                journal.close()


if __name__ == '__main__':
    launch(sys.argv[1:])
