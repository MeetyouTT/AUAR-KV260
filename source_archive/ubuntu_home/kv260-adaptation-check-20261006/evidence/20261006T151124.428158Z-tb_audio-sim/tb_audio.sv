`timescale 1ns/1ps
module tb_audio;
    reg clk=0;always #5 clk=~clk;
    reg resetn=0,awvalid=0,wvalid=0,bready=0,arvalid=0,rready=0;
    wire awready,wready,bvalid,arready,rvalid;
    wire [1:0] bresp,rresp;
    wire [31:0] rdata;
    aura_audio_decerr dut(.*);
    task write(input integer order);
        begin
            @(negedge clk);
            if(order==0) begin
                awvalid=1;do @(posedge clk);while(!awready);
                @(negedge clk);awvalid=0;repeat(4)@(negedge clk);
                if(bvalid)$fatal(1,"Write completed without W");
                wvalid=1;do @(posedge clk);while(!wready);
                @(negedge clk);wvalid=0;
            end else begin
                wvalid=1;do @(posedge clk);while(!wready);
                @(negedge clk);wvalid=0;repeat(4)@(negedge clk);
                if(bvalid)$fatal(1,"Write completed without AW");
                awvalid=1;do @(posedge clk);while(!awready);
                @(negedge clk);awvalid=0;
            end
            do @(posedge clk);while(!bvalid);
            repeat(4)begin
                @(negedge clk);
                if(!bvalid || bresp!==3 || awready || wready)$fatal(1,"Write response/backpressure invalid");
            end
            bready=1;repeat(2)@(negedge clk);bready=0;
            if(bvalid)$fatal(1,"Duplicate B response");
        end
    endtask
    initial begin
        repeat(4)@(negedge clk);resetn=1;
        write(0);write(1);
        arvalid=1;do @(posedge clk);while(!arready);
        @(negedge clk);arvalid=0;
        do @(posedge clk);while(!rvalid);
        repeat(4)begin
            @(negedge clk);
            if(!rvalid || arready || rresp!==3 || rdata!==0)$fatal(1,"Read response/backpressure invalid");
        end
        rready=1;repeat(2)@(negedge clk);rready=0;
        if(rvalid)$fatal(1,"Duplicate R response");
        awvalid=1;do @(posedge clk);while(!awready);
        @(negedge clk);awvalid=0;resetn=0;repeat(3)@(negedge clk);resetn=1;
        repeat(6)@(negedge clk);
        if(bvalid || rvalid || !awready || !wready)$fatal(1,"Reset did not discard partial write");
        $display("AURA_AUDIO_TEST_PASS independent_AW_W DECERR read write backpressure reset");$finish;
    end
    initial begin #10000;$fatal(1,"Audio-stub simulation timeout");end
endmodule
