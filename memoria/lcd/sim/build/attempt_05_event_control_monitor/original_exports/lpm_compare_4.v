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


module lpm_compare_4(dataa,datab,ageb);
input [4:0] dataa;
input [4:0] datab;
output ageb;

lpm_compare	lpm_instance(.dataa(dataa),.datab(datab),.ageb(ageb));
	defparam	lpm_instance.LPM_PIPELINE = 0;
	defparam	lpm_instance.LPM_REPRESENTATION = "UNSIGNED";
	defparam	lpm_instance.LPM_WIDTH = 5;

endmodule
