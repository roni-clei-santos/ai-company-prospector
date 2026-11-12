---
name: next-companies
description: Roda a próxima rodada da prospecção de empresas: registra sozinha o que o candidato enviou (e-mail e LinkedIn, só leitura), processa as próximas 10 empresas a partir de onde parou no controle/progresso.json, atualiza o painel e para. Use quando o usuário digitar /next-companies (opcional: /next-companies limite N).
---

# /next-companies — próxima rodada da prospecção

Esta skill roda UMA rodada do projeto de prospecção. O usuário (o CANDIDATO) digita só `/next-companies`. Opcional: `/next-companies limite N` (ou só um número) para processar N empresas em vez de 10. A skill descobre sozinha o que ele enviou desde a última rodada, processa EXATAMENTE as próximas 10 (ou N) empresas, na ordem combinada, e para. Nada fica implícito: siga os passos na ordem.

Tudo sobre o CANDIDATO está em `perfil.local.md` (o PERFIL). Nunca escreva dado pessoal fora das pastas pessoais (`controle/`, `rascunhos/`, `relatorios/`, `evidencias/`, `curriculos/`, `relatorio-*`).

## Passo 0 — Preflight (pare se falhar)

1. Leia e siga `skills/_shared/preflight.md` (pasta e perfil, Chrome conectado, LinkedIn logado e, se `modo_email` = "gmail_rascunho", Gmail logado).
2. Confira se existe `controle/progresso.json`. Se não existir, PARE e responda: "Não achei o controle/progresso.json. Rode /build-company-list primeiro (ou copie a planilha de empresas para cá e rode de novo)."
3. Se `progresso.json` não for um JSON válido, PARE e responda: "O controle/progresso.json está corrompido; não mexi em nada. Para restaurar a última versão boa, veja docs/guia/07-faq-e-erros.md." Mostre a linha do erro.

## Passo 1 — Carregar as regras e o estado

1. Leia `PROMPT-prospeccao.md` inteiro. TODAS as regras dele valem (status permitidos, formato de relatório, pastas, planilha, aderência, filtros eliminatórios, regra de vaga de gestão, regras de envio, LinkedIn só leitura).
2. Leia `perfil.local.md` inteiro e, se existirem: `controle/progresso.json` (`empresas`, `historico` e `data_corte`), `relatorio-parcial.md` (principalmente as seções 3, 4, 6 e 7), o arquivo do campo `arquivo_respostas` do PERFIL, `controle/perguntas-pendentes.md` e `controle/historico-contatos.md`.
3. Monte a lista de empresas COM status final: toda empresa presente em `progresso.json > empresas`. Essas nunca são reprocessadas. Status com nome antigo (de versões anteriores do projeto) valem como o equivalente novo: `PULADA_PELO_*` = `PULADA_PELO_CANDIDATO`, `DESISTENCIA_DO_*` = `DESISTENCIA_DO_CANDIDATO`.
4. DATA DE CORTE: leia o campo `progresso.json > data_corte` (ISO). Os envios do CANDIDATO são procurados a partir dessa data. Não deduza. Se o campo estiver vazio ou faltar, use a data da nota mais antiga de `progresso.json > historico`; se não houver histórico, use a data de hoje (primeira rodada, nada a procurar).
5. Anote o total de empresas da planilha (N, aba `Empresas` do arquivo do campo `planilha_empresas`).

## Passo 2 — Descobrir sozinha o que o CANDIDATO enviou (antes de processar empresas)

Monte duas listas de pendentes a partir do `relatorio-parcial.md` (se ele ainda não existir, não há pendentes: pule para o Passo 3): (a) e-mails da seção 3 sem ✅; (b) pessoas da seção 4 sem ✅ e sem "NÃO ENVIAR".

### 2.1 E-mail
- `modo_email` = "gmail_rascunho": para cada e-mail pendente, procure no Gmail, em Enviados, uma mensagem para o mesmo destinatário com o mesmo assunto, enviada depois da data de criação do rascunho. Se encontrar, ela conta como ENVIADA na data do envio. Só leitura: não abra rascunhos para editar nem envie nada.
- `modo_email` = "arquivo": o envio não pode ser conferido. Conte como ENVIADO só o arquivo de `rascunhos/email/` em que o próprio CANDIDATO escreveu `ENVIADO DD/MM/AAAA`.

### 2.2 LinkedIn (somente leitura)
Use a aba do Chrome do preflight, logada na conta do CANDIDATO. Abra estas DUAS telas:
1. https://www.linkedin.com/mynetwork/invitation-manager/sent/ (convites enviados ainda não aceitos). Cada item mostra nome, data ("Sent 19 hours ago", "Sent yesterday" etc.) e o texto da nota.
2. https://www.linkedin.com/messaging/ (lista de conversas). Cada item mostra nome, data e a última mensagem. Convite com nota que a pessoa ACEITOU some da tela 1 e aparece aqui, com a nota como mensagem do CANDIDATO ("You: ...").

