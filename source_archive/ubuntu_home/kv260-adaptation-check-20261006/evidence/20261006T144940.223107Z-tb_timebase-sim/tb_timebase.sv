`timescale 1ns/1ps
module tb_timebase;
    reg clk=0; always #5 clk=~clk;
    reg resetn=0;
    reg [11:0] awaddr=0;
    reg [31:0] wdata=0;
    reg awvalid=0,wvalid=0;
    wire awready,wready,bvalid,pwm;
    wire [1:0] bresp;
    aura_m3_regs dut(
        .s_axi_aclk(clk),.s_axi_aresetn(resetn),
        .s_axi_awaddr(awaddr),.s_axi_awprot(3'b0),.s_axi_awvalid(awvalid),.s_axi_awready(awready),
        .s_axi_wdata(wdata),.s_axi_wstrb(4'hf),.s_axi_wvalid(wvalid),.s_axi_wready(wready),
        .s_axi_bresp(bresp),.s_axi_bvalid(bvalid),.s_axi_bready(1'b1),
        .s_axi_araddr(12'b0),.s_axi_arprot(3'b0),.s_axi_arvalid(1'b0),.s_axi_rready(1'b1),
        .servo_pwm(pwm));
    task write(input [11:0] address,input [31:0] value);
        begin
            @(negedge clk);awaddr=address;wdata=value;awvalid=1;wvalid=1;
            do @(posedge clk);while(!awready || !wready);
            @(negedge clk);awvalid=0;wvalid=0;
            do @(posedge clk);while(!bvalid);
            if(bresp!==0)$fatal(1,"Command rejected");
            @(negedge clk);
        end
    endtask
    integer rises=0,falls=0;
    time last_rise=0,first_rise=0;
    always @(posedge pwm) begin
        if(rises>0 && $time-last_rise!=20000000)$fatal(1,"Default period incorrect: %t",$time-last_rise);
        if(rises==0)first_rise=$time;
        last_rise=$time;rises=rises+1;
    end
    always @(negedge pwm) if(rises>0) begin
        if($time-last_rise!=1500000)$fatal(1,"Default pulse incorrect: %t",$time-last_rise);
        falls=falls+1;
    end
    initial begin
        repeat(5)@(negedge clk);resetn=1;
        write('h010,32'h11);write('h014,32'h22);write('h018,1);
        write('h01c,1500);write('h020,50);
        write('h024,32'h42494e44);write('h024,32'h52454621);
        write('h024,32'h41524d21);write('h024,32'h434d5421);
        #50001000;
        if(rises!=3 || falls!=3 || pwm || dut.active || dut.armed || dut.bound || dut.referenced)
            $fatal(1,"Default timebase or finite lease failed");
        if(dut.reason!=4)$fatal(1,"Expected lease-expiry reason");
        $display("AURA_TIMEBASE_TEST_PASS default_period_ns=20000000 default_pulse_ns=1500000 lease_ms=50 pulses=3");
        $finish;
    end
    initial begin #60000000;$fatal(1,"Default-timebase simulation timeout");end
endmodule
