# Parte 3 — extração dos laudos

## Uso rápido

Na raiz do projeto, com as dependências de `requirements.txt` instaladas:

```bash
.venv/bin/python -m src.laudos.run_extraction
```

O modo padrão `rules` funciona **sem chave de API e sem internet**. Lê os arquivos TXT
em `Case_Bari/laudos_avaliacao/` sem alterá-los e grava `outputs/laudos_extraidos.json`,
`outputs/laudos_extraidos.csv` e `outputs/laudos_qualidade.md`. A tabela de qualidade
mostra, por documento, campos preenchidos, nulos e avisos. O CSV tem sempre as mesmas
colunas, inclusive `_evidencia` e `_confianca` de cada campo.

O modelo Pydantic declara todos os campos. Cada um tem `value`, `evidencia` literal
e `confianca` (alta, media ou baixa); campo ausente fica nulo. `onus` é o texto
encontrado e `tem_onus` é verdadeiro, falso ou nulo. Informação ausente sobre ônus
é nulo, jamais uma prova de inexistência. `responsavel_tecnico` é o nome;
`registro_profissional` guarda o número e conselho. Tipos de imóvel pertencem
a uma enumeração fechada. Áreas em hectares são convertidas explicitamente para
m² quando a unidade aparece no texto.

## API opcional

Copie `.env.example` para `.env` local e preencha `LAUDOS_API_URL` com URL HTTPS
de um endpoint compatível com chat completions e JSON Schema, `LAUDOS_MODEL` e
`LAUDOS_API_KEY`. O `.env` está ignorado pelo Git. Confirme custo, disponibilidade
e compatibilidade de saída estruturada com seu provedor antes da execução. Sem esses
valores, o modo LLM falha com mensagem clara e **não** faz chamadas externas.

```bash
.venv/bin/python -m src.laudos.run_extraction --mode llm --output-dir outputs/laudos_llm --attempts 3
```

Cada laudo é enviado entre delimitadores `<laudo>` e `</laudo>`, com mensagem de
sistema exigindo evidência literal, nulo para ausência e nulo com aviso para
contradições. Resposta inválida recebe feedback de validação e até o número de
tentativas informado. Se todas falharem, a linha aparece com `status=falha` e
valores nulos; a CLI retorna código de erro. Nenhuma chave é guardada nas saídas.
O terminal mostra cada documento e tentativa. Cada chamada tem limite de 30 segundos;
erros HTTP definitivos, como schema rejeitado (400), são exibidos e não repetidos.
O adaptador usa biblioteca padrão para HTTP; **não foi testado em um provedor real**
e pode exigir ajuste para o formato de resposta do serviço escolhido.

Se uma extração demorar ou terminar em timeout, execute
`.venv/bin/python tools/check_llm.py` para testar uma geração mínima sem schema.
O comando lê o mesmo `.env`, informa tempo e status, sem exibir a chave.

## Gabarito e métrica

`tests/gold/gold_laudos.csv` contém uma linha por arquivo e todas as colunas-alvo
**em branco**. Somente você deve preencher esse arquivo, conferindo cada laudo.
Uma célula vazia quer dizer **ainda não rotulada**. Para um valor realmente ausente,
escreva `NULL`. Use números canônicos com ponto decimal (área em m², valor em R$),
data `AAAA-MM-DD`, `true`/`false` para ônus e os valores fechados do tipo de imóvel.

```bash
.venv/bin/python -m src.laudos.evaluate
```

Antes do preenchimento, o relatório `outputs/avaliacao_laudos.md` informa que
nenhuma taxa está disponível. Após preencher, calcula acerto total, por campo e
por documento. Número exige igualdade exata; texto usa NFKC, caixa baixa e
espaços normalizados; data exige ISO; booleano é normalizado. O denominador é
o número de células rotuladas, nunca os espaços em branco. `NULL` esperado e
nulo retornado é acerto. `Null correto` usa como denominador todas as células
rotuladas como NULL; `alucinação` é o inverso: valor preenchido quando o
gabarito indica NULL. A matriz separa acerto de valor, null correto, omissão,
alucinação, valor errado e falha do documento. Uma falha do provedor **não conta
como null correto**, mesmo se o gabarito indicar ausência.

Para comparar os dois métodos, preserve saídas distintas:

```bash
.venv/bin/python -m src.laudos.run_extraction --mode rules --output-dir outputs/laudos_rules
.venv/bin/python -m src.laudos.run_extraction --mode llm --output-dir outputs/laudos_llm
.venv/bin/python -m src.laudos.evaluate --rules outputs/laudos_rules/laudos_extraidos.csv --llm outputs/laudos_llm/laudos_extraidos.csv
```

## Limitações e revisão

- O baseline usa regex deliberadamente conservadoras; pode deixar nulo um campo
  presente quando a redação varia. Endereço narrativo pode incluir contexto
  adicional, e “área útil” não é automaticamente equiparada a “privativa”.
- Idade aparente não define ano de construção; “ano de referência” não comprova
  ano de obra. Ausência de certidão não equivale a ausência de ônus.
- O laudo 17 declara dois números distintos de área total; esse campo fica nulo
  com ambos os valores em aviso. Outros desacordos novos dependem de revisão humana.
- A evidência literal, domínio dos valores, datas, matrícula, ano e coerência
  privativa/total são verificados após extração. Isso reduz respostas sem apoio,
  mas não comprova que toda interpretação do texto está correta.
- O mock prova retry e tratamento de falhas sem rede; não prova desempenho de LLM.
  A precisão só poderá ser afirmada após o preenchimento independente do gabarito.
