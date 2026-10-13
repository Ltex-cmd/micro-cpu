# Controlador LCD em BDF

Controlador para a primeira linha de um LCD HD44780 de 16 colunas, com barramento
paralelo de 8 bits e clock de 50 MHz. A fonte principal é o diagrama do Block
Editor do Quartus. Os exports Verilog servem à verificação da hierarquia real.

**Estado em 7 de outubro de 2026:** core conectado, compilado e verificado por
simulação; wrapper DE2-115 compilado após a correção do reset do debouncer.
A simulação funcional completa do wrapper também passou. Não houve teste físico
na placa, e a análise de temporização externa permanece incompleta.

## Fontes e projetos

| Projeto | Uso | Fonte principal | Pinagem de placa |
|---|---|---|---|
| [lcd_operation_display.qpf](lcd_operation_display.qpf) | Core independente | [lcd_operation_display.bdf](lcd_operation_display.bdf) | Não definida |
| [lcd_example_top.qpf](lcd_example_top.qpf) | Exemplo de integração com lógica síncrona | [lcd_example_top.bdf](lcd_example_top.bdf) | Não definida |
| [lcd_de2_115_top.qpf](lcd_de2_115_top.qpf) | Wrapper com KEY, SW e LCD da DE2-115 | [lcd_de2_115_top.bdf](lcd_de2_115_top.bdf) | Definida no QSF, sujeita à conferência física |

Os projetos selecionam Cyclone IV E, EP4CE115F29C7, no Quartus Prime Lite
25.1. O BSF do core fornece sua interface gráfica; o BDF fornece sua implementação.
O mux vem de [lcd_data_mux.qip](lcd_data_mux.qip), gerado pelo Quartus com duas
entradas separadas de 8 bits. Os QSFs usam os BDFs para síntese; não adicionar o
export Verilog do mesmo módulo como implementação concorrente.

O core final contém 17 IPs, quatro DFFs e 13 símbolos combinacionais. A
[auditoria geométrica](evidence/connected_geometry_audit.json) aprovou 110
portas conectadas, 154 bits de sinal e 26 taps físicos. O BDF final tem SHA-256
`7e165474f92b6c49520b716efdea7d89fc4c23aed9801a0de36c8a491b67faa5`.
A [auditoria estrutural](sim/build/audit_final_layout_20261007T0230/final_layout_report.md)
conferiu portas, conexões, larguras e parâmetros contra o export testado.

Capturas da revisão final: [visão geral](evidence/lcd_connected_full_desktop.png),
[detalhe da temporização](evidence/lcd_connected_timing_detail.png) e
[wrapper da placa](evidence/lcd_board_wrapper_full.png).

O exemplo síncrono encaminha CLOCK_50, RESET_N, PRINT e OPCODE ao core.
Seu QSF foi limpo de atribuições parciais de placa. O contrato de integração
está em [example_integration.md](example_integration.md).

O wrapper de placa foi montado na GUI com cinco DFFs, dois LPM_FF de quatro
bits, debouncer de 19 bits e portas AND/NOT. Usa duas etapas de sincronização
por bit, filtra KEY[1] e gera um pulso de PRINT por pressão. A cópia local
[debouncer.v](debouncer.v) inicializa `intermediate` e `outb` em `1'b1`, o nível
de botão liberado; o original em `../teste/` permanece intacto. O parâmetro
padrão do módulo continua 16; a instância do wrapper usa 19.
A [auditoria geométrica do wrapper](evidence/wrapper_connected_geometry_audit.json)
aprovou 63 endpoints, 25 grupos de conexão e 18 conferências do export. O símbolo
[lcd_de2_115_top.bsf](lcd_de2_115_top.bsf) também foi gerado pela GUI.
Detalhes e pinagem: [de2_115_board_top.md](de2_115_board_top.md).

### Interface do core

| Sinal | Direção | Contrato |
|---|---|---|
| CLOCK_50 | Entrada | Clock único de 50 MHz, período de 20 ns |
| RESET_N | Entrada | Reset ativo em zero; interrompe a operação atual |
| OPCODE[3..0] | Entrada | Código estável na borda que aceita PRINT |
| PRINT | Entrada | Pedido síncrono, aceito por uma nova borda de subida em idle |
| LCD_DATA[7..0] | Saída | Byte enviado ao LCD |
| LCD_EN | Saída | Enable registrado, pulso de 1 µs |
| LCD_RS | Saída | Zero para comando, um para caractere |
| LCD_RW | Saída | Zero; somente escrita |
| LCD_ON | Saída | Constante 1; alimentação do LCD habilitada |
| BUSY | Saída | Um durante inicialização ou impressão |
| INIT_DONE | Saída | Um após a inicialização, até o próximo reset |

