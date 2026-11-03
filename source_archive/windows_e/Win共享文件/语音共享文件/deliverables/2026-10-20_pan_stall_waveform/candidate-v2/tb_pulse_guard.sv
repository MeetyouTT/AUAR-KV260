`timescale 1ns/1ps
module tb_pulse_guard;
    reg clk=0;always #5 clk=~clk;
    reg resetn=0;
    reg[11:0] awaddr=0;
    reg[31:0] wdata=0;
    reg awvalid=0,wvalid=0;
    wire awready,wready,bvalid,pwm;
    wire[1:0] bresp;
    aura_m3_regs dut(.s_axi_aclk(clk),.s_axi_aresetn(resetn),
        .s_axi_awaddr(awaddr),.s_axi_awprot(3'b0),.s_axi_awvalid(awvalid),.s_axi_awready(awready),
        .s_axi_wdata(wdata),.s_axi_wstrb(4'hf),.s_axi_wvalid(wvalid),.s_axi_wready(wready),
        .s_axi_bresp(bresp),.s_axi_bvalid(bvalid),.s_axi_bready(1'b1),
        .s_axi_araddr(12'b0),.s_axi_arprot(3'b0),.s_axi_arvalid(1'b0),.s_axi_arready(),
        .s_axi_rdata(),.s_axi_rresp(),.s_axi_rvalid(),.s_axi_rready(1'b1),.servo_pwm(pwm));
    task write(input[11:0] address,input[31:0] value);
        begin
            @(negedge clk);awaddr=address;wdata=value;awvalid=1;wvalid=1;
            do @(posedge clk);while(!awready || !wready);
            @(negedge clk);awvalid=0;wvalid=0;
            do @(posedge clk);while(!bvalid);
            if(bresp!==0)$fatal(1,"AXI write failed");
            @(negedge clk);
        end
    endtask
    task begin_step(input integer epoch,input integer lease);
        begin
            write('h010,1);write('h014,epoch);write('h024,32'h42494e44);
            write('h03c,1420);write('h024,32'h52454621);write('h024,32'h41524d21);
            write('h018,1);write('h01c,1440);write('h020,lease);write('h024,32'h434d5421);
        end
    endtask
    integer cycle=0,last_rise=0,rises=0,falls=0;
    integer last_width=0,case_id=0;
    reg old_pwm=0,emergency_expected=0;
    always @(posedge clk) begin
        #1;cycle=cycle+1;
        if(pwm && !old_pwm) begin last_rise=cycle;rises=rises+1;end
        if(!pwm && old_pwm) begin
            last_width=cycle-last_rise;falls=falls+1;
            $display("EDGE case=%0d width_ns=%0d active=%0d reason=%0d",case_id,last_width*10,dut.active,dut.reason);
            if(!emergency_expected && (last_width<140000 || last_width>160000))
                $fatal(1,"Malformed pulse, including normal STOP/expiry");
        end
        old_pwm=pwm;
    end
    integer old_rises;
    initial begin
        repeat(10) @(negedge clk);resetn=1;
        // Normal completion during high finishes that pulse and emits no next.
        case_id=1;begin_step(1,100);wait(dut.phase>=500);
        old_rises=rises;write('h024,32'h51554945);wait(!dut.active);repeat(5)@(negedge clk);
        if(last_width!=142000 || rises!=old_rises || pwm || dut.quiescing)$fatal(1,"Graceful high stop failed");
        $display("GRACEFUL_HIGH_STOP_PASS pulse_ns=%0d",last_width*10);
        // A lease too short for a full pulse is rejected without a pulse.
        case_id=2;old_rises=rises;begin_step(2,1);repeat(5)@(negedge clk);
        if(dut.active || pwm || dut.ack_seq!=0 || dut.reason!=2 || rises!=old_rises)$fatal(1,"Short lease accepted");
        write('h024,32'h53544f50);$display("SHORT_LEASE_REJECTED_NO_PULSE_PASS");
        // Repeat the real 100 ms-renewal case that truncated VSRV/1 at 1000 us.
        case_id=3;begin_step(3,100);wait(dut.phase==19999);wait(dut.phase==1000);
        write('h018,2);write('h024,32'h434d5421);wait(!dut.active);repeat(5)@(negedge clk);
        if(last_width!=144000 || pwm || dut.reason!=4)$fatal(1,"100 ms expiry did not preserve complete pulses");
        $display("REAL_100MS_EXPIRY_FULL_PULSES_PASS last_pulse_ns=%0d",last_width*10);
        // Normal stop while low emits no new pulse.
        case_id=4;begin_step(4,100);wait(dut.phase>=2000);old_rises=rises;
        write('h024,32'h51554945);wait(!dut.active);repeat(5)@(negedge clk);
        if(rises!=old_rises || pwm)$fatal(1,"Graceful low stop added a pulse");
        $display("GRACEFUL_LOW_STOP_PASS");
        // Emergency STOP intentionally keeps its independent immediate cut.
        case_id=5;begin_step(5,100);wait(dut.phase>=500);emergency_expected=1;
        write('h024,32'h53544f50);repeat(5)@(negedge clk);
        if(dut.active || pwm || last_width>=140000)$fatal(1,"Emergency STOP no longer immediate");
        $display("EMERGENCY_STOP_IMMEDIATE_PASS pulse_ns=%0d",last_width*10);
        $display("AURA_V2_PULSE_GUARD_OFFLINE_PASS_NOT_BOARD_RELEASE");$finish;
    end
    initial begin #150000000;$fatal(1,"Timeout");end
endmodule
