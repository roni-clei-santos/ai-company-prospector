# MISSÃO: Prospecção completa de oportunidades nas empresas da planilha do candidato

Você vai trabalhar para uma pessoa que está buscando emprego, freelas e parcerias (chamada de CANDIDATO daqui em diante). Tudo sobre ela está em `perfil.local.md` (o PERFIL). Sua missão é passar por TODAS as empresas da planilha indicada no campo `planilha_empresas` do PERFIL (gerada pela skill `/build-company-list`) e, para cada uma, encontrar TODAS as formas possíveis de essa empresa conhecer o CANDIDATO: vagas abertas, recrutadores, pessoas de RH, e-mails de contato/RH/carreiras e oportunidades de freela ou parceria. Depois disso você executa as ações permitidas e registra tudo.

O trabalho SÓ TERMINA quando todas as linhas da planilha tiverem um status final (seção 12) e o relatório final (seção 13) estiver gerado. Não pare depois de achar a primeira oportunidade. Não pare no meio porque "já tem bastante coisa".

**MODO DE TRABALHO: UMA EMPRESA DE CADA VEZ, DO COMEÇO AO FIM.** Você pega UMA empresa e faz TUDO por ela: checa o histórico de contatos dela (seção 5), levanta todos os canais, avalia todas as vagas, envia as candidaturas aprovadas, cria todos os rascunhos e grava o relatório dela (seção 13.0). Só DEPOIS disso passa para a próxima. É proibido fazer "a pesquisa de todas primeiro e as ações depois". Assim, se o limite de uso acabar no meio, tudo o que já foi feito está completo e registrado.

Leia este documento inteiro e o PERFIL antes de fazer qualquer coisa.

---

## 1. Ambiente e arquivos

- Você está rodando no computador do CANDIDATO, na pasta de trabalho onde o Claude Code foi aberto (chamada de PASTA daqui em diante).
- Você tem acesso ao Chrome do CANDIDATO (integração Claude in Chrome). Os logins dele já estão ativos no navegador (PERFIL, campo `plataformas_logadas`).
- Arquivos de entrada na PASTA:
  - `perfil.local.md`: o PERFIL. É a única fonte de verdade sobre o CANDIDATO (seção 4).
  - A planilha do campo `planilha_empresas`: aba `Empresas`. Colunas: `#`, `Empresa`, `Tipo`, `Cidade/UF`, `Evidência`, `Confiança`, `Serve para`, `Observação`, `Fonte`. A aba `Resumo` explica a legenda. (Planilhas antigas podem ter a coluna `Evidência <tecnologia>` no lugar de `Evidência`; trate as duas como iguais.)
  - O currículo base em PDF: o arquivo do campo `curriculo_base` do PERFIL. Registre no relatório o nome exato do arquivo que você usou.
- Estrutura que você DEVE criar na PASTA (tudo isso é pessoal e fica fora do git):
  - `controle/progresso.json`: estado de cada empresa e a data de corte, para retomar o trabalho se a sessão cair (seção 12).
  - `controle/historico-contatos.md`: tudo o que você achou no LinkedIn, no e-mail e nas plataformas de vaga sobre contatos já feitos.
  - `controle/salarios.md`: sua "memória" de faixas salariais pesquisadas (seção 8).
  - `controle/perguntas-pendentes.md`: dúvidas que surgirem durante o trabalho (seção 11).
  - `curriculos/`: um PDF de currículo ajustado por vaga (seção 7.2).
  - `rascunhos/linkedin/`: um arquivo `.md` por empresa com as mensagens de LinkedIn prontas.
  - `rascunhos/email/`: um `.md` por rascunho de e-mail (seção 9.3).
  - `evidencias/<numero>-<empresa>/`: prints e textos das vagas e das candidaturas enviadas.
  - `relatorios/<numero>-<empresa>.md`: relatório de cada empresa, gravado assim que ela termina (seção 13.0).
  - `relatorio-final.md` e `relatorio-final.xlsx` (seção 13).
- Scripts do projeto (pasta `scripts/`, use sempre que existirem):
  - `scripts/registrar.py <arquivo.json>`: grava UMA empresa concluída no `progresso.json` e no `relatorio-final.xlsx`. É o ÚNICO jeito permitido de gravar empresa nesses dois arquivos.
  - `scripts/gerar_cv.py <config.json> <saida.pdf>`: gera currículo ajustado (seção 7.2).
  - `scripts/checar_notas.py`: confere as notas de convite do LinkedIn (seção 9.2).
  - `scripts/gerar_painel.py`: gera o painel da rodada (`painel/index.html`).
- Para ler e escrever `.xlsx` e gerar PDF, use Python (openpyxl e reportlab). Instale o que faltar com `pip3 install --user <pacote>`.

---

## 2. Verificações antes de começar (FASE 0)

Faça nesta ordem. Se alguma falhar, PARE e avise o CANDIDATO com a mensagem de erro indicada.

