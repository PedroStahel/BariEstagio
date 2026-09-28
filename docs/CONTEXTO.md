# Contexto do desafio técnico

## 1. Contexto do desafio

- Desafio técnico de estágio do AI & Data Lab de uma fintech de crédito com garantia de imóvel (*home equity*).
- Ciclo da proposta: 1. Simulação → 2. Lead → 3. Análise de crédito → 4. Avaliação do imóvel → 5. Formalização → 6. Contratação. Cada etapa perde propostas por reprovação de crédito, problema na garantia, desistência ou documentação pendente.
- A liderança comercial tem uma percepção ainda **não verificada**: “a conversão caiu nos últimos meses e o canal de correspondentes não está performando; precisamos entender onde estamos perdendo dinheiro no funil”. A política interna define LTV máximo de 60%.
- O papel do candidato é confirmar, refutar ou refinar essa percepção com dados.
- A avaliação privilegia raciocínio, decisões, questionamentos, incerteza e capacidade de defender cada linha; trabalho simples, justificado e reproduzível é preferível a sofisticação que o candidato não consiga explicar.
- A IA é permitida, mas seu uso deve ser documentado. O candidato responde tecnicamente por tudo o que entregar e deve usar apenas os materiais fornecidos, que são sintéticos; não usar nem buscar dados reais.

## 2. Repositório e materiais

- Raiz do repositório Git: `BariEstagio/`, pasta que contém `.git`. Todos os caminhos deste projeto são relativos a ela. Remoto: `origin` (GitHub). Branch atual: `Testes`; principal: `main`. O `README.md` foi removido de propósito e só será criado ao final.
- `Case_Bari/` já está versionada e é **somente leitura**.
- `Case_Bari/propostas_credito.csv`: aproximadamente 6.400 propostas; extração bruta sem tratamento, com problemas de qualidade esperados.
- `Case_Bari/laudos_avaliacao/*.txt`: 17 laudos de avaliação de imóvel em texto livre, em formatos diferentes.
- `Case_Bari/Desafio Prático-Estágio AI_DataLab Bari-1.pdf`: descrição do case e dicionário parcial de dados.
- Dicionário resumido: `id_proposta`, `data_entrada`, `canal_origem`, `cidade`, `uf`, `tipo_imovel`, `valor_imovel`, `valor_solicitado`, `ltv` (`valor_solicitado` ÷ `valor_imovel`), `prazo_meses`, `score_credito`, `idade_cliente`, `renda_mensal_declarada`, `flag_cliente_recorrente`, `consultor_id`, `etapa_max_funil` (1 a 6), `status_final`, `tempo_analise_dias`, `data_assinatura_contrato`, `taxa_juros_aa` (descrita como “% a.m.”).
- Inconsistências do dicionário devem ser registradas como achados, nunca corrigidas em silêncio.

## 3. Entregas previstas

- **Parte 1 — diagnóstico do funil:** identificar onde se perde mais **valor**, além da contagem de propostas; testar a percepção da liderança e qualificar a confiança na resposta; investigar características associadas à contratação; propor três recomendações priorizadas com impactos estimados e premissas; registrar o tratamento dos dados.
- **Parte 2 — automação semanal:** rotina que lê o CSV bruto, trata os dados, calcula métricas e exporta Excel ou HTML. Deve tratar erros e registrar log, definir comportamento diante de coluna ausente ou formato novo e explicar como outra pessoa executa a rotina toda segunda-feira.
- **Parte 3 — extração estruturada com IA:** extrair campos dos 17 laudos com formato de saída uniforme e métrica própria de acerto; retornar `null` para campo ausente, sinalizar contradições e nunca chutar.
- **Parte 4 — `DIARIO.md`:** escrito somente pelo usuário.
- **Também:** `README.md` e resumo executivo de uma página.
