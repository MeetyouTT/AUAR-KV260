`timescale 1ns/1ps
module tb_axi;
    reg clk = 0, resetn = 0;
    always #5 clk = ~clk;
    reg [11:0] awaddr = 0, araddr = 0;
    reg awvalid = 0, wvalid = 0, bready = 0, arvalid = 0, rready = 0;
    reg [31:0] wdata = 0;
    reg [3:0] wstrb = 0;
    wire awready, wready, bvalid, arready, rvalid, pwm;
    wire [1:0] bresp, rresp;
    wire [31:0] rdata;
    integer n, b, cycles, pulses;
    reg [31:0] expected, value;
    reg previous = 0;
    aura_pwm_probe #(.CLK_HZ(10000), .RUN_FRAMES(3)) dut (
        .s_axi_aclk(clk), .s_axi_aresetn(resetn),
        .s_axi_awaddr(awaddr), .s_axi_awprot(3'b0), .s_axi_awvalid(awvalid), .s_axi_awready(awready),
        .s_axi_wdata(wdata), .s_axi_wstrb(wstrb), .s_axi_wvalid(wvalid), .s_axi_wready(wready),
        .s_axi_bresp(bresp), .s_axi_bvalid(bvalid), .s_axi_bready(bready),
        .s_axi_araddr(araddr), .s_axi_arprot(3'b0), .s_axi_arvalid(arvalid), .s_axi_arready(arready),
        .s_axi_rdata(rdata), .s_axi_rresp(rresp), .s_axi_rvalid(rvalid), .s_axi_rready(rready),
        .servo_pwm(pwm));
    task tick; begin @(posedge clk); #1; end endtask
    task address(input [11:0] a);
        begin @(negedge clk); awaddr = a; awvalid = 1;
            @(posedge clk); while (!awready) @(posedge clk);
            @(negedge clk); awvalid = 0; end
    endtask
    task data(input [31:0] d, input [3:0] st);
        begin @(negedge clk); wdata = d; wstrb = st; wvalid = 1;
            @(posedge clk); while (!wready) @(posedge clk);
            @(negedge clk); wvalid = 0; end
    endtask
    task write_reg(input [11:0] a, input [31:0] d, input [3:0] st,
                   input integer order, input [1:0] resp);
        begin
            if (order == 0) begin address(a); repeat (3) tick(); data(d,st); end
            else if (order == 1) begin data(d,st); repeat (3) tick(); address(a); end
            else fork address(a); data(d,st); join
            while (!bvalid) tick();
            repeat (4) begin tick(); if (!bvalid || bresp != resp) $fatal(1, "write/backpressure failure a=%h", a); end
            @(negedge clk); bready = 1; tick();
            @(negedge clk); bready = 0;
            if (bvalid) $fatal(1, "write response not consumed");
        end
    endtask
    task read_reg(input [11:0] a, input [1:0] resp, output [31:0] v);
        begin
            @(negedge clk); araddr = a; arvalid = 1;
            @(posedge clk); while (!arready) @(posedge clk);
            @(negedge clk); arvalid = 0;
            while (!rvalid) tick();
            v = rdata;
            repeat (4) begin tick(); if (!rvalid || rresp != resp || rdata != v) $fatal(1, "read/backpressure failure"); end
            @(negedge clk); rready = 1; tick();
            @(negedge clk); rready = 0;
        end
    endtask
    initial begin
        repeat (3) tick(); @(negedge clk); resetn = 1;
        read_reg('h000, 0, value); if (value != 'h50574d54) $fatal(1, "identity");
        read_reg('h00c, 0, value); if (value != 4 || pwm) $fatal(1, "default disabled");
        read_reg('h014, 0, value); if (value != 200) $fatal(1, "period");
        read_reg('h018, 0, value); if (value != 15) $fatal(1, "width");
        expected = 0;
        for (n = 0; n < 16; n = n + 1) begin
            for (b = 0; b < 4; b = b + 1) if ((n >> b) & 1) expected[b*8 +: 8] = (32'h12345678+n) >> (b*8);
            write_reg('h02c, 32'h12345678+n, n, n%3, 0);
            read_reg('h02c, 0, value); if (value != expected) $fatal(1, "WSTRB");
        end
        write_reg('h000, 1, 15, 0, 2);
        write_reg('h011, 'h53544152, 15, 1, 2);
        write_reg('h010, 'h53544152, 7, 2, 2);
        write_reg('h010, 1, 15, 0, 2);
        read_reg('h001, 2, value); if (value != 0) $fatal(1, "unaligned");
        read_reg('h100, 2, value);
        if (pwm || dut.busy) $fatal(1, "invalid write enabled");
        // Reset between AW and W must discard the pending half-transaction.
        address('h010);
        @(negedge clk); resetn = 0; tick();
        @(negedge clk); resetn = 1;
        data('h53544152, 15); repeat (5) tick();
        if (bvalid || pwm) $fatal(1, "half write survived reset");
        @(negedge clk); resetn = 0; tick();
        @(negedge clk); resetn = 1;
        // Simultaneous read/write scratch returns its pre-update value.
        write_reg('h02c, 'h11223344, 15, 2, 0);
        fork
            address('h02c);
            data('h55667788, 15);
        join
        araddr = 'h02c; arvalid = 1;
        tick(); @(negedge clk); arvalid = 0;
        if (!rvalid || rdata != 'h11223344 || !bvalid) $fatal(1, "read/write ordering");
        @(negedge clk); bready = 1; rready = 1; tick();
        @(negedge clk); bready = 0; rready = 0;
        // Count all pulses across the command and its response stalls.
        cycles = 0; pulses = 0; previous = 0;
        fork
            begin
                write_reg('h010, 'h53544152, 15, 2, 0);
                write_reg('h010, 'h53544152, 15, 1, 2);
            end
            begin
                wait (dut.busy);
                while (dut.busy) begin
                    @(negedge clk);
                    if (pwm && !previous) pulses = pulses + 1;
                    previous = pwm; cycles = cycles + 1;
                end
            end
        join
        if (cycles != 601 || pulses != 3 || pwm) $fatal(1, "burst lifetime/renewal cycles=%0d pulses=%0d", cycles, pulses);
        read_reg('h01c, 0, value); if (value != 0) $fatal(1, "not expired");
        write_reg('h010, 'h53544152, 15, 0, 0);
        write_reg('h010, 'h53544f50, 15, 1, 0);
        if (pwm || dut.busy) $fatal(1, "software stop");
        write_reg('h010, 'h53544152, 15, 2, 0);
        @(negedge clk); resetn = 0; tick();
        if (pwm || dut.busy || bvalid || rvalid) $fatal(1, "reset clears output and bus");
        $display("AURA_AXI_ALL_PASS strobes=16 AW_first/W_first/same_backpressure/invalid/half_reset/expiry/stop");
        $finish;
    end
    initial begin #1000000; $fatal(1, "AXI test timeout"); end
endmodule