O produtor deve esperar INIT_DONE=1 e BUSY=0, apresentar OPCODE e gerar uma
borda de PRINT. O core captura o opcode no aceite. Pedidos durante BUSY são
descartados, sem fila; manter PRINT alto não repete nem adia um pedido. Voltar
PRINT a zero antes da próxima solicitação. PRINT e OPCODE do core devem
pertencer ao domínio de CLOCK_50.

### Sequência e dados

TIMER é um contador de 19 bits, módulo 500000: cada frame dura 10 ms. Os
comparadores TIMER>=50 e TIMER<100 delimitam a janela de 50 ciclos do EN,
registrada por um DFF. ACCEPT limpa TIMER e inicia a temporização do pedido.

SLOT é um contador de cinco bits, módulo 32:

| SLOT | Função |
|---|---|
| 0–4 | Espera inicial de 50 ms, sem EN |
| 5–12 | Comandos 30, 30, 30, 38, 08, 01, 06, 0C |
| 13 | Idle |
| 14 | Não usado no fluxo normal |
| 15 | Comando 80 para a primeira posição da linha |
| 16–31 | Dezesseis caracteres da operação |

O avanço é síncrono a CLOCK_50. ACCEPT carrega 15; após o último caractere,
SLOT retorna a 13. Dois DFFs sincronizam a liberação do reset interno. A
inicialização termina após aproximadamente 130 ms; cada impressão aceita
ocupa 17 frames, aproximadamente 170 ms.
Durante reset, LCD_EN, LCD_RS e LCD_RW ficam em zero. LCD_ON permanece em um,
pois está ligado diretamente a VCC no BDF.

ROM_CONTROL tem 16×8 bits e lê [control.mif](control.mif). ROM_OPERATIONS tem
256×8 bits e lê [operations.mif](operations.mif): endereço = opcode×16 + coluna.
As duas usam endereço registrado e saída não registrada. SLOT[4] seleciona
texto no mux e define RS. Nomes curtos recebem espaços para apagar o restante
da mensagem anterior.

### Acrescentar nomes de operações

[operations.txt](operations.txt) mantém os nove nomes atuais e sete slots livres,
9–F. A interface continua com quatro bits e 16 códigos. Para validar e gerar:

```sh
python3 lcd/generate_operations.py --check
python3 lcd/generate_operations.py
```

Executar da raiz do repositório. O gerador usa o C original, valida códigos
únicos, ASCII e limite de 16 caracteres e confere o MIF antes de substituí-lo.
Os 15 testes do gerador passaram. O fluxo de recompilação e atualização do
SOF está em [README_operations.md](README_operations.md).

O mapa 0=ADD, 1=SUB, 2=MUL, 3=DIV, 4=MOD, 5=AND, 6=OR, 7=XOR e 8=JMP é um
**fixture de teste, não uma ISA confirmada**. Associar os nomes aos códigos reais
da CPU antes da integração. Acrescentar texto não implementa uma instrução na
CPU. [operations_fixture.txt](operations_fixture.txt) permanece separado do
mapa editável; a simulação preservada se refere a esse fixture.

## Simulação

**Core: PASS da cobertura conjunta em duas execuções do DUT real.** A tentativa
5 aprovou os 16 opcodes e uma repetição em idle, totalizando 17 impressões. Foi
interrompida pelo ambiente durante o cenário final de reset, sem falha de
assertion. A tentativa 6 concluiu a recuperação e uma impressão pós-reset com
marcador terminal de PASS e código de saída 0. Não é alegado um PASS terminal
de uma única execução integral.

A cobertura inclui latch do opcode, rejeição de PRINT durante init/BUSY,
PRINT mantido, resets no meio de EN durante init e print, 16 caracteres por
pedido, EN de 1 µs, cadência de 10 ms, limites de inicialização e hold de 20 ns.
As duas execuções usam o mesmo DUT, MIF e modelo oficial, com os mesmos
monitores/tasks. O export final contém os mesmos tokens funcionais do export
testado; suas diferenças se limitam ao comentário de data de criação.
A [conferência final das 23 fontes](sim/build/final_package_core_equivalence_20261007T0302/export_equivalence.json)
repetiu essa igualdade após o último export do wrapper, sem refazer a simulação.

Evidências: [relatório](sim/verification_report.md),
[cobertura conjunta](sim/build/coverage_union.json) e
[reprodução](sim/README.md). Não foi usado um controlador comportamental
substituto nem foram acelerados os contadores do circuito.

