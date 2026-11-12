# 0. Sem instalar nada (Modo web)

[Próximo: instalação do Claude Code →](01-instalacao.md)

Para quem tem o plano grátis do Claude, ou só quer testar antes de instalar. Tudo acontece numa conversa no [claude.ai](https://claude.ai), no navegador. Você recebe uma planilha Excel com empresas reais que usam a sua tecnologia, com a fonte de cada uma e um rascunho de primeira mensagem por empresa.

## O que você precisa

- Uma conta no claude.ai (a grátis serve).
- **Code execution and file creation** ligado em **Settings > Capabilities** (na versão nova das configurações, o nome é "Create and edit files"). Nos planos Free, Pro, Max e Ultra ele já vem ligado ([fonte](https://support.claude.com/en/articles/12111783)).
- **Web search** ligado: numa conversa, clique no **+** e ligue "Web search". Na interface nova não existe esse botão: o Claude pesquisa sozinho quando precisa ([fonte](https://support.claude.com/en/articles/10684626)).

## Passo a passo

1. Abra o [texto do Modo web](../web/PROMPT-planilha.md) e copie o bloco inteiro (botão de copiar no canto do bloco).
2. Abra uma conversa nova no claude.ai, cole e envie. Um texto longo vira um anexo "PASTED": é normal.
3. O Claude faz 6 perguntas numa mensagem só: tecnologia, país ou região, tipos de empresa, objetivo, empresas a excluir e ex-empregadores. Ele também pergunta o tamanho do lote (até 25). Responda numa mensagem, por exemplo: `1. Magento / Adobe Commerce. 2. Brasil. 3. todos. 4. todos. 5. nenhuma. 6. nenhum. Lote: 25.`
4. Espere a pesquisa. Ao fim, baixe o arquivo `empresas-<tecnologia>-<país>.xlsx`.

## O que vem na planilha

- Aba **Empresas**: `#`, `Empresa`, `Tipo`, `Cidade/UF`, `Evidência`, `Confiança`, `Serve para`, `Observação`, `Fonte` e `Primeira mensagem (rascunho)`. São as mesmas colunas da planilha do `/build-company-list` ([guia 4](04-planilha.md)), mais o rascunho.
- Aba **Resumo**: as suas respostas, as contagens e as fontes que ficaram de fora.
- **Confiança:** "Certeza" é evidência direta e atual. "Provável" é evidência antiga ou indireta: a linha fica em amarelo, e vale confirmar antes de abordar.
- **Primeira mensagem:** até 300 caracteres, citando a evidência da linha. Onde a mensagem precisa de um dado seu, vem um espaço entre colchetes, como `[seu nome]`: preencha antes de enviar. Nada é enviado por você.

## Para mais empresas

Abra uma conversa nova, cole o mesmo texto e **anexe a planilha que você baixou**. O Claude lê as empresas que já estão nela, não repete nenhuma e devolve a planilha completa (antigas + novas).

## Se algo der errado

- **Veio uma tabela em texto, sem arquivo:** a criação de arquivos está desligada. Ligue "Code execution and file creation" em Settings > Capabilities, ou copie a tabela e cole no Excel ou no Google Planilhas (as colunas já vêm separadas).
- **Parou antes de 25:** a pesquisa para quando 3 buscas seguidas não trazem empresa nova. O Resumo diz onde parou.
- **Fontes "ficaram de fora":** alguns sites (diretório de parceiros, Clutch, TheirStack) às vezes bloqueiam a leitura. O Claude anota quais e segue com as outras.
- **Chegou ao limite de uso:** no plano grátis, pesquisa e criação de arquivos contam no limite, que se renova a cada 5 horas. Espere e continue numa conversa nova, com a planilha anexada.

## E depois?

Os nomes das colunas são os mesmos do robô. Se um dia você passar para o Claude Code (plano Pro ou superior), dá para continuar da mesma planilha:

1. Siga o [guia de instalação](01-instalacao.md) e o [do perfil](02-perfil.md).
2. Copie a planilha baixada para a pasta do projeto e ponha o nome dela no campo `planilha_empresas` do `perfil.local.md`.
3. Rode uma vez `python3 scripts/registrar.py --data-corte AAAA-MM-DD`, com a data de hoje (no Windows, `py -3` no lugar de `python3`). Isso cria o `controle/progresso.json`.
4. Siga para o [guia do Chrome](03-chrome.md) e rode `/next-companies`.

Para comparar os caminhos, veja [Qual caminho é o seu?](../../README.md#qual-caminho-é-o-seu).

[Próximo: instalação do Claude Code →](01-instalacao.md)
