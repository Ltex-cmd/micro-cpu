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
// CREATED		"Tue Oct  6 23:20:17 2026"

module lcd_operation_display(
	CLOCK_50,
	RESET_N,
	PRINT,
	OPCODE,
	LCD_EN,
	LCD_RS,
	LCD_RW,
	LCD_ON,
	BUSY,
	INIT_DONE,
	LCD_DATA
);


input wire	CLOCK_50;
input wire	RESET_N;
input wire	PRINT;
input wire	[3:0] OPCODE;
output reg	LCD_EN;
output wire	LCD_RS;
output wire	LCD_RW;
output wire	LCD_ON;
output wire	BUSY;
output wire	INIT_DONE;
output wire	[7:0] LCD_DATA;

wire	ACCEPT;
wire	BUSY_ALTERA_SYNTHESIZED;
wire	BYTE_ADVANCE;
wire	[7:0] CTRL_DATA;
wire	EN_NEXT;
wire	[18:0] FIFTY_CONST;
wire	[4:0] FIVE_CONST;
wire	FRAME_END;
wire	GE50;
wire	IDLE;
wire	[18:0] K100;
wire	[4:0] K13;
wire	[4:0] K15;
wire	[18:0] KEND;
wire	LT100;
wire	ONE;
wire	[3:0] OPCODE_Q;
reg	PRINT_PREV;
wire	PRINT_PREV_N;
wire	RESET;
reg	RESET_STAGE1;
wire	RETURN_IDLE;
reg	RST_N;
wire	SEND_ACTIVE;
wire	SLOT31;
wire	[4:0] SLOT_Q;
wire	STATE_GE5;
wire	[7:0] TEXT_DATA;
wire	[18:0] TIMER_Q;

assign	LCD_RW = 0;
assign	LCD_ON = 1;
wire	[7:0] GDFX_TEMP_SIGNAL_0;


assign	GDFX_TEMP_SIGNAL_0 = {OPCODE_Q[3:0],SLOT_Q[3:0]};

assign	ACCEPT = PRINT & PRINT_PREV_N & IDLE;


lpm_compare_0	b2v_CMP_FRAME_END(
	
	
	
	.dataa(TIMER_Q),
	.datab(KEND),
	
	.aeb(FRAME_END)
	
	
	
	);


lpm_compare_1	b2v_CMP_GE50(
	
	
	
	.dataa(TIMER_Q),
	.datab(FIFTY_CONST),
	
	
	
	
	.ageb(GE50)
	);


lpm_compare_2	b2v_CMP_IDLE(
	
	
	
	.dataa(SLOT_Q),
	.datab(K13),
	
	.aeb(IDLE),
	
	
	.ageb(INIT_DONE)
	);


lpm_compare_3	b2v_CMP_LT100(
	
	
	
	.dataa(TIMER_Q),
	.datab(K100),
	
	
	
	
	
	.alb(LT100));


lpm_compare_4	b2v_CMP_SLOT5(
	
	
	
	.dataa(SLOT_Q),
	.datab(FIVE_CONST),
	
	
	
	
	.ageb(STATE_GE5)
	);


lpm_constant_5	b2v_CONST_50(
	.result(FIFTY_CONST));



lcd_data_mux	b2v_DATA_MUX(
	.sel(SLOT_Q[4]),
	.data0x(CTRL_DATA),
	.data1x(TEXT_DATA),
	.result(LCD_DATA));

assign	EN_NEXT = SEND_ACTIVE & GE50 & LT100;


assign	BYTE_ADVANCE = FRAME_END & BUSY_ALTERA_SYNTHESIZED;

assign	RETURN_IDLE = FRAME_END & SLOT31;

assign	SEND_ACTIVE = STATE_GE5 & BUSY_ALTERA_SYNTHESIZED;

assign	BUSY_ALTERA_SYNTHESIZED =  ~IDLE;

assign	PRINT_PREV_N =  ~PRINT_PREV;

assign	RESET =  ~RST_N;


always@(posedge CLOCK_50 or negedge RST_N)
begin
if (!RST_N)
	begin
	LCD_EN <= 0;
	end
