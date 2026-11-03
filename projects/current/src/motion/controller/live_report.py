"""Bound live telemetry cost; complete traces are written after actuator STOP."""


def bounded_live_report(report,result,observations,input_summary,timing):
    value=dict(report)
    control=dict(result)
    control['command_trace']=list(result.get('command_trace',()))[-8:]
    control['events']=list(result.get('events',()))[-8:]
    value.update(result=control,observation_trace=list(observations)[-8:],
                 input_summary=input_summary,telemetry=dict(timing),
                 trace_scope='last_8_live; complete_bounded_traces_written_after_stop')
    return value
