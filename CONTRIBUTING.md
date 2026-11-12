# Como contribuir

Obrigado por querer ajudar! Este projeto é pequeno de propósito: Markdown para as regras, Python simples para os scripts e um painel em HTML sem build.

## Antes de abrir um PR

1. Rode os testes: `python3 -m pytest` (todos têm que passar).
2. **Nunca** inclua dados pessoais: nada de `perfil.local.md`, `controle/`, `rascunhos/`, `relatorios/`, `evidencias/`, `curriculos/`, planilhas `.xlsx` reais, PDFs ou prints do LinkedIn, do Gmail ou de qualquer tela com dado real. Exemplos e testes usam só dados fictícios ("Alex Exemplo", "Loja Exemplo 1", `example.com`).
3. Se mexer no `painel/index.html` ou no `painel/demo-data.json`, rode `python3 scripts/gerar_painel.py --demo` para atualizar a demo em `docs/demo/`.
4. Comentários de código em inglês; documentação em português (`README.md`, `docs/guia/`) e inglês (`README.en.md`).

## Regras que não mudam

- No LinkedIn, **só leitura**. Nenhuma contribuição pode fazer o agente enviar, aceitar, retirar convite, responder, curtir ou seguir.
- E-mail e mensagens são **sempre rascunhos**. Quem envia é a pessoa.
- Nada é afirmado sobre a pessoa fora do `perfil.local.md`, do currículo dela e das respostas dela.

## Ideias de contribuição

Veja o [ROADMAP.md](ROADMAP.md). Bugs e sugestões: abra uma issue com os modelos em `.github/ISSUE_TEMPLATE/`.

## Fluxo

1. Fork → branch (`feat/...` ou `fix/...`).
2. Commits pequenos, mensagem em inglês (`feat: ...`, `fix: ...`, `docs: ...`).
3. PR descrevendo o que mudou e como testou.
