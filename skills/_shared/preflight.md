# Preflight (Passo 0 compartilhado por /next-companies e /build-company-list)

Siga na ordem. Se um item falhar, PARE com a mensagem exata indicada e não altere nada.

## a) Pasta do projeto e perfil

1. A pasta atual tem que ser a pasta do projeto: precisa existir `PROMPT-prospeccao.md` e a pasta `scripts/`.
   Se faltar, PARE com: "Não estou na pasta do projeto de prospecção. Abra o Claude Code na pasta do projeto e rode o comando de novo."
2. Se `perfil.local.md` NÃO existir: copie `perfil.example.md` para `perfil.local.md` (`cp perfil.example.md perfil.local.md`) e PARE com:
   "Preencha o perfil.local.md (guia: docs/guia/02-perfil.md) e rode de novo."
3. Se `perfil.local.md` existir mas ainda tiver `nome: "Alex Exemplo"` ou `email: "alex@example.com"` (o exemplo sem preencher), PARE com a mesma mensagem do item 2. Exceção: pasta de teste com perfil fictício declarado pelo próprio usuário.
4. Leia `perfil.local.md` inteiro. Confira os campos obrigatórios: `nome`, `email`, `linkedin_url`, `cidade`, `tecnologias_principais`, `anos_experiencia`, `pisos_salariais` (`clt`, `pj`), `idiomas`, `ex_empregadores`, `empresas_excluidas`, `curriculo_base`, `tom_de_voz` (`saudacao`, `fechamento`), `modo_email` ("arquivo" ou "gmail_rascunho"). Se algum faltar, PARE e diga quais faltam, com o mesmo guia.

## b) Claude in Chrome conectado

1. Carregue as ferramentas do Chrome numa chamada só do ToolSearch:
   `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__computer`
2. Chame `tabs_context_mcp`. Se as ferramentas não existirem ou a chamada falhar, PARE com:
   "Instale a extensão Claude in Chrome e rode /chrome no Claude Code (guia: docs/guia/03-chrome.md). Depois rode de novo."

## c) LinkedIn logado

1. Crie uma aba nova (`tabs_create_mcp`) e abra `https://www.linkedin.com/feed/`.
2. Se a página cair na tela de login (URL com `/login`, `/authwall`, `/checkpoint` ou `/uas/login`, ou um formulário "Entrar"/"Sign in"), PARE com:
   "Entre no LinkedIn nessa aba do Chrome e digite: pronto."
3. Espere a pessoa digitar "pronto". Recarregue `https://www.linkedin.com/feed/` e confira de novo. Repita até estar logado.
4. Se `modo_email` = "gmail_rascunho" (só no /next-companies): abra `https://mail.google.com/` na mesma aba e confira se está logado na conta do campo `email`. Se não estiver, PARE com: "Entre no Gmail (conta <email>) nessa aba do Chrome e digite: pronto."

## Regra de LinkedIn (vale em TODA a skill)

SÓ LEITURA.
- Pode abrir: convites enviados, mensagens, abas Jobs e People de empresas, perfis de pessoas e páginas de vaga.
- Proibido: enviar, aceitar, retirar convite ("Withdraw"), responder, arquivar, apagar, seguir, curtir, conectar, candidatar-se, editar perfil. Nunca clique em botões dessas ações, nem por engano: se precisar de um link, leia a URL; não clique em botões.
- Ritmo humano: espere alguns segundos entre páginas. Se aparecer aviso de limite, verificação ou bloqueio, pare de usar o LinkedIn nesta rodada e registre isso no resumo.
- Não dispare alertas, pop-ups ou diálogos que travem o navegador.
