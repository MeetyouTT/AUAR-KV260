
wire kernel_monitor_reset;
wire kernel_monitor_clock;
wire kernel_monitor_report;
assign kernel_monitor_reset = ~ap_rst_n;
assign kernel_monitor_clock = ap_clk;
assign kernel_monitor_report = 1'b0;
wire [2:0] axis_block_sigs;
wire [9:0] inst_idle_sigs;
wire [3:0] inst_block_sigs;
wire kernel_block;

assign axis_block_sigs[0] = ~grp_FrmbufWrHlsDataFlow_fu_166.AXIvideo2MultiPixStream_U0.grp_AXIvideo2MultiPixStream_Pipeline_loop_wait_for_start_fu_195.s_axis_video_TDATA_blk_n;
assign axis_block_sigs[1] = ~grp_FrmbufWrHlsDataFlow_fu_166.AXIvideo2MultiPixStream_U0.grp_AXIvideo2MultiPixStream_Pipeline_loop_width_fu_215.s_axis_video_TDATA_blk_n;
assign axis_block_sigs[2] = ~grp_FrmbufWrHlsDataFlow_fu_166.AXIvideo2MultiPixStream_U0.grp_AXIvideo2MultiPixStream_Pipeline_loop_wait_for_eol_fu_245.s_axis_video_TDATA_blk_n;

assign inst_idle_sigs[0] = grp_FrmbufWrHlsDataFlow_fu_166.entry_proc_U0.ap_idle;
assign inst_block_sigs[0] = (grp_FrmbufWrHlsDataFlow_fu_166.entry_proc_U0.ap_done & ~grp_FrmbufWrHlsDataFlow_fu_166.entry_proc_U0.ap_continue) | ~grp_FrmbufWrHlsDataFlow_fu_166.entry_proc_U0.HwReg_frm_buffer_c_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.entry_proc_U0.HwReg_frm_buffer2_c_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.entry_proc_U0.WidthInBytes_c9_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.entry_proc_U0.stride_c_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.entry_proc_U0.video_format_c11_blk_n;
assign inst_idle_sigs[1] = grp_FrmbufWrHlsDataFlow_fu_166.AXIvideo2MultiPixStream_U0.ap_idle;
assign inst_block_sigs[1] = (grp_FrmbufWrHlsDataFlow_fu_166.AXIvideo2MultiPixStream_U0.ap_done & ~grp_FrmbufWrHlsDataFlow_fu_166.AXIvideo2MultiPixStream_U0.ap_continue) | ~grp_FrmbufWrHlsDataFlow_fu_166.AXIvideo2MultiPixStream_U0.grp_AXIvideo2MultiPixStream_Pipeline_loop_width_fu_215.img_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.AXIvideo2MultiPixStream_U0.height_c10_blk_n;
assign inst_idle_sigs[2] = grp_FrmbufWrHlsDataFlow_fu_166.MultiPixStream2Bytes_U0.ap_idle;
assign inst_block_sigs[2] = (grp_FrmbufWrHlsDataFlow_fu_166.MultiPixStream2Bytes_U0.ap_done & ~grp_FrmbufWrHlsDataFlow_fu_166.MultiPixStream2Bytes_U0.ap_continue) | ~grp_FrmbufWrHlsDataFlow_fu_166.MultiPixStream2Bytes_U0.grp_MultiPixStream2Bytes_Pipeline_VITIS_LOOP_586_1_fu_198.img_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.MultiPixStream2Bytes_U0.grp_MultiPixStream2Bytes_Pipeline_VITIS_LOOP_586_1_fu_198.bytePlanes_plane01_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.MultiPixStream2Bytes_U0.grp_MultiPixStream2Bytes_Pipeline_VITIS_LOOP_586_1_fu_198.bytePlanes_plane12_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.MultiPixStream2Bytes_U0.Height_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.MultiPixStream2Bytes_U0.WidthInBytes_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.MultiPixStream2Bytes_U0.VideoFormat_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.MultiPixStream2Bytes_U0.WidthInBytes_c_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.MultiPixStream2Bytes_U0.height_c_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.MultiPixStream2Bytes_U0.video_format_c_blk_n;
assign inst_idle_sigs[3] = grp_FrmbufWrHlsDataFlow_fu_166.Bytes2AXIMMvideo_U0.ap_idle;
assign inst_block_sigs[3] = (grp_FrmbufWrHlsDataFlow_fu_166.Bytes2AXIMMvideo_U0.ap_done & ~grp_FrmbufWrHlsDataFlow_fu_166.Bytes2AXIMMvideo_U0.ap_continue) | ~grp_FrmbufWrHlsDataFlow_fu_166.Bytes2AXIMMvideo_U0.grp_Bytes2AXIMMvideo_Pipeline_VITIS_LOOP_1117_1_fu_198.bytePlanes_plane01_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.Bytes2AXIMMvideo_U0.grp_Bytes2AXIMMvideo_Pipeline_VITIS_LOOP_1127_2_fu_208.bytePlanes_plane12_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.Bytes2AXIMMvideo_U0.dstImg_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.Bytes2AXIMMvideo_U0.dstImg2_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.Bytes2AXIMMvideo_U0.Height_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.Bytes2AXIMMvideo_U0.WidthInBytes_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.Bytes2AXIMMvideo_U0.StrideInBytes_blk_n | ~grp_FrmbufWrHlsDataFlow_fu_166.Bytes2AXIMMvideo_U0.VideoFormat_blk_n;

assign inst_idle_sigs[4] = 1'b0;
assign inst_idle_sigs[5] = grp_FrmbufWrHlsDataFlow_fu_166.ap_idle;
assign inst_idle_sigs[6] = grp_FrmbufWrHlsDataFlow_fu_166.AXIvideo2MultiPixStream_U0.ap_idle;
assign inst_idle_sigs[7] = grp_FrmbufWrHlsDataFlow_fu_166.AXIvideo2MultiPixStream_U0.grp_AXIvideo2MultiPixStream_Pipeline_loop_wait_for_start_fu_195.ap_idle;
assign inst_idle_sigs[8] = grp_FrmbufWrHlsDataFlow_fu_166.AXIvideo2MultiPixStream_U0.grp_AXIvideo2MultiPixStream_Pipeline_loop_width_fu_215.ap_idle;
assign inst_idle_sigs[9] = grp_FrmbufWrHlsDataFlow_fu_166.AXIvideo2MultiPixStream_U0.grp_AXIvideo2MultiPixStream_Pipeline_loop_wait_for_eol_fu_245.ap_idle;

kv260_ispMipiRx_vcu_DP_v_frmbuf_wr_0_0_hls_deadlock_idx0_monitor kv260_ispMipiRx_vcu_DP_v_frmbuf_wr_0_0_hls_deadlock_idx0_monitor_U (
    .clock(kernel_monitor_clock),
    .reset(kernel_monitor_reset),
    .axis_block_sigs(axis_block_sigs),
    .inst_idle_sigs(inst_idle_sigs),
    .inst_block_sigs(inst_block_sigs),
    .block(kernel_block)
);


always @ (kernel_block or kernel_monitor_reset) begin
    if (kernel_block == 1'b1 && kernel_monitor_reset == 1'b0) begin
        find_kernel_block = 1'b1;
    end
    else begin
        find_kernel_block = 1'b0;
    end
end
