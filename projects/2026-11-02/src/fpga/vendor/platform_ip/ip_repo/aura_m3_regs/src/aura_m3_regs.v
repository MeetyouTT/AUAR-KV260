// AURA M3: identification and scratch registers, no external outputs.
`timescale 1ns / 1ps
`include "m3_build_id.vh"

module aura_m3_regs (
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 s_axi_aclk CLK" *)
    (* X_INTERFACE_PARAMETER = "ASSOCIATED_BUSIF S_AXI, ASSOCIATED_RESET s_axi_aresetn" *)
    input wire s_axi_aclk,
    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 s_axi_aresetn RST" *)
    (* X_INTERFACE_PARAMETER = "POLARITY ACTIVE_LOW" *)
    input wire s_axi_aresetn,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWADDR" *)
    (* X_INTERFACE_PARAMETER = "PROTOCOL AXI4LITE, DATA_WIDTH 32, ADDR_WIDTH 12, READ_WRITE_MODE READ_WRITE" *)
    input wire [11:0] s_axi_awaddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWPROT" *)
    input wire [2:0] s_axi_awprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWVALID" *)
    input wire s_axi_awvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWREADY" *)
    output wire s_axi_awready,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WDATA" *)
    input wire [31:0] s_axi_wdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WSTRB" *)
    input wire [3:0] s_axi_wstrb,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WVALID" *)
    input wire s_axi_wvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WREADY" *)
    output wire s_axi_wready,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BRESP" *)
    output reg [1:0] s_axi_bresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BVALID" *)
    output reg s_axi_bvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BREADY" *)
    input wire s_axi_bready,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARADDR" *)
    input wire [11:0] s_axi_araddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARPROT" *)
    input wire [2:0] s_axi_arprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARVALID" *)
    input wire s_axi_arvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARREADY" *)
    output wire s_axi_arready,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *)
    output reg [31:0] s_axi_rdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RRESP" *)
    output reg [1:0] s_axi_rresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RVALID" *)
    output reg s_axi_rvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RREADY" *)
    input wire s_axi_rready
);

    localparam [31:0] IP_ID = 32'h41555241;
    localparam [31:0] ABI_VERSION = 32'h00010000;
    localparam [31:0] BUILD_ID = `AURA_M3_BUILD_ID;
    localparam [1:0] RESP_OKAY = 2'b00;
    localparam [1:0] RESP_SLVERR = 2'b10;

    reg aw_pending;
    reg [11:0] aw_address;
    reg w_pending;
    reg [31:0] w_data;
    reg [3:0] w_strobes;
    reg [31:0] scratch;
    integer byte_index;

    // AW and W are accepted independently; no simultaneous-arrival assumption.
    // Responses remain registered and stable until the master's handshake.
    assign s_axi_awready = s_axi_aresetn && !aw_pending && !s_axi_bvalid;
    assign s_axi_wready = s_axi_aresetn && !w_pending && !s_axi_bvalid;
    assign s_axi_arready = s_axi_aresetn && !s_axi_rvalid;

    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            aw_pending <= 1'b0;
            aw_address <= 12'b0;
            w_pending <= 1'b0;
            w_data <= 32'b0;
            w_strobes <= 4'b0;
            scratch <= 32'b0;
            s_axi_bvalid <= 1'b0;
            s_axi_bresp <= RESP_OKAY;
            s_axi_rvalid <= 1'b0;
            s_axi_rdata <= 32'b0;
            s_axi_rresp <= RESP_OKAY;
        end else begin
            if (s_axi_awvalid && s_axi_awready) begin
                aw_pending <= 1'b1;
                aw_address <= s_axi_awaddr;
            end
            if (s_axi_wvalid && s_axi_wready) begin
                w_pending <= 1'b1;
                w_data <= s_axi_wdata;
                w_strobes <= s_axi_wstrb;
            end
            if (s_axi_bvalid && s_axi_bready)
                s_axi_bvalid <= 1'b0;

            if (aw_pending && w_pending && !s_axi_bvalid) begin
                aw_pending <= 1'b0;
                w_pending <= 1'b0;
                s_axi_bvalid <= 1'b1;
                s_axi_bresp <= RESP_SLVERR;
                if (aw_address == 12'h00c) begin
                    s_axi_bresp <= RESP_OKAY;
                    for (byte_index = 0; byte_index < 4; byte_index = byte_index + 1)
                        if (w_strobes[byte_index])
                            scratch[byte_index*8 +: 8] <= w_data[byte_index*8 +: 8];
                end
            end

            if (s_axi_rvalid && s_axi_rready)
                s_axi_rvalid <= 1'b0;
            if (s_axi_arvalid && s_axi_arready) begin
                s_axi_rvalid <= 1'b1;
                s_axi_rresp <= RESP_OKAY;
                case (s_axi_araddr)
                    12'h000: s_axi_rdata <= IP_ID;
                    12'h004: s_axi_rdata <= ABI_VERSION;
                    12'h008: s_axi_rdata <= BUILD_ID;
                    12'h00c: s_axi_rdata <= scratch;
                    default: begin
                        s_axi_rdata <= 32'b0;
                        s_axi_rresp <= RESP_SLVERR;
                    end
                endcase
            end
        end
    end
endmodule
