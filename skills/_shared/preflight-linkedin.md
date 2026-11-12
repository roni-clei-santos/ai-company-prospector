# Preflight LinkedIn: Chrome conectado e LinkedIn logado

Usado só por `/next-companies`, DEPOIS de `skills/_shared/preflight-basico.md`. O `/build-company-list` não usa esta parte: ele roda sem LinkedIn.

Siga na ordem. Se um item falhar, PARE com a mensagem exata indicada e não altere nada.

## a) Claude in Chrome conectado

1. Carregue as ferramentas do Chrome numa chamada só do ToolSearch:
   `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__computer`
2. Chame `tabs_context_mcp`. Se as ferramentas não existirem ou a chamada falhar, PARE com:
   "Instale a extensão Claude in Chrome e rode /chrome no Claude Code (guia: docs/guia/03-chrome.md). Depois rode de novo."

## b) LinkedIn logado

1. Crie uma aba nova (`tabs_create_mcp`) e abra `https://www.linkedin.com/feed/`.
2. Se a página cair na tela de login (URL com `/login`, `/authwall`, `/checkpoint` ou `/uas/login`, ou um formulário "Entrar"/"Sign in"), PARE com:
   "Entre no LinkedIn nessa aba do Chrome e digite: pronto."
3. Espere a pessoa digitar "pronto". Recarregue `https://www.linkedin.com/feed/` e confira de novo. Repita até estar logado.
4. Gmail: SÓ se `modo_email` = "gmail_rascunho". Abra `https://mail.google.com/` na mesma aba e confira se está logado na conta do campo `email`. Se não estiver, PARE com: "Entre no Gmail (conta <email>) nessa aba do Chrome e digite: pronto."
   Com `modo_email` = "arquivo", NÃO abra o Gmail nem confira nada nele: este preflight confere só o Chrome (item a) e o LinkedIn (itens 1 a 3).

## Regra de LinkedIn (vale em TODA a skill)

SÓ LEITURA.
- Pode abrir: convites enviados, mensagens, abas Jobs e People de empresas, perfis de pessoas e páginas de vaga.
- Proibido: enviar, aceitar, retirar convite ("Withdraw"), responder, arquivar, apagar, seguir, curtir, conectar, candidatar-se, editar perfil. Nunca clique em botões dessas ações, nem por engano: se precisar de um link, leia a URL; não clique em botões.
- Ritmo humano: espere alguns segundos entre páginas. Se aparecer aviso de limite, verificação ou bloqueio, pare de usar o LinkedIn nesta rodada e registre isso no resumo.
- Não dispare alertas, pop-ups ou diálogos que travem o navegador.
