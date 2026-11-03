#!/bin/sh
# PROPOSAL ONLY. Never force-unloads or replaces an already loaded driver.
set -eu
expected_kernel='5.15.36-xilinx-v2022.2'
expected_srcversion='9BDC942A6014BCCBD1DCB78'
module='/usr/local/lib/kv260-runtime-repair/zocl.ko'

[ "$(uname -r)" = "$expected_kernel" ] || {
    echo "unexpected kernel: $(uname -r)" >&2
    exit 1
}

if [ -r /sys/module/zocl/srcversion ]; then
    current=$(cat /sys/module/zocl/srcversion)
    if [ "$current" = "$expected_srcversion" ]; then
        [ "$(cat /sys/module/zocl/parameters/enable_xgq_ert)" = "1" ] || {
            echo "repaired ZOCL is loaded with an unexpected enable_xgq_ert value" >&2
            exit 1
        }
        exit 0
    fi
    echo "refusing to replace already loaded zocl srcversion=$current" >&2
    exit 1
fi

/sbin/insmod "$module" enable_xgq_ert=1
[ "$(cat /sys/module/zocl/srcversion)" = "$expected_srcversion" ] || {
    echo "loaded ZOCL srcversion does not match reviewed candidate" >&2
    exit 1
}
[ "$(cat /sys/module/zocl/parameters/enable_xgq_ert)" = "1" ] || {
    echo "repaired ZOCL loaded with an unexpected enable_xgq_ert value" >&2
    exit 1
}
