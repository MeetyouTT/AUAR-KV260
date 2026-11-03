// Experimental USB-audio capacity profile. Legacy PL audio returns DECERR.
module aura_disabled_audio (ACLK, ARESETN, clk_out_audio, irq_i2s_rx, irq_i2s_tx, irq_mm2s_audio, irq_s2mm_audio, lrclk_rx, lrclk_tx, m_axi_aclk, m_axi_aresetn, m_axi_mm2s_audio_araddr, m_axi_mm2s_audio_arburst, m_axi_mm2s_audio_arcache, m_axi_mm2s_audio_arlen, m_axi_mm2s_audio_arlock, m_axi_mm2s_audio_arprot, m_axi_mm2s_audio_arqos, m_axi_mm2s_audio_arready, m_axi_mm2s_audio_arregion, m_axi_mm2s_audio_arsize, m_axi_mm2s_audio_aruser, m_axi_mm2s_audio_arvalid, m_axi_mm2s_audio_rdata, m_axi_mm2s_audio_rlast, m_axi_mm2s_audio_rready, m_axi_mm2s_audio_rresp, m_axi_mm2s_audio_rvalid, m_axi_s2mm_audio_awaddr, m_axi_s2mm_audio_awburst, m_axi_s2mm_audio_awcache, m_axi_s2mm_audio_awlen, m_axi_s2mm_audio_awlock, m_axi_s2mm_audio_awprot, m_axi_s2mm_audio_awqos, m_axi_s2mm_audio_awready, m_axi_s2mm_audio_awregion, m_axi_s2mm_audio_awsize, m_axi_s2mm_audio_awuser, m_axi_s2mm_audio_awvalid, m_axi_s2mm_audio_bready, m_axi_s2mm_audio_bresp, m_axi_s2mm_audio_bvalid, m_axi_s2mm_audio_wdata, m_axi_s2mm_audio_wlast, m_axi_s2mm_audio_wready, m_axi_s2mm_audio_wstrb, m_axi_s2mm_audio_wvalid, mclk_out_rx, mclk_out_tx, peripheral_aresetn, pl_clk1, pl_rstn1, s_axi_ctrl_i2s_rx_araddr, s_axi_ctrl_i2s_rx_arready, s_axi_ctrl_i2s_rx_arvalid, s_axi_ctrl_i2s_rx_awaddr, s_axi_ctrl_i2s_rx_awready, s_axi_ctrl_i2s_rx_awvalid, s_axi_ctrl_i2s_rx_bready, s_axi_ctrl_i2s_rx_bresp, s_axi_ctrl_i2s_rx_bvalid, s_axi_ctrl_i2s_rx_rdata, s_axi_ctrl_i2s_rx_rready, s_axi_ctrl_i2s_rx_rresp, s_axi_ctrl_i2s_rx_rvalid, s_axi_ctrl_i2s_rx_wdata, s_axi_ctrl_i2s_rx_wready, s_axi_ctrl_i2s_rx_wvalid, s_axi_ctrl_i2s_tx_araddr, s_axi_ctrl_i2s_tx_arready, s_axi_ctrl_i2s_tx_arvalid, s_axi_ctrl_i2s_tx_awaddr, s_axi_ctrl_i2s_tx_awready, s_axi_ctrl_i2s_tx_awvalid, s_axi_ctrl_i2s_tx_bready, s_axi_ctrl_i2s_tx_bresp, s_axi_ctrl_i2s_tx_bvalid, s_axi_ctrl_i2s_tx_rdata, s_axi_ctrl_i2s_tx_rready, s_axi_ctrl_i2s_tx_rresp, s_axi_ctrl_i2s_tx_rvalid, s_axi_ctrl_i2s_tx_wdata, s_axi_ctrl_i2s_tx_wready, s_axi_ctrl_i2s_tx_wvalid, s_axi_lite_audio_fmt_araddr, s_axi_lite_audio_fmt_arready, s_axi_lite_audio_fmt_arvalid, s_axi_lite_audio_fmt_awaddr, s_axi_lite_audio_fmt_awready, s_axi_lite_audio_fmt_awvalid, s_axi_lite_audio_fmt_bready, s_axi_lite_audio_fmt_bresp, s_axi_lite_audio_fmt_bvalid, s_axi_lite_audio_fmt_rdata, s_axi_lite_audio_fmt_rready, s_axi_lite_audio_fmt_rresp, s_axi_lite_audio_fmt_rvalid, s_axi_lite_audio_fmt_wdata, s_axi_lite_audio_fmt_wready, s_axi_lite_audio_fmt_wvalid, sclk_rx, sclk_tx, sdata_rx, sdata_tx);
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 ACLK CLK" *)
    (* X_INTERFACE_PARAMETER = "ASSOCIATED_BUSIF s_axi_ctrl_i2s_rx:s_axi_ctrl_i2s_tx:s_axi_lite_audio_fmt, ASSOCIATED_RESET ARESETN" *)
    input wire  ACLK;
    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 ARESETN RST" *)
    (* X_INTERFACE_PARAMETER = "POLARITY ACTIVE_LOW" *)
    input wire  ARESETN;
    output wire  clk_out_audio;
    output wire  irq_i2s_rx;
    output wire  irq_i2s_tx;
    output wire  irq_mm2s_audio;
    output wire  irq_s2mm_audio;
    output wire  lrclk_rx;
    output wire  lrclk_tx;
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 m_axi_aclk CLK" *)
    (* X_INTERFACE_PARAMETER = "ASSOCIATED_BUSIF m_axi_mm2s_audio:m_axi_s2mm_audio, ASSOCIATED_RESET m_axi_aresetn" *)
    input wire  m_axi_aclk;
    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 m_axi_aresetn RST" *)
    (* X_INTERFACE_PARAMETER = "POLARITY ACTIVE_LOW" *)
    input wire  m_axi_aresetn;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARADDR" *)
    (* X_INTERFACE_PARAMETER = "PROTOCOL AXI4, READ_WRITE_MODE READ_ONLY" *)
    output wire [63:0] m_axi_mm2s_audio_araddr;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARBURST" *)
    output wire [1:0] m_axi_mm2s_audio_arburst;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARCACHE" *)
    output wire [3:0] m_axi_mm2s_audio_arcache;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARLEN" *)
    output wire [7:0] m_axi_mm2s_audio_arlen;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARLOCK" *)
    output wire [0:0] m_axi_mm2s_audio_arlock;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARPROT" *)
    output wire [2:0] m_axi_mm2s_audio_arprot;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARQOS" *)
    output wire [3:0] m_axi_mm2s_audio_arqos;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARREADY" *)
    input wire  m_axi_mm2s_audio_arready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARREGION" *)
    output wire [3:0] m_axi_mm2s_audio_arregion;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARSIZE" *)
    output wire [2:0] m_axi_mm2s_audio_arsize;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARUSER" *)
    output wire [3:0] m_axi_mm2s_audio_aruser;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio ARVALID" *)
    output wire  m_axi_mm2s_audio_arvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RDATA" *)
    input wire [31:0] m_axi_mm2s_audio_rdata;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RLAST" *)
    input wire  m_axi_mm2s_audio_rlast;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RREADY" *)
    output wire  m_axi_mm2s_audio_rready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RRESP" *)
    input wire [1:0] m_axi_mm2s_audio_rresp;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_mm2s_audio RVALID" *)
    input wire  m_axi_mm2s_audio_rvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWADDR" *)
    (* X_INTERFACE_PARAMETER = "PROTOCOL AXI4, READ_WRITE_MODE WRITE_ONLY" *)
    output wire [63:0] m_axi_s2mm_audio_awaddr;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWBURST" *)
    output wire [1:0] m_axi_s2mm_audio_awburst;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWCACHE" *)
    output wire [3:0] m_axi_s2mm_audio_awcache;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWLEN" *)
    output wire [7:0] m_axi_s2mm_audio_awlen;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWLOCK" *)
    output wire [0:0] m_axi_s2mm_audio_awlock;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWPROT" *)
    output wire [2:0] m_axi_s2mm_audio_awprot;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWQOS" *)
    output wire [3:0] m_axi_s2mm_audio_awqos;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWREADY" *)
    input wire  m_axi_s2mm_audio_awready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWREGION" *)
    output wire [3:0] m_axi_s2mm_audio_awregion;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWSIZE" *)
    output wire [2:0] m_axi_s2mm_audio_awsize;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWUSER" *)
    output wire [3:0] m_axi_s2mm_audio_awuser;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio AWVALID" *)
    output wire  m_axi_s2mm_audio_awvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio BREADY" *)
    output wire  m_axi_s2mm_audio_bready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio BRESP" *)
    input wire [1:0] m_axi_s2mm_audio_bresp;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio BVALID" *)
    input wire  m_axi_s2mm_audio_bvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WDATA" *)
    output wire [31:0] m_axi_s2mm_audio_wdata;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WLAST" *)
    output wire  m_axi_s2mm_audio_wlast;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WREADY" *)
    input wire  m_axi_s2mm_audio_wready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WSTRB" *)
    output wire [3:0] m_axi_s2mm_audio_wstrb;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 m_axi_s2mm_audio WVALID" *)
    output wire  m_axi_s2mm_audio_wvalid;
    output wire  mclk_out_rx;
    output wire  mclk_out_tx;
    output wire [0:0] peripheral_aresetn;
    input wire  pl_clk1;
    input wire  pl_rstn1;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx ARADDR" *)
    (* X_INTERFACE_PARAMETER = "PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE" *)
    input wire [39:0] s_axi_ctrl_i2s_rx_araddr;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx ARREADY" *)
    output wire [0:0] s_axi_ctrl_i2s_rx_arready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx ARVALID" *)
    input wire [0:0] s_axi_ctrl_i2s_rx_arvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx AWADDR" *)
    input wire [39:0] s_axi_ctrl_i2s_rx_awaddr;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx AWREADY" *)
    output wire [0:0] s_axi_ctrl_i2s_rx_awready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx AWVALID" *)
    input wire [0:0] s_axi_ctrl_i2s_rx_awvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx BREADY" *)
    input wire [0:0] s_axi_ctrl_i2s_rx_bready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx BRESP" *)
    output wire [1:0] s_axi_ctrl_i2s_rx_bresp;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx BVALID" *)
    output wire [0:0] s_axi_ctrl_i2s_rx_bvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx RDATA" *)
    output wire [31:0] s_axi_ctrl_i2s_rx_rdata;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx RREADY" *)
    input wire [0:0] s_axi_ctrl_i2s_rx_rready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx RRESP" *)
    output wire [1:0] s_axi_ctrl_i2s_rx_rresp;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx RVALID" *)
    output wire [0:0] s_axi_ctrl_i2s_rx_rvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx WDATA" *)
    input wire [31:0] s_axi_ctrl_i2s_rx_wdata;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx WREADY" *)
    output wire [0:0] s_axi_ctrl_i2s_rx_wready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_rx WVALID" *)
    input wire [0:0] s_axi_ctrl_i2s_rx_wvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx ARADDR" *)
    (* X_INTERFACE_PARAMETER = "PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE" *)
    input wire [39:0] s_axi_ctrl_i2s_tx_araddr;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx ARREADY" *)
    output wire [0:0] s_axi_ctrl_i2s_tx_arready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx ARVALID" *)
    input wire [0:0] s_axi_ctrl_i2s_tx_arvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx AWADDR" *)
    input wire [39:0] s_axi_ctrl_i2s_tx_awaddr;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx AWREADY" *)
    output wire [0:0] s_axi_ctrl_i2s_tx_awready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx AWVALID" *)
    input wire [0:0] s_axi_ctrl_i2s_tx_awvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx BREADY" *)
    input wire [0:0] s_axi_ctrl_i2s_tx_bready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx BRESP" *)
    output wire [1:0] s_axi_ctrl_i2s_tx_bresp;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx BVALID" *)
    output wire [0:0] s_axi_ctrl_i2s_tx_bvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx RDATA" *)
    output wire [31:0] s_axi_ctrl_i2s_tx_rdata;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx RREADY" *)
    input wire [0:0] s_axi_ctrl_i2s_tx_rready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx RRESP" *)
    output wire [1:0] s_axi_ctrl_i2s_tx_rresp;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx RVALID" *)
    output wire [0:0] s_axi_ctrl_i2s_tx_rvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx WDATA" *)
    input wire [31:0] s_axi_ctrl_i2s_tx_wdata;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx WREADY" *)
    output wire [0:0] s_axi_ctrl_i2s_tx_wready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl_i2s_tx WVALID" *)
    input wire [0:0] s_axi_ctrl_i2s_tx_wvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt ARADDR" *)
    (* X_INTERFACE_PARAMETER = "PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE" *)
    input wire [39:0] s_axi_lite_audio_fmt_araddr;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt ARREADY" *)
    output wire [0:0] s_axi_lite_audio_fmt_arready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt ARVALID" *)
    input wire [0:0] s_axi_lite_audio_fmt_arvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt AWADDR" *)
    input wire [39:0] s_axi_lite_audio_fmt_awaddr;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt AWREADY" *)
    output wire [0:0] s_axi_lite_audio_fmt_awready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt AWVALID" *)
    input wire [0:0] s_axi_lite_audio_fmt_awvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt BREADY" *)
    input wire [0:0] s_axi_lite_audio_fmt_bready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt BRESP" *)
    output wire [1:0] s_axi_lite_audio_fmt_bresp;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt BVALID" *)
    output wire [0:0] s_axi_lite_audio_fmt_bvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt RDATA" *)
    output wire [31:0] s_axi_lite_audio_fmt_rdata;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt RREADY" *)
    input wire [0:0] s_axi_lite_audio_fmt_rready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt RRESP" *)
    output wire [1:0] s_axi_lite_audio_fmt_rresp;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt RVALID" *)
    output wire [0:0] s_axi_lite_audio_fmt_rvalid;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt WDATA" *)
    input wire [31:0] s_axi_lite_audio_fmt_wdata;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt WREADY" *)
    output wire [0:0] s_axi_lite_audio_fmt_wready;
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_lite_audio_fmt WVALID" *)
    input wire [0:0] s_axi_lite_audio_fmt_wvalid;
    output wire  sclk_rx;
    output wire  sclk_tx;
    input wire  sdata_rx;
    output wire  sdata_tx;
    aura_audio_decerr s_axi_ctrl_i2s_rx_stub(.clk(ACLK),.resetn(ARESETN),
        .awvalid(s_axi_ctrl_i2s_rx_awvalid), .awready(s_axi_ctrl_i2s_rx_awready), .wvalid(s_axi_ctrl_i2s_rx_wvalid), .wready(s_axi_ctrl_i2s_rx_wready), .bvalid(s_axi_ctrl_i2s_rx_bvalid), .bready(s_axi_ctrl_i2s_rx_bready), .bresp(s_axi_ctrl_i2s_rx_bresp), .arvalid(s_axi_ctrl_i2s_rx_arvalid), .arready(s_axi_ctrl_i2s_rx_arready), .rvalid(s_axi_ctrl_i2s_rx_rvalid), .rready(s_axi_ctrl_i2s_rx_rready), .rresp(s_axi_ctrl_i2s_rx_rresp), .rdata(s_axi_ctrl_i2s_rx_rdata));
    aura_audio_decerr s_axi_ctrl_i2s_tx_stub(.clk(ACLK),.resetn(ARESETN),
        .awvalid(s_axi_ctrl_i2s_tx_awvalid), .awready(s_axi_ctrl_i2s_tx_awready), .wvalid(s_axi_ctrl_i2s_tx_wvalid), .wready(s_axi_ctrl_i2s_tx_wready), .bvalid(s_axi_ctrl_i2s_tx_bvalid), .bready(s_axi_ctrl_i2s_tx_bready), .bresp(s_axi_ctrl_i2s_tx_bresp), .arvalid(s_axi_ctrl_i2s_tx_arvalid), .arready(s_axi_ctrl_i2s_tx_arready), .rvalid(s_axi_ctrl_i2s_tx_rvalid), .rready(s_axi_ctrl_i2s_tx_rready), .rresp(s_axi_ctrl_i2s_tx_rresp), .rdata(s_axi_ctrl_i2s_tx_rdata));
    aura_audio_decerr s_axi_lite_audio_fmt_stub(.clk(ACLK),.resetn(ARESETN),
        .awvalid(s_axi_lite_audio_fmt_awvalid), .awready(s_axi_lite_audio_fmt_awready), .wvalid(s_axi_lite_audio_fmt_wvalid), .wready(s_axi_lite_audio_fmt_wready), .bvalid(s_axi_lite_audio_fmt_bvalid), .bready(s_axi_lite_audio_fmt_bready), .bresp(s_axi_lite_audio_fmt_bresp), .arvalid(s_axi_lite_audio_fmt_arvalid), .arready(s_axi_lite_audio_fmt_arready), .rvalid(s_axi_lite_audio_fmt_rvalid), .rready(s_axi_lite_audio_fmt_rready), .rresp(s_axi_lite_audio_fmt_rresp), .rdata(s_axi_lite_audio_fmt_rdata));
    assign clk_out_audio = '0;
    assign irq_i2s_rx = '0;
    assign irq_i2s_tx = '0;
    assign irq_mm2s_audio = '0;
    assign irq_s2mm_audio = '0;
    assign lrclk_rx = '0;
    assign lrclk_tx = '0;
    assign m_axi_mm2s_audio_araddr = '0;
    assign m_axi_mm2s_audio_arburst = '0;
    assign m_axi_mm2s_audio_arcache = '0;
    assign m_axi_mm2s_audio_arlen = '0;
    assign m_axi_mm2s_audio_arlock = '0;
    assign m_axi_mm2s_audio_arprot = '0;
    assign m_axi_mm2s_audio_arqos = '0;
    assign m_axi_mm2s_audio_arregion = '0;
    assign m_axi_mm2s_audio_arsize = '0;
    assign m_axi_mm2s_audio_aruser = '0;
    assign m_axi_mm2s_audio_arvalid = '0;
    assign m_axi_mm2s_audio_rready = '0;
    assign m_axi_s2mm_audio_awaddr = '0;
    assign m_axi_s2mm_audio_awburst = '0;
    assign m_axi_s2mm_audio_awcache = '0;
    assign m_axi_s2mm_audio_awlen = '0;
    assign m_axi_s2mm_audio_awlock = '0;
    assign m_axi_s2mm_audio_awprot = '0;
    assign m_axi_s2mm_audio_awqos = '0;
    assign m_axi_s2mm_audio_awregion = '0;
    assign m_axi_s2mm_audio_awsize = '0;
    assign m_axi_s2mm_audio_awuser = '0;
    assign m_axi_s2mm_audio_awvalid = '0;
    assign m_axi_s2mm_audio_bready = '0;
    assign m_axi_s2mm_audio_wdata = '0;
    assign m_axi_s2mm_audio_wlast = '0;
    assign m_axi_s2mm_audio_wstrb = '0;
    assign m_axi_s2mm_audio_wvalid = '0;
    assign mclk_out_rx = '0;
    assign mclk_out_tx = '0;
    assign peripheral_aresetn = '0;
    assign sclk_rx = '0;
    assign sclk_tx = '0;
    assign sdata_tx = '0;
endmodule

// Unused AXI-Lite endpoint: complete independent AW/W and return DECERR.
`timescale 1ns/1ps
module aura_audio_decerr(
    input wire clk,resetn,awvalid,wvalid,bready,arvalid,rready,
    output wire awready,wready,arready,
    output reg bvalid,rvalid,
    output wire [1:0] bresp,rresp,
    output wire [31:0] rdata
);
    reg aw_pending,w_pending;
    assign awready=resetn && !aw_pending && !bvalid;
    assign wready=resetn && !w_pending && !bvalid;
    assign arready=resetn && !rvalid;
    assign bresp=2'b11;
    assign rresp=2'b11;
    assign rdata=0;
    always @(posedge clk) begin
        if(!resetn) begin aw_pending<=0;w_pending<=0;bvalid<=0;rvalid<=0;end
        else begin
            if(awvalid && awready)aw_pending<=1;
            if(wvalid && wready)w_pending<=1;
            if(aw_pending && w_pending && !bvalid) begin
                aw_pending<=0;w_pending<=0;bvalid<=1;
            end
            if(bvalid && bready)bvalid<=0;
            if(arvalid && arready)rvalid<=1;
            if(rvalid && rready)rvalid<=0;
        end
    end
endmodule
