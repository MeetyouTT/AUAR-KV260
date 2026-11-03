"""Stop motion before waiting for network-reader cleanup."""


def stop_then_close_stream(session,stream):
    try:
        result=session.close()
    except BaseException:
        try:stream.close()
        except Exception:pass
        raise
    stream.close()
    return result
