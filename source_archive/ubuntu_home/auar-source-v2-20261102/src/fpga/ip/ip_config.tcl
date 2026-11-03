# Package the two actual custom source modules into the NEW build directory.
# This script does not use an old IP cache or a placement checkpoint.
proc auar_configure_ips {root out vitis_root} {
    set part xck26-sfvc784-2LV-c
    foreach {name top rtl} {
        aura_visual_servo aura_m3_regs visual_servo.sv
        aura_disabled_audio aura_disabled_audio disabled_audio.sv
    } {
        create_project $name [file join $out ip_projects $name] -part $part
        add_files -norecurse [file join $root src fpga rtl $rtl]
        set_property top $top [current_fileset]
        update_compile_order -fileset sources_1
        ipx::package_project -root_dir [file join $out ip_repo $name] -vendor aura.local -library user -taxonomy /UserIP -import_files -set_current true
        set core [ipx::current_core]
        set_property name $name $core
        set_property version 1.0 $core
        if {$name eq "aura_visual_servo"} {
            set buses {S_AXI}
            set clocks {s_axi_aclk}
            set_property value 0x10282601 [ipx::get_user_parameters BUILD_ID -of_objects $core]
            set_property value 0x10282601 [ipx::get_hdl_parameters BUILD_ID -of_objects $core]
        } else {
            set buses {s_axi_ctrl_i2s_rx s_axi_ctrl_i2s_tx s_axi_lite_audio_fmt}
            set clocks {ACLK m_axi_aclk}
            foreach busname {m_axi_mm2s_audio m_axi_s2mm_audio} {
                set bus [ipx::get_bus_interfaces $busname -of_objects $core]
                set space [ipx::get_address_spaces $busname -of_objects $core]
                if {$space eq ""} {set space [ipx::add_address_space $busname $core]}
                set_property range 0x10000000000 $space
                set_property width 64 $space
                set_property master_address_space_ref $busname $bus
            }
        }
        foreach busname $buses {
            set bus [ipx::get_bus_interfaces $busname -of_objects $core]
            if {[llength $bus] != 1} {error "Missing custom interface $name/$busname"}
            set_property slave_memory_map_ref $busname $bus
            set mm [ipx::get_memory_maps $busname -of_objects $core]
            if {$mm eq ""} {set mm [ipx::add_memory_map $busname $core]}
            set blocks [ipx::get_address_blocks -of_objects $mm]
            if {[llength $blocks] == 0} {
                set block [ipx::add_address_block reg0 $mm]
            } else {
                set block [lindex $blocks 0]
            }
            set_property base_address 0 $block
            set_property range [expr {$name eq "aura_visual_servo" ? 4096 : 65536}] $block
            set_property width 32 $block
            set_property usage register $block
        }
        foreach clock $clocks {
            set bus [ipx::get_bus_interfaces $clock -of_objects $core]
            if {[llength [ipx::get_bus_parameters FREQ_HZ -of_objects $bus]]} {
                ipx::remove_bus_parameter FREQ_HZ $bus
            }
        }
        ipx::create_xgui_files $core
        ipx::update_checksums $core
        ipx::check_integrity $core
        ipx::save_core $core
        close_project
    }
    create_project platform [file join $out project] -part $part
    set_property board_part xilinx.com:kv260_som:part0:1.4 [current_project]
    set_property board_connections {som240_1_connector xilinx.com:kv260_carrier:som240_1_connector:1.3} [current_project]
    set_property ip_repo_paths [list [file join $out ip_repo] [file join $root third_party dpu] [file join $vitis_root data ip]] [current_project]
    set_property ip_output_repo [file join $out ip_cache] [current_project]
    update_ip_catalog
}
