# Verificacao do LCD exportado do BDF

## Estado desta entrega

**PASS da cobertura conjunta, em duas execucoes do DUT real.** A tentativa 5
aprovou os 16 opcodes e uma nova impressao do opcode 8 em idle (17 impressoes).
Foi interrompida pelo ambiente durante a recuperacao de reset, sem assertion
falhar. A tentativa 6 executou o segmento de recuperacao ate o PASS terminal e
codigo de saida 0: reinicializacao completa e uma impressao correta apos reset.
Nao ha um PASS terminal de uma unica execucao integral; essa distincao esta
registrada em `verification_report.md` e `build/coverage_union.json`.

As duas execucoes usam o mesmo export Quartus, MIF e biblioteca oficial 25.1,
com identicos monitores, tasks de verificacao e watchdog. O circuito usa tempos
reais de 50 MHz, sem aceleracao dos contadores. O script
`verify_coverage_union.py` confere logs, contagens, fontes e hashes. O Icarus 12.0
oficial esta instalado em `/workspace/shared/iverilog-toolchain/`.

A auditoria estrutural `audit_bdf_export.py` tambem aprovou o BDF reorganizado:
17 IPs, quatro DFFs, 13 simbolos combinacionais, interface, conexoes e parametros
coincidem com o export testado. E uma verificacao estrutural reproduzivel, nao
uma prova formal nem um novo export da GUI.

A primeira tentativa falhou devido a entrada escalar do mux exportado. Essa
versao e seus logs foram preservados; o export posterior usa o `lcd_data_mux`
gerado pelo Quartus, com entradas separadas de 8 bits. Nenhuma largura foi
reparada na simulacao e nenhum controlador comportamental foi usado.

O conversor original `teste/txt_to_mif.c` foi compilado com avisos tratados como
erros, nao foi alterado, e ambos os MIF foram conferidos byte a byte.

## BDF final com buses e taps

A revisao final do layout tem hash
`7e165474f92b6c49520b716efdea7d89fc4c23aed9801a0de36c8a491b67faa5`
e passou contra o export das 02:20, incluindo a religacao fisica de K100.
Ver `build/audit_final_layout_20261007T0230/final_layout_report.md`.

O export final da GUI foi comparado com as fontes testadas: todos os 23 arquivos
sao identicos fora do comentario de data de criacao. O BDF final tambem passou
contra ambos os exports. A evidencia esta em
`build/audit_bus_taps_final_20261007T0221/equivalence_report.md`.

O auditor distingue fios escalares de buses, preserva a ordem dos membros de
vetores/concatenacoes e conecta cada tap apenas ao bit nomeado. Shorts entre
bits e taps invalidos continuam sendo rejeitados. Para conferir os dez casos
positivos/negativos do auditor: `python3 -m unittest -v test_audit_bdf_export.py`.
A simulacao anterior nao foi repetida.

## Dados de teste

- `../control.mif`: 16 palavras de 8 bits, endereco e dado em HEX. Enderecos
  5, 6, 7: 30; 8: 38; 9: 08; A: 01; B: 06; C: 0C; F: 80; demais: 00
- `../operations.mif`: 256 palavras de 8 bits. Endereco = opcode * 16 + coluna
- `../operations_fixture.txt`: 0 ADD, 1 SUB, 2 MUL, 3 DIV, 4 MOD, 5 AND, 6 OR,
  7 XOR, 8 JMP; opcodes 9..F: dezesseis espacos cada
- Todos os nomes tem exatamente 16 bytes depois do preenchimento ASCII 20

**Esse mapa e um fixture explicito de teste, nao uma afirmacao sobre a ISA real.**
A correspondencia real entre opcodes e operacoes ainda depende de confirmacao.
Quando ela mudar, atualizar o fixture e as expectativas independentes do teste.

## Reproducao dos MIF

A partir da raiz do repositorio:

```sh
bash lcd/sim/regenerate_fixture.sh
python3 lcd/sim/verify_mifs.py
```

