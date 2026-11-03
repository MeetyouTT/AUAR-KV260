"""Bounded child termination without depending on possibly broken stdout pipes."""
import signal


def describe(error):
    try:return type(error).__name__+': '+str(error)[:160]
    except BaseException:return type(error).__name__


def terminate_follow_child(child,*,term_timeout=2.,kill_timeout=2.):
    result=dict(exit_confirmed=False,pid=getattr(child,'pid',None),returncode=None,
                term_requested=False,kill_requested=False,errors=[])
    try:
        code=child.poll()
        if type(code) is int:
            result.update(exit_confirmed=True,returncode=code);return result
    except BaseException as exc:result['errors'].append(describe(exc))
    try:
        child.send_signal(signal.SIGTERM);result['term_requested']=True
    except BaseException as exc:result['errors'].append(describe(exc))
    try:
        code=child.wait(timeout=term_timeout)
        if type(code) is int:
            result.update(exit_confirmed=True,returncode=code);return result
        result['errors'].append('Invalid non-integer child wait result')
    except BaseException as exc:result['errors'].append(describe(exc))
    try:
        child.kill();result['kill_requested']=True
    except BaseException as exc:result['errors'].append(describe(exc))
    try:
        code=child.wait(timeout=kill_timeout)
        if type(code) is int:result.update(exit_confirmed=True,returncode=code)
        else:result['errors'].append('Invalid non-integer child wait result')
    except BaseException as exc:result['errors'].append(describe(exc))
    return result