As duas listas carregam uns 10 itens por vez. Role a página ou clique em "Load more conversations" até aparecer um item mais antigo que a DATA DE CORTE ou até a lista acabar. (Rolar e "Load more" são as ÚNICAS interações permitidas nessas telas.)

Uma pessoa pendente conta como ENVIADA quando o nome dela aparece em qualquer uma das duas telas, com data igual ou posterior à DATA DE CORTE. Regras de comparação:
- O LinkedIn pode mostrar o nome com sufixos ou completo. Exemplos: "Maria Souza, MBA" = Maria Souza; "João Silva (Jota)" = João Silva; "Ana Paula Ribeiro do Carmo" = Ana Carmo. Compare pelo nome e sobrenome principais.
- Para confirmar, o texto da nota ou da mensagem deve ser parecido com o texto do rascunho em `rascunhos/linkedin/`.
- A data do envio é a data mostrada na tela, convertida para DD/MM/AAAA.
- Se ficar em dúvida (nome parecido, texto diferente), NÃO marque. Liste a pessoa em "Conferir" no resumo final.

PROIBIDO nas telas do LinkedIn: clicar em "Withdraw", enviar, responder, aceitar, arquivar, apagar, seguir ou curtir qualquer coisa. É só leitura.

Se a última mensagem de uma conversa for DA PESSOA (não começa com "You:"), registre que ela respondeu e liste em "Responderam" no resumo final.

Se o LinkedIn não abrir ou pedir login, não insista: anote no resumo "LinkedIn não conferido: <motivo>" e siga com o resto.

### 2.3 Registrar
Para cada envio confirmado (e-mail ou LinkedIn), atualize: `controle/historico-contatos.md`; o relatório da empresa em `relatorios/`; o arquivo do rascunho em `rascunhos/email/` ou `rascunhos/linkedin/` (marcar `ENVIADO DD/MM/AAAA`); a coluna "Rascunhos criados"/"Pendências do candidato" da empresa no `relatorio-final.xlsx` (regrave a empresa com `python3 scripts/registrar.py <arquivo.json>`, mantendo o status e a `data` atuais); e uma nota datada em `progresso.json > historico` (`python3 scripts/registrar.py --historico "<nota listando os envios>"`). Essas pessoas e endereços não recebem rascunho novo. Não altere o status de empresa nenhuma por causa de um envio.

## Passo 3 — Escolher as empresas da rodada

1. Ordem: se o `relatorio-parcial.md` existir, use a ordem da seção 6 dele, de cima para baixo: "Vaga — Certeza" → "Vaga — Provável" → "Freela/parceria white-label" → "Prospecção direta (loja)", mantendo a ordem em que as empresas aparecem ali. Se não existir (primeira rodada), monte a ordem pela seção 6.0 do PROMPT a partir da planilha.
2. Pegue as 10 primeiras (ou N, se o usuário passou `limite N`) que NÃO estão em `progresso.json > empresas`. Se restarem menos, processe as que restarem e diga isso no resumo.
3. Se não restar nenhuma, não processe nada: responda "As N empresas estão concluídas" e gere o `relatorio-final.md` oficial conforme a seção 13.2 do PROMPT.
4. Antes de começar, escreva uma linha com as escolhidas (número e nome) e siga direto, sem esperar resposta.

## Passo 4 — Processar cada empresa, uma por vez

Para cada uma, nesta ordem:
1. Antes de qualquer ação, cheque o histórico de contatos (`controle/historico-contatos.md`, e-mail conforme `modo_email`, LinkedIn só leitura e plataformas de vaga), como o PROMPT manda.
2. Siga o fluxo do PROMPT para a categoria da empresa.
3. Aplique as observações da seção 7 do `relatorio-parcial.md` e as notas de `progresso.json > historico` (por exemplo, empresa que o CANDIDATO já contatou por conta própria entra como `JA_CONTATADA_SEM_NOVA_ACAO`, sem rascunho novo).
4. Ao terminar a empresa, grave antes de passar à próxima: o relatório em `relatorios/<numero>-<empresa>.md` e, SEMPRE com `python3 scripts/registrar.py <arquivo.json>`, a linha na planilha `relatorio-final.xlsx` e a entrada em `progresso.json > empresas`. O JSON de entrada fica em `controle/registro-tmp.json` (campos: `numero`, `empresa`, `status`, `data`, `contato_anterior`, `canais`, `vagas`, `candidaturas`, `rascunhos`, `motivo`, `pendencias`, `evidencias`). Nunca edite `progresso.json` ou `relatorio-final.xlsx` à mão.
5. Se a empresa travar (site fora do ar, login exigido, erro de ferramenta), registre o status adequado do PROMPT com o motivo real e siga para a próxima. Nunca deixe empresa pela metade sem registro.

