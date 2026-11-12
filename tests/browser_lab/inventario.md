# Inventário dos elementos clicáveis do painel

O cenário D do laboratório (`run_lab.py`, função `cenario_d`) percorre esta lista nos 11 navegadores. Ele usa o painel real, aberto como o `/painel` abre (`gerar_painel.py`, servidor em `http://127.0.0.1`), sobre um projeto fictício (`projeto_lab.py`). O cenário C repete Feito, Desfazer e Relatório da empresa.

Se aparecer no painel um link ou botão que não está nesta lista, o teste reprova com "clicável fora do inventário". Assim, quem adicionar um botão também precisa adicionar o teste dele.

| Elemento | Aba | O que deve acontecer | Como o teste verifica |
|---|---|---|---|
| Abas: Pendentes, Última rodada, Projeto inteiro, Responderam, Follow-ups com data | cabeçalho (todas) | mostra só a seção escolhida | clica em cada aba e confere que só aquela seção está visível |
| Chips: Fazer hoje, LinkedIn, E-mails, Decisões suas, Enviados hoje | Pendentes | rola até o grupo | volta ao topo, clica em cada chip e confere que o grupo ficou dentro da janela |
| "ver detalhes" da conferência | Pendentes (só quando há diferença com o relatório) | abre a lista de diferenças | quando existe, clica e confere que abriu |
| Copiar texto (mensagem de LinkedIn; e-mail no modo `arquivo`) | Pendentes | copia o texto; o botão mostra "Copiado ✓", ou "Não copiou: selecione o texto" se o navegador bloquear | clica, exige "Copiado ✓" e, quando o navegador deixa ler a área de transferência, confere o texto |
| Outra versão (mensagem para depois que aceitar) | Pendentes / LinkedIn | abre a segunda mensagem | clica e confere que abriu; clica no "Copiar texto" dela e exige "Copiado ✓" |
| Feito | Pendentes: Fazer hoje, LinkedIn, E-mails, Decisões suas | grava o item como ENVIADO hoje no projeto, na hora, e move o item para "Enviados hoje"; só aquele checkbox espera a resposta (até 5 s) | clica em um item de cada grupo e confere que `progresso.json` e `painel-feitos.json` mudaram (C e D); com o servidor encerrado, confere o aviso "O painel foi encerrado…" uma vez só (F) |
| Desfazer | Pendentes / Enviados hoje | reverte o que o Feito gravou | clica e confere que `progresso.json` voltou ao que era e que o item saiu de `painel-feitos.json` |
| Tentar de novo | aviso no rodapé (só quando o servidor responde um erro) | tenta gravar de novo o mesmo clique; nada é repetido sozinho | simula um erro do servidor no Feito, confere que o checkbox voltou, que o motivo aparece com "Tentar de novo" e que o botão grava (D) |
| Relatório da empresa | Pendentes / Decisões suas | abre `relatorios/<nome>.html` pelo servidor, com "Voltar ao painel" no topo | confere que o href é `relatorios/<nome>.html`, clica (C e D), confere o título e o conteúdo (tabela ou lista), confere que não há link `javascript:` nem HTML cru, e clica em "Voltar ao painel" |
| Relatório da rodada (nome do arquivo) | Última rodada | abre o relatório da rodada em HTML | igual ao Relatório da empresa (http) |
| Ver tabela / Ver gráfico (3 gráficos) | Projeto inteiro | alterna entre gráfico e tabela | clica e confere que a tabela apareceu; clica de novo e confere que o gráfico voltou |
| Abrir perfil | Pendentes / LinkedIn | abre o perfil no LinkedIn, em nova aba | **não clica** (site externo): exige href `https://` absoluto, `target="_blank"` e `rel="noopener"` |
| Abrir Rascunhos do Gmail | Pendentes / E-mails (modo `gmail_rascunho`) | abre os rascunhos do Gmail, em nova aba | igual ao Abrir perfil |
| Abrir a vaga | Pendentes / Decisões suas | abre a vaga, em nova aba | igual ao Abrir perfil |
| Rodapé: LinkedIn, GitHub, Dar uma estrela no projeto | rodapé (todas) | abre o perfil e o repositório do autor, em nova aba | igual ao Abrir perfil |

Responderam e Follow-ups com data não têm elemento clicável, só leitura. Os gráficos têm dicas ao passar o mouse, sem clique. O `painel/index.html` aberto direto do disco só mostra a instrução do `/painel`, sem nenhum clicável além do rodapé (cenário A).
