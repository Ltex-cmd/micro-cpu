// Copyright (C) 2025  Altera Corporation. All rights reserved.
// Your use of Altera Corporation's design tools, logic functions 
// and other software and tools, and any partner logic 
// functions, and any output files from any of the foregoing 
// (including device programming or simulation files), and any 
// associated documentation or information are expressly subject 
// to the terms and conditions of the Altera Program License 
// Subscription Agreement, the Altera Quartus Prime License Agreement,
// the Altera IP License Agreement, or other applicable license
// agreement, including, without limitation, that your use is for
// the sole purpose of programming logic devices manufactured by
// Altera and sold by Altera or its authorized distributors.  Please
// refer to the Altera Software License Subscription Agreements 
// on the Quartus Prime software download page.

// PROGRAM		"Quartus Prime"
// VERSION		"Version 25.1std.0 Build 1129 10/21/2025 SC Lite Edition"
// CREATED		"Tue Oct  6 23:57:02 2026"

module lcd_de2_115_top(
	CLOCK_50,
	KEY,
	SW,
	LCD_EN,
	LCD_RS,
	LCD_RW,
	LCD_ON,
	BUSY,
	INIT_DONE,
	LCD_DATA
);


input wire	CLOCK_50;
input wire	[1:0] KEY;
input wire	[3:0] SW;
output wire	LCD_EN;
output wire	LCD_RS;
output wire	LCD_RW;
output wire	LCD_ON;
output wire	BUSY;
output wire	INIT_DONE;
output wire	[7:0] LCD_DATA;

wire	BUTTON_CLEAN;
wire	BUTTON_PRESSED;
reg	KEY_SYNC;
wire	PRINT_PULSE;
reg	RESET_N;
wire	[3:0] SYNC_Q;
wire	SYNTHESIZED_WIRE_0;
reg	DFF_inst5;
wire	SYNTHESIZED_WIRE_1;
reg	DFF_inst1;
reg	DFF_inst3;
wire	SYNTHESIZED_WIRE_5;
wire	[3:0] SYNTHESIZED_WIRE_4;

assign	SYNTHESIZED_WIRE_0 = 1;




debouncer	b2v_BUTTON_FILTER(
	.rst_n(RESET_N),
	.inb(KEY_SYNC),
	.clk(CLOCK_50),
	.outb(BUTTON_CLEAN));
	defparam	b2v_BUTTON_FILTER.DELAY_BITS = 19;


lcd_operation_display	b2v_inst(
	.CLOCK_50(CLOCK_50),
	.RESET_N(RESET_N),
	.PRINT(PRINT_PULSE),
	.OPCODE(SYNC_Q),
	.LCD_EN(LCD_EN),
	.LCD_RS(LCD_RS),
	.LCD_RW(LCD_RW),
	.LCD_ON(LCD_ON),
	.BUSY(BUSY),
	.INIT_DONE(INIT_DONE),
	.LCD_DATA(LCD_DATA));


always@(posedge CLOCK_50 or negedge KEY[0])
begin
if (!KEY[0])
	begin
	DFF_inst1 <= 0;
	end
else
	begin
	DFF_inst1 <= SYNTHESIZED_WIRE_0;
	end
end

assign	SYNTHESIZED_WIRE_1 =  ~DFF_inst5;

assign	PRINT_PULSE = BUTTON_PRESSED & SYNTHESIZED_WIRE_1;



always@(posedge CLOCK_50 or negedge KEY[0])
begin
if (!KEY[0])
	begin
	RESET_N <= 0;
	end
else
	begin
	RESET_N <= DFF_inst1;
	end
end


always@(posedge CLOCK_50 or negedge RESET_N)
begin
if (!RESET_N)
	begin
	DFF_inst3 <= 0;
	end
else
	begin
	DFF_inst3 <= KEY[1];
	end
end


always@(posedge CLOCK_50 or negedge RESET_N)
begin
if (!RESET_N)
	begin
	KEY_SYNC <= 0;
	end
else
	begin
	KEY_SYNC <= DFF_inst3;
	end
end


always@(posedge CLOCK_50 or negedge RESET_N)
begin
if (!RESET_N)
	begin
	DFF_inst5 <= 0;
	end
else
	begin
	DFF_inst5 <= BUTTON_PRESSED;
	end
end

assign	SYNTHESIZED_WIRE_5 =  ~RESET_N;

assign	BUTTON_PRESSED =  ~BUTTON_CLEAN;


lpm_ff_0	b2v_SYNC_META(
	
	.clock(CLOCK_50),
	
	
	
	
	
	.aclr(SYNTHESIZED_WIRE_5),
	.data(SW),
	.q(SYNTHESIZED_WIRE_4));


lpm_ff_1	b2v_SYNC_STABLE(
	
	.clock(CLOCK_50),
	
	
	
	
	
	.aclr(SYNTHESIZED_WIRE_5),
	.data(SYNTHESIZED_WIRE_4),
	.q(SYNC_Q));


endmodule

// Simulation only: empty lpm_ff_0 stub removed; real exported wrapper supplied.

// Simulation only: empty lpm_ff_1 stub removed; real exported wrapper supplied.
