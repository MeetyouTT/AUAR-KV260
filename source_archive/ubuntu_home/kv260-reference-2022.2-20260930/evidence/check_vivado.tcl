puts "VIVADO_VERSION=[version -short]"
set boards [get_board_parts "*:kv260_som:*" -latest_file_version]
puts "KV260_BOARDS=[join $boards { }]"
set parts [get_parts "xck26*"]
puts "K26_PARTS=[join $parts { }]"
create_project -in_memory -part xck26-sfvc784-2LV-c
puts "PS_IP=[join [get_ipdefs -all "xilinx.com:ip:zynq_ultra_ps_e:*"] { }]"
exit
