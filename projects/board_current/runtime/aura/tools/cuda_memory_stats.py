"""Per-inference allocator measurements, with no extra model load or sync."""
def begin(torch):
    try:
        if not torch.cuda.is_initialized():return {'initialized':False,'baseline_allocated_bytes':0,'baseline_reserved_bytes':0}
        value={'initialized':True,'baseline_allocated_bytes':int(torch.cuda.memory_allocated()),
               'baseline_reserved_bytes':int(torch.cuda.memory_reserved())}
        torch.cuda.reset_peak_memory_stats();return value
    except (RuntimeError,AttributeError):return None

def finish(torch,before,*,cache_hit=False,warmup=False):
    if cache_hit:return {'measured':False,'cache_hit':True,'warmup':bool(warmup)}
    if before is None:return {'measured':False,'cache_hit':False,'warmup':bool(warmup)}
    try:
        peak_allocated=int(torch.cuda.max_memory_allocated());peak_reserved=int(torch.cuda.max_memory_reserved())
        return dict(measured=True,cache_hit=False,warmup=bool(warmup),includes_cuda_initialization=not before['initialized'],
          baseline_allocated_bytes=before['baseline_allocated_bytes'],baseline_reserved_bytes=before['baseline_reserved_bytes'],
          peak_allocated_bytes=peak_allocated,peak_reserved_bytes=peak_reserved,
          allocated_extra_peak_bytes=max(0,peak_allocated-before['baseline_allocated_bytes']),
          reserved_extra_peak_bytes=max(0,peak_reserved-before['baseline_reserved_bytes']))
    except (RuntimeError,AttributeError):return {'measured':False,'cache_hit':False,'warmup':bool(warmup)}
