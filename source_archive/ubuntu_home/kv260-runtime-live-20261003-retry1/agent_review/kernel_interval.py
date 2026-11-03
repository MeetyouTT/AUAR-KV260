# SPDX-License-Identifier: MIT
"""Pure dmesg comparison for test-harness review. Does not execute board commands."""
import hashlib
import re

def compare_kernel_logs(before_raw,after_raw,allow_stock_remove=False):
    old=before_raw.decode('utf-8','replace').splitlines()
    new=after_raw.decode('utf-8','replace').splitlines()
    size=min(16,len(old))
    anchor=old[-size:] if size else []
    positions=[i for i in range(len(new)-size+1) if anchor and new[i:i+size]==anchor]
    unique=len(positions)==1
    index=positions[0] if unique else None
    new_lines=new[index+size:] if unique else []
    errors=[line for line in new_lines if re.search(
        r'BUG:|Oops:|Unable to handle|Kernel panic|Call trace:|ERROR|error|expected refcount',line)]
    permitted=[line for line in errors if 'expected refcount 1 instead of 2' in line and
               '/axi/zyxclmm_drm' in line] if allow_stock_remove else []
    allowed=allow_stock_remove and len(permitted)<=1 and permitted==errors
    unexpected=[] if allowed else errors
    prefix_removed=(len(old)-size-index) if unique and index<=len(old)-size else None
    return {'before_sha256':hashlib.sha256(before_raw).hexdigest(),
        'after_sha256':hashlib.sha256(after_raw).hexdigest(),
        'before_line_count':len(old),'after_line_count':len(new),
        'anchor_line_count':size,'anchor_old_index':len(old)-size,
        'anchor_sha256':hashlib.sha256('\n'.join(anchor).encode()).hexdigest(),
        'anchor_after_positions':positions,'continuity_confirmed':unique,
        'continuity_problem':None if unique else ('no_anchor' if not positions else 'ambiguous_anchor'),
        'old_prefix_removed_rows_estimate':prefix_removed,'new_lines':new_lines,
        'new_error_lines':errors,'permitted_stock_remove_errors':permitted if allowed else [],
        'unexpected_errors':unexpected,'allowed_once_known_stock_error':allow_stock_remove,
        'property_warnings':[line for line in new_lines if 'memory leak will occur' in line],
        'passed':unique and not unexpected}
