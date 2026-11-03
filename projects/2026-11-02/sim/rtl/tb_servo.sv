`timescale 1ns/1ps
module tb_servo;
    reg clk=0;always #5 clk=~clk;
    reg resetn=0;
    reg [11:0] awaddr=0,araddr=0;
    reg [31:0] wdata=0;
    reg [3:0] wstrb=15;
    reg awvalid=0,wvalid=0,bready=1,arvalid=0,rready=1;
    wire awready,wready,bvalid,arready,rvalid,pwm;
    wire [1:0] bresp,rresp;
    wire [31:0] rdata;
    aura_m3_regs #(.DIVIDER(2),.FRAME_US(40),.MILLIS_US(4),
        .MIN_US(14),.MAX_US(16),.CENTER_US(15),.STEP_US(1)) dut(
        .s_axi_aclk(clk),.s_axi_aresetn(resetn),
        .s_axi_awaddr(awaddr),.s_axi_awprot(3'b0),.s_axi_awvalid(awvalid),.s_axi_awready(awready),
        .s_axi_wdata(wdata),.s_axi_wstrb(wstrb),.s_axi_wvalid(wvalid),.s_axi_wready(wready),
        .s_axi_bresp(bresp),.s_axi_bvalid(bvalid),.s_axi_bready(bready),
        .s_axi_araddr(araddr),.s_axi_arprot(3'b0),.s_axi_arvalid(arvalid),.s_axi_arready(arready),
        .s_axi_rdata(rdata),.s_axi_rresp(rresp),.s_axi_rvalid(rvalid),.s_axi_rready(rready),.servo_pwm(pwm));
    task write(input[11:0] addr,input[31:0] value,input[1:0] expected,input integer order);
        begin
            @(negedge clk);awaddr=addr;wdata=value;
            if(order==0) begin
                awvalid=1;do @(posedge clk);while(!awready);
                @(negedge clk);awvalid=0;repeat(3) @(negedge clk);wvalid=1;
                do @(posedge clk);while(!wready);@(negedge clk);wvalid=0;
            end else begin
                wvalid=1;do @(posedge clk);while(!wready);
                @(negedge clk);wvalid=0;repeat(3) @(negedge clk);awvalid=1;
                do @(posedge clk);while(!awready);@(negedge clk);awvalid=0;
            end
            do @(posedge clk);while(!bvalid);
            if(bresp!==expected)$fatal(1,"BRESP addr=%h expected=%h actual=%h",addr,expected,bresp);
            @(negedge clk);
        end
    endtask
    task authorize;
        begin
            write('h010,32'h11,0,0);write('h014,32'h22,0,1);
            write('h024,32'h42494e44,0,0);
            write('h024,32'h41524d21,0,1); // business reject via reason
            if(dut.armed || dut.reason!=1)$fatal(1,"ARM before reference accepted");
            write('h03c,99,0,0);write('h024,32'h52454621,0,1);
            if(dut.referenced)$fatal(1,"Out-of-range reference accepted");
            write('h03c,15,0,0);
            write('h024,32'h52454621,0,1);
            write('h024,32'h41524d21,0,0);
        end
    endtask
    task reject_commit;
        reg[31:0] prior_seq;
        begin
            prior_seq=dut.ack_seq;
            write('h024,32'h434d5421,0,1);
            if(dut.reason!=2 || dut.ack_seq!=prior_seq)$fatal(1,"Invalid commit accepted");
        end
    endtask
    integer rises,falls,last_rise,last_fall,cycles;
    reg old_pwm;
    always @(posedge clk) begin
        cycles<=cycles+1;old_pwm<=pwm;
        if(pwm && !old_pwm) begin
            if(rises>0 && cycles-last_rise!=80)$fatal(1,"Bad PWM period %d",cycles-last_rise);
            last_rise<=cycles;rises<=rises+1;
        end
        if(!pwm && old_pwm && dut.active) begin
            if(cycles-last_rise<28 || cycles-last_rise>32)$fatal(1,"Bad pulse length %d",cycles-last_rise);
            falls<=falls+1;last_fall<=cycles;
        end
    end
    initial begin
        rises=0;falls=0;cycles=0;old_pwm=0;last_rise=0;last_fall=0;
        repeat(5) @(negedge clk);resetn=1;
        repeat(20) @(negedge clk);if(pwm)$fatal(1,"Boot output enabled");
        write('h018,1,0,0);write('h01c,16,0,1);write('h020,100,0,0);
        reject_commit();if(pwm)$fatal(1,"Unauthorized motion");
        authorize();write('h024,32'h434d5421,0,0);
        repeat(180) @(negedge clk);
        if(dut.width!=16 || rises<3 || falls<2)$fatal(1,"PWM ramp or waveform failed");
        reject_commit(); // duplicate seq cannot renew
        write('h018,2,0,0);write('h01c,99,0,1);reject_commit();
        write('h01c,14,0,1);write('h010,99,0,0);reject_commit();
        write('h010,32'h11,0,0);write('h014,99,0,1);reject_commit();
        write('h014,32'h22,0,1);write('h020,501,0,0);reject_commit();
        write('h020,100,0,0);write('h024,32'h434d5421,0,1);
        // Frozen writer does not keep the finite lease alive.
        repeat(850) @(negedge clk);
        if(pwm || dut.active || dut.armed || dut.bound || dut.referenced)$fatal(1,"Lease expiry did not disarm");
        write('h018,3,0,0);reject_commit();
        rises=0;authorize();write('h018,1,0,0);write('h024,32'h434d5421,0,1);
        repeat(5) @(negedge clk);
        write('h024,32'h53544f50,0,0);
        if(pwm || dut.active || dut.armed)$fatal(1,"STOP did not disarm");
        resetn=0;repeat(3) @(negedge clk);resetn=1;repeat(100) @(negedge clk);
        if(pwm || dut.armed)$fatal(1,"Reset resumed stale motion");
        // A user-selected reference is honored, not silently replaced by 15.
        write('h010,32'h33,0,0);write('h014,32'h44,0,1);
        write('h024,32'h42494e44,0,0);write('h03c,16,0,0);
        write('h024,32'h52454621,0,1);
        if(dut.width!=16 || dut.target!=16 || dut.reference_width!=16 || pwm)
            $fatal(1,"Reference changed position or enabled output");
        write('h024,32'h41524d21,0,0);write('h018,1,0,0);
        write('h01c,14,0,1);write('h020,100,0,0);
        rises=0;write('h024,32'h434d5421,0,0);
        if(dut.width!=16 || dut.target!=14)$fatal(1,"First submit jumped past reference");
        repeat(165) @(negedge clk);
        if(dut.width!=14)$fatal(1,"Reference-relative slew failed");
        write('h024,32'h53544f50,0,1);
        resetn=0;repeat(3) @(negedge clk);resetn=1;
        // Partial writes and invalid register addresses are rejected.
        wstrb=1;write('h010,123,2,0);wstrb=15;write('hffc,123,2,1);
        // A blocked read must hold both data and response, reject a second AR.
        @(negedge clk);rready=0;araddr=0;arvalid=1;
        do @(posedge clk);while(!arready);
        @(negedge clk);arvalid=0;
        do @(posedge clk);while(!rvalid);
        @(negedge clk);araddr=4;arvalid=1;
        repeat(6) begin
            @(posedge clk);
            if(!rvalid || arready || rdata!==32'h56535256 || rresp!==0)$fatal(1,"Read backpressure corrupted response");
        end
        @(negedge clk);arvalid=0;rready=1;repeat(2) @(negedge clk);
        // A blocked B response must prevent accepting another write pair.
        bready=0;awaddr='h010;wdata=77;awvalid=1;wvalid=1;
        do @(posedge clk);while(!awready || !wready);
        @(negedge clk);awvalid=0;wvalid=0;
        do @(posedge clk);while(!bvalid);
        @(negedge clk);awaddr='h014;wdata=88;awvalid=1;wvalid=1;
        repeat(6) begin
            @(posedge clk);
            if(!bvalid || bresp!==0 || awready || wready || dut.sh_epoch!==0)$fatal(1,"Write backpressure corrupted response");
        end
        @(negedge clk);awvalid=0;wvalid=0;bready=1;repeat(2) @(negedge clk);
        $display("AURA_SERVO_TEST_PASS authorization AXI_order backpressure registered_PWM reference ramp lease duplicate range session epoch STOP reset");
        $finish;
    end
    initial begin #100000;$fatal(1,"Simulation timeout");end
    always @(pwm) if($time>50 && $time%10!=5)$fatal(1,"PWM changed away from rising clock edge");
endmodule
