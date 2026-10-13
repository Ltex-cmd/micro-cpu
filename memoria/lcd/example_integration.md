# Exemplo de integração síncrona

`lcd_example_top.qpf` abre um projeto separado para instanciar o símbolo
`lcd_operation_display.bsf` em `lcd_example_top.bdf`. O top BDF foi montado
no Block Editor; os arquivos QPF/QSF/SDC configuram seu projeto e temporização.

**Este exemplo mostra como integrar o core a outro circuito síncrono.**
Seu QSF não contém nenhuma localização de pino ou atribuição de IO_STANDARD.
O Fitter pode escolher pinos automaticamente; isso não constitui uma
pinagem aprovada e o SOF deste exemplo não deve ser gravado na placa.

O projeto `lcd_de2_115_top` é o único wrapper desta entrega destinado à
DE2-115: reúne o condicionamento de KEY/SW e os metadados de pinagem.
Suas verificações e limitações estão em [de2_115_board_top.md](de2_115_board_top.md).

## Conexões do top

No BDF de exemplo, encaminhar diretamente as quatro entradas ao core:

- CLOCK_50
- RESET_N
- OPCODE[3..0]
- PRINT

Encaminhar do core às sete saídas do top:

- LCD_DATA[7..0]
- LCD_EN
- LCD_RS
- LCD_RW
- LCD_ON
- BUSY
- INIT_DONE

PRINT e OPCODE representam uma interface fornecida por lógica síncrona a
CLOCK_50. O exemplo não transforma botões em pedidos, não sincroniza
OPCODE vindo de switches e não adiciona uma CPU. Para uma integração real,
conectar essas entradas ao produtor que respeita o contrato abaixo.

O BSF é uma interface gráfica: a implementação hierárquica vem do core BDF,
incluído explicitamente no QSF. O QIP `lcd_data_mux.qip` inclui o mux gerado
pelo IP Catalog, com entradas de 8 bits separadas. Não adicionar os exports
de simulação do core como fontes sintetizáveis concorrentes ao BDF.

## Contrato com o produtor

1. Usar um único CLOCK_50 de 50 MHz, período 20 ns, no produtor e no core
2. Manter RESET_N em zero para reset; o core faz a liberação interna sincronizada
3. Esperar INIT_DONE=1 e BUSY=0
4. Apresentar OPCODE estável na borda de subida de CLOCK_50 que aceita PRINT
5. Gerar uma borda de subida de PRINT; um pulso síncrono de um ciclo é suficiente
6. Voltar PRINT a zero antes do próximo pedido e respeitar BUSY

O core captura o opcode somente na aceitação. Pedidos durante BUSY são
descartados, inclusive se PRINT continuar alto quando BUSY cair. Não há fila
nem protocolo de repetição automática. Um pedido que chega na mesma borda
em que a operação anterior termina ainda vê o estado anterior ocupado e é
descartado; o produtor deve observar idle antes de emitir a nova borda.

O conteúdo `operations.mif` continua sendo o fixture explícito de teste;
não presumir que os valores de opcode representam a ISA real da micro-CPU.

## Metadados incluídos

- Dispositivo: EP4CE115F29C7, família Cyclone IV E
- Top: lcd_example_top
- Fontes: top BDF, core BDF e QIP do mux
- Dados de ROM: control.mif e operations.mif
- SDC: apenas lcd_example_top.sdc, evitando duplicar o clock do SDC standalone
- Relatórios/saídas: example_output_files, separados do projeto standalone
- Pinagem e padrões de I/O: ausentes; definidos apenas no wrapper de placa

O SDC declara CLOCK_50 com 20 ns e `derive_clock_uncertainty`. Não inventa
atrasos de entrada/saída e não declara LCD_EN como clock. Esse arquivo não
completa a análise temporal da interface externa. Em uma futura integração
com a CPU, revisar o SDC do top completo e evitar clocks duplicados.

Em 7 de outubro de 2026, as antigas atribuições parciais de placa foram
removidas do QSF deste exemplo. Os relatórios anteriores em
`example_output_files/` foram atualizados pela compilação completa de
2026-10-07 às 03:00:18 UTC: Successful, 65 LE, 32 registradores e 2176 bits
de ROM. O QSF atual permanece sem pinagem de placa. O TimeQuest registra
slacks positivos nos caminhos analisados, com seis entradas e 12 saídas
ainda sem restrições externas; isso não constitui fechamento de timing da placa.

## Auditoria do debouncer existente

Fonte lida: [../teste/debouncer.v](../teste/debouncer.v), especialmente linhas
28-73. O símbolo [../teste/debouncer.bsf](../teste/debouncer.bsf) concorda com
as portas e o parâmetro abaixo. Nenhum dos dois foi modificado, e o debouncer
não é instanciado no exemplo síncrono.

| Item | Comportamento observado no código |
|---|---|
| clk | Borda de subida |
| rst_n | Reset assíncrono ativo baixo |
| inb | Entrada cujo nível é filtrado |
| outb | Nível filtrado, preservando polaridade; não é pulso |
| DELAY_BITS | Largura do contador, padrão 16 |

Uma mudança amostrada em inb atualiza intermediate e zera o contador. Se a
entrada permanecer nesse nível, o contador sobe até todos os bits estarem
em um. Na borda estável seguinte, outb recebe intermediate. Qualquer nova
mudança reinicia a espera. O contador satura; não fica transbordando após
aceitar um nível estável.

O atraso desde a borda de clock que detecta a mudança até a atualização é
2^DELAY_BITS ciclos. Para CLOCK_50=50 MHz:

| DELAY_BITS | Ciclos | Intervalo |
|---|---:|---:|
| 16, padrão atual | 65536 | 1,31072 ms |
| 19, alternativa a avaliar | 524288 | 10,48576 ms |
| 20, alternativa a avaliar | 1048576 | 20,97152 ms |

Esses números descrevem o código e não garantem que um botão específico
fique livre de bouncing. A escolha depende do sinal e da placa usados.

Limites importantes:

- Não há sincronizador de dois flip-flops na entrada. intermediate sozinho
  não constitui uma cadeia de sincronização: a comparação também lê inb
- O reset copia inb diretamente para intermediate e outb, sem filtragem e
  sem impor um valor de repouso conhecido. Testar botão pressionado durante
  reset e na liberação antes de adotar esse bloco em um top de placa
- O debounce não resolve a coerência de um opcode de vários bits
- Para um botão ativo em zero, seu nível filtrado deve ser invertido para
  que o pressionamento gere a borda positiva esperada por PRINT. O próprio
  core já detecta essa borda; manter o botão pressionado não deve repetir
- Em um top de placa posterior, tratar CDC antes do filtro, revisar a
  liberação do reset e aplicar debounce apenas onde necessário. Não usar
  o botão ou outb como clock do core

A auditoria foi feita por leitura do código e cálculo de ciclos. Não equivale
a uma nova simulação do debouncer, análise de metastabilidade ou teste físico.

## Antes de usar o exemplo

1. Abrir o top BDF existente pela GUI e conferir a correspondência de todas as portas
2. Compilar esse projeto separado e verificar seu próprio relatório; o resultado
   de compilação do core standalone não valida automaticamente este top
3. Simular a hierarquia real do exemplo ou testar suas conexões com o core já
   verificado, sem reutilizar um export desatualizado
4. Para uma placa, escolher a origem física ou lógica de RESET_N/PRINT/OPCODE e
   o destino de BUSY/INIT_DONE; conferir pinos, tensões e restrições externas
5. Somente após essas etapas e a revisão de timing considerar uma programação
   da placa. Nenhum SOF board-ready é declarado por estes metadados
