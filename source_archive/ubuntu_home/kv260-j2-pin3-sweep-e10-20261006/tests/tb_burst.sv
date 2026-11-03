`timescale 1ns/1ps
module sweep_case #(
    parameter integer CLK_HZ = 10000,
    parameter integer PWM_HZ = 50,
    parameter integer PULSE_US = 1400,
    parameter integer PULSE_HIGH_US = 1600,
    parameter integer HOLD_FRAMES = 3,
    parameter integer RUN_FRAMES = 0,
    parameter integer EXPECT_VALID = 1,
    parameter integer FRAMES_TO_CHECK = 15
) (output reg done = 0);
    reg clk = 0, resetn = 0, start = 0, stop = 0;
    wire pwm, busy, valid;
    wire [31:0] frames_left, period, low_ticks, high_ticks, selected_us, frame_index;
    integer n, frame, width, expected_period, expected_low, expected_high;
    always #5 clk = ~clk;
    pwm_burst #(.CLK_HZ(CLK_HZ), .PWM_HZ(PWM_HZ), .PULSE_US(PULSE_US),
        .RUN_FRAMES(RUN_FRAMES), .PULSE_HIGH_US(PULSE_HIGH_US), .HOLD_FRAMES(HOLD_FRAMES)) dut (
        .clk(clk), .resetn(resetn), .start(start), .stop(stop), .pwm(pwm),
        .busy(busy), .frames_left(frames_left), .config_valid(valid),
        .period_ticks(period), .pulse_ticks(low_ticks), .pulse_high_ticks(high_ticks),
        .selected_us(selected_us), .frame_index(frame_index));
    task tick; begin @(posedge clk); #1; end endtask
    initial begin
        repeat (3) tick();
        if (pwm || busy) $fatal(1,"reset must disable output");
        @(negedge clk); resetn = 1;
        repeat (10) begin tick(); if (pwm || busy) $fatal(1,"automatic start"); end
        if (valid != EXPECT_VALID) $fatal(1,"parameter validity");
        @(negedge clk); start = 1; tick(); start = 0;
        if (!EXPECT_VALID) begin
            repeat (20) begin tick(); if (pwm || busy) $fatal(1,"invalid config started"); end
        end else begin
            expected_period = $rtoi(CLK_HZ / (1.0 * PWM_HZ) + 0.5);
            expected_low = $rtoi(CLK_HZ * (PULSE_US / 1000000.0) + 0.5);
            expected_high = $rtoi(CLK_HZ * (PULSE_HIGH_US / 1000000.0) + 0.5);
            if (period != expected_period || low_ticks != expected_low || high_ticks != expected_high)
                $fatal(1,"independent duration conversion");
            for (n=0;n<FRAMES_TO_CHECK*expected_period;n=n+1) begin
                frame=n/expected_period;
                width=((frame/HOLD_FRAMES)%2) ? expected_high : expected_low;
                if (!busy || frames_left || pwm != ((n%expected_period)<width))
                    $fatal(1,"pulse/period/dwell mismatch cycle=%0d",n);
                if (selected_us != (((frame/HOLD_FRAMES)%2) ? PULSE_HIGH_US : PULSE_US) ||
                    frame_index != frame%HOLD_FRAMES)
                    $fatal(1,"phase telemetry mismatch");
                // Includes START at dwell transitions: no extra or truncated pulse.
                @(negedge clk); start = n%expected_period == expected_period-2; tick();
            end
            @(negedge clk); start = 0; stop = 1; tick();
            if (pwm || busy || selected_us != PULSE_US || frame_index)
                $fatal(1,"STOP must disable and restore first phase");
            @(negedge clk); start=1; tick();
            if (pwm || busy) $fatal(1,"START beat STOP");
            @(negedge clk); start=0; stop=0;
            repeat (2*expected_period) begin tick(); if (pwm || busy) $fatal(1,"auto restart"); end
            @(negedge clk); start=1; tick();
            if (!pwm || !busy || selected_us != PULSE_US || frame_index)
                $fatal(1,"explicit restart not at first phase");
            @(negedge clk); start=0; resetn=0; tick();
            if (pwm || busy) $fatal(1,"reset during high pulse");
        end
        $display("SWEEP_CASE_PASS CLK_HZ=%0d HZ=%0d LOW=%0d HIGH=%0d HOLD=%0d VALID=%0d",CLK_HZ,PWM_HZ,PULSE_US,PULSE_HIGH_US,HOLD_FRAMES,EXPECT_VALID);
        done=1;
    end
endmodule

module tb_burst;
    wire [10:0] done;
    sweep_case basic(done[0]);
    sweep_case #(.HOLD_FRAMES(50),.FRAMES_TO_CHECK(201)) dwell_one_second(done[1]);
    sweep_case #(.HOLD_FRAMES(1),.FRAMES_TO_CHECK(10)) boundary_every_frame(done[2]);
    sweep_case #(.CLK_HZ(99999001),.HOLD_FRAMES(1),.FRAMES_TO_CHECK(3)) real_clock(done[3]);
    sweep_case #(.PULSE_US(1399),.EXPECT_VALID(0)) low_outside_range(done[4]);
    sweep_case #(.PULSE_HIGH_US(1601),.EXPECT_VALID(0)) high_outside_range(done[5]);
    sweep_case #(.PULSE_HIGH_US(1400),.EXPECT_VALID(0)) equal_widths(done[6]);
    sweep_case #(.HOLD_FRAMES(0),.EXPECT_VALID(0)) zero_dwell(done[7]);
    sweep_case #(.HOLD_FRAMES(501),.EXPECT_VALID(0)) oversized_dwell(done[8]);
    sweep_case #(.PWM_HZ(0),.EXPECT_VALID(0)) zero_frequency(done[9]);
    sweep_case #(.RUN_FRAMES(1),.EXPECT_VALID(0)) unsupported_bounded_mode(done[10]);
    initial begin wait (&done); $display("AURA_SWEEP_ALL_PASS"); $finish; end
    initial begin #120000000; $fatal(1,"sweep timeout"); end
endmodule
