# 6. O painel

[← Rodada](05-rodada.md) · [Próximo: FAQ e erros →](07-faq-e-erros.md)

O painel é o lugar onde você vê tudo o que precisa fazer, de todas as rodadas, sem abrir outro arquivo. Ao fim de cada rodada, o `/next-companies` roda `python3 scripts/gerar_painel.py`, que grava os dados, inicia um servidor local e abre o painel no navegador padrão (macOS, Linux e Windows), já na aba **Pendentes**.

O servidor (`scripts/servidor_painel.py`) usa só a biblioteca padrão do Python, escuta em `http://127.0.0.1` numa porta livre e só aceita pedidos do próprio computador e da própria página do painel. Ele roda em segundo plano, é reaproveitado se já estiver aberto e para sozinho depois de 12 horas sem uso.

## `/painel`: atualizar os pendentes sem gastar uma rodada

Mandou umas mensagens e quer ver a lista atualizada? Digite no Claude Code:

```
/painel
```

Ele faz só o Passo 2 do `/next-companies`: confere no LinkedIn e no Gmail (só leitura) o que você enviou desde a data de corte, registra os envios, regenera o painel e abre. **Não processa nenhuma empresa nova** e não cria rascunho. Precisa do mesmo Chrome com o LinkedIn logado do `/next-companies`.

Para só reabrir o painel, sem conferir nada:

```bash
python3 scripts/gerar_painel.py             # macOS e Linux (servidor local + navegador)
py -3 scripts\gerar_painel.py               # Windows
python3 scripts/gerar_painel.py --no-open   # só atualiza os dados, sem servidor e sem navegador
python3 scripts/gerar_painel.py --arquivo   # abre o arquivo direto do disco (só leitura: "Feito" desativado)
```

O script lê `relatorio-parcial.md` (seções 2, 3 e 4), os rascunhos de `rascunhos/linkedin/` e `rascunhos/email/`, `controle/progresso.json`, todos os `relatorios/rodada-*.md` e `relatorio-final.xlsx`, e grava `painel/data.json` + `painel/data.js` (dados pessoais, fora do git).

**Demo com dados fictícios:** [roni-clei-santos.github.io/ai-company-prospector/demo](https://roni-clei-santos.github.io/ai-company-prospector/demo/)

## Pendentes (a primeira aba)

No topo, os totais: "X mensagens de LinkedIn, Y e-mails, Z follow-ups vencidos e W decisões suas". Depois, nesta ordem:

- **Fazer hoje:** follow-ups com data vencida ou igual a hoje e respostas recebidas que pedem uma ação sua (ex.: "pediu o currículo"). Resposta que você já respondeu não entra.
- **LinkedIn:** todas as mensagens ainda não enviadas, de todas as rodadas, numeradas 1, 2, 3… na ordem de prioridade do PROMPT (seção 6.0: vaga com "Certeza", vaga "Provável", freela/parceria, prospecção direta; dentro de cada grupo, pela coluna `#`). Cada item mostra empresa, nome, cargo, tipo (convite com nota ou mensagem direta), o texto completo, **Abrir perfil** e **Copiar texto**. Quando o rascunho tem a mensagem para depois que a pessoa aceitar, ela fica logo abaixo, com o próprio botão de copiar.
- **E-mails:** cada rascunho pendente, com destinatário, assunto e o botão **Abrir Rascunhos do Gmail** (no modo `arquivo`, o texto do e-mail com **Copiar texto**).
- **Decisões suas:** vagas em que o robô não se candidatou e deixou para você (vaga de gestão, idioma acima do seu perfil etc.), com o motivo e o link da vaga.

### "Feito": marcou, está registrado

No topo da aba aparece: **"Marcou como Feito, está registrado."** Cada item tem a caixinha **Feito**. Ao clicar, o painel avisa o servidor local, que chama o `scripts/registrar.py` e grava o item como ENVIADO com a data de hoje em todos os lugares onde o robô registra envio: `controle/progresso.json` (histórico), `relatorio-parcial.md` (✅ na seção 3 ou 4), o relatório da empresa em `relatorios/`, o arquivo do rascunho, `controle/historico-contatos.md` e a linha da empresa no `relatorio-final.xlsx`. O item sai dos pendentes e vai para **Enviados hoje**, com o botão **Desfazer**, que reverte exatamente o que foi gravado.

O seu clique é a fonte da verdade. A conferência no LinkedIn e no Gmail (na rodada seguinte ou no `/painel`) continua só para os itens que você NÃO marcou, para pegar envios que você esqueceu de marcar, e para as respostas recebidas. Ela nunca desmarca um item que você marcou.

Aberto direto do arquivo (`--arquivo` ou dois cliques no `index.html`), não há servidor: os botões "Feito" ficam desativados, com a dica "Abra pelo /painel para registrar". Na demo do GitHub Pages, o "Feito" só risca o item na tela (aviso "demonstração").

Pessoas e empresas marcadas `NAO_CONTATAR` nunca aparecem como pendentes. Seção vazia mostra "Nada pendente aqui". Abaixo dos totais, a linha **Conferência** compara o total de LinkedIn da aba com as pessoas sem ✅ e sem "NÃO ENVIAR" na seção 4 do `relatorio-parcial.md`; se não baterem, ela fica amarela.

![Aba "Pendentes" do painel demo](img/painel-pendentes.png)

## Última rodada

Empresas, rascunhos novos, candidaturas, follow-ups, "O que fazer agora", status da rodada e a tabela das empresas.

![Aba "Última rodada" do painel demo](img/painel-rodada.png)

## Projeto inteiro

Progresso X de N, funil por status, empresas por tipo (concluídas / total) e empresas registradas por dia. Todo gráfico tem o botão **Ver tabela**.

![Aba "Projeto inteiro" do painel demo](img/painel-projeto.png)

## Responderam e Follow-ups com data

Quem respondeu nas últimas rodadas e todos os follow-ups marcados (em laranja, os que já podem ser enviados).

![Aba "Follow-ups com data" do painel demo](img/painel-followups.png)

## Para quem contribui

A demo do GitHub Pages (`docs/demo/`) é uma cópia do painel que lê `painel/demo-data.json`. Depois de mudar `painel/index.html` ou os dados de demo, rode `python3 scripts/gerar_painel.py --demo`. As abas também abrem por link: `index.html#pendentes`, `#rodada`, `#projeto`, `#responderam`, `#followups`.

[← Rodada](05-rodada.md) · [Próximo: FAQ e erros →](07-faq-e-erros.md)
