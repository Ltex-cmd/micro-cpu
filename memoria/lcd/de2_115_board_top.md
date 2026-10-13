# Wrapper de placa DE2-115

O projeto `lcd_de2_115_top.qpf` reúne o wrapper BDF da placa, o core BDF,
o QIP do mux e a cópia adaptada do debouncer. O wrapper foi construído no
Block Editor e compilado no Quartus. A pinagem implementada e as exceções
de CDC foram conferidas; a simulação completa do export real passou. Resultados
e evidências estão em [sim/board_verification_report.md](sim/board_verification_report.md).

**O Quartus gerou `board_output_files/lcd_de2_115_top.sof`. Ele não foi
gravado nem testado na placa. Antes de programar, conferir a posição real
de JP7, os padrões de I/O e as pendências de temporização externa abaixo.**

## Hipótese elétrica explícita

O QSF deste projeto assume **JP7 na configuração padrão documentada de 2,5 V**
e aplica `2.5 V` a KEY[1..0] e SW[3..0]. O manual Terasic informa que esses
sinais dependem de JP7. A tabela 4-8 indica os pinos 5 e 6 do jumper para
2,5 V. Essa escolha documental não confirma a posição na placa recebida.

Conferir fisicamente a seleção de tensão e o VCCIO antes da programação.
Se a placa estiver em outra configuração, harmonizar o projeto e o hardware
de forma deliberada; o software não muda o jumper nem verifica sua posição.
Não mover jumpers com a placa energizada.

CLOCK_50 e o LCD usam 3,3 V. BUSY e INIT_DONE vão a LEDG[0] e LEDG[1], que
o manual lista como 2,5 V; por isso o QSF usa `2.5 V` nesses dois sinais,
sem aplicar um padrão global indistinto a todas as portas.

## Interface e pinos

| Porta do wrapper | Recurso de placa | Pino | Padrão no QSF |
|---|---|---|---|
| CLOCK_50 | Oscilador 50 MHz | Y2 | 3.3-V LVTTL |
| KEY[0] | Botão de reset | M23 | 2.5 V, exige conferir JP7 |
| KEY[1] | Botão de impressão | M21 | 2.5 V, exige conferir JP7 |
| SW[0] | Bit 0 do opcode | AB28 | 2.5 V, exige conferir JP7 |
| SW[1] | Bit 1 do opcode | AC28 | 2.5 V, exige conferir JP7 |
| SW[2] | Bit 2 do opcode | AC27 | 2.5 V, exige conferir JP7 |
| SW[3] | Bit 3 do opcode | AD27 | 2.5 V, exige conferir JP7 |
| BUSY | LEDG[0] | E21 | 2.5 V |
| INIT_DONE | LEDG[1] | E22 | 2.5 V |

LCD_DATA[7..0] usa M5, M3, K2, K1, K7, L2, L1, L3, respectivamente.
LCD_EN=L4, LCD_RS=M2, LCD_RW=M1 e LCD_ON=L5. Todos os sinais do LCD estão
configurados como 3.3-V LVTTL. LCD_BLON não é usado.

