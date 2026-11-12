# 6. O painel

[← Rodada](05-rodada.md) · [Próximo: FAQ e erros →](07-faq-e-erros.md)

O painel é o lugar onde você vê tudo o que precisa fazer, de todas as rodadas, sem abrir outro arquivo. Ao fim de cada rodada, o `/next-companies` roda `python3 scripts/gerar_painel.py`, que grava os dados, liga o servidor local e abre o painel no navegador padrão (macOS, Linux e Windows), já na aba **Pendentes**.

**Como abrir o painel:** rode /painel no Claude Code. Ele também abre sozinho no fim de cada rodada. O painel roda só no seu computador e desliga sozinho alguns minutos depois que você fecha a aba.

Funciona como um app local (no estilo do Jupyter): o `/painel` liga um servidor só no seu computador (`scripts/servidor_painel.py`, só biblioteca padrão do Python, em `http://127.0.0.1` numa porta que o sistema escolhe) e abre o painel no navegador. Nada sai do seu computador. Se o painel já estiver aberto, o `/painel` reaproveita o mesmo servidor; nunca há dois para o mesmo projeto. Ele desliga sozinho alguns minutos depois que você fecha a aba (recarregar a página não desliga). Nada liga junto com o computador.

Abrir o `painel/index.html` direto do disco mostra só uma tela com a instrução de abrir pelo `/painel`.

## `/painel`: abrir o painel de qualquer pasta

Digite no Claude Code, em qualquer pasta:

```
/painel
```

Ele só roda `scripts/gerar_painel.py`: regenera os dados, liga o servidor se estiver parado e abre o painel. **Não abre o LinkedIn, o Gmail nem o Chrome**, não processa empresa e não cria rascunho. A conferência do que você enviou fica no `/next-companies` (passo 1 de cada rodada).

O projeto é encontrado nesta ordem: a variável `PROSPECT_DIR`; o caminho gravado em `~/.config/ai-company-prospector/projeto` (Windows: `%APPDATA%\ai-company-prospector\projeto`), que o instalador e o painel gravam; a pasta atual. Se nenhum tiver `controle/progresso.json`, aparece "Não achei o projeto. Rode o instalador na pasta do projeto."

Pelo terminal:

```bash
python3 scripts/gerar_painel.py             # macOS e Linux (liga ou reaproveita o servidor e abre o painel)
py -3 scripts\gerar_painel.py               # Windows
python3 scripts/gerar_painel.py --no-open   # só atualiza os dados, sem servidor e sem navegador
```

O script lê `relatorio-parcial.md` (seções 2, 3 e 4), os rascunhos de `rascunhos/linkedin/` e `rascunhos/email/`, `controle/progresso.json`, todos os `relatorios/rodada-*.md` e `relatorio-final.xlsx`. Ele grava `painel/data.json` e os relatórios em HTML de `painel/relatorios/`, tudo dado pessoal e fora do git. Enquanto o servidor está ligado, ele guarda o próprio endereço em `controle/.painel-servidor.json` e apaga esse arquivo ao desligar.

**Demo com dados fictícios:** [roni-clei-santos.github.io/ai-company-prospector/demo](https://roni-clei-santos.github.io/ai-company-prospector/demo/)

## Pendentes (a primeira aba)

No topo, os totais: "X mensagens de LinkedIn, Y e-mails, Z follow-ups vencidos e W decisões suas". Depois, nesta ordem:

- **Fazer hoje:** follow-ups com data vencida ou igual a hoje e respostas recebidas que pedem uma ação sua (ex.: "pediu o currículo"). Resposta que você já respondeu não entra.
- **LinkedIn:** todas as mensagens ainda não enviadas, de todas as rodadas, numeradas 1, 2, 3… na ordem de prioridade do PROMPT (seção 6.0: vaga com "Certeza", vaga "Provável", freela/parceria, prospecção direta; dentro de cada grupo, pela coluna `#`). Cada item mostra empresa, nome, cargo, tipo (convite com nota ou mensagem direta), o texto completo, **Abrir perfil** e **Copiar texto**. Quando o rascunho tem a mensagem para depois que a pessoa aceitar, ela fica logo abaixo, com o próprio botão de copiar.
- **E-mails:** cada rascunho pendente, com destinatário, assunto e o botão **Abrir Rascunhos do Gmail** (no modo `arquivo`, o texto do e-mail com **Copiar texto**).
- **Decisões suas:** vagas em que o robô não se candidatou e deixou para você (vaga de gestão, idioma acima do seu perfil etc.), com o motivo e o link da vaga.

### "Feito": marcou, está registrado

Cada item tem a caixinha **Feito**. Ao clicar, o painel avisa o servidor local, que chama o `scripts/registrar.py` e grava o item, na hora, como ENVIADO com a data de hoje em todos os lugares onde o robô registra envio: `controle/progresso.json` (histórico), `relatorio-parcial.md` (✅ na seção 3 ou 4), o relatório da empresa em `relatorios/`, o arquivo do rascunho, `controle/historico-contatos.md` e a linha da empresa no `relatorio-final.xlsx`. O item vai para **Enviados hoje** e aparece **"Marcou como Feito, está registrado."** O botão **Desfazer** reverte exatamente o que foi gravado. Clicar duas vezes no mesmo item não grava duas vezes.

Só a caixinha clicada espera a resposta, por no máximo 5 segundos. Se não der certo, ela volta como estava e aparece o motivo, com o botão **Tentar de novo**; nada é repetido sozinho. Se o servidor tiver sido desligado com a página aberta, aparece uma vez: **"O painel foi encerrado. Rode /painel para abrir de novo."** A tela nunca se redesenha sozinha: só muda quando você clica ou troca de aba.

O seu clique é a fonte da verdade. A conferência no LinkedIn e no Gmail (no passo 1 de cada rodada do `/next-companies`) continua só para os itens que você NÃO marcou, para pegar envios que você esqueceu de marcar, e para as respostas recebidas. Ela nunca desmarca um item que você marcou. Na demo do GitHub Pages, o "Feito" só risca o item na tela (aviso "demonstração").

**Relatório da empresa:** o botão abre o relatório da empresa como página (`painel/relatorios/<nome>.html`, gerada a partir do `.md`), com "Voltar ao painel" no topo. Funciona igual com o painel aberto do arquivo ou pelo servidor. O nome do relatório da rodada, na aba Última rodada, também abre a página dele.

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

A página do painel fica em `scripts/painel_template.html` (o servidor a entrega com a chave de cada execução). A demo do GitHub Pages (`docs/demo/`) é uma cópia dela que lê `painel/demo-data.json` e só risca na tela. Depois de mudar o template ou os dados de demo, rode `python3 scripts/gerar_painel.py --demo`. As abas também abrem por link: `#pendentes`, `#rodada`, `#projeto`, `#responderam`, `#followups`.

[← Rodada](05-rodada.md) · [Próximo: FAQ e erros →](07-faq-e-erros.md)
