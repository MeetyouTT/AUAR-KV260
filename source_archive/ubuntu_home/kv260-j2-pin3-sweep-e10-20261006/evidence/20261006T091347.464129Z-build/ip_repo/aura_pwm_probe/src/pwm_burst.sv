`timescale 1ns/1ps
// Explicitly started near-center servo motion test. All pulse arithmetic is
// elaboration-time. Select the next width only at a complete frame boundary.
module pwm_burst #(
    parameter integer CLK_HZ = 99999001,
    parameter integer PWM_HZ = 50,
    parameter integer PULSE_US = 1400,
    parameter integer RUN_FRAMES = 0,
    parameter integer PULSE_HIGH_US = 1600,
    parameter integer HOLD_FRAMES = 50
) (
    input wire clk, resetn, start, stop,
    output reg pwm = 0,
    output reg busy = 0,
    output wire [31:0] frames_left,
    output wire config_valid,
    output wire [31:0] period_ticks, pulse_ticks, pulse_high_ticks,
    output wire [31:0] selected_us, frame_index
);
    localparam [63:0] PERIOD = PWM_HZ > 0 ?
        (64'd1 * CLK_HZ + PWM_HZ / 2) / PWM_HZ : 0;
    localparam [63:0] LOW = (64'd1 * CLK_HZ * PULSE_US + 500000) / 1000000;
    localparam [63:0] HIGH = (64'd1 * CLK_HZ * PULSE_HIGH_US + 500000) / 1000000;
    assign config_valid = CLK_HZ > 0 && PWM_HZ == 50 && RUN_FRAMES == 0 &&
        PULSE_US >= 1400 && PULSE_HIGH_US <= 1600 && PULSE_US < PULSE_HIGH_US &&
        PERIOD >= 2 && PERIOD <= 64'hffffffff && LOW >= 1 &&
        LOW < HIGH && HIGH < PERIOD && HOLD_FRAMES >= 1 && HOLD_FRAMES <= 500;
    assign period_ticks = PERIOD[31:0];
    assign pulse_ticks = LOW[31:0];
    assign pulse_high_ticks = HIGH[31:0];
    assign frames_left = 0;
    reg [31:0] phase = 0, dwell_frame = 0;
    reg select_high = 0;
    wire [31:0] active_width = select_high ? HIGH[31:0] : LOW[31:0];
    assign selected_us = select_high ? PULSE_HIGH_US : PULSE_US;
    assign frame_index = dwell_frame;

    always @(posedge clk) begin
        if (!resetn || stop) begin
            pwm <= 0;
            busy <= 0;
            phase <= 0;
            dwell_frame <= 0;
            select_high <= 0;
        end else if (busy) begin
            // Duplicate START does not reset the frame or extend its pulse.
            if (phase == PERIOD - 1) begin
                phase <= 0;
                pwm <= 1;
                if (dwell_frame == HOLD_FRAMES - 1) begin
                    dwell_frame <= 0;
                    select_high <= !select_high;
                end else dwell_frame <= dwell_frame + 1'b1;
            end else begin
                phase <= phase + 1'b1;
                pwm <= (phase + 1'b1) < active_width;
            end
        end else if (start && config_valid) begin
            phase <= 0;
            dwell_frame <= 0;
            select_high <= 0;
            pwm <= 1;
            busy <= 1;
        end else begin
            phase <= 0;
            dwell_frame <= 0;
            select_high <= 0;
            pwm <= 0;
        end
    end
endmodule
