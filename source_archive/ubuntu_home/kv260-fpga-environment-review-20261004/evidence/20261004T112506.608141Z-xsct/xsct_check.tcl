if {[catch {
    set xsa /home/ghmd/kv260-m3-axilite-20261002/src/kv260/overlays/examples/benchmark/binary_container_1/dpu.xsa
    hsi::open_hw_design $xsa
    puts "AURA_XSA_DESIGN=[hsi::current_hw_design]"
    puts "AURA_XSA_CELL_COUNT=[llength [hsi::get_cells -hier]]"
    hsi::close_hw_design [hsi::current_hw_design]
} result options]} {
    puts stderr "AURA_XSCT_ENV_ERROR=$result"
    exit 1
}
puts "AURA_XSA_READ_COMPLETE"
exit 0
