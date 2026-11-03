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
