# DE2-115 primary oscillator; all wrapper/core logic uses this clock.
create_clock -name CLOCK_50 -period 20.000 [get_ports {CLOCK_50}]
derive_clock_uncertainty

# Names verified in the board timing netlist/report from 2026-10-07.
# Each asynchronous data input feeds only the D pin of its first-stage FF.
# Require one exact input and one exact register for every cut; fail loudly
# after hierarchy changes rather than silently masking a different endpoint.
foreach {board_cdc_port_name board_cdc_reg_name} {
    {SW[0]} {lpm_ff:SYNC_META|dffs[0]}
    {SW[1]} {lpm_ff:SYNC_META|dffs[1]}
    {SW[2]} {lpm_ff:SYNC_META|dffs[2]}
    {SW[3]} {lpm_ff:SYNC_META|dffs[3]}
    {KEY[1]} {inst3}
} {
    set board_cdc_port [get_ports $board_cdc_port_name]
    set board_cdc_reg [get_registers $board_cdc_reg_name]
    if {[get_collection_size $board_cdc_port] != 1 ||
        [get_collection_size $board_cdc_reg] != 1} {
        error "Expected one CDC input and first-stage register: $board_cdc_port_name -> $board_cdc_reg_name"
    }
    set_false_path -from $board_cdc_port -to $board_cdc_reg
}

# Do not cut first-stage -> second-stage, the functional logic, all KEY[*],
# KEY[0] reset recovery/removal, or entire clock domains.
# No broad false paths, guessed input/output delays or LCD_EN generated clock.
# External LCD timing and reset/CDC analysis still require explicit review.
