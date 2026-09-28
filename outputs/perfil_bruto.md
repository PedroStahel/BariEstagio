# Perfil do CSV bruto (antes do tratamento)

Fonte: `Case_Bari/propostas_credito.csv`. O arquivo foi lido, não alterado.

Linhas: 6400; colunas: 19; tipos lidos: texto para preservar os formatos originais.
BOM UTF-8: True; campos entre aspas em todas as linhas: True; CRLF: 6401; LF isolado: 0.
Linhas totalmente duplicadas: 0; IDs duplicados: 0.

## Colunas e ausências

| coluna | tipo bruto | nulos/vazios |
| --- | --- | ---: |
| id_proposta | texto | 0 |
| data_entrada | texto | 0 |
| canal_origem | texto | 0 |
| cidade | texto | 0 |
| uf | texto | 0 |
| tipo_imovel | texto | 0 |
| valor_imovel | texto | 0 |
| valor_solicitado | texto | 0 |
| prazo_meses | texto | 0 |
| score_credito | texto | 0 |
| idade_cliente | texto | 0 |
| renda_mensal_declarada | texto | 0 |
| flag_cliente_recorrente | texto | 0 |
| consultor_id | texto | 0 |
| etapa_max_funil | texto | 0 |
| status_final | texto | 0 |
| tempo_analise_dias | texto | 0 |
| data_assinatura_contrato | texto | 5159 |
| taxa_juros_aa | texto | 5159 |

## Categóricas (valores originais, inclusive espaços)

### `canal_origem` — 8 valores

| valor | N |
| --- | ---: |
| `Correspondente` | 1772 |
| `Organico` | 1410 |
| `Mídia paga` | 1270 |
| `Indicação` | 979 |
| `Parceria` | 965 |
| `mídia paga ` | 2 |
| `indicação ` | 1 |
| `organico ` | 1 |

### `cidade` — 12 valores

| valor | N |
| --- | ---: |
| `Campinas` | 566 |
| `Recife` | 564 |
| `Rio de Janeiro` | 558 |
| `Santos` | 541 |
| `São Paulo` | 541 |
| `Porto Alegre` | 540 |
| `Goiânia` | 522 |
| `Brasília` | 521 |
| `Salvador` | 521 |
| `Curitiba` | 516 |
| `Florianópolis` | 507 |
| `Belo Horizonte` | 503 |

### `uf` — 10 valores

| valor | N |
| --- | ---: |
| `SP` | 1648 |
| `PE` | 564 |
| `RJ` | 558 |
| `RS` | 540 |
| `GO` | 522 |
| `DF` | 521 |
| `BA` | 521 |
| `PR` | 516 |
| `SC` | 507 |
| `MG` | 503 |

### `tipo_imovel` — 5 valores

| valor | N |
| --- | ---: |
| `Apartamento` | 2745 |
| `Casa` | 2077 |
| `Sala comercial` | 795 |
| `Terreno` | 535 |
| `Imóvel rural` | 248 |

### `flag_cliente_recorrente` — 2 valores

| valor | N |
| --- | ---: |
| `0` | 5174 |
| `1` | 1226 |

### `consultor_id` — 30 valores

| valor | N |
| --- | ---: |
| `CONS-022` | 246 |
| `CONS-003` | 246 |
| `CONS-016` | 244 |
| `CONS-002` | 236 |
| `CONS-029` | 233 |
| `CONS-024` | 228 |
| `CONS-014` | 226 |
| `CONS-011` | 221 |
| `CONS-028` | 221 |
| `CONS-027` | 220 |
| `CONS-012` | 218 |
| `CONS-015` | 214 |
| `CONS-023` | 212 |
| `CONS-019` | 210 |
| `CONS-007` | 209 |
| `CONS-006` | 208 |
| `CONS-004` | 208 |
| `CONS-013` | 207 |
| `CONS-009` | 206 |
| `CONS-030` | 205 |
| `CONS-001` | 205 |
| `CONS-026` | 204 |
| `CONS-017` | 204 |
| `CONS-005` | 203 |
| `CONS-021` | 202 |
| `CONS-018` | 201 |
| `CONS-008` | 196 |
| `CONS-025` | 195 |
| `CONS-020` | 190 |
| `CONS-010` | 182 |

