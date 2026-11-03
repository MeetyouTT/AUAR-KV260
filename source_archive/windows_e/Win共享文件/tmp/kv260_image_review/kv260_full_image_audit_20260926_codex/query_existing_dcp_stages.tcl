# Read-only checkpoint comparison. Opens existing DCPs without opening/modifying XPR.
set src_root /home/ghmd/kv260_clockfix_rebuild_20260926
set impl_dir "$src_root/kv260_dpu.runs/impl_1"
set out_path /home/ghmd/kv260_full_image_audit_20260926_codex/reports/reset_stage_connectivity.txt
file mkdir [file dirname $out_path]
set out [open $out_path w]

foreach stage {synth opt placed physopt routed} {
  if {$stage eq "synth"} {
    set dcp "$src_root/kv260_dpu.runs/synth_1/kv260_dpu_bd_wrapper.dcp"
  } else {
    set dcp "$impl_dir/kv260_dpu_bd_wrapper_${stage}.dcp"
  }
  puts $out "===== STAGE=$stage DCP=$dcp ====="
  if {![file exists $dcp]} {
    puts $out "MISSING_DCP"
    continue
  }
  if {[catch {open_checkpoint $dcp} err]} {
    puts $out "OPEN_ERROR=$err"
    continue
  }

  set reset_cells [get_cells -hier -quiet -filter {NAME =~ *rst_dpu_dsp*}]
  puts $out "RST_DPU_DSP_CELLS=[llength $reset_cells]"
  foreach cell $reset_cells {
    puts $out "RESET_CELL=$cell REF_NAME=[get_property REF_NAME $cell]"
  }

  foreach pin_name {dpu_2x_clk dpu_2x_resetn m_axi_dpu_aclk m_axi_dpu_aresetn} {
    set pin_name_full "kv260_dpu_bd_i/dpu_0/$pin_name"
    set pin_obj [get_pins -hier -quiet -filter "NAME == $pin_name_full"]
    if {[llength $pin_obj] == 0} {
      puts $out "DPU_PIN=$pin_name_full MISSING"
      continue
    }
    set pin [lindex $pin_obj 0]
    set connected unknown
    catch {set connected [get_property IS_CONNECTED $pin]}
    set nets [get_nets -quiet -of_objects $pin]
    puts $out "DPU_PIN=$pin REF_PIN=[get_property REF_PIN_NAME $pin] DIRECTION=[get_property DIRECTION $pin] IS_CONNECTED=$connected NETS=$nets CLOCKS=[get_clocks -quiet -of_objects $pin]"
    foreach net $nets {
      set peer_pins [get_pins -quiet -of_objects $net]
      puts $out "  NET_FANOUT=$net PIN_COUNT=[llength $peer_pins]"
      foreach peer $peer_pins {
        if {[regexp {dpu_0/(dpu_2x_resetn|m_axi_dpu_aresetn|dpu_2x_clk|m_axi_dpu_aclk)$|dpu_clk_wiz/(clk_dsp|clk_dpu)$|rst_dpu_(dsp|clk)/peripheral_aresetn\[0\]$|axi_mem_intercon_2/S00_ARESETN$} $peer]} {
          set cells [get_cells -quiet -of_objects $peer]
          set ref NA
          if {[llength $cells] > 0} { set ref [get_property REF_NAME $cells] }
          puts $out "    ENDPOINT_PIN=$peer DIR=[get_property DIRECTION $peer] CELL=$cells REF=$ref"
        }
      }
    }
  }

  foreach net [get_nets -hier -quiet -filter {NAME =~ *rst_dpu_dsp_peripheral_aresetn || NAME =~ *rst_dpu_clk_peripheral_aresetn}] {
    set netpins [get_pins -quiet -of_objects $net]
    puts $out "RESET_NET=$net PIN_COUNT=[llength $netpins]"
    foreach pin $netpins {
      if {[regexp {dpu_0/(dpu_2x_resetn|m_axi_dpu_aresetn)$|rst_dpu_(dsp|clk)/peripheral_aresetn\[0\]$|axi_mem_intercon_2/S00_ARESETN$} $pin]} {
        set cells [get_cells -quiet -of_objects $pin]
        set ref NA
        if {[llength $cells] > 0} { set ref [get_property REF_NAME $cells] }
        puts $out "  RESET_ENDPOINT_PIN=$pin DIR=[get_property DIRECTION $pin] CELL=$cells REF=$ref"
      }
    }
  }

  close_design
}
close $out
exit
