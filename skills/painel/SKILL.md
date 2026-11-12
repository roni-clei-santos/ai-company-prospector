---
name: painel
description: Atualiza a lista de pendentes da prospecção sem gastar uma rodada: confere sozinha o que o candidato enviou no LinkedIn e no Gmail (só leitura, o Passo 2 do /next-companies), registra, regenera o painel e abre na aba Pendentes. Não processa nenhuma empresa. Use quando o usuário digitar /painel.
---

# /painel — atualizar os pendentes e abrir o painel

O usuário (o CANDIDATO) digita só `/painel`. Esta skill faz três coisas e para:
1. descobre o que ele enviou no LinkedIn e no Gmail desde a DATA DE CORTE e registra (o mesmo Passo 2 do `/next-companies`);
2. regenera o painel;
3. abre o painel pelo servidor local (http://127.0.0.1, só neste computador), que começa na aba **Pendentes**. Aberto assim, cada clique em "Feito" registra o item como ENVIADO hoje em todos os lugares, com "Desfazer" em "Enviados hoje".

O clique do CANDIDATO em "Feito" é a fonte da verdade: a conferência deste passo é só para os itens que ele NÃO marcou (envios que esqueceu de marcar) e para as respostas recebidas. Nunca desmarque nem registre de novo um item que está em `controle/painel-feitos.json` ou já tem ✅.

NÃO processe nenhuma empresa nova: não pesquise empresas, não crie rascunho, não se candidate, não crie `relatorios/rodada-*.md` e não mude o status de empresa nenhuma.

Tudo sobre o CANDIDATO está em `perfil.local.md` (o PERFIL). Nunca escreva dado pessoal fora das pastas pessoais (`controle/`, `rascunhos/`, `relatorios/`, `evidencias/`, `curriculos/`, `relatorio-*`).

## Passo 0 — Preflight (pare se falhar)

1. Leia e siga, nesta ordem, `skills/_shared/preflight-basico.md` e `skills/_shared/preflight-linkedin.md` (Chrome conectado e LinkedIn logado; o Gmail só é conferido se `modo_email` = "gmail_rascunho"). A regra de LinkedIn SÓ LEITURA vale em toda a skill.
2. Se não existir `controle/progresso.json`, PARE com: "Não achei o controle/progresso.json. Rode /build-company-list primeiro."
3. Se não existir `relatorio-parcial.md`, não há envio para conferir: pule para o Passo 3.

## Passo 1 — Carregar o estado

Leia `perfil.local.md`, `controle/progresso.json` (`empresas`, `historico`, `data_corte`, `nao_contatar`) e as seções 1, 2, 3 e 4 do `relatorio-parcial.md`. A DATA DE CORTE é `progresso.json > data_corte` (mesma regra do Passo 1.4 do `/next-companies`).

## Passo 2 — Conferir e registrar os envios (o Passo 2 do /next-companies)

Leia `skills/next-companies/SKILL.md` e execute SÓ o "Passo 2 — Descobrir sozinha o que o CANDIDATO enviou", inteiro e do jeito que está escrito lá: 2.1 E-mail, 2.2 LinkedIn (somente leitura) e 2.3 Registrar. Não execute nenhum outro passo daquela skill.

Depois, como esta skill não tem o Passo 5 do `/next-companies`, atualize também o `relatorio-parcial.md`, sem mexer em mais nada dele:
- seção 3: para cada e-mail confirmado, acrescente `✅ ENVIADO DD/MM` na coluna `#` da linha;
- seção 4: para cada pessoa confirmada, troque a coluna `Prio` por `✅` e comece a coluna `Destinatário` com `**ENVIADO DD/MM/AAAA**`;
- seção 1: atualize só os números de rascunhos enviados e pendentes (e-mail e LinkedIn);
- seção 2: tire os itens que esses envios resolveram.

Então atualize a DATA DE CORTE como no Passo 5.4 do `/next-companies`: a data de criação do rascunho pendente mais antigo (sem ✅ e sem NÃO ENVIAR) das seções 3 e 4; se não houver nenhum, a data de hoje. Grave com `python3 scripts/registrar.py --data-corte AAAA-MM-DD`.

Se o LinkedIn ou o Gmail não abrir, não insista: anote "LinkedIn não conferido: <motivo>" (ou Gmail) e siga para o Passo 3 com o que tiver.

## Passo 3 — Regenerar e abrir o painel

1. Rode `python3 scripts/checar_nao_contatar.py`. Se ele apontar algum rascunho pendente para pessoa ou empresa `NAO_CONTATAR`, marque `NÃO ENVIAR` nesse rascunho e na linha dele no `relatorio-parcial.md`.
2. Rode `python3 scripts/gerar_painel.py`. Ele grava `painel/data.json`, inicia (ou reaproveita) em segundo plano o servidor local `scripts/servidor_painel.py` (só biblioteca padrão do Python, em http://127.0.0.1 numa porta livre, acessível só por este computador) e abre o painel no navegador padrão (macOS, Linux e Windows), já na aba Pendentes. O servidor para sozinho depois de 12 horas sem uso.
3. Leia `painel/data.json > pendentes > conferencia`: `linkedin_secao4` (pessoas sem ✅ e sem NÃO ENVIAR na seção 4) tem que ser igual a `linkedin_painel` + `ocultos_nao_contatar`. Se não for, diga isso no resumo.

## Passo 4 — Responder

Responda ao CANDIDATO só com, nesta ordem:
- Envios que encontrei (e-mail e LinkedIn), "Responderam" e "Conferir", se houver. Se nada foi encontrado, diga "Nenhum envio novo desde DD/MM/AAAA."
- A linha de totais da aba Pendentes: "X mensagens de LinkedIn, Y e-mails, Z follow-ups vencidos e W decisões suas."
- "Painel atualizado e aberto: <URL http://127.0.0.1:... que o script mostrou> (aba Pendentes). Marcou como Feito, está registrado."