### `etapa_max_funil` — 7 valores

| valor | N |
| --- | ---: |
| `3` | 1799 |
| `4` | 1267 |
| `6` | 1240 |
| `2` | 984 |
| `5` | 836 |
| `1` | 273 |
| `7` | 1 |

### `status_final` — 6 valores

| valor | N |
| --- | ---: |
| `Sem retorno` | 1639 |
| `Desistiu` | 1492 |
| `Contratada` | 1241 |
| `Reprovada crédito` | 920 |
| `Problema garantia` | 668 |
| `Documentação pendente` | 440 |

## Numéricas (interpretação provisória somente para perfil)

| coluna | presentes | mínimo | máximo | prefixo R$ | falhas após retirar prefixo |
| --- | ---: | ---: | ---: | ---: | ---: |
| valor_imovel | 6400 | 119954.21 | 3741992.93 | 3 | 0 |
| valor_solicitado | 6400 | 45707.69 | 2280018.3 | 0 | 0 |
| prazo_meses | 6400 | 60 | 240 | 0 | 0 |
| score_credito | 6400 | 360 | 990 | 0 | 0 |
| idade_cliente | 6400 | 14 | 76 | 0 | 0 |
| renda_mensal_declarada | 6400 | 1800.0 | 35231.29 | 0 | 0 |
| tempo_analise_dias | 6400 | 2 | 78 | 0 | 0 |
| taxa_juros_aa | 1241 | 0.94 | 1.73 | 0 | 0 |

## Datas (formatos brutos)

| coluna | ISO AAAA-MM-DD | BR DD/MM/AAAA | outros não vazios | datas impossíveis nos formatos reconhecidos |
| --- | ---: | ---: | ---: | ---: |
| data_entrada | 6397 | 3 | 0 | 0 |
| data_assinatura_contrato | 1241 | 0 | 0 | 0 |

Faixa de `data_entrada` válida: 2024-01-11 00:00:00 a 2025-12-29 00:00:00.
Faixa de `data_assinatura_contrato` válida: 2024-02-04 00:00:00 a 2026-02-04 00:00:00.

## Coerência e outros achados

| verificação | linhas |
| --- | ---: |
| `ltv` no cabeçalho | 0 |
| LTV calculável | 6400 |
| LTV calculado mínimo | 0.2299999882482816 |
| LTV calculado máximo | 0.7900000081946045 |
| LTV calculado > 0,60 | 981 |
| `tipo_imovel` Terreno | 535 |
| idade < 18 | 1 |
| etapa fora de 1–6 | 1 |
| Contratada fora da etapa 6 | 1 |
| Não contratada na etapa 6 | 0 |
| Contratada sem assinatura | 0 |
| Não contratada com assinatura | 0 |
| Contratada sem taxa | 0 |
| Não contratada com taxa | 0 |
| Assinatura anterior à entrada | 1 |
| Prazo declarado diferente do intervalo até assinatura | 1 |
| Canal com espaço exterior | 4 |

A descrição de `taxa_juros_aa` em `% a.m.` conflita com o sufixo `aa`; o perfil não infere nem converte a unidade.

### `status_final` × `etapa_max_funil`

| status | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Contratada | 0 | 0 | 0 | 0 | 0 | 1240 | 1 |
| Desistiu | 136 | 346 | 614 | 0 | 396 | 0 | 0 |
| Documentação pendente | 0 | 0 | 0 | 0 | 440 | 0 | 0 |
| Problema garantia | 0 | 0 | 0 | 668 | 0 | 0 | 0 |
| Reprovada crédito | 0 | 312 | 608 | 0 | 0 | 0 | 0 |
| Sem retorno | 137 | 326 | 577 | 599 | 0 | 0 | 0 |
