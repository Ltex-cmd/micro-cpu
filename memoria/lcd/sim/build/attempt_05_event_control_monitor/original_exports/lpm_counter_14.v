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
// CREATED		"Tue Oct  6 20:29:19 2026"


module lpm_counter_14(sload,clock,aclr,sset,cnt_en,data,q);
input sload;
input clock;
input aclr;
input sset;
input cnt_en;
input [4:0] data;
output [4:0] q;

lpm_counter	lpm_instance(.sload(sload),.clock(clock),.aclr(aclr),.sset(sset),.cnt_en(cnt_en),.data(data),.q(q));
	defparam	lpm_instance.LPM_DIRECTION = "UP";
	defparam	lpm_instance.LPM_MODULUS = 32;
	defparam	lpm_instance.LPM_SVALUE = 13;
	defparam	lpm_instance.LPM_WIDTH = 5;

endmodule
