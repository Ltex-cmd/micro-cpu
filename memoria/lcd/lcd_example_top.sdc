# Synchronous example: one 50 MHz clock shared by producer and LCD controller.
create_clock -name CLOCK_50 -period 20.000 [get_ports {CLOCK_50}]
derive_clock_uncertainty

# The core's standalone SDC is intentionally not also included in this project.
# No input/output delays or blanket false paths are invented here.
# External I/O, reset recovery/removal and LCD setup/hold still need review.
# LCD_EN and BYTE_ADVANCE are not generated clocks.
