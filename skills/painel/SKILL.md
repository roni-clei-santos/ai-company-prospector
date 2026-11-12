---
name: painel
description: Abre o painel da prospecção (aba Pendentes) de qualquer pasta: regenera os dados, liga o servidor local se estiver parado e abre no navegador. Não acessa LinkedIn, Gmail nem Chrome e não processa nenhuma empresa. Use quando o usuário digitar /painel.
---

# /painel: abrir o painel

O usuário (o CANDIDATO) digita só `/painel`. Esta skill roda UM comando e para.

PROIBIDO nesta skill: abrir ou usar o LinkedIn, o Gmail, o Chrome ou o Claude in Chrome; pesquisar empresas; criar rascunhos; candidatar-se; mudar status; editar `relatorio-parcial.md`. A conferência do que o CANDIDATO enviou fica só no `/next-companies` (Passo 2). O clique do CANDIDATO em "Feito", no painel, já registra o envio no projeto.

## Passo 1: achar o projeto

O script do painel fica na pasta do projeto. Use, nesta ordem, a primeira opção que existir:
1. `scripts/gerar_painel.py` na pasta atual;
2. a pasta escrita no arquivo `~/.config/ai-company-prospector/projeto` (Windows: `%APPDATA%\ai-company-prospector\projeto`), que os instaladores e o próprio painel gravam;
3. no Windows, a pasta escrita no arquivo `.installed-from` desta skill.

Se nenhuma existir, PARE com: "Não achei o projeto. Rode o instalador na pasta do projeto."

## Passo 2: abrir o painel

Rode `python3 "<pasta do projeto>/scripts/gerar_painel.py"` (no Windows, `py -3` no lugar de `python3`). O script regenera `painel/data.json` e os relatórios em `painel/relatorios/`. Também liga o servidor local do painel (ou reaproveita o que já está ligado) e abre o painel no navegador padrão, na aba Pendentes. O servidor fica em http://127.0.0.1, só neste computador, e desliga sozinho alguns minutos depois que a aba do painel é fechada.

Se o script responder "Não achei o projeto. Rode o instalador na pasta do projeto.", repasse a frase e pare.

## Passo 3: responder

Responda só com:
- a linha de totais da aba Pendentes, lida em `painel/data.json > pendentes`: "X mensagens de LinkedIn, Y e-mails, Z follow-ups vencidos e W decisões suas." (follow-ups vencidos são os de `followups` com `data` até hoje);
- "Painel aberto (aba Pendentes). Marcou como Feito, está registrado."
- se o script avisou que não conseguiu ligar o painel, repita o aviso dele.
