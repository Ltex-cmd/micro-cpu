`timescale 1ns/1ps

// This is a black-box checker, not an implementation of the LCD controller.
// DUT MUST be the real lcd_operation_display exported from the Quartus BDF.
// The opcode names below are an explicit test fixture, not the confirmed ISA.
module tb_lcd_operation_display;
    localparam time CLOCK_PERIOD = 20ns;
    localparam time FRAME_PERIOD = 10000000ns;
    localparam time EN_WIDTH = 1000ns;
    localparam time FIRST_INIT_MIN = 50000000ns;
    localparam time INIT_DONE_MIN = 130000000ns;
    localparam time HOLD_MIN = 20ns;

    logic CLOCK_50 = 0;
    logic RESET_N = 0;
    logic [3:0] OPCODE = 0;
    logic PRINT = 0;
    wire [7:0] LCD_DATA;
    wire LCD_EN, LCD_RS, LCD_RW, LCD_ON, BUSY, INIT_DONE;

    lcd_operation_display dut (
        .CLOCK_50(CLOCK_50), .RESET_N(RESET_N), .OPCODE(OPCODE), .PRINT(PRINT),
        .LCD_DATA(LCD_DATA), .LCD_EN(LCD_EN), .LCD_RS(LCD_RS),
        .LCD_RW(LCD_RW), .LCD_ON(LCD_ON), .BUSY(BUSY), .INIT_DONE(INIT_DONE)
    );

    always #(CLOCK_PERIOD / 2) CLOCK_50 = ~CLOCK_50;

    logic [7:0] init_command [0:7];
    integer init_bytes = 0;
    integer print_bytes = 0;
    integer completed_transactions = 0;
    integer completed_initializations = 0;
    integer reset_epoch = 0;
    integer trace_fd;
    bit epoch_valid = 0;
    bit transaction_expected = 0;
    logic [3:0] expected_opcode = 0;
    time reset_released_at = 0;
    time last_en_rise = 0;
    time last_en_fall = 0;
    time last_init_fall = 0;
    time last_print_fall = 0;
    bit pulse_open = 0;
    bit have_fall = 0;
    bit have_init_fall = 0;
    bit have_print_fall = 0;
    logic [7:0] pulse_data;
    logic pulse_rs;

    task automatic fail(input string message);
        $fatal(1, "FAIL at %0t: %s", $time, message);
    endtask

    // Independent golden data: do not obtain expected bytes from the DUT ROM.
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

    function automatic logic [7:0] fixture_char(
        input logic [3:0] opcode, input integer column
    );
        logic [127:0] line;
        begin
            line = fixture_line(opcode);
            fixture_char = line[127 - column * 8 -: 8];
        end
    endfunction

    task automatic check_constants;
        if (LCD_RW !== 1'b0) fail("LCD_RW must be 0 (write only)");
        if (LCD_ON !== 1'b1) fail("LCD_ON must be 1 while out of reset");
    endtask

    always @(negedge RESET_N) begin
        epoch_valid = 0;
        init_bytes = 0;
        print_bytes = 0;
        transaction_expected = 0;
        pulse_open = 0;
        have_fall = 0;
        have_init_fall = 0;
        have_print_fall = 0;
    end

    always @(posedge RESET_N) begin
        reset_released_at = $time;
        epoch_valid = 1;
        reset_epoch = reset_epoch + 1;
        $display("Reset epoch %0d released at %0t", reset_epoch, $time);
    end

    always @(posedge INIT_DONE) begin
        if (RESET_N === 1'b1 && epoch_valid) begin
            #1ps;
            if ($time - reset_released_at < INIT_DONE_MIN)
                fail("INIT_DONE rose earlier than 130 ms after reset release");
            if (init_bytes != 8)
                fail($sformatf("INIT_DONE after %0d init bytes; expected 8", init_bytes));
            if (LCD_EN !== 1'b0) fail("INIT_DONE rose while EN was active");
            completed_initializations = completed_initializations + 1;
            $display("PASS init epoch %0d at %0t", reset_epoch, $time);
        end
    end

    always @(negedge INIT_DONE) begin
        if (RESET_N === 1'b1 && epoch_valid)
            fail("INIT_DONE deasserted without reset");
    end

    always @(posedge LCD_EN) begin
        if (RESET_N !== 1'b1 || !epoch_valid) fail("EN rose during reset");
        if (pulse_open) fail("EN rose before the previous pulse ended");
        check_constants();
        if ((^LCD_DATA) === 1'bx || (LCD_RS !== 0 && LCD_RS !== 1))
            fail("Unknown LCD data or RS at EN rise");
        if (init_bytes == 0 && $time - reset_released_at < FIRST_INIT_MIN)
            fail("First initialization pulse started earlier than 50 ms");
        if (init_bytes >= 8 && !transaction_expected)
            fail("Unexpected EN pulse while idle / rejected PRINT was queued");
        if (init_bytes >= 8 && BUSY !== 1'b1)
            fail("Display pulse without BUSY asserted");
        last_en_rise = $time;
        pulse_data = LCD_DATA;
        pulse_rs = LCD_RS;
        pulse_open = 1;
    end

    always @(negedge LCD_EN) begin
        if (RESET_N === 1'b1 && epoch_valid) begin
            if (!pulse_open) fail("EN fell without a corresponding rise");
            if ($time - last_en_rise != EN_WIDTH)
                fail($sformatf("EN width %0t; expected exactly 1 us", $time-last_en_rise));
            check_constants();
            if (LCD_DATA !== pulse_data || LCD_RS !== pulse_rs)
                fail("LCD data/RS changed within an EN pulse");
            if (init_bytes < 8) begin
                if (INIT_DONE !== 1'b0) fail("INIT_DONE active before init sequence ends");
                if (LCD_RS !== 1'b0 || LCD_DATA !== init_command[init_bytes])
                    fail($sformatf("Init byte %0d: RS=%b DATA=%02h expected RS=0 DATA=%02h",
                                   init_bytes, LCD_RS, LCD_DATA, init_command[init_bytes]));
                if (have_init_fall && $time-last_init_fall != FRAME_PERIOD)
                    fail("Initialization bytes are not spaced exactly 10 ms apart");
                $fdisplay(trace_fd, "%0d,%0d,init,%0d,-,%b,%02h",
                          $time, reset_epoch, init_bytes, LCD_RS, LCD_DATA);
                last_init_fall = $time;
                have_init_fall = 1;
                init_bytes = init_bytes + 1;
            end else begin
                if (INIT_DONE !== 1'b1 || !transaction_expected)
                    fail("Unexpected display byte; no accepted idle PRINT edge");
                if (BUSY !== 1'b1) fail("BUSY dropped before last EN fall");
                if (print_bytes >= 17) fail("More than 17 bytes in one print request");
                if (print_bytes == 0) begin
                    if (LCD_RS !== 1'b0 || LCD_DATA !== 8'h80)
                        fail("Print must begin with command 80, RS=0");
                end else begin
                    if (LCD_RS !== 1'b1 ||
                        LCD_DATA !== fixture_char(expected_opcode, print_bytes-1))
                        fail($sformatf("Opcode %h char %0d: RS=%b DATA=%02h expected RS=1 DATA=%02h",
                                       expected_opcode, print_bytes-1, LCD_RS, LCD_DATA,
                                       fixture_char(expected_opcode, print_bytes-1)));
                end
                if (have_print_fall && $time-last_print_fall != FRAME_PERIOD)
                    fail("Print bytes are not spaced exactly 10 ms apart");
                $fdisplay(trace_fd, "%0d,%0d,print,%0d,%h,%b,%02h",
                          $time, reset_epoch, print_bytes, expected_opcode, LCD_RS, LCD_DATA);
                last_print_fall = $time;
                have_print_fall = 1;
                print_bytes = print_bytes + 1;
            end
            last_en_fall = $time;
            have_fall = 1;
            pulse_open = 0;
        end
        // A reset may deliberately truncate an active pulse. That truncated
        // pulse is not counted as a valid LCD transfer and has no hold check.
    end

    always @(LCD_DATA or LCD_RS or LCD_RW) begin
        // Let same-timestamp EN/reset monitors settle before checking hold.
        #0;
        if (RESET_N === 1'b1 && epoch_valid) begin
            if (LCD_EN === 1'b1)
                fail("LCD data, RS or RW changed while EN was high");
            if (have_fall && $time-last_en_fall < HOLD_MIN)
                fail("LCD data/RS/RW did not hold for 20 ns after EN fall");
        end
    end

    // These invariants depend only on the observed controls and reset state.
    // Check every change after delta-cycle settling instead of re-evaluating
    // identical values on ~190 million clock edges. This also catches changes
    // between clock samples; no invariant or stimulus is removed.
    always @(LCD_EN or INIT_DONE or BUSY or LCD_RW or LCD_ON or RESET_N or epoch_valid) begin
        #1ps;
        if (RESET_N === 1'b1 && epoch_valid) begin
            if ((LCD_EN !== 1'b0 && LCD_EN !== 1'b1) ||
                (INIT_DONE !== 1'b0 && INIT_DONE !== 1'b1) ||
                (BUSY !== 1'b0 && BUSY !== 1'b1))
                fail("Unknown EN, INIT_DONE or BUSY");
            check_constants();
            if (INIT_DONE === 1'b1 && BUSY === 1'b0 && LCD_EN !== 1'b0)
                fail("EN is active while initialized and idle");
        end
    end

    task automatic reset_for(input time duration);
        RESET_N = 0;
        #21ns;
        if (LCD_EN !== 1'b0 || INIT_DONE !== 1'b0)
            fail("Reset did not clear EN and INIT_DONE within one 50 MHz clock");
        #(duration - 21ns);
        @(negedge CLOCK_50);
        RESET_N = 1;
    endtask

    // Called only serially by test_sequence. Static tasks avoid the Icarus 12
    // automatic-context JOIN_DETACH bug; stimuli/assertions are unchanged.
    task wait_initialized;
        fork : wait_for_init
            begin wait (INIT_DONE === 1'b1); end
            begin #160000000ns; fail("Initialization timeout (160 ms)"); end
        join_any
        disable wait_for_init;
        #1ns;
        if (init_bytes != 8) fail("Incorrect initialization byte count");
        // A PRINT edge during initialization, held through its end, must not queue.
        #20000000ns;
        if (BUSY !== 1'b0 || LCD_EN !== 1'b0)
            fail("Controller did not remain idle after initialization");
    endtask

    task arm_print(input logic [3:0] opcode);
        if (INIT_DONE !== 1'b1 || BUSY !== 1'b0 || PRINT !== 1'b0)
            fail("Test driver tried to request a print outside idle/PRINT=0");
        expected_opcode = opcode;
        transaction_expected = 1;
        print_bytes = 0;
        have_print_fall = 0;
        OPCODE = opcode;
        @(negedge CLOCK_50);
        PRINT = 1;
        fork : wait_for_busy
            begin wait (BUSY === 1'b1); end
            begin #20000ns; fail("Idle PRINT edge was not accepted within 20 us"); end
        join_any
        disable wait_for_busy;
        #1ns;
    endtask

    task wait_print_count(input integer count);
        fork : wait_for_count
            begin wait (print_bytes >= count); end
            begin #200000000ns; fail("Timeout waiting for a partial print"); end
        join_any
        disable wait_for_count;
    endtask

    task finish_print;
        fork : wait_for_print
            begin wait (BUSY === 1'b0); end
            begin #200000000ns; fail("Print did not finish within 200 ms"); end
        join_any
        disable wait_for_print;
        #1ns;
        if (print_bytes != 17)
            fail($sformatf("Request ended with %0d bytes; expected 17", print_bytes));
        if (LCD_EN !== 1'b0) fail("EN active after transaction ended");
        completed_transactions = completed_transactions + 1;
        $display("PASS opcode %h: command 80 + 16 fixture chars at %0t", expected_opcode, $time);
        transaction_expected = 0;
        // Keep PRINT high for two full frames after BUSY ends. A queued request
        // or level-sensitive retrigger is caught by the independent EN monitor.
        #20000000ns;
        if (BUSY !== 1'b0 || LCD_EN !== 1'b0)
            fail("Held-high PRINT restarted the controller after BUSY ended");
        @(negedge CLOCK_50);
        PRINT = 0;
        repeat (4) @(negedge CLOCK_50);
    endtask

    initial begin : test_sequence
        integer opcode;
        bit recovery_only;
        recovery_only = $test$plusargs("RECOVERY_ONLY");
        init_command[0] = 8'h30;
        init_command[1] = 8'h30;
        init_command[2] = 8'h30;
        init_command[3] = 8'h38;
        init_command[4] = 8'h08;
        init_command[5] = 8'h01;
        init_command[6] = 8'h06;
        init_command[7] = 8'h0C;
        $timeformat(-9, 0, " ns", 16);
        trace_fd = $fopen("lcd_trace.csv", "w");
        if (!trace_fd) fail("Could not create lcd_trace.csv");
        $fdisplay(trace_fd, "time_ns,reset_epoch,kind,index,opcode,rs,data_hex");
        if ($test$plusargs("VCD")) begin
            $dumpfile("lcd_trace.vcd");
            // Exclude CLOCK_50 and internal counters to keep multi-second runs small.
            $dumpvars(0, RESET_N, OPCODE, PRINT, LCD_DATA, LCD_EN, LCD_RS,
                         LCD_RW, LCD_ON, BUSY, INIT_DONE);
        end

        reset_for(200ns);
        #5000000ns;
        @(negedge CLOCK_50);
        PRINT = 1;                       // rejected during initialization
        wait (init_bytes == 2);
        @(posedge LCD_EN);
        #200ns;
        reset_for(200ns);                 // truncate the third init pulse
        wait_initialized();              // full sequence must restart at 30
        @(negedge CLOCK_50);
        PRINT = 0;
        repeat (4) @(negedge CLOCK_50);

        // Full fixture coverage, with OPCODE changed after BUSY rises so the
        // requested opcode must have been latched at acceptance.
        // The optional recovery segment repeats the same interruptive resets
        // and final print, but skips the already-recorded opcode sweep.
        if (!recovery_only) begin
        for (opcode = 0; opcode < 16; opcode = opcode + 1) begin
            arm_print(opcode[3:0]);
            @(negedge CLOCK_50);
            OPCODE = ~opcode[3:0];
            if (opcode == 0) begin
                // Additional rising PRINT edge while busy, kept high across
                // return to idle. It must neither corrupt nor queue a print.
                // Do this after real data transfers, so a broken restart cannot
                // hide as a small delay before the first byte of the request.
                wait_print_count(4);
                @(negedge CLOCK_50);
                PRINT = 0;
                repeat (8) @(negedge CLOCK_50);
                if (BUSY !== 1'b1) fail("Unexpected early end of print");
                PRINT = 1;
            end
            finish_print();
        end

        // A fresh idle edge must work again, including a previously used opcode.
        arm_print(4'h8);
        @(negedge CLOCK_50);
        PRINT = 0;                       // request may end before printing ends
        finish_print();
        end

        // Reset during printing, in the middle of an EN pulse. A stale print
        // must not resume when reset is released; initialization starts over.
        arm_print(4'h3);
        wait_print_count(4);
        @(posedge LCD_EN);
        #200ns;
        reset_for(200ns);
        wait_initialized();
        @(negedge CLOCK_50);
        PRINT = 0;
        repeat (4) @(negedge CLOCK_50);
        arm_print(4'h8);
        @(negedge CLOCK_50);
        OPCODE = 4'h0;
        finish_print();

        if (completed_transactions != (recovery_only ? 1 : 18) || completed_initializations != 2)
            fail("Test driver coverage counters are inconsistent");
        $fclose(trace_fd);
        if (recovery_only) begin
        $display("PASS: actual DUT recovery checked; 1 complete print after reset, 2 complete init sequences,");
        $display("      reset during init/print, opcode latch after reset, held PRINT, no idle/reset EN,");
        $display("      1 us EN, 10 ms cadence, init deadlines and 20 ns hold.");
        end else begin
        $display("PASS: actual DUT checked; 16 opcodes, 18 complete prints, 2 complete init sequences,");
        $display("      reset during init/print, opcode latch, rejected busy/init edges, held PRINT,");
        $display("      no idle/reset EN, 1 us EN, 10 ms cadence, init deadlines and 20 ns hold.");
        end
        $finish;
    end

    initial begin
        #8000000000ns;
        fail("Global watchdog expired (8 simulated seconds)");
    end
endmodule
