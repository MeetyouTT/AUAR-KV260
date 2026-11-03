`timescale 1ns/1ps
module burst_case #(
    parameter integer CLK_HZ = 10000,
    parameter integer PWM_HZ = 50,
    parameter integer PULSE_US = 1500,
    parameter integer FRAMES = 3,
    parameter integer EXPECT_VALID = 1
) (output reg done = 0);
    reg clk = 0, resetn = 0, start = 0, stop = 0;
    wire pwm, busy, valid;
    wire [31:0] frames_left, period, pulse;
    integer n, highs, expected_period, expected_pulse;
    always #5 clk = ~clk;
    pwm_burst #(.CLK_HZ(CLK_HZ), .PWM_HZ(PWM_HZ), .PULSE_US(PULSE_US),
        .RUN_FRAMES(FRAMES)) dut (clk, resetn, start, stop, pwm, busy,
        frames_left, valid, period, pulse);
    task tick; begin @(posedge clk); #1; end endtask
    initial begin
        repeat (3) tick();
        if (pwm || busy) $fatal(1, "reset not disabled");
        @(negedge clk); resetn = 1;
        repeat (10) begin tick(); if (pwm || busy) $fatal(1, "automatic start"); end
        if (valid != EXPECT_VALID) $fatal(1, "parameter validity mismatch");
        @(negedge clk); start = 1;
        tick();
        start = 0; // tick() returns after NBA; begin checking frame cycle zero.
        if (!EXPECT_VALID) begin
            repeat (20) begin tick(); if (pwm || busy) $fatal(1, "invalid config enabled"); end
        end else begin
            expected_period = ($rtoi(CLK_HZ / (1.0 * PWM_HZ)) +
                ((CLK_HZ % PWM_HZ) * 2 >= PWM_HZ));
            expected_pulse = $rtoi(CLK_HZ * (PULSE_US / 1000000.0) + 0.5);
            if (period != expected_period || pulse != expected_pulse)
                $fatal(1, "independent tick conversion mismatch");
            highs = 0;
            for (n = 0; n < FRAMES * expected_period; n = n + 1) begin
                if (!busy || pwm != ((n % expected_period) < expected_pulse))
                    $fatal(1, "pulse length/period/lifetime mismatch at cycle %0d", n);
                if (frames_left != FRAMES - n / expected_period)
                    $fatal(1, "frames countdown mismatch");
                highs = highs + pwm;
                // Duplicate START, including last-frame boundary, must not renew.
                @(negedge clk); start = (n % expected_period == expected_period - 2);
                tick();
            end
            @(negedge clk); start = 0;
            if (busy || pwm || frames_left != 0 || highs != FRAMES * expected_pulse)
                $fatal(1, "expiration mismatch or extra pulse");
            repeat (20) begin tick(); if (pwm || busy) $fatal(1, "auto restart"); end
            @(negedge clk); start = 1;
            tick();
            @(negedge clk); start = 0; stop = 1;
            tick();
            if (pwm || busy) $fatal(1, "STOP did not truncate");
            @(negedge clk); start = 1;
            tick();
            if (pwm || busy) $fatal(1, "START beat STOP");
            @(negedge clk); stop = 0;
            tick();
            if (!pwm || !busy) $fatal(1, "explicit restart failed");
            @(negedge clk); resetn = 0;
            tick();
            if (pwm || busy || frames_left) $fatal(1, "reset failed mid pulse");
        end
        $display("BURST_CASE_PASS CLK_HZ=%0d HZ=%0d US=%0d FRAMES=%0d VALID=%0d", CLK_HZ, PWM_HZ, PULSE_US, FRAMES, EXPECT_VALID);
        done = 1;
    end
endmodule

module tb_burst;
    wire [8:0] done;
    burst_case a(done[0]);
    burst_case #(.CLK_HZ(99999001)) b(done[1]);
    burst_case #(.CLK_HZ(100000000), .FRAMES(1)) c(done[2]);
    burst_case #(.PWM_HZ(100), .PULSE_US(2000), .FRAMES(2)) d(done[3]);
    burst_case #(.PULSE_US(0), .EXPECT_VALID(0)) e(done[4]);
    burst_case #(.PULSE_US(20000), .EXPECT_VALID(0)) f(done[5]);
    burst_case #(.FRAMES(0), .EXPECT_VALID(0)) g(done[6]);
    burst_case #(.PWM_HZ(0), .EXPECT_VALID(0)) h(done[7]);
    burst_case #(.FRAMES(1001), .EXPECT_VALID(0)) i(done[8]);
    initial begin wait (&done); $display("AURA_BURST_ALL_PASS"); $finish; end
    initial begin #200000000; $fatal(1, "burst test timeout"); end
endmodule