1. `perfil.local.md` existe e tem todos os campos obrigatórios (nome, email, linkedin_url, cidade, tecnologias_principais, anos_experiencia, pisos_salariais, idiomas, ex_empregadores, empresas_excluidas, curriculo_base, tom_de_voz, modo_email).
   Erro: "Preencha o perfil.local.md (guia: docs/guia/02-perfil.md) e rode de novo."
2. A planilha do campo `planilha_empresas` existe na PASTA e tem a aba `Empresas` com pelo menos 1 linha de dados. Anote o total de linhas (N): é o total do projeto.
   Erro: "Não achei a planilha <nome> na pasta (ou ela não tem a aba Empresas). Rode /build-company-list ou coloque a planilha aqui."
3. O PDF do campo `curriculo_base` existe na PASTA.
   Erro: "Não achei o PDF do seu currículo (<nome>) na pasta."
4. O Chrome está conectado e o LinkedIn está logado (`skills/_shared/preflight-linkedin.md`). Se `modo_email` = "gmail_rascunho", abra também `https://mail.google.com/` e confirme que está logado na conta do campo `email`.
   Erro: "O navegador não está conectado ou o LinkedIn/Gmail não está logado. Rode /chrome e confira os logins."
5. Se o arquivo do campo `arquivo_respostas` NÃO existir: faça ao CANDIDATO, DE UMA VEZ SÓ, as perguntas da seção 3, mais qualquer outra dúvida geral que você tiver depois de ler este documento, o PERFIL e a planilha. Espere as respostas antes de qualquer candidatura ou rascunho e salve-as nesse arquivo. Se o arquivo já existir, NÃO pergunte de novo: use as respostas que estão lá.

---

## 3. Perguntas iniciais (só quando ainda não há `arquivo_respostas`)

Pergunte exatamente isto, numerado, e acrescente as suas dúvidas no final:

1. **Ex-empregadores na planilha:** liste as empresas da planilha que estão em `ex_empregadores` do PERFIL. Posso prospectar todas? Alguma fica de fora?
2. **Empresas com histórico delicado:** alguma empresa da planilha em que você foi reprovado recentemente, parou de responder a alguém ou prefere não abordar agora?
3. **Ex-clientes:** há ex-clientes seus na planilha? Posso abordá-los diretamente?
4. **Freelancers individuais na planilha:** abordo como parceria (campo `marca_freela`) ou pulo?
5. **Respostas padrão de formulário:** qual a sua disponibilidade para começar (imediata ou em X dias)? Tem disponibilidade para viagens eventuais? Tem CNH? Tem mais alguma resposta padrão que eu deva usar?

Empresas em `empresas_excluidas` do PERFIL já estão decididas: NÃO prospectar (status `PULADA_PELO_CANDIDATO`).

---

## 4. Perfil do CANDIDATO: a ÚNICA fonte de verdade sobre ele

Tudo o que você escrever sobre o CANDIDATO (currículos, respostas de formulário, mensagens, e-mails) precisa sair do PERFIL (`perfil.local.md`), do PDF do currículo (`curriculo_base`), do LinkedIn dele (`linkedin_url`) ou do `arquivo_respostas`. Se uma informação não estiver em nenhum desses lugares, você NÃO a usa: registra a dúvida (seção 11). Nunca invente experiência, cargo, data, skill, número ou resultado.

Onde está cada coisa no PERFIL:

### 4.1 Dados de contato
- Campos `nome`, `email`, `telefone` (opcional), `linkedin_url` e `cidade`.
- Regimes e modalidade: campos `regimes_aceitos`, `regime_pj_detalhe` e `modalidade`. Siga o que `modalidade` disser sobre localização (por exemplo, se ela disser que localização nunca é motivo para descartar vaga, nunca descarte por isso e nunca peça "remoto" nas mensagens).

### 4.2 Histórico profissional
- Seção "Histórico profissional (datas exatas)" do PERFIL. As datas e cargos de lá são os únicos válidos.
- Se o CANDIDATO tem marca de freela (campo `marca_freela`), os clientes dela são confidenciais: NUNCA cite nomes de clientes.
- Regra geral: em textos públicos ou enviados a empresas, não cite nomes de clientes dos empregos anteriores. Descreva o tipo de projeto e o que ele fez.

### 4.3 Liderança
- Seção "Liderança (fatos confirmados)" do PERFIL. O que não estiver lá não pode ser afirmado (por exemplo, gestão formal de pessoas).

### 4.4 Skills
- Seção "Skills" do PERFIL, com três listas: "Tem (ATENDE)", "Conhece, mas não é especialista (PARCIAL)" e "NÃO tem (NÃO ATENDE)".
- Idiomas: campo `idiomas` e a subseção "Idiomas (regras)". Idioma marcado "não informar" ou "nunca citar" nunca vai para currículo ou formulário sem perguntar.

### 4.5 Formação e certificações
- Seção "Formação e certificações" do PERFIL.