else
	begin
	LCD_EN <= EN_NEXT;
	end
end


always@(posedge CLOCK_50 or negedge RST_N)
begin
if (!RST_N)
	begin
	PRINT_PREV <= 0;
	end
else
	begin
	PRINT_PREV <= PRINT;
	end
end


always@(posedge CLOCK_50 or negedge RESET_N)
begin
if (!RESET_N)
	begin
	RESET_STAGE1 <= 0;
	end
else
	begin
	RESET_STAGE1 <= ONE;
	end
end


always@(posedge CLOCK_50 or negedge RESET_N)
begin
if (!RESET_N)
	begin
	RST_N <= 0;
	end
else
	begin
	RST_N <= RESET_STAGE1;
	end
end


lpm_constant_6	b2v_inst2(
	.result(K100));


lpm_constant_7	b2v_inst3(
	.result(KEND));


lpm_constant_8	b2v_inst4(
	.result(K15));


assign	LCD_RS = SLOT_Q[4];



lpm_constant_9	b2v_inst8(
	.result(FIVE_CONST));


lpm_constant_10	b2v_inst9(
	.result(K13));

assign	SLOT31 = ONE & SLOT_Q[4] & SLOT_Q[0] & SLOT_Q[3] & SLOT_Q[2] & SLOT_Q[1];


lpm_ff_11	b2v_OPCODE_LATCH(
	.enable(ACCEPT),
	.clock(CLOCK_50),
	
	
	
	
	
	.aclr(RESET),
	.data(OPCODE),
	.q(OPCODE_Q));


lpm_rom_12	b2v_ROM_CONTROL(
	.inclock(CLOCK_50),
	
	
	.address(SLOT_Q[3:0]),
	.q(CTRL_DATA));


lpm_rom_13	b2v_ROM_OPERATIONS(
	.inclock(CLOCK_50),
	
	
	.address(GDFX_TEMP_SIGNAL_0),
	.q(TEXT_DATA));


lpm_counter_14	b2v_SLOT(
	.sload(ACCEPT),
	.clock(CLOCK_50),
	
	
	.aclr(RESET),
	
	
	.sset(RETURN_IDLE),
	
	.cnt_en(BYTE_ADVANCE),
	
	.data(K15),
	
	.q(SLOT_Q));


lpm_counter_15	b2v_TIMER(
	
	.clock(CLOCK_50),
	
	
	.aclr(RESET),
	
	
	
	
	
	.sclr(ACCEPT),
	
	
	.q(TIMER_Q));

assign	BUSY = BUSY_ALTERA_SYNTHESIZED;
assign	ONE = 1;

endmodule

// Simulation only: empty lpm_compare_0 stub removed; real exported wrapper supplied.

// Simulation only: empty lpm_compare_1 stub removed; real exported wrapper supplied.

// Simulation only: empty lpm_compare_2 stub removed; real exported wrapper supplied.

// Simulation only: empty lpm_compare_3 stub removed; real exported wrapper supplied.

// Simulation only: empty lpm_compare_4 stub removed; real exported wrapper supplied.

// Simulation only: empty lpm_constant_10 stub removed; real exported wrapper supplied.

// Simulation only: empty lpm_constant_5 stub removed; real exported wrapper supplied.

// Simulation only: empty lpm_constant_6 stub removed; real exported wrapper supplied.

// Simulation only: empty lpm_constant_7 stub removed; real exported wrapper supplied.

// Simulation only: empty lpm_constant_8 stub removed; real exported wrapper supplied.

// Simulation only: empty lpm_constant_9 stub removed; real exported wrapper supplied.

// Simulation only: empty lpm_counter_14 stub removed; real exported wrapper supplied.

// Simulation only: empty lpm_counter_15 stub removed; real exported wrapper supplied.

// Simulation only: empty lpm_ff_11 stub removed; real exported wrapper supplied.

// Simulation only: empty lpm_rom_12 stub removed; real exported wrapper supplied.

// Simulation only: empty lpm_rom_13 stub removed; real exported wrapper supplied.
