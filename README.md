# Micro-CPU

Projeto de uma micro-CPU com blocos de 4 bits, desenvolvido com esquemas
gráficos no Quartus Prime Lite 24.1. O projeto está configurado para o FPGA
Cyclone V `5CEBA4F23C7`, com `Micro_CPU` como entidade principal.

## Organização

```text
micro-cpu/
├── Micro_CPU.qpf          # Projeto: abra este arquivo no Quartus
├── Micro_CPU.qsf          # FPGA, entidade principal, fontes e bibliotecas
├── src/
│   ├── top/              # Micro_CPU.bdf: integração dos blocos
│   ├── ula/              # Somadores, comparador, multiplicador e divisor
│   ├── contadores/       # Contadores e TFF_Jump
│   ├── registradores/    # Registrador PIPO
│   ├── display/          # Decodificador hexadecimal
│   └── logica/           # Multiplexadores e demultiplexadores
├── memoria/
│   └── INSTRUCAO.mif     # Conteúdo de inicialização da memória
├── README.md
└── .gitignore
```

Cada `.bdf` contém o circuito de um bloco. Seu `.bsf`, quando existente,
fica na mesma pasta e representa o símbolo usado para inserir esse bloco
em outros esquemas. Os nomes dos blocos foram preservados para manter as
referências entre eles.

As pastas `db/`, `incremental_db/`, `output_files/` e `simulation/` contêm
resultados gerados pelas ferramentas e ficam fora do Git. Os resultados
locais anteriores foram preservados; recompile para atualizá-los depois
da reorganização. O arquivo gerado `c5_pin_model_dump.txt` foi movido para
`output_files/`.

## Abrir e compilar

1. Abra `Micro_CPU.qpf` na raiz do repositório.
2. Abra `src/top/Micro_CPU.bdf` para editar o circuito principal.
3. Execute **Processing → Start Compilation**. Os resultados ficam em
   `output_files/`.

Também é possível compilar pelo terminal, a partir da raiz do repositório,
quando o executável do Quartus estiver no `PATH`:

```sh
quartus_sh --flow compile Micro_CPU
```

O `.qsf` lista explicitamente os esquemas e o arquivo de memória. As pastas
dos blocos estão configuradas como bibliotecas locais com `SEARCH_PATH`.
Os caminhos são relativos à raiz do projeto, seguindo a
[orientação de portabilidade do Quartus](https://docs.altera.com/r/docs/683475/19.4/intel-quartus-prime-standard-edition-user-guide-getting-started/migrating-design-files-and-libraries).

## Adicionar ou alterar blocos

1. Salve o novo `.bdf` na pasta correspondente à sua função em `src/`.
2. Adicione-o ao projeto em **Project → Add/Remove Files in Project**.
3. Para usar o bloco em outro esquema, gere seu símbolo em
   **File → Create/Update → Create Symbol Files for Current File** e
   mantenha o `.bsf` junto do `.bdf`.
4. Se criar uma nova pasta, adicione-a às bibliotecas do projeto em
   **Assignments → Settings → Libraries**. Use um caminho relativo,
   por exemplo `src/controle`.
5. Versione o circuito, o símbolo e as alterações no `.qsf`.

Arquivos de memória ficam em `memoria/`. Ao configurar uma ROM, indique o
arquivo no parâmetro `LPM_FILE`, por exemplo `memoria/INSTRUCAO.mif`.
Adicionar um `.mif` ao projeto não o associa automaticamente a uma ROM.
No esquema atual, `LPM_FILE` está vazio; essa configuração preexistente
foi preservada nesta reorganização.

Quando forem necessários, crie `constraints/` para restrições de tempo
(`.sdc`), `sim/` para testbenches e scripts de simulação escritos manualmente,
e `docs/` para documentação. Esses arquivos devem entrar no Git; a pasta
`simulation/` fica reservada às saídas geradas pelo Quartus.

## Verificação da reorganização

Os caminhos do `.qsf` e a preservação dos arquivos de circuitos, símbolos e
memória foram verificados. A compilação precisa ser executada em um ambiente
com Quartus instalado; o executável `quartus_sh` não estava disponível no
ambiente utilizado para organizar o projeto.