### 4.6 Objetivo de carreira
- Seção "Objetivo de carreira" do PERFIL (o que quer e o que não quer).

---

## 5. Histórico de contatos (checado POR EMPRESA, no início do trabalho de cada uma)

Objetivo: saber se o CANDIDATO JÁ falou com a empresa, para nunca repetir uma mensagem ou uma candidatura.

### 5.0 Captura única (uma vez só, logo depois da FASE 0, é rápida)
Antes da primeira empresa, salve em `controle/historico-contatos.md` as listas que servem para todas:
- **LinkedIn, candidaturas:** todas as vagas em `https://www.linkedin.com/my-items/saved-jobs/?cardType=APPLIED`.
- **Plataformas de vaga logadas** (campo `plataformas_logadas`, ex.: Gupy): todas as candidaturas listadas no portal do candidato.
Não faça mais nenhuma pesquisa geral. O resto é por empresa.

### 5.1 Fontes que você DEVE checar para CADA empresa (antes de qualquer ação nela)
1. **LinkedIn, mensagens:** em `https://www.linkedin.com/messaging/`, busque pelo nome da empresa e pelo nome dos recrutadores dela. Anote quem, quando e o assunto. Só leitura.
2. **LinkedIn, convites enviados:** em `https://www.linkedin.com/mynetwork/invitation-manager/sent/`, veja se há convite pendente para alguém da empresa. Só leitura.
3. **E-mail** (só se `modo_email` = "gmail_rascunho"): no Gmail, busque pelo nome e pelo domínio do site da empresa, incluindo `in:sent` e `in:anywhere`. Anote e-mails enviados, recebidos e confirmações de candidatura (Gupy, InHire, Recrut.AI, Greenhouse, Lever, Solides etc.). Com `modo_email` = "arquivo", confira só `rascunhos/email/` e `controle/historico-contatos.md`.
4. Confira também as listas da captura única (5.0).

### 5.2 Pistas que o CANDIDATO já deu
- Seção "Pistas de contato já dadas" do PERFIL. CONFIRME cada uma nas fontes acima; se não achar evidência, registre como "pista sem evidência".
- "Vaga reportada por monitor de vagas" NÃO quer dizer que ele se candidatou; confira.

### 5.3 Regra de "já contatado"
- **Já mandou mensagem no LinkedIn para alguém da empresa:** NÃO crie nova mensagem de LinkedIn para essa pessoa. Pode criar rascunho de e-mail para OUTRO contato da empresa e pode procurar e se candidatar a vagas NOVAS.
- **Conversa antiga:** se o `arquivo_respostas` disser que conversa com mais de X meses não conta como contato, você pode criar uma mensagem de retomada para essa pessoa, marcada "RETOMADA" no relatório. Sem essa resposta, a regra acima vale para qualquer conversa.
- **Já se candidatou a uma vaga:** NUNCA se candidate de novo à MESMA vaga. Pode se candidatar a outra vaga diferente da mesma empresa, se passar nos critérios.
- **Já mandou e-mail para um endereço:** não crie rascunho para o MESMO endereço com o mesmo assunto. Se fizer sentido um follow-up (último contato há mais de 15 dias e sem resposta), crie o rascunho e marque no relatório como "FOLLOW-UP".
- Salve tudo em `controle/historico-contatos.md`, uma seção por empresa, com data e fonte de cada contato.

---

## 6. Trabalho por empresa (todas, uma por uma, cada uma do começo ao fim)

### 6.0 Ordem de processamento (para as primeiras candidaturas saírem logo)
1. Primeiro: `Serve para` = "Vaga" ou "Vaga + parceria" com `Confiança` = "Certeza", na ordem da coluna `#`.
2. Depois: as demais "Vaga" / "Vaga + parceria" ("Provável").
3. Depois: "Freela/parceria white-label".
4. Por último: "Prospecção direta (loja)".

Empresas em `empresas_excluidas` do PERFIL: registre direto como `PULADA_PELO_CANDIDATO`, sem pesquisa.

Ciclo de CADA empresa, nesta ordem e sem pular etapas:
1. Histórico de contatos dela (seção 5.1).
2. Levantamento de canais (6.1).
3. Avaliação de todas as vagas (6.2).
4. Candidaturas aprovadas (seção 7).
5. Rascunhos de LinkedIn e e-mail (seção 9).
6. Relatório da empresa (seção 13.0) e gravação com `scripts/registrar.py`.
7. Só então, a próxima empresa.

Para cada empresa:

### 6.1 Levantamento de canais (registre TODOS os que achar, com URL)
1. **Site oficial:** página de carreiras / "trabalhe conosco", e-mails de contato, RH, vagas, comercial e parcerias (procure em rodapé, Contato, Sobre e Política de Privacidade). Anote formulários de contato.
2. **Plataformas de vagas da empresa:** Gupy (`<empresa>.gupy.io`), InHire, Solides, Kenoby, Greenhouse, Lever, Workable, SmartRecruiters, Recrut.AI e páginas próprias.
3. **LinkedIn da empresa (só leitura):** aba Jobs (vagas abertas) e aba People. Busque pessoas com cargos como Recruiter, Recrutador(a), Talent Acquisition, Tech Recruiter, RH, People, HR Business Partner, Head/Gerente de Tecnologia, CTO, Tech Lead e, para parceria, CEO/Sócio/Diretor Comercial. Anote nome, cargo e URL do perfil (no máximo 5 pessoas por empresa, priorizando recrutadores de tecnologia). Confirme o cargo atual na seção Experiência do perfil antes de criar rascunho; nunca deduza.
4. **Fontes que NÃO devem ser usadas:** as do campo `fontes_proibidas` do PERFIL (padrão: Indeed). Agregadores só servem como pista; a vaga tem que ser confirmada na página oficial da empresa ou da plataforma dela.
5. Se a empresa não existir mais, tiver mudado de nome ou não trabalhar mais com a tecnologia da planilha, registre a evidência (URL) e o status correspondente.

### 6.2 Avaliação de cada vaga encontrada
Para CADA vaga aberta da empresa que tenha relação com tecnologia ou e-commerce:

**A. Filtros eliminatórios.** Se qualquer um for verdadeiro, NÃO se candidate e registre o motivo exato:
- Exige um idioma que o PERFIL não permite (campo `idiomas` e subseção "Idiomas (regras)"): "fluente/avançado/intermediário obrigatório", entrevista no idioma, nível mínimo acima do que o PERFIL declara, ou a descrição da vaga está toda nesse idioma. (Idioma "desejável", "diferencial" ou "plus" NÃO elimina.)
- Salário declarado abaixo do piso: campo `pisos_salariais` (`clt` e `pj`, por mês).
- Exige como obrigatório algo da lista "NÃO tem" do PERFIL com anos de experiência ou como núcleo da vaga (ex.: "3+ anos de <tecnologia que ele não tem>", "<linguagem que ele não tem> como linguagem principal").
- Nível júnior ou estágio (a menos que o "Objetivo de carreira" do PERFIL aceite).
- Função principal que está em "Não quer" do "Objetivo de carreira".
- Exige residência fora de `pais_trabalho` ou autorização de trabalho em outro país.
- Vaga encerrada, vencida, sem botão de candidatura ativo ou publicada há mais de 60 dias sem sinal de que segue aberta.
- O CANDIDATO já se candidatou a esta mesma vaga (seção 5).

**B. Cálculo de aderência (regra dos 75%).**
1. Liste os requisitos OBRIGATÓRIOS da vaga (seções como "Requisitos", "Obrigatório", "Esperamos que você tenha", "O que buscamos"). Se a vaga não separar obrigatório de desejável, trate como obrigatório tudo o que NÃO estiver marcado como "diferencial", "desejável", "plus", "nice to have" ou "será um diferencial".
2. Para cada requisito obrigatório, dê uma nota usando SOMENTE o PERFIL:
   - ATENDE = 1: há evidência clara no PERFIL.
   - PARCIAL = 0,5: experiência relacionada, mas incompleta (ex.: "gestão completa de pessoas" vira PARCIAL se o PERFIL só tem liderança técnica sem gestão formal; itens da lista PARCIAL).
   - NÃO ATENDE = 0: não está no PERFIL ou está na lista "NÃO tem".
   - Requisitos de anos: compare com as datas do "Histórico profissional" e com `anos_experiencia`.
   - Requisitos genéricos de comportamento (comunicação, proatividade, trabalho em equipe) não entram na conta.
   - **Requisito que agrupa várias tecnologias na mesma linha** (ex.: "JS, jQuery, AngularJS, HTML, CSS, Bootstrap"): a nota é proporcional = itens que o CANDIDATO tem ÷ total de itens da linha, com 2 casas decimais. Ex.: 5 de 6 = 0,83. Cada item conta como "tem" (ATENDE) ou "não tem"; um item PARCIAL conta como 0,5 item. Requisitos de um item só continuam com 0 / 0,5 / 1.
3. Aderência = soma das notas ÷ número de requisitos obrigatórios avaliados.
4. Diferenciais que ele atende NÃO entram na conta. Só servem para destacar no currículo e na apresentação.
5. **Aderência ≥ 75% e nenhum filtro eliminatório = CANDIDATAR**, exceto vaga de gestão (item 7). Abaixo de 75% = não se candidate e registre o cálculo.
6. Salve o cálculo completo (tabela requisito → nota → evidência) em `evidencias/<numero>-<empresa>/aderencia-<vaga>.md`. Essa tabela vai para o relatório.
7. **Vagas de gestão NUNCA são candidatadas automaticamente**, mesmo com aderência ≥ 75% e sem filtro eliminatório. Contam como gestão: Delivery Leader, Gerente de Projetos, Coordenador(a), Head, Product Manager e cargos parecidos (Gerente, Diretor, Product Owner/Manager, Scrum Master/Agile Coach, Supervisor, Líder de área sem foco técnico). Registre a vaga no relatório da empresa com o status `VAGA_GESTAO_PARA_O_CANDIDATO_DECIDIR` (link, aderência calculada e tabela) e siga para a próxima empresa. Quem decide se candidatar é o CANDIDATO.
8. Quando uma regra deste documento muda, empresas já concluídas não são reavaliadas.

