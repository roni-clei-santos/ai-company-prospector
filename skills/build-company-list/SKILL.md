---
name: build-company-list
description: Monta a planilha de empresas (empresas-<tecnologia>-<pais>.xlsx) para a prospecção, a partir de fontes públicas com evidência e link, e deixa o controle/progresso.json pronto para o /next-companies. Use quando o usuário digitar /build-company-list (opcional: limite N).
---

# /build-company-list — gerar a planilha real de empresas

Objetivo: montar, para qualquer pessoa, uma planilha de empresas que usam uma tecnologia num país ou região, com evidência e link de fonte em TODA linha. Nada inventado. O resultado alimenta o `/next-companies`.

Parâmetro opcional: `limite N` (ex.: `/build-company-list limite 5`) para parar em N empresas válidas (usado em testes).

## Passo 0 — Preflight

Leia e siga `skills/_shared/preflight.md` (pasta e perfil, Chrome conectado, LinkedIn logado). O LinkedIn aqui é SÓ LEITURA (páginas de empresa, abas Jobs e People, páginas de vaga).

## Passo 1 — Perguntas iniciais (UMA mensagem só)

Leia `perfil.local.md`. Monte UMA mensagem com as 6 perguntas abaixo, numeradas, cada uma com exemplo e, quando o PERFIL tiver o dado, o valor padrão entre colchetes ("[padrão do seu perfil: ...] — responda 'ok' para manter"):

1. **Tecnologia/plataforma** (ex.: "Magento / Adobe Commerce", "VTEX", "Shopify Plus", "SAP Commerce"). Padrão: o primeiro item de `tecnologias_principais`.
2. **País ou região** (ex.: "Brasil", "Portugal", "América Latina", "Sul do Brasil"). Padrão: `pais_trabalho`.
3. **Tipos de empresa desejados** (pode escolher vários, ou "todos"): agências especialistas; consultorias/integradoras grandes; agências multiplataforma; marcas/varejistas que usam a tecnologia; empresas com vaga aberta; internacionais que contratam remoto na região; ecossistema (módulos, plataformas, ferramentas sobre a tecnologia).
4. **Objetivo**: vaga, parceria, freela ou todos.
5. **Empresas a excluir** (ex.: "Empresa X, Empresa Y"). Padrão: `empresas_excluidas`.
6. **Ex-empregadores** (entram na planilha marcados em Observação). Padrão: `ex_empregadores`.

Espere a resposta. Não pesquise antes.

## Passo 2 — Pesquisa (fontes nesta ordem)

Para cada fonte, registre cada empresa encontrada num arquivo de trabalho `controle/empresas-coletadas.json` (lista de objetos com `empresa`, `tipo`, `cidade_uf`, `evidencia`, `confianca`, `serve_para`, `observacao`, `fonte` e, se souber, `site` = site oficial da empresa, usado para achar duplicatas). Grave o arquivo depois de cada fonte, para não perder o trabalho se a sessão cair.

1. **Diretório oficial de parceiros da tecnologia** (ex.: Adobe Solution Partner Directory para Magento/Adobe Commerce; VTEX Partners; Shopify Partners Directory), filtrado pelo país/região.
2. **Clutch**: página da tecnologia no país (ex.: `clutch.co/br/developers/magento`) e nas principais cidades da região.
3. **TheirStack**: página da tecnologia no país (ex.: `theirstack.com/en/technology/magento/br`), empresas que usam ou contratam a tecnologia.
4. **Eventos da comunidade**: patrocinadores e palestrantes (ex.: Meet Magento, Adobe Summit, VTEX Day, meetups locais).
5. **Parceiros de ferramentas do ecossistema** (ex.: parceiros Hyvä para Magento; parceiros de módulos, gateways e ERPs conhecidos da tecnologia).
6. **Vagas abertas que citam a tecnologia** no país: LinkedIn Jobs (só leitura), Gupy, Glassdoor, sites de carreira e TheirStack Jobs. **Nunca use o Indeed** (nem os outros de `fontes_proibidas` do PERFIL).
7. **Cases públicos de agências** (páginas de cases, portfólios, notícias de lançamento de lojas) para achar marcas/varejistas que usam a tecnologia.

