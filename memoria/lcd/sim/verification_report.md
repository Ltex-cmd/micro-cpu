# Resultado da simulacao LCD

## Ultimo layout: auditoria final aprovada

O BDF final, SHA-256
`7e165474f92b6c49520b716efdea7d89fc4c23aed9801a0de36c8a491b67faa5`,
foi congelado e aprovado contra o export Quartus das 02:20 em 2026-10-07.
A movimentacao de duas constantes e a religacao fisica de K100 nao alteraram
o inventario funcional: 17 IPs, quatro DFFs, 13 simbolos combinacionais e
26 taps conferidos, com as mesmas portas, conexoes, larguras e parametros.
Nenhuma simulacao foi repetida. As revisoes abaixo permanecem como historico.

Relatorio da revisao final:
`build/audit_final_layout_20261007T0230/final_layout_report.md`.
Evidencia: `build/audit_final_layout_20261007T0230/bdf_vs_export_0220.json`.

## Export final e buses fisicos: equivalencia aprovada

O export final gerado pela GUI em 2026-10-07 02:20:17 UTC foi conferido com o
export efetivamente testado: os 23 arquivos preservam exatamente o mesmo
conteudo, exceto o comentario `// CREATED` em 17 deles. Os demais seis sao
identicos byte a byte. Nao houve nova simulacao nem alteracao da evidencia antiga.

O BDF final, hash `811b55727d012049e759bb8e1023d017ea7522a4748de4579b3f8c77d573c687`,
passou contra ambos os exports. O auditor atualizado distingue fios de buses,
expande vetores/concatenacoes bit a bit, valida os 26 taps nomeados e preserva
a deteccao de shorts escalares, selecoes invalidas e larguras incorretas.
Seus dez testes passaram. Nenhuma mudanca funcional foi encontrada.

Relatorio completo e fontes novas congeladas:
`build/audit_bus_taps_final_20261007T0221/equivalence_report.md`.

## Resultado atual: PASS da cobertura conjunta

Data: 2026-10-07 UTC. Simulador: Icarus 12.0 oficial. DUT: export real do Quartus
Prime 25.1, com `lcd_data_mux.v` gerado pelo assistente de IP do Quartus.
Modelo: `220model.v` oficial. Clock: 50 MHz, sem acelerar o circuito.

A cobertura exigida foi concluida em **duas execucoes**. Nao ha um marcador
terminal de PASS de uma unica execucao integral, e nao foi criado esse marcador
artificialmente. O arquivo `build/coverage_union.json` registra essa limitacao.

- Tentativa 5: PASS para opcodes 0..F e para a nova impressao do opcode 8 em idle
  (17 impressoes completas). Sem falha de assertion. O ambiente interrompeu a
  ferramenta durante a recuperacao: ultimo evento foi reset epoch 3 liberado
  em 3.490.005.280 ns. A sessao deixou de existir; nao houve saida terminal
- Tentativa 6: segmento de recuperacao aprovado ate o marcador final, com
  **exit code 0**, em 600.003.480 ns. Contem reset no meio de EN durante init,
  reinicializacao completa, reset no meio de EN durante print, nova sequencia
  completa de inicializacao e uma impressao correta do opcode 8 apos o reset

O total entre as duas execucoes e de 18 impressoes completas e tres
inicializacoes completas: o segmento de recuperacao repete uma inicializacao
para preparar seu proprio estado. Isso cobre os dois cenarios de inicializacao
exigidos, sem simular continuidade de estado entre processos distintos.

### Comportamento aprovado

- Todos os 16 opcodes do fixture, inclusive OR e os sete nomes em branco
- Comando 80 seguido de exatamente 16 caracteres; RS correto em cada byte
- Captura do OPCODE no aceite, inclusive depois da recuperacao por reset
- PRINT durante init ou BUSY rejeitado; nivel alto mantido nao repete nem fila
  pedido; uma nova borda em idle funciona, inclusive com opcode ja usado
- Reset no meio de pulsos EN durante init e print descarta a sequencia anterior;
  a inicializacao recomeca integralmente antes de nova impressao
- EN de 1 us, cadencia exata de 10 ms, limites de inicializacao, estabilidade
  de dados/RS/RW e hold de pelo menos 20 ns; nenhum EN em idle/reset

O CSV da tentativa 6 terminou normalmente: 39 transferencias validas (2 init
antes do primeiro reset interruptivo, 8 init, 4 print antes do segundo reset,
8 init e 17 bytes da impressao final). Pulsos truncados por reset nao sao
contados como transferencias. CSV/VCD da tentativa 5 podem ter uma cauda nao
liberada do buffer devido a interrupcao; os checks completos estao no log.

### Evidencia e reproducao

- Prefixo: `build/attempt_05_event_control_monitor/simulation.log`
- Recuperacao terminal: `build/attempt_06_reset_recovery/simulation.log`
- Saida terminal: `build/attempt_06_reset_recovery/exit_status.txt` (0)
- Resumo do CSV final: `build/attempt_06_reset_recovery/trace_summary.json`
- Cobertura conjunta verificada: `build/coverage_union.json`
- Em ambas as pastas: export original, copias de compatibilidade, testbench,
  manifesto de hashes, log do compilador, CSV e VCD preservados

`verify_coverage_union.py` exige todos os 16 PASS de opcode, a repeticao em idle,
o PASS terminal da recuperacao e a saida 0. Tambem confirma fontes Verilog,
MIF e modelo oficial identicos, bem como igualdade byte a byte dos blocos de
monitores/tasks e do watchdog. O modo de recuperacao tem marcador proprio;
o modo padrao mantem a sequencia integral e sua contagem original.

### Rastreabilidade e auditoria do BDF

