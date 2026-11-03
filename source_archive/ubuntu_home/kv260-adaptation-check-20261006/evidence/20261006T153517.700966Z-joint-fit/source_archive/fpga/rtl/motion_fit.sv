// Experimental single-axis capacity ABI; not the formal motion ABI.
`timescale 1ns/1ps
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
    input wire s_axi_rready,
    output wire servo_pwm
);

    // Capacity/compatibility candidate. Conservative near-center bench range.
    // A shared ~1 us enable replaces variable multiply/divide and clock gating.
    parameter integer DIVIDER = 100;
    parameter integer FRAME_US = 20000;
    parameter integer MILLIS_US = 1000;
    parameter integer MIN_US = 1400;
    parameter integer MAX_US = 1600;
    parameter integer CENTER_US = 1500;
    parameter integer STEP_US = 4;
    localparam [31:0] ID=32'h4d464954, ABI=32'h00000001;
    localparam [31:0] BIND=32'h42494e44, REFERENCE=32'h52454621;
    localparam [31:0] ARM=32'h41524d21, COMMIT=32'h434d5421, STOP=32'h53544f50;
    reg aw_pending, w_pending;
    reg [11:0] aw_address;
    reg [31:0] w_data;
    reg [3:0] w_strobes;
    reg [31:0] sh_session,sh_epoch,sh_seq,sh_width,sh_lease;
    reg [31:0] session,epoch,ack_seq;
    reg [3:0] reason;
    reg bound,referenced,armed,active;
    reg [6:0] divider;
    reg [14:0] phase;
    reg [9:0] ms_phase;
    reg [8:0] lease_left;
    reg [10:0] width,target;
    wire tick=divider==DIVIDER-1;
    wire ms_tick=tick && ms_phase==MILLIS_US-1;
    wire expire=active && ms_tick && lease_left<=1;
    wire write_fire=aw_pending && w_pending && !s_axi_bvalid;
    wire command=write_fire && aw_address==12'h024 && w_strobes==4'hf;
    wire stop=command && w_data==STOP;
    wire valid_commit=armed && bound && referenced &&
        sh_session==session && sh_epoch==epoch &&
        ack_seq!=32'hffffffff && sh_seq==ack_seq+1 &&
        sh_width>=MIN_US && sh_width<=MAX_US && sh_lease>=1 && sh_lease<=500;
    assign servo_pwm=s_axi_aresetn && active && phase<width;
    assign s_axi_awready=s_axi_aresetn && !aw_pending && !s_axi_bvalid;
    assign s_axi_wready=s_axi_aresetn && !w_pending && !s_axi_bvalid;
    assign s_axi_arready=s_axi_aresetn && !s_axi_rvalid;
    always @(posedge s_axi_aclk) begin
        if(!s_axi_aresetn) begin
            aw_pending<=0;w_pending<=0;aw_address<=0;w_data<=0;w_strobes<=0;
            s_axi_bvalid<=0;s_axi_bresp<=0;s_axi_rvalid<=0;s_axi_rresp<=0;s_axi_rdata<=0;
            sh_session<=0;sh_epoch<=0;sh_seq<=0;sh_width<=0;sh_lease<=0;
            session<=0;epoch<=0;ack_seq<=0;reason<=0;
            bound<=0;referenced<=0;armed<=0;active<=0;
            divider<=0;phase<=0;ms_phase<=0;lease_left<=0;
            width<=CENTER_US;target<=CENTER_US;
        end else begin
            divider<=tick ? 0 : divider+1'b1;
            if(tick) ms_phase<=ms_phase==MILLIS_US-1 ? 0 : ms_phase+1'b1;
            if(active && tick) begin
                if(phase==FRAME_US-1) begin
                    phase<=0;
                    if(target>width) width<=target-width>STEP_US ? width+STEP_US : target;
                    else if(target<width) width<=width-target>STEP_US ? width-STEP_US : target;
                end else phase<=phase+1'b1;
            end
            if(active && ms_tick) lease_left<=lease_left-1'b1;
            if(s_axi_awvalid && s_axi_awready) begin aw_pending<=1;aw_address<=s_axi_awaddr;end
            if(s_axi_wvalid && s_axi_wready) begin w_pending<=1;w_data<=s_axi_wdata;w_strobes<=s_axi_wstrb;end
            if(s_axi_bvalid && s_axi_bready) s_axi_bvalid<=0;
            if(write_fire) begin
                aw_pending<=0;w_pending<=0;s_axi_bvalid<=1;s_axi_bresp<=2'b10;
                if(w_strobes==4'hf) begin
                    case(aw_address)
                        12'h010: begin sh_session<=w_data;s_axi_bresp<=0;end
                        12'h014: begin sh_epoch<=w_data;s_axi_bresp<=0;end
                        12'h018: begin sh_seq<=w_data;s_axi_bresp<=0;end
                        12'h01c: begin sh_width<=w_data;s_axi_bresp<=0;end
                        12'h020: begin sh_lease<=w_data;s_axi_bresp<=0;end
                        12'h024: begin
                            reason<=1;
                            case(w_data)
                                STOP: begin reason<=0;s_axi_bresp<=0;end
                                BIND: if(!armed && !active && sh_session!=0 && sh_epoch!=0) begin
                                    session<=sh_session;epoch<=sh_epoch;ack_seq<=0;bound<=1;
                                    referenced<=0;reason<=0;s_axi_bresp<=0;
                                end
                                REFERENCE: if(bound && !armed && !active) begin
                                    referenced<=1;width<=CENTER_US;target<=CENTER_US;
                                    reason<=0;s_axi_bresp<=0;
                                end
                                ARM: if(bound && referenced && !armed) begin armed<=1;reason<=0;s_axi_bresp<=0;end
                                COMMIT: if(valid_commit && !expire) begin
                                    ack_seq<=sh_seq;target<=sh_width[10:0];lease_left<=sh_lease[8:0];
                                    if(!active) begin phase<=0;divider<=0;ms_phase<=0;end
                                    active<=1;reason<=0;s_axi_bresp<=0;
                                end else reason<=2;
                                default: reason<=3;
                            endcase
                        end
                        default: reason<=3;
                    endcase
                end
            end
            // Stop/expiry wins over command processing, invalidates permission.
            if(stop || expire) begin
                active<=0;armed<=0;referenced<=0;bound<=0;lease_left<=0;phase<=0;
                reason<=expire ? 4 : 0;
            end
            if(s_axi_rvalid && s_axi_rready) s_axi_rvalid<=0;
            if(s_axi_arvalid && s_axi_arready) begin
                s_axi_rvalid<=1;s_axi_rresp<=0;
                case(s_axi_araddr)
                    12'h000:s_axi_rdata<=ID;
                    12'h004:s_axi_rdata<=ABI;
                    12'h008:s_axi_rdata<=32'h20261006;
                    12'h00c:s_axi_rdata<={24'b0,reason,bound,referenced,armed,active};
                    12'h010:s_axi_rdata<=sh_session;
                    12'h014:s_axi_rdata<=sh_epoch;
                    12'h018:s_axi_rdata<=sh_seq;
                    12'h01c:s_axi_rdata<=sh_width;
                    12'h020:s_axi_rdata<=sh_lease;
                    12'h028:s_axi_rdata<=ack_seq;
                    12'h02c:s_axi_rdata<={21'b0,width};
                    12'h030:s_axi_rdata<={23'b0,lease_left};
                    12'h034:s_axi_rdata<=session;
                    12'h038:s_axi_rdata<=epoch;
                    default:begin s_axi_rdata<=0;s_axi_rresp<=2'b10;end
                endcase
            end
        end
    end
endmodule
