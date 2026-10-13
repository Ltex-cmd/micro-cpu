# Verificação do wrapper DE2-115

Atualização final: 7 de outubro de 2026, 03:10 UTC.

## Estado

Compilação Quartus, pinagem implementada e exceções CDC: **PASS**.
Simulação funcional completa: **PASS**, marcador final presente e código de saída 0.
SOF gerado pelo Quartus; **não gravado nem testado na placa**.

## Revisão verificada

- Top BDF: `lcd_de2_115_top.bdf`
- SHA-256 do BDF: `665a52e1e65e3e0d9a6f4e5a01643d0fc56f95c85d7c3a8f2c3d891e5d552fe6`
- Export Verilog gerado pela GUI, com KEY_SYNC escalar separado de SYNC_Q[3:0]
- Core BDF e IP mux reais, ROMs control.mif e operations.mif e cópia local do debouncer
- O runner confere que os módulos board, core e debouncer permanecem byte a byte
  iguais nas cópias preparadas para Icarus. Não há controlador substituto,
  reparo de conexões, redução de contadores ou force de estado interno
- O debouncer local difere do original `../teste/debouncer.v` somente nas
  duas atribuições de reset: intermediate=1 e outb=1. O original permanece intacto

## Compilação e pinagem

Quartus Prime 25.1 Standard Lite, EP4CE115F29C7. Compilação final concluída em
07/10/2026 às 02:57 UTC: zero erros e zero Critical Warnings. Uso: 105 elementos
lógicos, 66 registradores, 21 pinos e 2176 bits de memória.

A auditoria comparou todos os 21 pinos efetivamente implementados no `.pin`
com o QSF, incluindo padrão elétrico e marca de atribuição pelo usuário;
as direções também foram conferidas contra a interface do top.
Não há conflitos ou alocações automáticas nessas portas. KEY/SW e os dois LEDs
usam 2.5 V; CLOCK_50 e LCD usam 3.3-V LVTTL. Conferir a posição física de JP7
antes de programar: o QSF assume o padrão documental de 2,5 V, pinos 5–6.

O reset constante da cópia local do debouncer eliminou os avisos 13004/13310
e os latches inferidos pelo reset dependente da entrada. Os avisos restantes incluem:

- Contador do debouncer: soma de 32 bits truncada para 19 bits. A lógica
  compara o valor máximo antes de incrementar, mantendo a saturação prevista
- Buffers tri-state internos das ROMs convertidos em fios, e LCD_RW/LCD_ON
  reconhecidos como saídas constantes
- Drive strength não explicitado nas 14 saídas; slew rate também não
  explicitado em BUSY/INIT_DONE. O Fitter aplica seus padrões, que ainda
  exigem revisão elétrica para a carga real
- Recomendação AN447 para CLOCK_50 em 3.3-V LVTTL; conferir requisitos
  elétricos da interface na validação da placa
- Aviso de recurso LogicLock dependente de licença; o projeto compilou

Esses avisos não foram suprimidos para obter a aprovação de compilação.

Evidências: `../board_output_files/lcd_de2_115_top.map.rpt`, `.fit.rpt`, `.pin`
e `build/board/board_pin_audit.json`, que registra os 21 pinos e hashes das fontes.

## CDC e temporização interna

O SDC foi lido com status OK. Cinco seleções exatas, verificadas por contagem,
cortam apenas SW[i]→lpm_ff:SYNC_META|dffs[i] e KEY[1]→inst3. Todos os caminhos
primeiro estágio→segundo estágio continuam presentes nos três cantos analisados.

| Caminho | Menor margem reportada entre estágios |
|---|---:|
| SYNC_META[0] → SYNC_STABLE[0] | 0,190 ns |
| SYNC_META[1] → SYNC_STABLE[1] | 0,191 ns |
| SYNC_META[2] → SYNC_STABLE[2] | 0,189 ns |
| SYNC_META[3] → SYNC_STABLE[3] | 0,189 ns |
| inst3 → inst4, botão | 0,263 ns |

