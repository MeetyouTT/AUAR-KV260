"""Compare live-report publication cost without any motion/device imports."""
import argparse,json,statistics,tempfile,time
from pathlib import Path
from live_report import bounded_live_report
from live_writer import LatestReportWriter


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--output-parent',type=Path,required=True)
    args=parser.parse_args();report=json.loads(args.report.read_text())
    report.pop('pre_stop_result',None)  # Final-only full trace is absent live.
    value=bounded_live_report(report,report['result'],report.get('observation_trace',[]),report['input_summary'],report['telemetry'])
    rows=[];delayed=[]
    with tempfile.TemporaryDirectory(prefix='live-writer-bench-',dir=args.output_parent) as directory:
        path=Path(directory)/'report.json'
        def write(raw,cancel=None):
            temp=path.with_name('temporary.json');temp.write_text(raw)
            if cancel is None or not cancel.is_set():temp.replace(path)
            elif temp.exists():temp.unlink()
        with LatestReportWriter(path,write=write) as writer:
            for index in range(12):
                # Alternate ordering; both modes include identical JSON encode.
                for asynchronous in ([False,True] if index%2==0 else [True,False]):
                    began=time.monotonic();raw=json.dumps(value,separators=(',',':'))+'\n'
                    if asynchronous:writer.submit(raw)
                    else:
                        # Separate path from the worker to avoid file races.
                        target=Path(directory)/'sync.json';temp=target.with_suffix('.tmp')
                        temp.write_text(raw);temp.replace(target)
                    rows.append(dict(asynchronous=asynchronous,main_publish_ms=round((time.monotonic()-began)*1000,3)))
                    time.sleep(.01)
            writer_stats=writer.diagnostics()
        def slow(raw,cancel):time.sleep(.05)
        with LatestReportWriter(path,write=slow) as writer:
            for _ in range(8):
                start=time.monotonic();writer.submit('{}\n')
                delayed.append(round((time.monotonic()-start)*1000,3));time.sleep(.02)
            slow_stats=writer.diagnostics()
    summary={str(mode):{'p50_ms':round(statistics.median(x['main_publish_ms'] for x in rows if x['asynchronous']==mode),3),
                       'max_ms':max(x['main_publish_ms'] for x in rows if x['asynchronous']==mode)} for mode in (False,True)}
    print(json.dumps(dict(status='LIVE_WRITER_READONLY_BENCH_DONE',payload_bytes=len(raw.encode()),
        samples=rows,summary=summary,writer=writer_stats,
        injected_50ms_writer_main_submit_ms=delayed,injected_writer=slow_stats,
        real_motor_commands=0,real_DPU_jobs=0,scope='live JSON encoding plus filesystem writes, and separately labeled injected writer stall; not mechanical delay')))


if __name__=='__main__':main()
