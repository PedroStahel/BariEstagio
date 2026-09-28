# Como gerar o relatório semanal

Este guia começa na pasta do projeto, onde ficam `Case_Bari/` e `run_weekly.sh`.
O arquivo bruto permanece intacto. Os resultados são gerados em `outputs/`.

## Preparar uma vez

Tenha Python 3.11 ou mais recente. No Linux/macOS, abra um terminal nesta pasta e rode:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

No Windows, abra o Prompt de Comando nesta pasta:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Toda segunda-feira

Substitua o CSV de entrada apenas quando houver uma nova extração autorizada; mantenha uma
cópia anterior fora da pasta do projeto se precisar comparar versões. Rode `./run_weekly.sh`
no Linux/macOS (se necessário, `bash run_weekly.sh`) ou dê duplo clique em
`run_weekly.bat` no Windows. Os lançadores encontram a pasta do projeto mesmo se forem
chamados de outro diretório. Também é possível executar diretamente:

```bash
.venv/bin/python -m funnel.run
```

Os arquivos principais são `outputs/relatorio_semanal.html` (abre no navegador, inclusive
sem internet) e `outputs/relatorio_semanal.xlsx` (abas Resumo, Funil, Por canal, Tendência
e Qualidade dos dados). O CSV tratado da rodada fica em `outputs/propostas_weekly_clean.csv`.
Consulte o log mais recente em `outputs/logs/`; cada execução tem um log próprio.
Os relatórios com o mesmo nome são substituídos quando a execução termina.

Para escolher outra origem, saída ou data de referência:

```bash
.venv/bin/python -m funnel.run --input Case_Bari/propostas_credito.csv --output-dir outputs/ --as-of 2026-02-04
```

`--as-of` é a data até a qual a coorte pode ter sido observada. Sem ela, a rotina estima
uma data com o maior `data_entrada + tempo_analise_dias`; essa estimativa é incerta.
`--exclude-types` é uma lista opcional separada por vírgulas, vazia por padrão. Use
apenas em uma análise de sensibilidade solicitada e registre a exclusão. O limiar
`--max-parse-failure-rate` usa fração entre 0 e 1, padrão 0,02: conta falhas de
conversão divididas por células não vazias das colunas de data e número.

## Se aparecer um erro

| Mensagem | Ação |
| --- | --- |
| Arquivo de entrada inexistente | Confira o nome e a pasta no `--input`. |
| CSV vazio / cabeçalhos duplicados | Solicite nova extração; não use relatório antigo como se fosse atual. |
| Coluna obrigatória ausente | Solicite correção da extração ou avalie o mapeamento de schema antes de continuar. A rotina aborta. |
| Coluna opcional ausente | O relatório prossegue; confira o aviso e as métricas indisponíveis. |
| Categoria nova / coluna extra | A rotina continua, mostra “Não mapeado” nos agrupamentos e preserva o rótulo no CSV tratado; revise se há um novo significado de negócio. |
| Formato não reconhecido | Veja a contagem no log e no relatório. Corrija a origem; acima do limiar a rotina aborta. Não aumente o limiar sem avaliar o impacto. |
| Falha inesperada | Veja a última mensagem em `outputs/logs/`, confira espaço em disco e dependências, e peça apoio técnico. |

Uma execução malsucedida não gera um novo relatório após falha de schema ou de conversão.
Se já existia relatório de uma execução anterior, confira o horário indicado no topo e não
o distribua como se fosse o arquivo novo.

## Agendar, se desejado

No cron do Linux, use caminhos absolutos na configuração do agendador para encontrar o
lançador (os caminhos internos do projeto permanecem relativos). Exemplo para 08:00
de segunda-feira, substituindo `/caminho/para/BariEstagio` pelo seu caminho:

```cron
0 8 * * 1 /bin/bash /caminho/para/BariEstagio/run_weekly.sh
```

No Agendador de Tarefas do Windows, crie uma tarefa semanal para segunda-feira:
**Programa/script** `C:\caminho\para\BariEstagio\run_weekly.bat`, **Iniciar em**
`C:\caminho\para\BariEstagio`. Verifique o histórico da tarefa e o novo log.

Exemplo de arquivo de GitHub Actions, **somente documentação; não está configurado**:

```yaml
name: Relatorio semanal
on:
  schedule:
    - cron: '0 11 * * 1' # 08:00 em Brasília se UTC-3; horário de verão pode alterar
  workflow_dispatch:
jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: python -m pip install -r requirements.txt
      - run: python -m funnel.run
      - uses: actions/upload-artifact@v4
        with:
          name: relatorio-semanal
          path: |
            outputs/relatorio_semanal.html
            outputs/relatorio_semanal.xlsx
            outputs/logs/
```

O exemplo pressupõe que o repositório privado tenha o CSV versionado e que a política
interna permita executar o fluxo na plataforma. O agendamento não substitui a chegada
de uma extração nova; confira o hash e a data do arquivo em cada semana.

## Limites de interpretação

Não há data de extração nem data de encerramento para propostas abertas. A maturidade
é aproximada a partir do tempo de análise observado e pode subestimar censura.
O crédito solicitado sem contratação é valor potencial, não perda de receita.
“Sem retorno”, “Desistiu” e “Documentação pendente” podem precisar de definição operacional.
Campos com conversão inválida continuam no CSV tratado como nulos e ficam fora apenas
dos cálculos que exigem o campo. Propostas com categoria nova são mantidas, mas a
contratação depende do status conhecido “Contratada”; um status novo exige revisão humana.