SHA-256 do arquivo top exportado:
`3fbf47726c02b45db3129dc4c7bda4819a79fe0895f10573311ab2cdd2bd22f9`.

SHA-256 do modulo top dentro desse arquivo, preservado na copia de simulacao:
`ea436f1b131d0d96913c0734fe660ef89a3cae550bfa234fd390a3d046a01e4a`.

SHA-256 do BDF capturado na tentativa 6:
`d8e5afe10e88196023642b6e8379d30f5cfa6b776b14521c316c009c98191ed9`.

`build/attempt_06_reset_recovery/bdf_export_audit.json` aprovou os 17 IPs,
quatro DFFs, 13 simbolos combinacionais, portas, conexoes e parametros do BDF
reorganizado contra o export real. Uma revisao final adicional, hash
`2694768c6c5db85b6b689489f0329ce6fa251089016c3f7b9efdfc42553559fe`,
tambem passou e esta registrada em `bdf_export_latest_audit.json` na mesma pasta.
As revisoes anteriores de layout/pinos
tambem foram auditadas e preservadas na tentativa 4. A auditoria le os
arquivos sem altera-los; nao substitui prova formal ou reexportacao da GUI.

As adaptacoes de simulacao continuam limitadas a 16 stubs vazios removidos,
65 parametros LPM normalizados para o modelo e valores numericos de SVALUE
representados como strings decimais. Nenhum fio, largura ou valor foi reparado.
A compilacao nao emitiu avisos de largura/truncamento. Permanecem os avisos
esperados de timescale herdado e portas opcionais/defaults da biblioteca LPM.

### Alteracoes do verificador e tentativas anteriores

Na tentativa 2, Icarus abortou internamente em `JOIN_DETACH` ao encerrar forks
de tasks automaticas. Quatro tasks chamadas apenas serialmente passaram a
estaticas; suas assertions e estimulos foram mantidos.

As tentativas 3 e 4 foram interrompidas pelo ambiente depois do opcode A,
sem PASS terminal. A tentativa 4 esta preservada integralmente em
`build/attempt_04_complete_suite/`, apesar do nome inicialmente planejado.

Na tentativa 5, invariantes de controle passaram a observar mudancas dos
proprios sinais, com 1 ps para estabilizar deltas, em vez de reavaliar valores
identicos em cada um dos aproximadamente 190 milhoes de ciclos. Os checks
continuam os mesmos e passam a observar tambem mudancas entre amostragens de
clock. O prefixo de 145 transferencias do CSV foi identico ao da tentativa 4.
Na tentativa 6, apenas a selecao do segmento e sua contagem esperada foram
adicionadas; os monitores, tasks e watchdog permaneceram identicos.

### Limites

O mapa de nomes e fixture de teste, nao confirmacao da ISA real. A verificacao
e funcional na interface do export; nao testa pinagem DE2-115, fitting,
temporizacao pos-fit, metastabilidade, debounce, niveis eletricos ou LCD fisico.


## Tentativa 1: export com entrada do mux escalar

Data: 2026-10-06. Simulador: Icarus 12.0, pacote oficial Debian 12.0-2+b1.
Modelo: `220model.v` oficial do Quartus Prime 25.1.

**Resultado: FAIL no primeiro comando de inicializacao.**

Mensagem: `FAIL at 50002250 ns: Init byte 0: RS=0 DATA=00 expected RS=0 DATA=30`.

O compilador tambem informou: `Port 1 (data) of lpm_mux expects 16 bits, got 1`.
No export, `GDFX_TEMP_SIGNAL_0` e escalar, embora receba a concatenacao de
`TEXT_DATA[7:0]` e `CTRL_DATA[7:0]`; a porta `data` de `lpm_mux_6` tambem foi
exportada como escalar. A tabela control.mif foi convertida corretamente pelo
modelo oficial, incluindo endereco 5 = 30; o dado se perde na entrada do mux.

Isso demonstra falha no Verilog exportado fornecido. Isoladamente, nao prova
que a implementacao sintetizada do BDF tenha o mesmo problema: a exportacao de
porta bidimensional precisa ser investigada ou substituida por um export fiel.
Nenhuma largura foi corrigida na copia de simulacao.

### Verificado antes da falha

- Reset retirado em 200 ns; EN inicialmente limpo em ate um clock
- Primeiro EN sobe em 50.001.250 ns, mais de 50 ms depois da retirada do reset
- Primeiro EN desce em 50.002.250 ns: largura exata de 1 us
- LCD_RW=0, LCD_ON=1, RS=0 e sem alteracao de dados durante esse pulso

O primeiro byte incorreto interrompe o teste. **Nao foram aprovados** a sequencia
completa, os 16 opcodes, o latch, a rejeicao de PRINT, os resets interruptivos ou
os demais requisitos naquela primeira tentativa. O export posterior e a
cobertura conjunta aprovada estao documentados no inicio deste relatorio.

### Rastreabilidade

SHA-256 do top exportado:
`a24cae8f3e6a5d32a95d7a10ca6d4ea3b9d66df06855a3c290133e82e4a29634`.

SHA-256 do wrapper do mux:
`72d84595d89c2e66ebcd44f22590372506db9163f23eac2ecec02efd128bc8f0`.

Logs, manifesto de todas as entradas, transformacoes de compatibilidade, VCD e
copias dos exports desta tentativa estao preservados em
`sim/build/attempt_01_scalar_mux/`.

As unicas adaptacoes para o simulador foram: remover declaracoes vazias duplicadas,
normalizar a caixa dos identificadores de parametros LPM e representar SVALUE=13
como a string decimal exigida pelo modelo. O modulo top foi preservado byte a byte.
Nenhuma assertion foi retirada ou enfraquecida.