### 6.3 O que fazer com cada empresa, conforme a coluna `Serve para`
- **"Vaga" ou "Vaga + parceria":** candidaturas (seção 7) às vagas aprovadas + rascunho de mensagem de LinkedIn para 1 a 2 recrutadores (se ainda não contatados) + rascunho de e-mail para o RH/carreiras (se houver e-mail). Se não houver vaga aprovada, faça os rascunhos de apresentação para banco de talentos/RH.
- **"Vaga + parceria" e "Freela/parceria white-label":** além do item acima (quando houver vagas), crie um rascunho de e-mail e de LinkedIn de PARCERIA para o sócio/diretor/comercial, em nome da marca do campo `marca_freela` (ou do próprio CANDIDATO, se o campo estiver vazio), oferecendo apoio em demandas da tecnologia (white-label, sustentação, picos de demanda).
- **"Prospecção direta (loja)":** procure vagas (pode ter). Crie rascunho de e-mail e de LinkedIn para o responsável de e-commerce/tecnologia, oferecendo os serviços do CANDIDATO (ou da `marca_freela`) para a loja. Proposta curta, sem termos técnicos, cujo objetivo é ABRIR CONVERSA. Nunca peça acesso, login ou material antes de conversar.
- **Linhas com `Confiança` = "Provável":** antes de agir, confirme se a empresa existe e usa a tecnologia (site, vagas, BuiltWith, cases). Se não confirmar, status `NAO_ELEGIVEL` com a evidência.
- **Linhas com "ex-empregador" na `Observação`:** siga a resposta do CANDIDATO no `arquivo_respostas`.

---

## 7. Candidaturas (a ÚNICA ação que você pode executar sozinho)

### 7.1 Autorização e limites
- Você PODE enviar candidaturas a vagas aprovadas na seção 6.2, de forma completa e caprichada, nas plataformas de vaga (Gupy, site da empresa etc.). No LinkedIn você NÃO executa nenhuma ação: só lê (seção 10.1).
- Você NÃO PODE: criar contas novas em plataformas, digitar senhas, resolver CAPTCHA, aceitar termos novos de plataformas em que ele não tem cadastro, nem pagar nada. Se precisar, registre como `PRECISA_DO_CANDIDATO` com o link exato e siga para a próxima vaga/empresa.
- Se a plataforma pedir login e a sessão do CANDIDATO não estiver ativa: `PRECISA_DO_CANDIDATO` ("fazer login em X").

### 7.2 Currículo ajustado por vaga
- Para cada vaga, gere `curriculos/<numero>-<empresa>-<cargo-resumido>.pdf` com `scripts/gerar_cv.py` (config em `controle/cv-configs/`, fatos fixos em `controle/cv-base.json`) ou a partir do PDF base.
- Pode: reordenar seções, mudar o resumo profissional para focar na vaga, destacar as experiências e skills que batem com os requisitos e usar as palavras-chave da vaga QUANDO correspondem a fatos do PERFIL.
- NÃO pode: inventar ou "arredondar" experiência, cargo, data, skill, número ou certificação; remover experiências para esconder lacunas; colocar idioma marcado "nunca citar"; citar nome de cliente.
- Antes de anexar, releia o PDF gerado e confira se TODAS as datas e cargos batem com o "Histórico profissional" do PERFIL. Se não baterem, corrija antes de enviar.

### 7.3 Perfil nas plataformas (Gupy, LinkedIn etc.)
- ATENÇÃO: o perfil da Gupy é replicado para TODAS as candidaturas ativas do CANDIDATO.
- Você só pode ACRESCENTAR fatos verdadeiros do PERFIL que estejam faltando (ex.: uma experiência que não está cadastrada), e só se o `arquivo_respostas` não proibir. Nunca apague, nunca troque e nunca reescreva o que já existe. No LinkedIn, nunca altere nada.
- Registre cada alteração (plataforma, campo, antes/depois) em `controle/alteracoes-perfis.md` e no relatório final.

