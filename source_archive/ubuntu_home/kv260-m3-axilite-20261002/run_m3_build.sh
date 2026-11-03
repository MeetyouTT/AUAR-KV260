#!/usr/bin/env bash
set -eo pipefail
m3_root=${AURA_M3_PROJECT_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)}
source /home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh
export TRD_PATH="$m3_root/dependencies/DPUCZDX8G_VAI_v3.0"
m3_overlay="$m3_root/src/kv260/overlays/examples/benchmark"
m3_platform="$m3_root/src/kv260/platforms/xilinx_kv260_ispMipiRx_vcu_DP_202220_1/kv260_ispMipiRx_vcu_DP.xpfm"
cd "$m3_root"
case "${1:-}" in
    ip)
        python3 "$m3_root/scripts/build_identity.py"
        vivado -mode batch -source "$m3_root/scripts/package_m3.tcl" \
            -log "$m3_root/logs/package_m3_vivado.log" \
            -journal "$m3_root/logs/package_m3_vivado.jou"
        ;;
    platform)
        test -f "$m3_root/ip_repo/aura_m3_regs/component.xml"
        make -C "$m3_root/src/kv260" platform PFM=kv260_ispMipiRx_vcu_DP \
            JOBS=4 XSCT="$XILINX_VITIS/bin/xsct -nodisp"
        ;;
    resume-platform)
        vivado -mode batch -source "$m3_root/scripts/resume_platform.tcl" \
            -log "$m3_root/logs/resume_platform_vivado.log" \
            -journal "$m3_root/logs/resume_platform_vivado.jou"
        make -C "$m3_root/src/kv260" platform PFM=kv260_ispMipiRx_vcu_DP \
            JOBS=4 XSCT="$XILINX_VITIS/bin/xsct -nodisp"
        ;;
    overlay)
        test -f "$m3_platform"
        make -C "$m3_overlay" all PLATFORM="$m3_platform" JOBS=4 \
            VPP='v++ --vivado.synth.jobs 4 --vivado.impl.jobs 4'
        ;;
    review|review-finalize)
        if [[ "$1" == review ]]; then
            vivado -mode batch -source "$m3_root/scripts/review_routed.tcl" \
                -log "$m3_root/logs/review_routed_vivado.log" \
                -journal "$m3_root/logs/review_routed_vivado.jou"
        else
            test -f "$m3_root/evidence/postroute/timing_summary.rpt"
            test -f "$m3_root/evidence/postroute/route_status.rpt"
            test -f "$m3_root/evidence/postroute/endpoint_clocks.tsv"
        fi
        m3_xclbin="$m3_overlay/binary_container_1/sd_card/dpu.xclbin"
        xclbinutil --input "$m3_xclbin" --info > "$m3_root/evidence/xclbin_info.txt"
        for m3_section in IP_LAYOUT CONNECTIVITY MEM_TOPOLOGY; do
            xclbinutil --input "$m3_xclbin" --force \
                --dump-section "$m3_section:JSON:$m3_root/evidence/xclbin_$m3_section.json"
        done
        m3_parent_xclbin=/home/ghmd/kv260-dpu41-control-20261001/test_bundle/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/kv260-benchmark-b4096-dpu41.xclbin
        xclbinutil --input "$m3_parent_xclbin" --force \
            --dump-section "MEM_TOPOLOGY:JSON:$m3_root/evidence/validated_parent_MEM_TOPOLOGY.json"
        python3 "$m3_root/scripts/audit_inputs.py"
        python3 "$m3_root/scripts/summarize_host_review.py"
        python3 "$m3_root/scripts/collect_artifacts.py"
        ;;
    *)
        echo 'Usage: bash run_m3_build.sh ip|platform|resume-platform|overlay|review|review-finalize' >&2
        exit 2
        ;;
esac
