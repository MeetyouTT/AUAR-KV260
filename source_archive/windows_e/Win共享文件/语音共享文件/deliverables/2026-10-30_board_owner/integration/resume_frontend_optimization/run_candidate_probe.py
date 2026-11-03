"""Explicit fresh-process adapter for the parent's unchanged diagnostic probe.

No production file is replaced. All native runtime imports still happen inside
the probe's own priority/deadline scope. Baseline/optimization selection affects
only this process; the parent's proc-race fixes and safety guards stay intact.
"""
import argparse
import functools
import hashlib
import importlib.util
from pathlib import Path
import sys


def module_from(path,name):
    spec = importlib.util.spec_from_file_location(name,path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-mode',choices=('baseline','reuse','io','combined'),required=True)
    parser.add_argument('--probe-file',type=Path,required=True)
    parser.add_argument('--candidate-file',type=Path,default=Path(__file__).parent/'candidate/board_gtcrn_reuse.py')
    parser.add_argument('--code-root',type=Path,required=True)
    args,rest = parser.parse_known_args(argv)
    sys.path.insert(0,str(args.code_root.resolve()))
    candidate = module_from(args.candidate_file,'isolated_gtcrn_candidate')
    candidate.verify_baseline()
    import board.runtime.audio.board_gtcrn_fft as original
    reuse,binding = args.candidate_mode in ('reuse','combined'),args.candidate_mode in ('io','combined')
    if args.candidate_mode != 'baseline':
        original.BoardFftSpeechGate = functools.partial(candidate.ReuseFftSpeechGate,
                                                        buffer_reuse=reuse,io_binding=binding)
    probe = module_from(args.probe_file,'parent_audio_probe_unchanged')
    tags = dict(mode=args.candidate_mode,buffer_reuse=reuse,cpu_io_binding=binding,
        candidate_sha256=hashlib.sha256(args.candidate_file.read_bytes()).hexdigest(),
        baseline_sha256=candidate.BASELINE_SHA256,frontend_sha256=candidate.FRONTEND_SHA256,
        parent_probe_sha256=hashlib.sha256(args.probe_file.read_bytes()).hexdigest(),
        production_files_replaced=False)
    run = probe.run_probe
    def tagged_run(*a,**k):
        try:
            value = run(*a,**k)
            value['frontend_candidate'] = tags
            return value
        except probe.PublicPipelineFailure as exc:
            exc.diagnostics['frontend_candidate'] = tags
            raise
    probe.run_probe = tagged_run
    return probe.main(['--code-root',str(args.code_root)]+rest)


if __name__ == '__main__':
    raise SystemExit(main())
