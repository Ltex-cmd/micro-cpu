# Base clock only: CLOCK_50 is 50 MHz, with a 20 ns period.
# Add this file to the Quartus project through its project settings.
# For a parent top, adapt the port target and avoid duplicate clock definitions.
create_clock -name CLOCK_50 -period 20.000 [get_ports {CLOCK_50}]
derive_clock_uncertainty

# Intentionally no invented input/output delays, generated clock on LCD_EN,
# or blanket false paths. PRINT/OPCODE integration, asynchronous reset handling,
# external LCD setup/hold and board delays still need a timing review.
# This file does not establish complete I/O timing coverage or timing closure.