## Regras fixas (valem em toda a rodada)

- NUNCA envie e-mail, mensagem de LinkedIn ou candidatura que o PROMPT não autorize. E-mail e LinkedIn são sempre só rascunho.
- LinkedIn: SÓ LEITURA (regra em `skills/_shared/preflight.md`). Pode abrir convites enviados, mensagens, abas Jobs e People de empresas e páginas de vaga. Proibido: enviar, aceitar, retirar convite, responder, arquivar, apagar, seguir, curtir.
- E-mail conforme `modo_email`: "arquivo" = só `rascunhos/email/*.md`; "gmail_rascunho" = rascunho no Gmail pelo navegador (nunca clicar em Enviar). No modo Gmail, releia cada rascunho logo depois de criá-lo: destinatário certo, assunto, corpo não vazio e currículo anexado. Se algo falhar, corrija antes de seguir.
- Notas de convite do LinkedIn com até 200 caracteres. Rode `python3 scripts/checar_notas.py` ao fim da rodada e corrija o que ele apontar.
- Vaga de gestão (Delivery Leader, Gerente de Projetos, Coordenador, Head, Product Manager e parecidas) nunca recebe candidatura automática: registre como `VAGA_GESTAO_PARA_O_CANDIDATO_DECIDIR` e siga.
- Nunca altere o perfil ou currículo do CANDIDATO em nenhuma plataforma (Gupy, LinkedIn, InHire etc.), a menos que o PROMPT (seção 7.3) e o `arquivo_respostas` permitam.
- Empresas com decisão do CANDIDATO (`DESISTENCIA_DO_CANDIDATO`, `PULADA_PELO_CANDIDATO`, empresas de `empresas_excluidas` e rascunhos marcados NÃO ENVIAR) não recebem nada novo.
- Localização: siga o campo `modalidade` do PERFIL.
- Ao concluir a 10ª (ou N-ésima) empresa: PARE. Não comece a próxima.

## Passo 5 — Ao parar

1. Atualize o `relatorio-parcial.md` com o consolidado de TODO o projeto, no mesmo formato e nas mesmas seções atuais (crie-o na primeira rodada com as seções: 1. Resumo em números; 2. Ações urgentes que só o candidato pode fazer; 3. Rascunhos de e-mail; 4. Rascunhos de LinkedIn; 5. Empresa por empresa; 6. Empresas que faltam processar (ordem combinada); 7. Observações importantes), incluindo a nova contagem "X de N", os envios registrados no Passo 2 e o novo ponto de retomada na seção 6. Na tabela "Resumo em números" use os nomes oficiais de status.
2. Crie `relatorios/rodada-AAAA-MM-DD.md` só com esta rodada, no mesmo formato da rodada anterior (seções: "Envios que encontrei", "Resumo", "Empresa por empresa", "Rascunhos novos de e-mail", "Rascunhos novos de LinkedIn", "O que depende do candidato"). Se já existir um arquivo com a data de hoje, use o sufixo `-2`.
3. Acrescente uma nota em `progresso.json > historico` com a data, as empresas e o ponto de retomada: `python3 scripts/registrar.py --historico "<nota>" --sessao <n>`.
4. Atualize a DATA DE CORTE: a data de criação do rascunho pendente (ainda não enviado, sem NÃO ENVIAR) mais antigo do projeto inteiro, conferida nas seções 3 e 4 do `relatorio-parcial.md` e na data de registro da empresa dona do rascunho. Se não houver nenhum pendente, use a data de hoje. Grave: `python3 scripts/registrar.py --data-corte AAAA-MM-DD`.
5. Confira que os números do resumo batem com a tabela (soma dos status = empresas processadas).
6. Gere e abra o painel: `python3 scripts/gerar_painel.py` e depois `open painel/index.html`.
7. Responda ao CANDIDATO só com, nesta ordem:
   - Envios que encontrei (e-mail e LinkedIn), "Responderam" e "Conferir", se houver.
   - Tabela das empresas da rodada: número, empresa, status e quantidade de rascunhos.
   - O que o CANDIDATO precisa fazer (envios pendentes desta rodada e follow-ups com data).
   - Pontos para ele conferir.
   - "X de N concluídas. Próxima rodada começa pela #M <empresa>."
   - "Painel atualizado e aberto: painel/index.html."
