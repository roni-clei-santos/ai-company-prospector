# Preflight básico: pasta e perfil

Usado por `/build-company-list` (só esta parte) e por `/next-companies` (esta parte e depois `skills/_shared/preflight-linkedin.md`).

Siga na ordem. Se um item falhar, PARE com a mensagem exata indicada e não altere nada.

**Sistema operacional.** Os comandos Python aparecem como `python3`. No Windows, se `python3` não existir, use `py -3` (ou `python`) no lugar, com os mesmos argumentos. Use caminhos relativos à pasta do projeto (`scripts/...`, `controle/...`); não use comandos exclusivos de um sistema (como `open`, `cp` ou `ls`) quando houver um script do projeto ou uma ferramenta do Claude Code que faça o mesmo.

## Pasta do projeto e perfil

1. A pasta atual tem que ser a pasta do projeto: precisa existir `PROMPT-prospeccao.md` e a pasta `scripts/`.
   Se faltar, PARE com: "Não estou na pasta do projeto de prospecção. Abra o Claude Code na pasta do projeto e rode o comando de novo."
2. Se `perfil.local.md` NÃO existir: copie `perfil.example.md` para `perfil.local.md` (leia o exemplo e grave a cópia com a ferramenta de arquivos, que funciona em qualquer sistema) e PARE com:
   "Preencha o perfil.local.md (guia: docs/guia/02-perfil.md) e rode de novo."
3. Se `perfil.local.md` existir mas ainda tiver `nome: "Alex Exemplo"` ou `email: "alex@example.com"` (o exemplo sem preencher), PARE com a mesma mensagem do item 2. Exceção: pasta de teste com perfil fictício declarado pelo próprio usuário.
4. Leia `perfil.local.md` inteiro. Confira os campos obrigatórios: `nome`, `email`, `linkedin_url`, `cidade`, `tecnologias_principais`, `anos_experiencia`, `pisos_salariais` (`clt`, `pj`), `idiomas`, `ex_empregadores`, `empresas_excluidas`, `curriculo_base`, `tom_de_voz` (`saudacao`, `fechamento`), `modo_email` ("arquivo" ou "gmail_rascunho"). Se algum faltar, PARE e diga quais faltam, com o mesmo guia.
