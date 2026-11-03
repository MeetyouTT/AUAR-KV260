# Writes only to this audit's new directory; existing M3 RTL remains unchanged.
if {[catch {
    set out $::env(AURA_FPGA_REVIEW_OUT)
    set part xck26-sfvc784-2LV-c
    if {[llength [get_parts -quiet $part]] != 1} {error "K26 device support is unavailable"}
    set boards [get_board_parts "*:kv260_som:*" -latest_file_version]
    if {[llength $boards] != 1} {error "Expected one KV260 SOM board definition"}
    puts "AURA_K26_PART=$part"
    puts "AURA_KV260_BOARD=$boards"
    set_param general.maxThreads 2
    create_project env_clock [file join $out clock_project] -part $part
    set_property board_part $boards [current_project]
    create_ip -name clk_wiz -vendor xilinx.com -library ip -module_name env_clock_0
    generate_target all [get_ips env_clock_0]
    puts "AURA_CLOCK_PRODUCTS_READY"
    close_project

    set rtl /home/ghmd/kv260-m3-axilite-20261002/rtl
    create_project -in_memory -part $part
    set_property include_dirs [list $rtl] [current_fileset]
    read_verilog [file join $rtl aura_m3_regs.v]
    synth_design -top aura_m3_regs -mode out_of_context -part $part
    report_utilization -file [file join $out m3_current_synthesis_utilization.rpt]
    puts "AURA_M3_SYNTHESIS_COMPLETE"
    close_project
} result options]} {
    puts stderr "AURA_FPGA_ENV_ERROR=$result"
    exit 1
}
puts "AURA_FPGA_ENV_COMPLETE"
exit 0