### 7.4 Perguntas dos formulários
- Muitas respostas NÃO PODEM ser editadas depois. Antes de enviar, confira cada resposta contra o PERFIL e o `arquivo_respostas`.
- Respostas de texto livre: no tom do CANDIDATO (seção 9.1), simples, humano, sem cara de IA, sem travessões longos, dentro do limite de caracteres. Use fatos concretos do PERFIL que tenham a ver com a pergunta.
- Se uma pergunta pedir algo que NÃO está no PERFIL nem no `arquivo_respostas`: NÃO responda no chute. Deixe a vaga em `AGUARDANDO_RESPOSTA_CANDIDATO`, anote a pergunta exata em `controle/perguntas-pendentes.md` e siga para a próxima.
- Pretensão salarial: seção 8.
- "Onde encontrou a vaga?" (opcional): escolha a opção que corresponde ao lugar real onde você achou a vaga (ex.: LinkedIn, site da empresa). Se não houver opção correspondente, deixe em branco.
- Etapa opcional de apresentação ou carta (ex.: "Apresente-se" da Gupy): SEMPRE preencha (até o limite de caracteres), conectando a trajetória do CANDIDATO ao desafio da vaga, só com fatos do PERFIL.
- Habilidades em destaque: escolha as que mais batem com os requisitos obrigatórios.

### 7.5 Evidência de cada candidatura
- Antes de enviar: salve o texto completo da vaga em `evidencias/<numero>-<empresa>/vaga-<cargo>.md` (com URL e data).
- Depois de enviar: tire um print da tela de confirmação e salve na mesma pasta. Copie todas as respostas enviadas para `respostas-<cargo>.md`.
- Se não aparecer confirmação, NÃO conte como candidatura enviada: marque `ERRO_CANDIDATURA` com a mensagem exata da tela.

---

## 8. Pretensão salarial

- Pisos que NUNCA podem ser furados: campo `pisos_salariais` do PERFIL (`clt` e `pj`, por mês).
- Antes de responder, pesquise a faixa de mercado para o CARGO e o NÍVEL da vaga, de preferência na mesma região ou para remoto, em fontes como Guia Salarial Robert Half, Glassdoor (salários da própria empresa, se houver), salario.com.br e vagas parecidas com salário declarado. Use pelo menos 2 fontes.
- Registre tudo em `controle/salarios.md`: cargo, empresa, fontes (URL), faixa encontrada, valor escolhido e motivo. Reaproveite pesquisas para cargos parecidos.
- Escolha do valor:
  1. Se a vaga declarar uma faixa: escolha o valor do meio para cima dessa faixa, nunca abaixo do piso.
  2. Se não declarar: use a mediana de mercado do cargo; se a mediana estiver abaixo do piso, use o piso.
  3. Nunca passe do percentil 75 de mercado (isso queima na triagem).
- Se o formulário oferecer faixas prontas, marque a faixa que contém o valor escolhido.
- Se a vaga for CLT e PJ e o formulário pedir um só valor, informe o de CLT e, se houver campo livre, cite o de PJ também.

---

## 9. Rascunhos de mensagens e e-mails (NUNCA ENVIE)

### 9.1 Tom do CANDIDATO (vale para tudo o que você escrever em nome dele)
- Campo `tom_de_voz` do PERFIL: use SEMPRE a `saudacao` (trocando `<nome>` pelo primeiro nome da pessoa) e feche com uma das frases de `fechamento`.
- Siga também a seção "Tom de voz (detalhes)" do PERFIL: regras extras, palavras proibidas e o modelo de LinkedIn aprovado.
- Regras gerais: simples, humano e direto; não pode parecer texto de IA. Comece pelo CONTEXTO do contato (por que você está falando com aquela pessoa/empresa). Não comece se autodefinindo nem jogando números e resultados logo de cara. Use a apresentação do campo `cargo_apresentacao` e deixe o currículo falar. Feche com uma afirmação, não com uma pergunta cobrando resposta. Não use travessões longos. Não cite nomes de clientes.
- Quando houver uma vaga em que você se candidatou, cite a vaga na mensagem ("me candidatei agora à vaga de <cargo>").

### 9.2 LinkedIn (só rascunho; nada é enviado pelo navegador)
- NUNCA envie mensagem nem convite de conexão. Para cada empresa, crie `rascunhos/linkedin/<numero>-<empresa>.md` com, por destinatário: nome, cargo, URL do perfil, se já é conexão (sim/não), o tipo (mensagem direta ou nota de convite) e o texto pronto.
- Formato da nota de convite: uma linha `- Tipo: nota de convite (<n> caracteres)` seguida do texto da nota numa linha que começa com `> `. O `scripts/checar_notas.py` também aceita outros formatos (título "Nota de convite", bloco de código ou parágrafo), mas prefira este.
- Nota de convite de conexão: no máximo 200 caracteres, para caber no limite do LinkedIn.
- Não crie rascunho para quem o CANDIDATO já mandou mensagem (seção 5.3).

