# Editar os nomes mostrados no LCD

Edite [operations.txt](operations.txt). Use um código hexadecimal de `0` a `F`,
um espaço e o nome com até 16 caracteres ASCII, sem acentos. Exemplo:

```text
9 LOAD
A STORE
F HALT
```

Esses nomes são exemplos. Escolha os códigos que a CPU realmente produz.
Os nove nomes atuais estão mantidos; para acrescentar nomes, preencha os sete
slots livres de `9` a `F`.
Código sem nome, ou ausente do arquivo, mostra 16 espaços. Códigos repetidos
são rejeitados; nomes curtos recebem espaços à direita. Comentários começam
com `#` em uma linha própria. Deve existir pelo menos um nome.

A interface continua com quatro bits: cabem 16 códigos. Adicionar um nome
muda o texto exibido pelo LCD; não implementa a instrução na CPU. Mais de
16 códigos exige uma alteração de interface e circuito, ainda não feita.

## Gerar e aplicar

Requisitos: Python 3 e compilador C (`cc`, GCC ou Clang). Na raiz do repositório:

```sh
python3 lcd/generate_operations.py --check
python3 lcd/generate_operations.py
```

O segundo comando gera `lcd/operations.mif` usando o C original
`teste/txt_to_mif.c`, sem alterá-lo. O helper traduz os códigos hex para quatro
bits binários e confere os 256 bytes antes de substituir o MIF. Uma falha de
validação ou compilação mantém o arquivo anterior. Para testar uma cópia:

```sh
python3 lcd/generate_operations.py --output /tmp/operations_preview.mif
```

1. Salve o mapa e gere o MIF
2. Abra o projeto que você usa no Quartus e execute uma compilação completa
3. No projeto da placa incluído, `lcd/lcd_de2_115_top.qpf`, o novo arquivo fica
   em `lcd/board_output_files/lcd_de2_115_top.sof`
4. No Programmer, selecione o SOF recém-gerado e programe a FPGA; depois reinicie
   o controlador e solicite a impressão

Editar o TXT ou o MIF não altera um SOF já existente nem a FPGA já programada.
O Assembler gera o SOF ao final da compilação completa, conforme a
[documentação oficial](https://www.intel.com/content/www/us/en/docs/programmable/813773/24-2/generating-programming-files-using-the.html).
Se o LCD estiver integrado em outro top, compile e use o SOF desse projeto.

## Fixture de teste

[operations_fixture.txt](operations_fixture.txt) continua sendo o mapa fixo
usado pela simulação já concluída. Ele não é a ISA confirmada e não é atualizado
pelo gerador. O checker atual espera esse fixture: depois de personalizar os
nomes, não trate sua rejeição ao novo mapa como falha do hardware.
`sim/regenerate_fixture.sh` restaura o mapa de teste em `operations.mif`, portanto
só execute esse comando quando quiser voltar ao fixture.
