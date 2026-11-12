# 6. O painel

[← Rodada](05-rodada.md) · [Próximo: FAQ e erros →](07-faq-e-erros.md)

Ao fim de cada rodada, o `/next-companies` roda `python3 scripts/gerar_painel.py` e abre `painel/index.html`. Para abrir de novo quando quiser:

```bash
python3 scripts/gerar_painel.py && open painel/index.html
```

O script lê `controle/progresso.json`, `relatorios/rodada-*.md` e `relatorio-final.xlsx` e grava `painel/data.json` + `painel/data.js` (dados pessoais, fora do git). O painel funciona direto do disco, sem servidor.

**Demo com dados fictícios:** [roni-clei-santos.github.io/ai-company-prospector/demo](https://roni-clei-santos.github.io/ai-company-prospector/demo/)

## Esta rodada

Empresas, rascunhos novos, candidaturas, follow-ups, "O que fazer agora", status da rodada e a tabela das empresas.

![Seção "Esta rodada" do painel demo](img/painel-rodada.png)

## Projeto inteiro

Progresso X de N, funil por status, empresas por tipo (concluídas / total) e empresas registradas por dia. Todo gráfico tem o botão **Ver tabela**.

![Seção "Projeto inteiro" do painel demo](img/painel-projeto.png)

## Responderam e Follow-ups com data

Quem respondeu nas últimas rodadas e os follow-ups marcados (em laranja, os que já podem ser enviados).

![Seções "Responderam" e "Follow-ups" do painel demo](img/painel-followups.png)

## Para quem contribui

A demo do GitHub Pages (`docs/demo/`) é uma cópia do painel que lê `painel/demo-data.json`. Depois de mudar `painel/index.html` ou os dados de demo, rode `python3 scripts/gerar_painel.py --demo`.

[← Rodada](05-rodada.md) · [Próximo: FAQ e erros →](07-faq-e-erros.md)
