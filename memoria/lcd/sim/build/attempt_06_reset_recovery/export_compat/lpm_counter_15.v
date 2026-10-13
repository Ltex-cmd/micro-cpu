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


module lpm_counter_15(clock,aclr,sclr,q);
input clock;
input aclr;
input sclr;
output [18:0] q;

lpm_counter	lpm_instance(.clock(clock),.aclr(aclr),.sclr(sclr),.q(q));
	defparam	lpm_instance.lpm_direction = "UP";
	defparam	lpm_instance.lpm_modulus = 500000;
	defparam	lpm_instance.lpm_width = 19;

endmodule
