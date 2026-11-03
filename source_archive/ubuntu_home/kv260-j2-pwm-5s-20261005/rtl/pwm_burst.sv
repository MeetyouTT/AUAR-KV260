`timescale 1ns/1ps
// Bounded bench pulse generator. Reset and STOP take priority over START.
// All arithmetic below is elaboration-time; run-time logic is counters only.
module pwm_burst #(
    parameter integer CLK_HZ = 99999001,
    parameter integer PWM_HZ = 50,
    parameter integer PULSE_US = 1500,
    parameter integer RUN_FRAMES = 250
) (
    input wire clk,
    input wire resetn,
    input wire start,
    input wire stop,
    output reg pwm = 1'b0,
    output reg busy = 1'b0,
    output reg [31:0] frames_left = 0,
    output wire config_valid,
    output wire [31:0] period_ticks,
    output wire [31:0] pulse_ticks
);
    localparam [63:0] PERIOD = PWM_HZ > 0 ?
        (64'd1 * CLK_HZ + PWM_HZ / 2) / PWM_HZ : 0;
    localparam [63:0] PULSE =
        (64'd1 * CLK_HZ * PULSE_US + 500000) / 1000000;
    assign config_valid = CLK_HZ > 0 && PWM_HZ > 0 && PULSE_US > 0 &&
        PERIOD >= 2 && PERIOD <= 64'hffffffff &&
        PULSE >= 1 && PULSE < PERIOD && PULSE <= 64'hffffffff &&
        RUN_FRAMES >= 1 && RUN_FRAMES <= 1000;
    assign period_ticks = PERIOD[31:0];
    assign pulse_ticks = PULSE[31:0];
    reg [31:0] phase = 0;

    always @(posedge clk) begin
        if (!resetn || stop) begin
            pwm <= 1'b0;
            busy <= 1'b0;
            frames_left <= 0;
            phase <= 0;
        end else if (busy) begin
            // START while busy cannot extend the fixed lifetime.
            if (phase == PERIOD - 1) begin
                phase <= 0;
                if (frames_left == 1) begin
                    pwm <= 1'b0;
                    busy <= 1'b0;
                    frames_left <= 0;
                end else begin
                    frames_left <= frames_left - 1'b1;
                    pwm <= 1'b1;
                end
            end else begin
                phase <= phase + 1'b1;
                pwm <= (phase + 1'b1) < PULSE;
            end
        end else if (start && config_valid) begin
            phase <= 0;
            pwm <= 1'b1;
            busy <= 1'b1;
            frames_left <= RUN_FRAMES;
        end else begin
            phase <= 0;
            pwm <= 1'b0;
            frames_left <= 0;
        end
    end
endmodule
