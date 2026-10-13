# Equivalencia do BDF final e do novo export Quartus

Resultado: **PASS**, em 2026-10-07. Nenhuma mudanca funcional encontrada.
A simulacao concluida anteriormente foi preservada e nao foi repetida.

## Export final comparado com o export testado

Os 23 arquivos Verilog preservados foram comparados em ordem de tokens,
retendo integralmente strings e valores de parametros. Todos sao iguais.
Seis arquivos sao identicos byte a byte; nos outros 17, a unica diferenca
esta no comentario `// CREATED` inserido pelo Quartus.

- BDF final SHA-256: `811b55727d012049e759bb8e1023d017ea7522a4748de4579b3f8c77d573c687`
- Top testado SHA-256: `3fbf47726c02b45db3129dc4c7bda4819a79fe0895f10573311ab2cdd2bd22f9`
- Top novo SHA-256: `0c99fcddd450443dfc6aec04061d3726da48bfe699a565c08dfd202b3d253cbc`
- Comparacao: `export_equivalence_verified.json`
- Fontes novas congeladas: `fresh_exports/`

O mesmo BDF final passou contra o export testado e contra o novo: 17 IPs,
quatro DFFs e 13 simbolos combinacionais, com interface, conexoes, larguras e
parametros correspondentes. Relatorios: `bdf_vs_tested_export.json` e
`bdf_vs_fresh_export.json`.

## Auditoria dos taps

O auditor anterior tratava fios e buses como uma unica rede geometrica.
Esse modelo fundia todos os membros de um bus quando encontrava um tap e
produzia um falso conflito entre SLOT_Q[4..0] e suas selecoes individuais.

O auditor atualizado separa componentes de fio e bus, expande vetores e
concatenacoes na ordem declarada e associa cada tap somente ao bit nomeado.
Verifica tambem a largura da porta do simbolo. O BDF final possui 26 pontos
de tap validados, envolvendo SLOT_Q[4..0] e OPCODE_Q[3..0], sem bus ambiguo.
Dois rotulos escalares diferentes no mesmo fio continuam sendo erro.

Dez testes passaram: selecao de bit, concatenacao, ligacao entre buses de
larguras diferentes, short entre bits, bit fora do bus, ordem invertida,
cruzamento com/sem juncao, tap sem nome e largura de porta incorreta.
O log esta em `auditor_tests.log`. BDFs anteriores, inclusive o que usava
um unico pino de saida agregado, tambem passaram como regressao.

## Reproducao

A partir de `lcd/sim/`:

```sh
python3 -m unittest -v test_audit_bdf_export.py
python3 compare_quartus_exports.py \
  build/attempt_06_reset_recovery/original_exports \
  build/audit_bus_taps_final_20261007T0221/fresh_exports \
  --output /tmp/lcd_export_equivalence.json
python3 audit_bdf_export.py \
  build/audit_bus_taps_final_20261007T0221/lcd_operation_display.bdf \
  build/audit_bus_taps_final_20261007T0221/fresh_exports \
  --output /tmp/lcd_final_bdf_audit.json
```

Essa verificacao estrutural cobre os recursos usados por este BDF. Nao e um
parser geral do Quartus, prova formal, nova simulacao ou verificacao fisica.
Todos os arquivos anteriores de evidencia permaneceram intactos.