Pare de pesquisar quando 3 buscas SEGUIDAS não trouxerem nenhuma empresa nova (ou quando atingir o `limite N`). Diga no resumo em qual fonte isso aconteceu.

### Regras de cada linha
- **Empresa**: nome comercial atual (se mudou de nome ou foi comprada, use o atual e explique em Observação).
- **Tipo**: um destes: "Agência especialista", "Consultoria/integradora grande", "Agência digital multiplataforma", "Marca/varejista que usa a tecnologia", "Empresa com vaga aberta", "Internacional que contrata remoto na região", "Ecossistema (módulo/plataforma sobre a tecnologia)".
- **Cidade/UF**: da sede ou do escritório na região; "Remoto" se não houver.
- **Evidência**: o fato concreto que liga a empresa à tecnologia (ex.: "Adobe Silver Solution Partner", "vaga 'Dev Magento Pleno' aberta em 10/2026", "loja oficial roda Magento 2 (requirejs-config no HTML)").
- **Confiança**: "Certeza" = evidência direta e atual (vaga aberta, site oficial, case, diretório oficial); "Provável" = evidência antiga (mais de 2 anos) ou indireta. Linhas "Provável" ficam em amarelo.
- **Serve para**: "Vaga", "Vaga + parceria", "Freela/parceria white-label" ou "Prospecção direta (loja)", de acordo com o tipo e o objetivo escolhido.
- **Observação**: o que mais importa saber (ex.: "Ex-empregador", "comprada pela X em 2024", "só contrata PJ").
- **Fonte**: o link (URL completa) onde está a evidência. Linha sem link NÃO entra.
- Para conferir se uma loja usa a tecnologia, prefira marcadores específicos no HTML (para Magento: `Magento_`, `mage/cookies`, `requirejs-config`, `static/version`), nunca palavras genéricas.
- Nada inventado: se não achou evidência, a empresa não entra. Sem duplicatas (mesmo nome ou mesmo domínio).
- Empresas a excluir não entram. Ex-empregadores entram com "Ex-empregador" em Observação.

## Passo 3 — Gerar a planilha

1. Nome do arquivo: `empresas-<tecnologia>-<pais>.xlsx`, tudo minúsculo, sem acento, palavras separadas por hífen, só a primeira palavra da tecnologia (ex.: `empresas-magento-brasil.xlsx`, `empresas-vtex-portugal.xlsx`).
2. Rode:
   `python3 scripts/montar_planilha.py controle/empresas-coletadas.json <arquivo.xlsx> --titulo "<tecnologia> / <país>" --excluir "<A;B>" --ex-empregadores "<C;D>" [--limite N]`
   O script grava a aba `Empresas` (colunas `#`, `Empresa`, `Tipo`, `Cidade/UF`, `Evidência`, `Confiança`, `Serve para`, `Observação`, `Fonte`) e a aba `Resumo` (contagem por tipo, por confiança, por "Serve para" e legenda), remove duplicatas, descarta linhas sem fonte e excluídas, marca ex-empregadores e pinta "Provável" de amarelo. Ele também cria `controle/progresso.json` vazio e pronto para o `/next-companies`, se ainda não existir (nunca sobrescreve).
3. Atualize o campo `planilha_empresas` do `perfil.local.md` com o nome do arquivo (só esse campo; não mexa em mais nada do perfil).
4. Abra a planilha gerada com openpyxl e confira: número de linhas, toda linha com Fonte começando com `http`, nenhum nome repetido.

## Passo 4 — Resposta

Responda só com:
- "Planilha pronta: <arquivo> com <N> empresas (<x> Certeza, <y> Provável)."
- Tabela curta: contagem por Tipo e por "Serve para".
- As fontes usadas e onde a pesquisa parou (3 buscas sem empresa nova, ou limite).
- Empresas que ficaram de fora e o motivo (excluídas, sem fonte, duplicadas).
- "Próximo passo: /next-companies"
