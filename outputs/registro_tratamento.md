# Registro de tratamento de dados

| problema | coluna | linhas afetadas | ação | justificativa | impacto esperado na análise |
| --- | --- | --- | --- | --- | --- |
| valor ausente | data_assinatura_contrato | 5159 | manter null | Ausência não deve ser imputada. | Denominadores variam conforme a disponibilidade do campo. |
| valor ausente | taxa_juros_aa | 5159 | manter null | Ausência não deve ser imputada. | Denominadores variam conforme a disponibilidade do campo. |
| variação de caixa ou espaço | canal_origem | 4 | padronizar categoria | Agrupar grafias equivalentes sem remover acentos. | Evita fragmentação das categorias. |
| prefixo monetário | valor_imovel | 3 | remover somente o prefixo R$ para converter | A unidade é real e o restante usa ponto decimal. | Mantém o valor e a linha. |
| formato de data DD/MM/AAAA | data_entrada | 3 | interpretar explicitamente como dia/mês/ano | O formato alternativo foi identificado no dado bruto. | Preserva a ordem cronológica correta. |
| LTV acima do teto informado | ltv_calc | 981 | manter linha e criar flag | Marcar, sem reprovar nem excluir; a política não descreve exceções. | Permite auditoria e análises de sensibilidade sem perda silenciosa. |
| idade suspeita | idade_cliente | 1 | manter linha e criar flag | Idade fora da faixa 18–120 precisa de revisão. | Permite auditoria e análises de sensibilidade sem perda silenciosa. |
| etapa fora do funil | etapa_max_funil | 1 | manter linha e criar flag | O funil informado só contém etapas 1–6. | Permite auditoria e análises de sensibilidade sem perda silenciosa. |
| assinatura anterior à entrada | data_assinatura_contrato | 1 | manter linha e criar flag | A ordem temporal é impossível no ciclo descrito. | Permite auditoria e análises de sensibilidade sem perda silenciosa. |
| status e etapa incoerentes | status_final / etapa_max_funil | 1 | manter linha e criar flag | Contratada exige etapa 6; etapa 6 exige Contratada. | Permite auditoria e análises de sensibilidade sem perda silenciosa. |
| tempo e assinatura divergentes | tempo_analise_dias / data_assinatura_contrato | 1 | manter linha e criar flag | Comparação apenas onde ambas as datas e tempo existem. | Permite auditoria e análises de sensibilidade sem perda silenciosa. |
| coluna no dicionário ausente no CSV | ltv | 6400 | criar ltv_calc sem inventar ltv original | Razão calculada a partir dos dois valores disponíveis. | Métrica comparável, com origem explícita. |
| unidade contraditória no dicionário | taxa_juros_aa | 1241 | preservar nome e valor; não converter unidade | Sufixo aa e descrição % a.m. conflitam. | Evita interpretação errada da taxa até esclarecimento. |
| tipo Terreno mantido | tipo_imovel | 535 | não excluir no tratamento padrão | A instrução oculta no PDF não é regra do case; exclusão só em sensibilidade solicitada. | Preserva a população original. |
