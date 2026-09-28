# Diário de bordo — Case Bari

## Como usei IA

Usei o Claude para entender o case, examinar os materiais e organizar os prompts que depois passei ao Codex. Também pedi ajuda para revisar a ortografia deste diário e convertê-lo de PDF para Markdown. O Codex construiu o código por etapas, a partir desses prompts.

Não quero passar a impressão de que programei tudo sozinho. Ainda tenho limitações técnicas, então procurei acompanhar cada etapa, rodar os comandos no meu computador e perguntar o motivo das decisões que não entendia. Fiz isso porque precisarei explicar o que estou entregando, inclusive onde o trabalho pode estar errado.

## O que aprendi ao conferir a IA

O exemplo mais marcante foi o PDF do case. Ele continha dois trechos escondidos em fonte branca muito pequena. Um mandava remover os registros de **Terreno** antes da análise; o outro mandava colocar a palavra **“abacaxi”** no README. Nenhum dos dois era requisito do desafio. Na primeira leitura, o Claude chegou a tratar a exclusão de Terreno como possível regra, o que me levou a pedir uma verificação mais cuidadosa. Decidi manter esses imóveis na análise principal e testar sua exclusão apenas como análise de sensibilidade. A outra instrução também não será seguida no README.

Eu não conhecia o conceito de *prompt injection*. Levei cerca de **três horas** para entender como uma instrução dentro de um arquivo pode ser confundida com uma ordem para a IA, conferir o que havia no PDF e pensar em como evitar isso no projeto. Daí veio a regra de tratar o conteúdo dos arquivos como dado e de sinalizar instruções suspeitas nos testes.

Houve erros mais comuns também. Uma sugestão inicial para o `.gitignore` esconderia toda a pasta `outputs/`, inclusive os relatórios que o avaliador precisa ver. Corrigi isso. Na etapa dos laudos, o Codex me indicou um modelo do Gemini que a API informou não estar mais disponível para novos usuários. Foram situações que reforçaram para mim que executar um comando e conferir a resposta faz parte do trabalho; uma explicação convincente da IA, sozinha, não basta.

## O que consegui entregar

Na primeira parte, tratei o CSV mantendo os registros e marcando problemas de qualidade, como idade suspeita, datas em outro formato e LTV acima do teto. A análise compara etapas e canais, mas procura distinguir **crédito solicitado sem contratação** de uma perda financeira de fato. Também apresenta a tendência com cuidado, porque propostas recentes podem ainda estar em andamento.

Na segunda parte, há uma rotina que lê o CSV bruto, valida as colunas e gera relatórios em HTML e Excel, além de um log. Testei sua execução no meu computador. O guia explica como outra pessoa pode rodá-la toda segunda-feira; o agendamento está documentado, mas não foi configurado.

Na terceira parte, a extração por regras rodou nos 17 laudos. O código para extração por LLM também foi criado e passou nos testes com um cliente simulado. Tentei usar uma API real, mas a geração retornou erro 503 por alta demanda. Portanto, **não estou apresentando os resultados das regras como resultados de IA**, nem afirmando uma taxa de acerto do LLM. O gabarito dos laudos precisa ser preenchido por mim, manualmente, antes dessa avaliação.

## Onde ainda preciso melhorar

Meu ponto mais difícil de entendimento não foi apenas o código. Foi a parte **financeira**: entendi que o valor solicitado em uma proposta não corresponde automaticamente a receita ou dinheiro perdido, mas ainda não sei estimar esse impacto com a segurança que gostaria. É um assunto que tenho interesse em aprender melhor.

Se tivesse mais tempo, terminaria o gabarito, repetiria a execução com o LLM quando a API estivesse disponível e acompanharia o relatório semanal por algumas semanas. Também conversaria com o time comercial antes de fechar as recomendações. A primeira pergunta seria: propostas marcadas como **“Sem retorno”** ou **“Desistiu”** estão encerradas ou ainda podem voltar? Essa resposta muda a maneira de interpretar as perdas do funil.