Fontes primárias: [manual oficial Terasic](https://www.terasic.com.tw/attachment/archive/502/DE2_115_User_manual.pdf),
tabelas 4-1/4-2, página 35; tabela 4-3, página 36; tabela 4-5, página 38;
tabela 4-6, páginas 39-40; seção 4.7, páginas 40-41, para JP7.
A [cópia no wiki oficial](https://www.terasic.com.tw/wiki/images/f/ff/DE2_115_User_manual_2013.pdf)
também permite conferir KEY e SW. A conferência documental de 7 de outubro
de 2026 confirmou CLOCK_50=Y2, a pinagem LCD acima, os seis pinos KEY/SW,
LEDG[0]=E21 e LEDG[1]=E22. Estes dois LEDs estão listados em 2,5 V.

## Cadeia funcional do BDF

1. KEY[0] comanda a cadeia de reset dos DFFs `inst1` e `inst2`: asserção assíncrona,
   liberação sincronizada. O reset interno alimenta o condicionamento das
   entradas e o core
2. SW[3..0] passa pelos LPM_FF de largura 4 `SYNC_META` e
   `SYNC_STABLE`. KEY[1] passa pelos DFFs `inst3` e `inst4`, primeiro e
   segundo estágio respectivamente. Todos usam CLOCK_50 e reset para zero.
   As saídas do segundo estágio são SYNC_Q[3..0] para SW e KEY_SYNC para
   o botão. O particionamento 4+1 preserva duas etapas por bit e permite
   exportar o barramento de FFs e o DFF escalar como sinais separados
3. KEY_SYNC alimenta o debouncer BUTTON_FILTER, com **DELAY_BITS=19**.
   O parâmetro padrão do arquivo original continua 16
4. Um NOT inverte BUTTON_CLEAN, o nível filtrado do botão ativo em zero,
   para obter BUTTON_PRESSED. O DFF `inst5` armazena esse nível;
   sua saída anterior, NOT + AND2 geram PRINT_PULSE,
   positivo por um ciclo na nova pressão
5. PRINT_PULSE alimenta PRINT e SYNC_Q[3..0] alimenta OPCODE[3..0]
   do core. Todos os clocks permanecem CLOCK_50
6. As saídas do core alimentam o LCD e os dois LEDs de estado

Com 19 bits e 50 MHz, o filtro exige 524288 ciclos estáveis, aproximadamente
10,48576 ms, após a mudança amostrada. Ele preserva a polaridade e não gera
um pulso por conta própria. A auditoria detalhada do código original está em
[example_integration.md](example_integration.md#auditoria-do-debouncer-existente).

A cópia local `debouncer.v` é adaptada para esta interface de botão ativo
baixo: durante reset, `intermediate` e `outb` recebem o valor constante
`1'b1`, correspondente ao botão liberado. O original `../teste/debouncer.v`
permanece intacto; licença, portas e parâmetro padrão 16 são preservados.
O valor 19 é aplicado à instância BUTTON_FILTER no BDF.

Essa adaptação corrige a inicialização da entrada e o aviso de síntese
13004/13310 observado na primeira compilação, quando o reset ainda copiava
`inb` e gerava circuitos com latch. A nova síntese, concluída em 7 de outubro
de 2026 às 02:57 UTC, já confirmou a ausência desses avisos e dos latches
inferidos pelo reset anterior. A simulação da hierarquia completa é uma
verificação adicional, registrada separadamente.
Durante reset, o checker exige BUTTON_CLEAN=1, BUTTON_PRESSED=0 e
PRINT_PULSE=0, inclusive com KEY[1] em nível de pressão. Ainda é
necessário aplicar KEY[0] e validar a inicialização real na placa.

Uma cadeia de dois FFs por bit reduz o risco de metastabilidade, mas não
torna uma troca multibit de switches atômica. Ajustar SW primeiro, aguardar
sua estabilização e só então pressionar KEY[1]; manter SW estável até o
aceite. Não alterar switches enquanto pressiona o botão e supor uma captura
coerente garantida.

Pedidos durante BUSY ou inicialização continuam sendo descartados. Para um
novo pedido, liberar o botão pelo intervalo de debounce e pressionar de novo
quando INIT_DONE=1 e BUSY=0. Manter pressionado não deve repetir a impressão.
Pressão mantida durante reset e liberação foi coberta pela simulação aprovada.

## Clock e CDC

`lcd_de2_115_top.sdc` declara CLOCK_50 com 20 ns e deriva sua incerteza. O
QSF não inclui também os SDCs do core ou do exemplo síncrono, evitando uma
declaração duplicada do mesmo clock.

O relatório de temporização do wrapper confirmou os cinco registradores
de entrada: `lpm_ff:SYNC_META|dffs[0]` até `dffs[3]` e `inst3`. O SDC corta
individualmente apenas SW[i] até seu primeiro estágio correspondente e
KEY[1] até inst3. Esses sinais chegam exclusivamente às respectivas entradas
D. Cada seleção exige uma entrada e um registrador com `get_collection_size`;
se a hierarquia mudar e a seleção deixar de ser única, a leitura do SDC falha.
A execução final do Timing Analyzer leu o SDC com status OK e confirmou as
cinco seleções: restou apenas KEY[0] entre as entradas não restringidas.
Não são cortados caminhos entre estágios, debouncer, detector de borda ou
core. KEY[0] e os caminhos de recovery/removal do reset ficam fora desses
cortes. Nomes de símbolos do BDF, sozinhos, não substituem essa verificação
da netlist e das coleções.

Não foram inventados atrasos de I/O, exceções gerais ou clocks derivados
de PRINT, BYTE_ADVANCE ou LCD_EN. O SDC ainda não demonstra cobertura total
de temporização do LCD e da placa.

O relatório final do wrapper contém um único clock CLOCK_50, nenhum clock
sem restrição e margens internas agregadas de setup 14,128 ns, hold 0,139 ns,
recovery 17,734 ns e removal 0,647 ns. Permanecem sem restrição a entrada
assíncrona KEY[0] e 12 saídas: BUSY, INIT_DONE, LCD_DATA[7..0], LCD_EN e
LCD_RS. LCD_RW e LCD_ON são constantes. Esses resultados verificam os
caminhos internos analisados, sem equivaler à validação de toda a
temporização externa do LCD, reset físico ou placa.

## Estado da verificação

- Compilação, Fitter e Timing Analyzer concluídos sem erros ou Critical Warnings:
  105 elementos lógicos, 66 registradores, 21 pinos e 2176 bits de ROM
- Os 21 pinos e padrões de I/O do arquivo `.pin` coincidem com o QSF
- DELAY_BITS=19 confirmado no BDF e no parâmetro da instância exportada
- Cinco exceções CDC resolvidas, com todos os cinco caminhos entre primeiro
  e segundo estágio ainda analisados e com margem positiva nos três cantos
- Simulação funcional do export real concluída com PASS e código de saída 0,
  após 803,461821 ms simulados; ver [board_verification_report.md](sim/board_verification_report.md)

## Pendências antes da validação física

- Definir/verificar setup e hold externos do LCD, a entrada assíncrona KEY[0]
  e os demais caminhos de I/O ainda sem restrição temporal
- Revisar os padrões de drive strength/slew rate usados pelo Fitter e o
  aviso AN447 para CLOCK_50, conforme a carga e a interface reais
- Confirmar ISA real: operations.mif ainda é fixture de teste
- Conferir JP7, níveis elétricos e pinagem física antes de qualquer programação
- Programar/testar na placa somente após essas verificações e registrar o resultado

## Testbench da hierarquia real

`sim/tb_lcd_de2_115_top.sv` e `sim/run_board_iverilog.sh` executam o export
real do wrapper. A execução completa só é aprovada quando chega ao marcador
final de PASS; checkpoints intermediários não substituem esse resultado.

O teste preserva CLOCK_50 em 50 MHz, o parâmetro DELAY_BITS=19 e todos os
contadores do core. Não há aceleração por override, force de estado interno
ou controlador substituto. As sondas internas apenas observam RESET_N,
KEY_SYNC, SYNC_Q[3..0], BUTTON_CLEAN, BUTTON_PRESSED e PRINT_PULSE; a
instância do debouncer é identificada por leitura do export. O checker
combina `{KEY_SYNC, SYNC_Q[3:0]}` apenas para comparar a amostragem dos cinco
bits, sem adicionar lógica ou modificar conexões dentro do DUT.
O runner verifica que board, core e debouncer seguem byte a byte idênticos
nas cópias preparadas para o simulador.

Cobertura do teste:

- Latência dos dois estágios de sincronização de KEY[1] e dos quatro switches
- Asserção assíncrona de KEY[0] e liberação de RESET_N após dois clocks
- Debounce medido em 524288 clocks a partir da mudança amostrada
- Bouncing com duração total maior que 10 ms, mas sem nível estável suficiente
- Um único pulso de PRINT de 20 ns por pressão estável, sem repetição mantida
- Pedido em BUSY descartado e opcode preservado após a captura
- Botão pressionado durante reset e mantido até depois da inicialização
- Reset durante EN na inicialização e durante EN de uma impressão
- Duas inicializações completas e duas impressões completas, com fixture
  independente, 17 bytes por impressão, EN de 1 us e cadência de 10 ms

Execução a partir da raiz do repositório, depois do export pela GUI:

```sh
source /workspace/shared/iverilog-toolchain/env.sh
QUARTUS_SIM_LIB=/workspace/shared/quartus_sim_lib \
  bash lcd/sim/run_board_iverilog.sh lcd/*.v
```

Fornecer somente os exports e dependências reais, sem versões antigas que
definam o mesmo módulo. Logs, hashes, sondas e trace ficam em
`sim/build/board/`, separados da execução standalone do core. O sucesso
exige o marcador `PASS: actual board DUT checked;`; código de saída zero
sozinho não basta, pois um modelo de biblioteca pode chamar `$finish`.

O teste não valida metastabilidade analógica, coerência simultânea de
switches físicos, posição de JP7, níveis elétricos, timing pós-fit ou placa.
