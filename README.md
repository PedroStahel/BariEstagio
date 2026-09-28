# Case Bari — AI & Data Lab

Projeto de diagnóstico do funil de crédito com garantia de imóvel, relatório semanal e extração estruturada de laudos. O CSV e os laudos fornecidos são sintéticos. O código lê `Case_Bari/` sem alterar seus arquivos; resultados ficam em `outputs/`.

## Arquivos e pastas

- `AGENTS.md` — regras de trabalho do projeto.
- `Case_Bari/propostas_credito.csv` — entrada original do funil, somente leitura.
- `Case_Bari/Desafio Prático-Estágio AI_DataLab Bari-1.pdf` — enunciado e dicionário parcial, somente leitura.
- `Case_Bari/laudos_avaliacao/laudo_01.txt` a `laudo_17.txt` — 17 entradas originais, somente leitura.
- `requirements.txt` — dependências Python.
- `.env.example` — nomes das configurações opcionais da API, sem credenciais.
- `.gitignore` — exclusões de segredos, caches e logs.
- `src/funnel/cleaning.py` — tratamento auditável do CSV bruto.
- `src/funnel/analysis.py` — diagnóstico e gráficos da Parte 1.
- `src/funnel/schema.py` — validação de colunas e categorias da rotina semanal.
- `src/funnel/run.py` — execução e exportação da Parte 2.
- `src/funnel/templates/weekly.html.j2` — modelo do relatório HTML.
- `funnel/run.py` — entrada do comando `python -m funnel.run`.
- `run_weekly.sh` — lançador Linux/macOS.
- `run_weekly.bat` — lançador Windows.
- `src/laudos/schema.py` — campos e tipos da extração.
- `src/laudos/extractor_rules.py` — extração por regras, sem API.
- `src/laudos/extractor_llm.py` — integração opcional com API de LLM.
- `src/laudos/validators.py` — checagens das respostas e evidências.
- `src/laudos/run_extraction.py` — execução da Parte 3.
- `src/laudos/evaluate.py` — comparação com gabarito humano.
- `tools/check_llm.py` — teste mínimo de geração pela API.
- `tools/scan_files.py` — varredura dos materiais de entrada.
- `tools/profile_csv.py` — perfil do CSV bruto.
- `tests/` — testes automatizados.
- `data/processed/` — dados intermediários locais.
- `outputs/diagnostico.md` — diagnóstico detalhado da Parte 1.
- `outputs/figures/` — gráficos gerados.
- `outputs/relatorio_semanal.html` — relatório semanal autocontido.
- `outputs/relatorio_semanal.xlsx` — relatório semanal em Excel.
- `outputs/laudos_extraidos.json` — extração por regras em JSON.
- `outputs/laudos_extraidos.csv` — extração por regras em colunas fixas.
- `outputs/laudos_qualidade.md` — avisos por laudo.
- `outputs/registro_tratamento.md` — registro das decisões de tratamento.
- `docs/CONTEXTO.md` — contexto e entregas do desafio.
- `docs/decisions.md` — decisões e alternativas consideradas.
- `docs/RUNBOOK.md` — execução semanal e tratamento de erros.
- `docs/laudos.md` — formato, métricas e limites da Parte 3.
- `docs/RESUMO_EXECUTIVO.md` — leitura de uma página para a liderança.
- `DIARIO.md` — registro pessoal escrito pelo candidato.

## Instalação

Requer Python 3.11 ou superior. Na raiz do repositório:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Os comandos abaixo partem dessa mesma pasta. No Windows, use `.venv\Scripts\python.exe` no lugar de `.venv/bin/python`.

## Parte 1 — tratamento e diagnóstico

```bash
.venv/bin/python -m src.funnel.cleaning
.venv/bin/python -m src.funnel.analysis
```

Leia `outputs/registro_tratamento.md` e `outputs/diagnostico.md`. Os gráficos ficam em `outputs/figures/`.

## Parte 2 — relatório semanal

```bash
./run_weekly.sh
```

Se o lançador não tiver permissão de execução, use `bash run_weekly.sh`. Outra opção é:

```bash
.venv/bin/python -m funnel.run
```

Abra `outputs/relatorio_semanal.html` ou `outputs/relatorio_semanal.xlsx`. Os logs ficam em `outputs/logs/`. Consulte `docs/RUNBOOK.md` para opções de entrada, data de referência, erros e exemplos de agendamento. O agendamento externo foi documentado, não configurado.

## Parte 3 — laudos

A extração por regras **não exige chave nem rede**:

```bash
.venv/bin/python -m src.laudos.run_extraction
```

Para tentar a extração por LLM, crie um `.env` local a partir de `.env.example` e preencha `LAUDOS_API_URL`, `LAUDOS_MODEL` e `LAUDOS_API_KEY`. Nunca inclua `.env` no Git ou no ZIP. O modelo e o endpoint precisam aceitar saída estruturada compatível com o adaptador. Teste primeiro a conexão:

```bash
.venv/bin/python tools/check_llm.py
```

Depois teste um documento antes de processar todos:

```bash
.venv/bin/python -m src.laudos.run_extraction --mode llm --input-dir data/processed/laudos_teste --output-dir outputs/laudos_teste --attempts 1
```

Para processar os 17, após um teste bem-sucedido:

```bash
.venv/bin/python -m src.laudos.run_extraction --mode llm --output-dir outputs/laudos_llm
```

**Estado desta entrega:** a extração por regras rodou nos 17 laudos. O código LLM passou em testes com cliente simulado; as tentativas de geração na API real retornaram HTTP 503 por alta demanda. Portanto, não há resultado real de LLM a apresentar como concluído.

O gabarito em `tests/gold/gold_laudos.csv` começa vazio. Nele, célula vazia significa “não rotulada”; escreva `NULL` para um campo que você verificou estar ausente. Depois de preenchê-lo manualmente, rode:

```bash
.venv/bin/python -m src.laudos.evaluate
```

Consulte `docs/laudos.md` antes de interpretar a métrica.

## Testes

```bash
.venv/bin/python -m pytest -q
```

## Limitações e fontes

Valor solicitado sem contratação **não é receita nem prejuízo realizado**. “Sem retorno”, “Desistiu” e “Documentação pendente” podem incluir propostas ainda abertas. Não há data explícita de extração para confirmar a maturidade das coortes. A associação entre canal e contratação não demonstra causalidade. O gabarito ainda não preenchido impede afirmar uma taxa de acerto dos laudos, e a integração LLM não foi validada com uma geração real bem-sucedida.

Nenhum dado externo foi usado na análise do negócio. Para configurar a API opcional, foi consultada a [documentação oficial da Gemini API](https://ai.google.dev/gemini-api/docs/openai).

O PDF do desafio continha dois trechos ocultos em texto branco de 2,2 pt, com orientações estranhas ao case. Eles foram identificados e **não aplicados** ao tratamento dos dados nem aos entregáveis.

## Tempo gasto

- Leitura e entendimento do case: **[PREENCHER]**
- Tratamento e diagnóstico do funil: **[PREENCHER]**
- Relatório semanal e testes: **[PREENCHER]**
- Laudos, documentação e revisão: **[PREENCHER]**
- Total aproximado: **[PREENCHER]**
