`timescale 1ns/1ps
module tb_wide;
 reg clk=0;always #5 clk=~clk;
 reg rst=0;reg[11:0] aw=0,ar=0;reg[31:0] wd=0;reg av=0,wv=0,rv=0;
 wire awr,wr,bv,arr,rr,pwm;wire[1:0] br,rresp;wire[31:0] rd;
 aura_m3_regs #(.DIVIDER(1)) dut(.s_axi_aclk(clk),.s_axi_aresetn(rst),
 .s_axi_awaddr(aw),.s_axi_awprot(3'b0),.s_axi_awvalid(av),.s_axi_awready(awr),
 .s_axi_wdata(wd),.s_axi_wstrb(4'hf),.s_axi_wvalid(wv),.s_axi_wready(wr),
 .s_axi_bresp(br),.s_axi_bvalid(bv),.s_axi_bready(1'b1),
 .s_axi_araddr(ar),.s_axi_arprot(3'b0),.s_axi_arvalid(rv),.s_axi_arready(arr),
 .s_axi_rdata(rd),.s_axi_rresp(rresp),.s_axi_rvalid(rr),.s_axi_rready(1'b1),.servo_pwm(pwm));
 task put(input[11:0] a,input[31:0] v);
  begin @(negedge clk);aw=a;wd=v;av=1;wv=1;
   do @(posedge clk);while(!awr||!wr);
   @(negedge clk);av=0;wv=0;do @(posedge clk);while(!bv);
   if(br!==0)$fatal(1,"AXI write rejected");@(negedge clk);
  end
 endtask
 task check(input[11:0] a,input[31:0] v);
  begin @(negedge clk);ar=a;rv=1;do @(posedge clk);while(!arr);
   @(negedge clk);rv=0;do @(posedge clk);while(!rr);
   if(rresp!==0||rd!==v)$fatal(1,"read %h got %d expected %d",a,rd,v);@(negedge clk);
  end
 endtask
 task reference(input[31:0] ep,input[31:0] width);
  begin put('h024,32'h53544f50);put('h010,123);put('h014,ep);put('h024,32'h42494e44);
   put('h03c,width);put('h024,32'h52454621);check('h02c,width);check('h040,width);check('h044,width);
   if(pwm||dut.active)$fatal(1,"reference emitted output");put('h024,32'h41524d21);
  end
 endtask
 task commit(input[31:0] seq,input[31:0] width,input[31:0] lease);
  begin put('h018,seq);put('h01c,width);put('h020,lease);put('h024,32'h434d5421);end
 endtask
 integer cycle=0,rises=0,falls=0,begin_cycle=0,last_width=0,old_rises,old_falls;reg prev=0;
 always @(posedge clk) begin
  #1;cycle=cycle+1;
  if(pwm&&!prev)begin rises=rises+1;begin_cycle=cycle;end
  if(!pwm&&prev)begin falls=falls+1;last_width=cycle-begin_cycle;end
  prev=pwm;
 end
 initial begin
  repeat(10)@(negedge clk);rst=1;check('h008,32'h10282601);check('h02c,1500);
  reference(1,2500);commit(1,2500,3);
  if(dut.active||dut.ack_seq!=0||dut.reason!=2)$fatal(1,"short lease accepted");
  commit(1,2500,50);check('h044,2500);wait(falls>=1);
  if(last_width!=2500)$fatal(1,"2500 truncated: %d",last_width);
  wait(rises>=2);repeat(100)@(negedge clk);put('h024,32'h51554945);wait(falls>=2);
  if(last_width!=2500)$fatal(1,"QUIESCE truncated max pulse");repeat(3)@(negedge clk);
  if(pwm||dut.active||dut.armed)$fatal(1,"QUIESCE failed");
  reference(2,500);commit(1,499,30);
  if(dut.active||dut.ack_seq!=0)$fatal(1,"lower out-of-range accepted");
  commit(1,2501,30);if(dut.active||dut.ack_seq!=0)$fatal(1,"upper out-of-range accepted");
  old_falls=falls;commit(1,500,4);wait(falls>old_falls);
  if(last_width!=500)$fatal(1,"500 pulse incorrect");wait(!dut.active);
  if(pwm||dut.lease_left!=0)$fatal(1,"lease expiry failed");
  reference(3,2496);old_falls=falls;commit(1,2500,60);wait(falls==old_falls+1);
  if(last_width!=2496)$fatal(1,"ramp initial pulse incorrect");wait(falls==old_falls+2);
  if(last_width!=2500)$fatal(1,"ramp crossing 2047 incorrect");
  check('h02c,2500);put('h024,32'h53544f50);
  if(pwm||dut.active||dut.armed)$fatal(1,"STOP failed");
  put('h010,123);put('h014,4);put('h024,32'h42494e44);put('h03c,2501);put('h024,32'h52454621);
  if(dut.referenced)$fatal(1,"out-of-range reference accepted");
  $display("AURA_WIDE_TEST_PASS endpoints readback pulse widths range rejection lease4 QUIESCE ramp STOP");$finish;
 end
 initial begin #3000000;$fatal(1,"timeout");end
endmodule