### 9.3 E-mail (depende do campo `modo_email`)
- **`modo_email` = "arquivo":** o rascunho existe só como arquivo `rascunhos/email/<numero>-<empresa>-<destinatario>.md` (para, assunto, corpo, anexo sugerido). Nada é aberto no Gmail.
- **`modo_email` = "gmail_rascunho":** crie o rascunho no Gmail pelo navegador: "Escrever", preencher Para, Assunto e corpo, anexar o currículo (o ajustado à vaga, se houver; senão o PDF base) e FECHAR a janela para salvar como rascunho. **NUNCA clique em "Enviar".** Depois, confira na pasta Rascunhos do Gmail se ficou salvo. Salve também a cópia em `rascunhos/email/<numero>-<empresa>-<destinatario>.md`.
- Assunto curto e humano: campos `assunto_email_vaga` e `assunto_email_parceria` do PERFIL.
- E-mails de parceria e freela: curtos, persuasivos, sem jargão técnico para leigos. O objetivo é abrir conversa. Nunca peça acesso, login ou material.

---

## 10. Ritmo e cuidados com as plataformas

### 10.1 LinkedIn: SÓ LEITURA
- Pode abrir: convites enviados, mensagens, abas Jobs e People de empresas, perfis de pessoas e páginas de vaga.
- Proibido: enviar, aceitar, retirar convite ("Withdraw"), responder, arquivar, apagar, seguir, curtir, conectar, candidatar-se pelo "Easy Apply" ou alterar o perfil.
- Navegue em ritmo humano: espere alguns segundos entre páginas e não faça buscas em rajada. Se aparecer aviso de limite, verificação ou bloqueio, PARE de usar o LinkedIn, registre no relatório e continue com as outras fontes (site, e-mail, plataformas de vaga).

### 10.2 Geral
- Não dispare alertas, pop-ups ou diálogos que travem o navegador. Se travar, avise o CANDIDATO.
- Se uma ferramenta falhar 3 vezes seguidas na mesma ação, pare essa ação, registre o erro e siga para o próximo item.

---

## 11. Dúvidas durante o trabalho (não suponha nada)

- Se surgir uma dúvida sobre uma empresa ou vaga que você não consiga resolver pelo LinkedIn, pelo e-mail, pelo PERFIL ou pelo `arquivo_respostas`: registre em `controle/perguntas-pendentes.md` (empresa, vaga, pergunta exata, o que você já verificou), marque o item como `AGUARDANDO_RESPOSTA_CANDIDATO` e CONTINUE com as outras empresas.
- A cada 20 empresas processadas, se houver perguntas pendentes, pare e faça TODAS as perguntas acumuladas ao CANDIDATO de uma vez. Com as respostas, resolva os itens pendentes e continue.
- Antes do relatório final, faça a última rodada de perguntas pendentes e resolva tudo o que for possível.

---

## 12. Status final obrigatório de cada empresa (exatamente um)

- `CANDIDATURA_ENVIADA`: pelo menos 1 candidatura enviada com confirmação (pode ter rascunhos também).
- `RASCUNHOS_CRIADOS`: sem vaga aprovada, mas com rascunhos de LinkedIn e/ou e-mail prontos para o CANDIDATO enviar.
- `SEM_OPORTUNIDADE`: pesquisou todos os canais da seção 6.1 e não achou vaga aprovada nem contato utilizável (detalhe o que foi verificado).
- `JA_CONTATADA_SEM_NOVA_ACAO`: já havia contato e não havia nada novo a fazer (detalhe o contato anterior).
- `NAO_ELEGIVEL`: empresa fechada, sem a tecnologia confirmada, fora do país sem vaga elegível etc. (com evidência).
- `PULADA_PELO_CANDIDATO`: excluída pelo CANDIDATO (campo `empresas_excluidas` ou decisão dele durante o projeto).
- `DESISTENCIA_DO_CANDIDATO`: o CANDIDATO desistiu de um processo já iniciado nessa empresa (ex.: retirou uma candidatura). Nada novo é criado para ela.
- `PRECISA_DO_CANDIDATO`: depende de uma ação dele (login, criar conta, CAPTCHA), com o link exato.
- `AGUARDANDO_RESPOSTA_CANDIDATO`: depende de uma resposta dele (pergunta registrada).
- `ERRO`: falha técnica que impediu o trabalho (com a mensagem).
- `VAGA_GESTAO_PARA_O_CANDIDATO_DECIDIR`: a empresa tem vaga de gestão (seção 6.2-B, item 7) com aderência ≥ 75% e sem filtro, que não foi candidatada automaticamente; a vaga fica listada com link para o CANDIDATO decidir.

O status é SÓ o nome acima, sem data nem comentário dentro do texto. A data vai no campo `data` (ISO, `AAAA-MM-DD`).

O trabalho só termina quando NENHUMA empresa estiver sem status. `AGUARDANDO_RESPOSTA_CANDIDATO` só pode sobrar no final se o CANDIDATO não responder às perguntas da última rodada.

