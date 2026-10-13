`timescale 1ns/1ps
`include "board_probe_paths.svh"

// Checker only. Instantiate the actual Quartus export, with its real clock,
// ROMs, 19-bit debounce and LCD controller. Never force internal DUT state.
module tb_lcd_de2_115_top;
    localparam time CLOCK_PERIOD = 20ns;
    localparam time DEBOUNCE_TIME = 10485760ns;
    logic CLOCK_50 = 0;
    logic [1:0] KEY = 2'b11;
    logic [3:0] SW = 4'h0;
    wire [7:0] LCD_DATA;
    wire LCD_EN, LCD_RS, LCD_RW, LCD_ON, BUSY, INIT_DONE;
    lcd_de2_115_top dut (
        .CLOCK_50(CLOCK_50), .KEY(KEY), .SW(SW), .LCD_DATA(LCD_DATA),
        .LCD_EN(LCD_EN), .LCD_RS(LCD_RS), .LCD_RW(LCD_RW),
        .LCD_ON(LCD_ON), .BUSY(BUSY), .INIT_DONE(INIT_DONE)
    );
    wire [4:0] synchronized_inputs = `BOARD_SYNC_BUS;
    always #(CLOCK_PERIOD/2) CLOCK_50 = ~CLOCK_50;

    integer init_bytes = 0;
    integer print_bytes = 0;
    integer complete_inits = 0;
    integer complete_prints = 0;
    integer print_pulses = 0;
    integer epoch = 0;
    integer trace_fd;
    bit epoch_live = 0;
    bit transaction_expected = 0;
    bit en_open = 0;
    bit print_open = 0;
    bit have_init_fall = 0;
    bit have_print_fall = 0;
    bit have_lcd_fall = 0;
    logic [3:0] expected_opcode;
    logic [7:0] init_command [0:7];
    logic [7:0] en_data;
    logic en_rs;
    time reset_release, en_rise, print_rise;
    time init_fall, print_fall, lcd_fall;
    logic sampled_button = 0;
    time button_stable_since = 0;
    bit button_change_seen = 0;
    logic [4:0] sampled_inputs = 0;
    logic [4:0] expected_sync = 0;

    task automatic fail(input string message);
        $fatal(1, "FAIL board at %0t: %s", $time, message);
    endtask

    function automatic logic [127:0] fixture_line(input logic [3:0] opcode);
        case (opcode)
            4'h0: fixture_line = "ADD             ";
            4'h1: fixture_line = "SUB             ";
            4'h2: fixture_line = "MUL             ";
            4'h3: fixture_line = "DIV             ";
            4'h4: fixture_line = "MOD             ";
            4'h5: fixture_line = "AND             ";
            4'h6: fixture_line = "OR              ";
            4'h7: fixture_line = "XOR             ";
            4'h8: fixture_line = "JMP             ";
            default: fixture_line = "                ";
        endcase
    endfunction

    function automatic logic [7:0] fixture_char(input logic [3:0] opcode,
                                               input integer column);
        logic [127:0] line;
        begin
            line = fixture_line(opcode);
            fixture_char = line[127-column*8 -: 8];
        end
    endfunction

    always @(negedge KEY[0]) begin
        epoch_live = 0;
        init_bytes = 0;
        print_bytes = 0;
        transaction_expected = 0;
        en_open = 0;
        print_open = 0;
        have_init_fall = 0;
        have_print_fall = 0;
        have_lcd_fall = 0;
        #1ns;
        if (dut.RESET_N !== 0 || LCD_EN !== 0 || INIT_DONE !== 0)
            fail("KEY0 assertion did not clear reset, EN and INIT_DONE asynchronously");
        if (dut.BUTTON_CLEAN !== 1 || dut.BUTTON_PRESSED !== 0 || dut.PRINT_PULSE !== 0)
            fail("Reset must initialize the active-low button as released, without PRINT");
    end

    always @(posedge dut.RESET_N) begin
        if (KEY[0] !== 1) fail("Internal reset released while KEY0 is asserted");
        reset_release = $time;
        epoch_live = 1;
        epoch = epoch + 1;
        $display("Board epoch %0d released at %0t", epoch, $time);
    end

    // Observe the logical 5-bit bus as a two-cycle sampled interface. It may
    // use a 4-bit SW LPM_FF pair and a separate KEY1 DFF pair. This verifies
    // simulation connectivity/latency, not analog metastability.
    always @(posedge CLOCK_50 or negedge dut.RESET_N) begin
        if (!dut.RESET_N) begin
            sampled_inputs = 0;
            expected_sync = 0;
        end else begin
            expected_sync = sampled_inputs;
            sampled_inputs = {KEY[1], SW};
        end
        #1ps;
        if (dut.RESET_N === 1 && synchronized_inputs !== expected_sync)
            fail("SYNC_Q is not the expected two-stage {KEY1,SW[3:0]} sample");
    end

    // Measure each accepted clean-level change from the sampling edge on
    // which the debouncer first sees its new synchronized input.
    always @(posedge CLOCK_50 or negedge dut.RESET_N) begin
        if (!dut.RESET_N) begin
            sampled_button = synchronized_inputs[4];
            button_change_seen = 0;
        end else if (synchronized_inputs[4] !== sampled_button) begin
            sampled_button = synchronized_inputs[4];
            button_stable_since = $time;
            button_change_seen = 1;
        end
    end
    always @(dut.BUTTON_CLEAN) begin
        if (epoch_live && dut.RESET_N === 1 && button_change_seen) begin
            if ($time - button_stable_since != DEBOUNCE_TIME)
                fail($sformatf("Debounce delay %0t, expected 2^19 clocks (%0t)",
                               $time-button_stable_since, DEBOUNCE_TIME));
            if (dut.BUTTON_CLEAN !== sampled_button)
                fail("Debouncer changed polarity or accepted the wrong level");
        end
    end

    always @(posedge dut.PRINT_PULSE) begin
        if (epoch_live && dut.RESET_N === 1) begin
            if (print_open) fail("PRINT rose without a completed prior pulse");
            print_pulses = print_pulses + 1;
            print_rise = $time;
            print_open = 1;
            if (CLOCK_50 !== 1) fail("PRINT did not rise on a clock edge");
        end
    end
    always @(negedge dut.PRINT_PULSE) begin
        if (epoch_live && dut.RESET_N === 1 && print_open) begin
            if ($time-print_rise != CLOCK_PERIOD)
                fail("PRINT pulse is not exactly one 50 MHz clock cycle");
            print_open = 0;
        end
    end

    always @(posedge INIT_DONE) begin
        if (epoch_live) begin
            #1ps;
            if (init_bytes != 8 || $time-reset_release < 130000000ns)
                fail("Initialization completed without eight commands / 130 ms wait");
            if (LCD_EN !== 0) fail("INIT_DONE rose during an LCD pulse");
            complete_inits = complete_inits + 1;
            $display("PASS board initialization %0d at %0t", complete_inits, $time);
        end
    end

    always @(posedge LCD_EN) begin
        if (!epoch_live || KEY[0] !== 1) fail("LCD_EN rose during reset");
        if (en_open) fail("Nested LCD_EN pulse");
        if (LCD_RW !== 0 || LCD_ON !== 1 || (^LCD_DATA) === 1'bx)
            fail("Invalid LCD output at EN rise");
        if (init_bytes == 0 && $time-reset_release < 50000000ns)
            fail("First initialization byte before 50 ms");
        if (init_bytes >= 8 && !transaction_expected)
            fail("Unexpected print: idle/held/busy/reset request was queued");
        if (init_bytes >= 8 && BUSY !== 1) fail("LCD write without BUSY");
        en_open = 1;
        en_rise = $time;
        en_data = LCD_DATA;
        en_rs = LCD_RS;
    end

    always @(negedge LCD_EN) begin
        if (epoch_live && KEY[0] === 1) begin
            if (!en_open || $time-en_rise != 1000ns)
                fail("LCD_EN is not exactly 1 us wide");
            if (LCD_DATA !== en_data || LCD_RS !== en_rs)
                fail("LCD data or RS changed during EN");
            if (init_bytes < 8) begin
                if (LCD_RS !== 0 || LCD_DATA !== init_command[init_bytes])
                    fail($sformatf("Wrong initialization command %0d: %02h",init_bytes,LCD_DATA));
                if (have_init_fall && $time-init_fall != 10000000ns)
                    fail("Initialization cadence differs from 10 ms");
                init_fall = $time;
                have_init_fall = 1;
                $fdisplay(trace_fd,"%0d,%0d,init,%0d,-,%b,%02h",$time,epoch,init_bytes,LCD_RS,LCD_DATA);
                init_bytes = init_bytes + 1;
            end else begin
                if (!transaction_expected || INIT_DONE !== 1 || BUSY !== 1)
                    fail("Unexpected print byte");
                if (print_bytes >= 17) fail("More than 17 bytes per request");
                if (print_bytes == 0) begin
                    if (LCD_RS !== 0 || LCD_DATA !== 8'h80)
                        fail("Print does not begin with cursor-home command 80");
                end else if (LCD_RS !== 1 || LCD_DATA !== fixture_char(expected_opcode,print_bytes-1))
                    fail($sformatf("Wrong character for opcode %h column %0d: %02h",
                                   expected_opcode,print_bytes-1,LCD_DATA));
                if (have_print_fall && $time-print_fall != 10000000ns)
                    fail("Printing cadence differs from 10 ms");
                print_fall = $time;
                have_print_fall = 1;
                $fdisplay(trace_fd,"%0d,%0d,print,%0d,%h,%b,%02h",$time,epoch,print_bytes,expected_opcode,LCD_RS,LCD_DATA);
                print_bytes = print_bytes + 1;
            end
            lcd_fall = $time;
            have_lcd_fall = 1;
            en_open = 0;
        end
        // Reset deliberately truncates EN. A truncated pulse is not a byte.
    end

    always @(LCD_DATA or LCD_RS or LCD_RW) begin
        #0;
        if (epoch_live && KEY[0] === 1) begin
            if (LCD_EN === 1) fail("LCD data/control changed while EN was high");
            if (have_lcd_fall && $time-lcd_fall < CLOCK_PERIOD)
                fail("LCD data/control hold time is shorter than one clock");
        end
    end

    always @(negedge CLOCK_50) begin
        if (epoch_live) begin
            if ((^{LCD_EN, LCD_RS, LCD_RW, LCD_ON, BUSY, INIT_DONE,
                   dut.PRINT_PULSE, dut.BUTTON_CLEAN}) === 1'bx)
                fail("Unknown board control output");
            if (LCD_RW !== 0 || LCD_ON !== 1) fail("Wrong write-only/power constants");
        end
    end

    task automatic assert_reset;
        KEY[0] = 0;
        #200ns;
        if (LCD_EN !== 0 || INIT_DONE !== 0 || dut.RESET_N !== 0)
            fail("Reset did not clear state");
        if (dut.BUTTON_CLEAN !== 1 || dut.BUTTON_PRESSED !== 0 || dut.PRINT_PULSE !== 0)
            fail("Reset did not retain the released button level");
    endtask

    task automatic release_reset;
        @(negedge CLOCK_50);
        #3ns;
        KEY[0] = 1;
        #1ns;
        if (dut.RESET_N !== 0) fail("Reset release was asynchronous");
        @(posedge CLOCK_50);
        #1ps;
        if (dut.RESET_N !== 0) fail("Reset released after only one stage");
        @(posedge CLOCK_50);
        #1ps;
        if (dut.RESET_N !== 1) fail("Reset failed to release after two stages");
    endtask

    task automatic await_idle;
        time deadline;
        deadline = $time + 160000000ns;
        while (INIT_DONE !== 1 || BUSY !== 0) begin
            @(negedge CLOCK_50);
            if ($time >= deadline) fail("Initialization timeout");
        end
        #1ns;
    endtask

    task automatic release_button;
        KEY[1] = 1;
        #11000000ns;
        if (dut.BUTTON_CLEAN !== 1 || dut.PRINT_PULSE !== 0)
            fail("Button did not return to released state");
    endtask

    task automatic expect_request(input logic [3:0] opcode);
        SW = opcode;
        #200ns;
        expected_opcode = opcode;
        print_bytes = 0;
        have_print_fall = 0;
        transaction_expected = 1;
    endtask

    task automatic press_button;
        integer previous_pulses;
        previous_pulses = print_pulses;
        KEY[1] = 0;
        #11000000ns;
        if (dut.BUTTON_CLEAN !== 0 || print_pulses != previous_pulses+1)
            fail("Stable pressure did not create exactly one PRINT pulse");
    endtask

    task automatic finish_print;
        time deadline;
        deadline = $time + 200000000ns;
        while (BUSY !== 0) begin
            @(negedge CLOCK_50);
            if ($time >= deadline) fail("Print completion timeout");
        end
        #1ns;
        if (print_bytes != 17) fail("Completed print did not contain exactly 17 bytes");
        transaction_expected = 0;
        complete_prints = complete_prints + 1;
        $display("PASS board print %0d, opcode %h at %0t",complete_prints,expected_opcode,$time);
    endtask

    integer baseline_pulses;
    initial begin
        trace_fd = $fopen("board_lcd_trace.csv","w");
        if (!trace_fd) fail("Cannot open board LCD trace");
        $fdisplay(trace_fd,"time_ns,epoch,kind,index,opcode,rs,data_hex");
        init_command[0]=8'h30; init_command[1]=8'h30; init_command[2]=8'h30;
        init_command[3]=8'h38; init_command[4]=8'h08; init_command[5]=8'h01;
        init_command[6]=8'h06; init_command[7]=8'h0C;
        if (`BOARD_FILTER.DELAY_BITS != 19) fail("Actual debouncer instance is not DELAY_BITS=19");
        if ($test$plusargs("VCD")) begin
            $dumpfile("board_lcd_trace.vcd");
            $dumpvars(1, tb_lcd_de2_115_top);
        end

        // Held active-low button across reset, including interruption of the
        // first LCD initialization pulse. No request may survive to idle.
        #1ns;
        KEY[1] = 0;
        assert_reset();
        release_reset();
        @(posedge LCD_EN);
        #400ns;
        assert_reset();
        release_reset();
        await_idle();
        #12000000ns;
        if (BUSY !== 0) fail("Held-during-reset button caused a delayed request");
        release_button();
        baseline_pulses = print_pulses;

        // Total bouncing lasts longer than the threshold, but no individual
        // state does. It must never be accepted as a stable pressure.
        repeat (4) begin
            KEY[1] = 0; #3000000ns;
            KEY[1] = 1; #2000000ns;
        end
        #11000000ns;
        if (print_pulses != baseline_pulses || dut.BUTTON_CLEAN !== 1 || BUSY !== 0)
            fail("Bounce/short pressure caused a request");
        $display("PASS board bounce rejection at %0t",$time);

        expect_request(4'h6);
        press_button();
        if (BUSY !== 1) fail("Debounced request was not accepted while idle");
        SW = 4'h9; #203ns; SW = 4'h3; // Captured opcode must remain OR.
        release_button();
        press_button(); // This new pulse occurs during BUSY and is discarded.
        baseline_pulses = print_pulses;
        finish_print();
        #12000000ns;
        if (BUSY !== 0 || print_pulses != baseline_pulses)
            fail("Held or busy request repeated after return to idle");

        // Interrupt a real print while EN is high, still holding the button.
        release_button();
        expect_request(4'h1);
        press_button();
        @(posedge LCD_EN);
        #400ns;
        assert_reset();
        release_reset();
        await_idle();
        #12000000ns;
        if (BUSY !== 0) fail("Interrupted print resumed after reset");

        release_button();
        expect_request(4'h8);
        press_button();
        if (BUSY !== 1) fail("New request after reset was not accepted");
        baseline_pulses = print_pulses;
        finish_print();
        #12000000ns;
        if (BUSY !== 0 || print_pulses != baseline_pulses)
            fail("Held button repeated the final print");
        if (complete_inits != 2 || complete_prints != 2)
            fail("Coverage counters differ from expected completed scenarios");
        $fclose(trace_fd);
        $display("PASS: actual board DUT checked; debounce=19, sync/reset, bounce, one-cycle pulses, held/busy rejection, opcode capture, two full prints and reset interruptions");
        $finish;
    end

    initial begin
        #1200000000ns;
        fail("Global board simulation timeout");
    end
endmodule
