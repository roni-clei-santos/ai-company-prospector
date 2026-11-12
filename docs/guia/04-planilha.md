# 4. A planilha de empresas (`/build-company-list`)

[← Chrome](03-chrome.md) · [Próximo: a rodada →](05-rodada.md)

Rode `/build-company-list`. Ele faz **uma** mensagem com 6 perguntas (os padrões vêm do seu perfil):

1. tecnologia/plataforma (ex.: "Magento / Adobe Commerce", "VTEX");
2. país ou região;
3. tipos de empresa (agências especialistas, consultorias grandes, agências multiplataforma, marcas que usam a tecnologia, empresas com vaga aberta, internacionais que contratam remoto na região, ecossistema);
4. objetivo (vaga, parceria, freela ou todos);
5. empresas a excluir;
6. ex-empregadores.

Depois ele pesquisa, nesta ordem: diretório oficial de parceiros da tecnologia → Clutch → TheirStack → eventos da comunidade → parceiros do ecossistema → vagas abertas que citam a tecnologia (nunca Indeed) → cases públicos. Para quando 3 buscas seguidas não trazem empresa nova.

Para testar rápido: `/build-company-list limite 5`.

![Resumo do /build-company-list com dados fictícios](img/terminal-planilha.png)

## O que sai

`empresas-<tecnologia>-<pais>.xlsx`:

- aba **Empresas**: `#`, `Empresa`, `Tipo`, `Cidade/UF`, `Evidência`, `Confiança`, `Serve para`, `Observação`, `Fonte`;
- aba **Resumo**: contagem por tipo, por confiança e por "Serve para", com a legenda.

Regras: toda linha tem link de fonte; sem duplicatas; nada inventado. **Certeza** = evidência direta e atual (vaga, site, case, diretório). **Provável** = evidência antiga ou indireta, em amarelo. Ex-empregadores ficam marcados em Observação; empresas excluídas não entram.

O `scripts/montar_planilha.py` aplica essas regras e cria o `controle/progresso.json` vazio, pronto para o `/next-companies` (nunca sobrescreve um que já existe).

[← Chrome](03-chrome.md) · [Próximo: a rodada →](05-rodada.md)