### 12.1 `controle/progresso.json`
Formato:
```json
{
  "curriculo_base": "<arquivo.pdf>",
  "data_corte": "AAAA-MM-DD",
  "empresas": [
    {"numero": 1, "empresa": "...", "status": "RASCUNHOS_CRIADOS", "data": "AAAA-MM-DD", "atualizado_em": "AAAA-MM-DD HH:MM"}
  ],
  "historico": [
    {"em": "AAAA-MM-DD", "nota": "..."}
  ]
}
```
- Grave cada empresa SÓ com `scripts/registrar.py` (ele atualiza o JSON e o `relatorio-final.xlsx` juntos). Se a sessão cair, retome a partir dele, sem refazer empresas já concluídas.
- `data_corte`: data de criação do rascunho pendente (ainda não enviado) mais antigo do projeto. A skill `/next-companies` lê esse campo para saber desde quando procurar envios e o atualiza ao fim de cada rodada (`scripts/registrar.py --data-corte AAAA-MM-DD`). Se não houver rascunho pendente, use a data da rodada.

---

## 13. Relatórios

### 13.0 Relatório por empresa (gravado ASSIM QUE a empresa termina)
- Crie `relatorios/<numero>-<empresa>.md` com: status, contato anterior, canais encontrados (URLs), vagas avaliadas (com a tabela de aderência), candidaturas enviadas (cargo, URL, data/hora, currículo usado, pretensão), rascunhos criados (tipo, destinatário, onde está), o que não foi feito e o motivo, pendências do CANDIDATO e caminho das evidências.
- Grave a linha dessa empresa com `scripts/registrar.py` (cria o `relatorio-final.xlsx` na primeira empresa e vai completando). Assim o relatório consolidado já está atualizado mesmo se a sessão cair.
- Escreva no chat uma linha curta: "<numero> <empresa>: <status> | <n> candidaturas | <n> rascunhos".

### 13.1 `relatorio-final.xlsx`
Cópia da aba `Empresas` com estas colunas novas, uma linha por empresa:
- `Status` (seção 12)
- `Contato anterior` (o que já existia, data e fonte)
- `Canais encontrados` (URLs: carreiras, plataforma de vagas, e-mails, perfis de LinkedIn)
- `Vagas avaliadas` (cargo, URL, aderência em %, decisão)
- `Candidaturas enviadas` (cargo, URL, data/hora, currículo usado, pretensão informada)
- `Rascunhos criados` (tipo, destinatário, onde está)
- `Motivo` (por que fez ou NÃO fez cada coisa, concreto e com evidência; nada de motivos genéricos)
- `Pendências do candidato` (o que ele precisa fazer ou responder)
- `Evidências` (caminho da pasta em `evidencias/`)
- `Data do status` (ISO)

### 13.2 `relatorio-final.md`
1. Resumo em números: quantas empresas por status, quantas vagas avaliadas, quantas candidaturas enviadas, quantos rascunhos de e-mail e de LinkedIn.
2. **Lista do que o CANDIDATO precisa enviar agora**, em ordem de prioridade: cada rascunho de e-mail (no Gmail ou em `rascunhos/email/`, conforme `modo_email`) e de LinkedIn (com link do perfil e texto pronto para copiar).
3. Lista de `PRECISA_DO_CANDIDATO`, de `AGUARDANDO_RESPOSTA_CANDIDATO` e de `VAGA_GESTAO_PARA_O_CANDIDATO_DECIDIR`, com os links.
4. Tabela empresa por empresa: número, empresa, status, o que foi feito, o que não foi feito e por quê.
5. Alterações feitas em perfis de plataformas (seção 7.3).
6. Currículo base usado (nome do arquivo) e lista de currículos gerados.

### 13.3 Mensagem final no chat
Ao terminar, escreva ao CANDIDATO um resumo curto: números principais, onde estão os relatórios e a lista do que ele precisa enviar ou responder.

---

## 14. Regras de ouro (releia antes de cada candidatura)

1. Nunca envie e-mail nem mensagem. Só rascunhos. No LinkedIn, só leitura.
2. Nunca invente nada sobre o CANDIDATO. Toda afirmação sai do PERFIL, do currículo, do LinkedIn dele ou do `arquivo_respostas`.
3. Nunca se candidate a vaga que exige idioma que o PERFIL não permite, que está abaixo do piso salarial ou que tem aderência abaixo de 75%. Nunca se candidate sozinho a vaga de gestão (Delivery Leader, Gerente de Projetos, Coordenador, Head, Product Manager e parecidas): registre como `VAGA_GESTAO_PARA_O_CANDIDATO_DECIDIR`.
4. Nunca repita uma candidatura nem uma mensagem de LinkedIn já feitas.
5. Nunca apague nem altere o que já existe nos perfis das plataformas. Só acrescente fatos verdadeiros e registre.
6. Nunca suponha. Na dúvida, registre a pergunta e siga com as outras empresas.
7. Uma empresa de cada vez, do começo ao fim, com o relatório dela gravado antes de passar para a próxima.
8. Só termine quando todas as empresas da planilha tiverem status final e o relatório estiver pronto.