**Wrapper DE2-115: PASS terminal em execução completa, código de saída 0.**
O teste terminou em 803,461821 ms simulados, com CLOCK_50=50 MHz e
DELAY_BITS=19. Aprovou sincronização/reset, bouncing, debounce, pulso de um
ciclo, botão mantido, descarte durante BUSY, captura do opcode e interrupções
por reset. Houve duas impressões completas, OR e JMP, e recuperação após reset.
O DUT exportado e a cópia adaptada do debouncer foram preservados byte a byte.

Relatório: [verificação do wrapper](sim/board_verification_report.md).
O comando de reprodução e as limitações estão em
[de2_115_board_top.md](de2_115_board_top.md#testbench-da-hierarquia-real).
Os caminhos de ferramentas nos exemplos de simulação descrevem o ambiente
usado; ajuste PATH e a localização da biblioteca Quartus no seu computador.

## Compilação

Resultados de compilação completa no Quartus, com horários em UTC de
7 de outubro de 2026:

| Projeto | Estado da revisão atual | Recursos |
|---|---|---|
| Core lcd_operation_display | Successful às 02:30:41 | 63 LE, 32 registradores, 2176 bits de ROM |
| Exemplo lcd_example_top | Successful às 03:00:18, após remover a pinagem parcial | 65 LE, 32 registradores, 2176 bits de ROM |
| Wrapper lcd_de2_115_top | Successful às 02:57:42, após corrigir o reset do debouncer | 105 LE, 66 registradores, 21 pinos, 2176 bits de ROM |

Relatórios: [core](output_files/lcd_operation_display.flow.rpt),
[exemplo](example_output_files/lcd_example_top.flow.rpt) e
[wrapper](board_output_files/lcd_de2_115_top.flow.rpt). Saídas do exemplo ficam
em `example_output_files/`, separadas dos outros projetos. Uma compilação
bem-sucedida não encerra a revisão temporal externa nem constitui teste físico.

## Temporização

Cada projeto usa seu próprio SDC, com um único CLOCK_50 de 20 ns e incerteza
derivada. Os SDCs do core e do exemplo não são incluídos novamente no wrapper.
Não há clock derivado de PRINT, BYTE_ADVANCE ou LCD_EN.

O SDC da placa corta individualmente SW[3..0] e KEY[1] somente até os cinco
registradores de primeiro estágio. Cada seleção exige uma porta e um
registrador únicos. Os caminhos entre estágios, pelo debouncer e pelo core
continuam analisados; KEY[0] não recebeu uma exceção geral.

No relatório final do wrapper, os menores slacks multicorner são: setup
14,128 ns, hold 0,139 ns, recovery 17,734 ns, removal 0,647 ns e largura mínima
de pulso 9,202 ns, com TNS=0. Esses valores descrevem os caminhos analisados.
Ainda constam **KEY[0] e 12 saídas sem restrições externas**: BUSY, INIT_DONE,
LCD_DATA[7..0], LCD_EN e LCD_RS. O core standalone também mantém I/O sem
restrições completas. Não é declarado fechamento de timing da placa ou
cumprimento dos requisitos externos de setup/hold do LCD.

O [TimeQuest do exemplo](example_output_files/lcd_example_top.sta.rpt) registra
setup 14,182 ns, hold 0,101 ns, recovery 17,990 ns e removal 0,571 ns; seis
entradas e 12 saídas continuam sem restrições externas. Isso é coerente com
um exemplo de integração sem uma interface externa especificada.

Fonte do wrapper: [TimeQuest](board_output_files/lcd_de2_115_top.sta.rpt).
A revisão final das exceções CDC e das interfaces externas deve acompanhar a
integração e a placa efetivamente usada.

## Placa

**Teste físico: não realizado.** O wrapper com pinagem é lcd_de2_115_top.
Core e exemplo síncrono não possuem pinagem de placa aprovada; seus SOFs não
são imagens destinadas à programação da DE2-115.

No wrapper, KEY[0] é reset, KEY[1] solicita impressão e SW[3..0] seleciona o
opcode. BUSY e INIT_DONE vão a LEDG[0] e LEDG[1]. Ajustar os switches, esperar
sua estabilização e só então pressionar o botão; duas etapas por bit não
asseguram uma mudança multibit atômica. Para novo pedido, liberar o botão
pelo intervalo de debounce e pressionar quando INIT_DONE=1 e BUSY=0.

O QSF assume a configuração documentada de JP7 em 2,5 V para KEY/SW. A posição
real do jumper, VCCIO, pinagem, alimentação/contraste do LCD e polaridades
precisam ser conferidos na placa. A tabela e as fontes oficiais estão em
[de2_115_board_top.md](de2_115_board_top.md). A existência de um SOF gerado pelo
Quartus não significa que essas verificações físicas já tenham sido feitas.