Margens agregadas do projeto: setup 14,128 ns; hold 0,139 ns;
recovery 17,734 ns; removal 0,647 ns. CLOCK_50 é o único clock e não há clocks
sem restrição. A análise não corta KEY[0] ou os caminhos internos de reset.

Ainda ficam sem restrição temporal KEY[0] e 12 saídas: BUSY, INIT_DONE,
LCD_DATA[7:0], LCD_EN e LCD_RS. LCD_RW e LCD_ON são constantes. Esses resultados
não são uma validação completa de I/O externo, setup/hold do LCD ou da placa.

Evidências: `../board_output_files/lcd_de2_115_top.sta.rpt`, `.sta.summary`
e `build/board/board_timing_audit.json`.

## Simulação real

Icarus 12.0, biblioteca oficial Quartus 220model.v, CLOCK_50=50 MHz,
DELAY_BITS=19 e tempos originais do controlador.

Execução iniciada às 03:00:07 UTC e concluída às 03:09 UTC, sem alteração do
DUT ou aceleração. O runner retornou código 0 e o marcador final
`PASS: actual board DUT checked;`. Cenários aprovados:

- Reset assíncrono e liberação sincronizada após dois clocks
- Reset no meio do primeiro EN de inicialização, aos 50,002 ms simulados
- Primeira inicialização completa, aos 180,002 ms simulados
- Rejeição de bouncing, aos 234,002 ms simulados
- Primeira impressão completa, opcode 6 (OR), aos 414,488 ms simulados,
  com descarte do pedido extra durante BUSY e sem repetição por botão mantido
- Reset durante a impressão seguinte; terceira época iniciada aos 457,976 ms
- Segunda inicialização completa, aos 587,976 ms simulados
- Segunda impressão completa, opcode 8 (JMP), aos 791,462 ms simulados
- Observação adicional de botão mantido; PASS final aos 803,461821 ms simulados

O trace contém 51 bytes completos: 16 comandos das duas inicializações,
34 bytes das duas impressões completas e um comando da impressão interrompida.
Os pulsos truncados por reset não contam como transferências completas.
Foram reconferidos os 65 hashes do manifesto após o término; todas as fontes,
bibliotecas e cópias de simulação coincidem com a revisão executada.

Evidência congelada: `../evidence/board_validation_20261007T0300/`.
Inclui `compile.log`, `simulation.log`, `board_lcd_trace.csv`, `input_manifest.txt`,
`export_compatibility.json`, `board_preflight.json`, `final_status.json`,
as auditorias de pinagem/CDC e cópias das fontes usadas.
As saídas originais da execução permanecem também em `build/board/`.

O runner pode ser reproduzido a partir da raiz do repositório:

```sh
source /workspace/shared/iverilog-toolchain/env.sh
QUARTUS_SIM_LIB=/workspace/shared/quartus_sim_lib \
  bash lcd/sim/run_board_iverilog.sh lcd/*.v
```

Dois bloqueios anteriores foram resolvidos, com evidências preservadas:

- O export inicialmente misturava DFF escalar e saída de LPM_FF no mesmo
  vetor reg[4:0], rejeitado por Icarus. O fio foi separado na GUI e o BDF
  reexportado, sem alteração artificial no Verilog de simulação
- O simulador abortou internamente ao encerrar fork/join_any dentro de uma
  task automática do checker. Os timeouts do testbench passaram a usar
  espera por clocks com limite; a implementação do DUT permaneceu intacta

## Limites e etapas externas

O mapa de opcodes é um fixture de teste, ainda sem confirmação da ISA real.
A simulação RTL não mede metastabilidade analógica nem garante captura
atômica quando vários switches físicos mudam. Estabilizar SW antes de KEY[1].
Antes da validação física, revisar os caminhos externos ainda não restringidos,
conferir JP7/tensões, programar a placa sob essas condições e registrar o teste.