O primeiro comando recompila o conversor original em `sim/build/` e regenera
somente `operations.mif`. `control.mif` e uma tabela fixa, versionavel e validada
pelo segundo comando. Ambos exigem todos os enderecos explicitos, sem sobreposicao.
Esses scripts nao alteram BDF, QSF ou HDL sintetizavel.

## Simulacao real

1. Salvar o BDF completo na GUI do Quartus e exportar seu Verilog real, mantendo
   o top `lcd_operation_display` e os nomes de portas abaixo
2. Nas ROMs, usar nomes relativos `control.mif` e `operations.mif`; nao caminhos
   absolutos. Incluir no comando quaisquer submodulos realmente exportados
3. Executar em um ambiente com Icarus e as bibliotecas dessa instalacao Quartus

```sh
source /workspace/shared/iverilog-toolchain/env.sh
QUARTUS_ROOTDIR=/home/agent/altera_lite/25.1std/quartus \
  bash lcd/sim/run_iverilog.sh /caminho/do/export_real/lcd_operation_display.v
```

Tambem se aceita a raiz `.../25.1std`; o runner procura `quartus/eda/sim_lib`.
Se somente as bibliotecas foram materializadas, usar `QUARTUS_SIM_LIB`:

```sh
QUARTUS_SIM_LIB=/workspace/shared/quartus_sim_lib DUMP_VCD=1 \
  bash lcd/sim/run_iverilog.sh lcd/lcd_operation_display.v lcd/lcd_data_mux.v lcd/lpm*.v
```

O runner verifica o carregador do `lpm_rom` instalado. A biblioteca Quartus 25.1
chama `convert_to_ver_file` antes de `$readmemh`: nesse caso os MIF autenticos sao
copiados para `sim/build/`. Para modelos com `$readmemh` direto, sao usados dados
HEX com os mesmos nomes relativos. Portanto, **nao reutilizar dados de
`sim/build/` como fontes de sintese**: os MIF autenticos estao sempre em `lcd/`.

O export GUI inclui stubs vazios `synthesis black_box` que duplicam seus wrappers
`lpm_*.v`. `prepare_quartus_sources.py` cria copias exclusivamente para simulacao:

- remove somente stubs vazios quando ha uma implementacao exportada unica
- adapta os identificadores `LPM_*` para a caixa minuscula da biblioteca oficial
- representa valores numericos LPM_SVALUE/AVALUE/PVALUE como strings decimais,
  conforme o contrato do modelo oficial, preservando o valor numerico

Cada transformacao e cada hash ficam em `export_compatibility.json`; o modulo
top `lcd_operation_display` precisa permanecer byte a byte identico. Nao sao
corrigidos largura, fio, conexao, logica ou temporizacao. Os exports originais
nao sao sobrescritos. O runner exige o marcador final de PASS, inclusive quando
um `$finish` da biblioteca termina o simulador com codigo zero.

Saidas: `compile.log`, `simulation.log`, `input_manifest.txt`, `lcd_trace.csv`
e, com `DUMP_VCD=1`, `lcd_trace.vcd`, todos em `sim/build/`. O manifesto registra
hashes do BDF, export, bibliotecas e dados efetivamente usados. Ele nao substitui
a necessidade de reexportar o BDF depois da ultima alteracao.

## Segmento de recuperacao e cobertura conjunta

O modo padrao continua sendo a suite integral. Para repetir somente o segmento
que interrompe init/print, reinicializa e imprime depois do reset:

```sh
source /workspace/shared/iverilog-toolchain/env.sh
QUARTUS_SIM_LIB=/workspace/shared/quartus_sim_lib DUMP_VCD=1 \
SIM_SCENARIO=reset_recovery bash lcd/sim/run_iverilog.sh \
  lcd/lcd_operation_display.v lcd/lcd_data_mux.v lcd/lpm*.v
```

Esse modo exige seu proprio marcador `PASS: actual DUT recovery checked;` e
nao produz o marcador da suite integral. Ele mantem todos os monitores e as
mesmas assertions; apenas omite a varredura anterior dos 16 opcodes e ajusta a
contagem esperada para uma impressao completa no segmento selecionado.

