`timescale 1ns/1ps
module tb_nominal;
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
            if(bresp!==0)$fatal(1,"Nominal AXI write failed");
            @(negedge clk);
        end
    endtask
    integer cycle=0,rises=0,falls=0,last_rise=0,width_cycles=0;
    reg old_pwm=0;
    always @(posedge clk) begin
        #1;
        cycle=cycle+1;
        if(pwm && !old_pwm) begin
            if(rises>0 && cycle-last_rise!=2000000)$fatal(1,"Nominal period incorrect %d",cycle-last_rise);
            last_rise=cycle;rises=rises+1;
        end
        if(!pwm && old_pwm && dut.active) begin
            width_cycles=cycle-last_rise;
            case(falls)
                0:if(width_cycles!=145000)$fatal(1,"Initial reference pulse wrong %d",width_cycles);
                1:if(width_cycles!=145400)$fatal(1,"First boundary ramp wrong %d",width_cycles);
                2:if(width_cycles!=145800)$fatal(1,"Second boundary ramp wrong %d",width_cycles);
                3:if(width_cycles!=146000)$fatal(1,"Final ramp wrong %d",width_cycles);
            endcase
            falls=falls+1;
        end
        old_pwm=pwm;
    end
    initial begin
        repeat(10) @(negedge clk);resetn=1;
        write('h010,1);write('h014,1);write('h024,32'h42494e44);
        write('h03c,1450);write('h024,32'h52454621);write('h024,32'h41524d21);
        write('h018,1);write('h01c,1460);write('h020,90);write('h024,32'h434d5421);
        wait(falls>=4);
        write('h024,32'h53544f50);
        if(pwm || dut.active || dut.armed)$fatal(1,"Nominal STOP failed");
        $display("AURA_NOMINAL_TEST_PASS 100MHz 50Hz reference1450us ramp1454_1458_1460us registered_STOP");
        $finish;
    end
    initial begin #100000000;$fatal(1,"Nominal timeout");end
endmodule
