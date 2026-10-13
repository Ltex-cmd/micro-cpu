# Auditoria do ultimo layout do BDF

Resultado: **PASS**, em 2026-10-07 02:30 UTC.

BDF final SHA-256:
`7e165474f92b6c49520b716efdea7d89fc4c23aed9801a0de36c8a491b67faa5`.

A ultima reorganizacao visual, incluindo a movimentacao de duas constantes e
a religacao fisica do barramento K100, permanece estruturalmente equivalente
ao export Quartus das 02:20. Nenhuma mudanca funcional foi encontrada.

- 17 IPs, quatro DFFs e 13 simbolos combinacionais correspondentes
- Portas, larguras, conexoes e parametros conferidos contra o export
- 26 taps validos; nenhum bus com membros ambiguos
- Inventario funcional identico ao da auditoria anterior do BDF 811b5572...

O export das 02:20 ja foi comparado com o export simulado: todos os 23 arquivos
sao identicos fora dos comentarios CREATED. A cobertura funcional anterior
permanece preservada. Nenhuma simulacao foi repetida nesta etapa.

Evidencia: `bdf_vs_export_0220.json`; BDF congelado:
`lcd_operation_display.bdf`. As fontes usadas estao em
`../audit_bus_taps_final_20261007T0221/fresh_exports/`.

A partir de `lcd/sim/`, reproduzir sem sobrescrever a evidencia:

```sh
python3 audit_bdf_export.py \
  build/audit_final_layout_20261007T0230/lcd_operation_display.bdf \
  build/audit_bus_taps_final_20261007T0221/fresh_exports \
  --output /tmp/lcd_final_layout_audit.json
```

Este resultado e da auditoria estrutural. A compilacao final na GUI e uma
verificacao separada, nao executada nem afirmada por este relatorio.