A cobertura preservada pode ser conferida a partir de `lcd/sim/`:

```sh
python3 verify_coverage_union.py \
  build/attempt_05_event_control_monitor build/attempt_06_reset_recovery \
  --output build/coverage_union.json
python3 audit_bdf_export.py \
  build/attempt_06_reset_recovery/lcd_operation_display.bdf \
  build/attempt_06_reset_recovery/original_exports \
  --output build/attempt_06_reset_recovery/bdf_export_audit.json
```

O segmento completo possui CSV/VCD terminados normalmente. O CSV/VCD da tentativa
interrompida podem perder sua cauda ainda em buffer; o log registra os checks
concluidos. Os arquivos de cada tentativa foram congelados antes da seguinte.

## Interface esperada

Entradas: CLOCK_50, RESET_N, OPCODE[3:0], PRINT.

Saidas: LCD_DATA[7:0], LCD_EN, LCD_RS, LCD_RW, LCD_ON, BUSY, INIT_DONE.

## O que o testbench exige

- Clock de 50 MHz, periodo 20 ns
- Primeiro EN de inicializacao nunca antes de 50 ms apos soltar RESET_N
- Comandos 30, 30, 30, 38, 08, 01, 06, 0C, todos com RS=0 e separados por
  exatamente 10 ms, medidos nas bordas de descida de EN
- INIT_DONE so apos os oito bytes e nunca antes de 130 ms; permanece alto ate reset
- Cada PRINT aceito em idle: comando 80 com RS=0, seguido de exatamente 16 bytes
  com RS=1. Cadencia de 10 ms tambem na impressao, incluindo comando -> primeiro
  caractere. Testa todos os 16 opcodes, inclusive OR e os sete nomes vazios
- OPCODE capturado no aceite; alteracoes durante BUSY nao mudam a mensagem
- PRINT durante inicializacao e bordas extras durante BUSY ignorados, inclusive
  quando continuam altos depois do retorno a idle
- PRINT mantido alto nao repete; uma nova borda em idle permite nova impressao
- Reset durante a inicializacao e durante uma impressao, no meio de um pulso EN;
  ambas as situacoes reiniciam a sequencia completa e descartam a operacao anterior
- EN = 1 us exato, dados/RS/RW estaveis durante EN e por pelo menos 20 ns depois
  da descida. Pulso truncado deliberadamente pelo reset nao e contado como byte
- Sem EN em reset ou idle; reset limpa EN/INIT_DONE em ate um clock (checagem em
  21 ns); LCD_RW=0 e LCD_ON=1 fora do reset; nao tolera X nos sinais de controle; invariantes sao verificadas apos cada
  mudanca dos proprios sinais, com 1 ps para estabilizacao de deltas

O aceite precisa aparecer em BUSY em ate 20 us; a inicializacao tem timeout de
160 ms; cada impressao, 200 ms; watchdog global, 8 segundos simulados. Esses sao
limites de vivacidade do teste, nao parametros de aceleracao do circuito. A
simulacao usa tempos reais: ha aproximadamente 190 milhoes de ciclos no percurso
completo, dependendo da implementacao do aceite/termino. A primeira tentativa
levou cerca de 23 s reais para 50 ms simulados; a suite completa pode levar
aproximadamente meia hora neste executor com a biblioteca oficial.

Sucesso final esperado: 18 impressoes completas, duas inicializacoes completas,
alem das duas operacoes deliberadamente interrompidas por reset. Uma execucao
parcial isolada, compilacao isolada ou apenas validacao dos MIF nao equivale a
esse PASS. A entrega atual conclui a cobertura por dois segmentos, como descrito
acima, sem alegar o marcador terminal de uma execucao integral.

## Limites

O verificador e funcional e observa a interface exportada. Nao verifica pinagem
DE2-115, niveis eletricos, temporizacao pos-fit, metastabilidade, debounce de
botao, contraste/alimentacao do LCD, nem o mapa real da ISA. Nao substitui
compilacao/fitting do Quartus ou validacao fisica na placa.
