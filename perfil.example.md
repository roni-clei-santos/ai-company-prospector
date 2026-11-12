# Perfil do candidato (perfil.local.md)

> Arquivo PESSOAL. Fica só no seu computador (está no .gitignore). É a ÚNICA fonte de verdade sobre você
> para o PROMPT-prospeccao.md e as skills /next-companies e /build-company-list.
> Nada que não esteja aqui, no PDF do currículo, no seu LinkedIn ou no arquivo de respostas pode ser usado.
>
> Este é o EXEMPLO (pessoa fictícia). Copie para perfil.local.md e troque tudo pelos seus dados.
> Guia passo a passo: docs/guia/02-perfil.md

## Campos obrigatórios

```yaml
nome: "Alex Exemplo"
email: "alex@example.com"
telefone: ""                  # opcional; deixe vazio se não quiser usar
linkedin_url: "https://www.linkedin.com/in/alex-exemplo/"
cidade: "Curitiba/PR"
tecnologias_principais:
  - "Magento / Adobe Commerce"
  - "PHP"
  - "JavaScript"
anos_experiencia: 8
pisos_salariais:
  clt: 10000                  # R$/mês, nunca furar
  pj: 12000                   # R$/mês, nunca furar
idiomas:
  - idioma: "Português"
    nivel: "nativo"
  - idioma: "Inglês"
    nivel: "intermediário"    # se escrever "não informar", vagas que EXIGEM o idioma são descartadas
ex_empregadores:
  - "Agência Fictícia Um"
  - "Loja Exemplo Ltda"
empresas_excluidas:
  - "Empresa Que Não Quero"
curriculo_base: "Alex_Exemplo_CV.pdf"
tom_de_voz:
  saudacao: "Oi, <nome>, tudo bem?"
  fechamento:
    - "Fico à disposição."
    - "Se fizer sentido, é só me chamar."
modo_email: "arquivo"          # "arquivo" = só rascunhos/email/*.md | "gmail_rascunho" = rascunho no Gmail pelo navegador (nunca envia)
```

## Campos opcionais (usados pelo PROMPT e pelas skills)

```yaml
planilha_empresas: "empresas-magento-brasil.xlsx"   # gerada pelo /build-company-list
arquivo_respostas: "controle/respostas-candidato.md"
cargo_apresentacao: "Desenvolvedor PHP / Magento sênior."
regimes_aceitos: ["CLT", "PJ"]
regime_pj_detalhe: ""
modalidade: "Aceita remoto ou híbrido em Curitiba."
pais_trabalho: "Brasil"
marca_freela: ""                 # nome usado em propostas de freela/parceria (deixe vazio se não faz freela)
marca_freela_desde: ""
plataformas_logadas: ["LinkedIn"]
fontes_proibidas: ["Indeed"]
palavras_proibidas: []       # o scripts/checar_notas.py acusa estas frases nos rascunhos
assunto_email_vaga: "Dev Magento / PHP | Alex Exemplo"
assunto_email_parceria: ""
```

## Histórico profissional (datas exatas)

- Agência Fictícia Um, Desenvolvedor Magento Pleno, 01/2020 a 12/2023. Manutenção de lojas Magento 2 e criação de módulos.
- Loja Exemplo Ltda, Desenvolvedor PHP, 03/2017 a 12/2019.
- Regra: em textos enviados a empresas, não cite nomes de clientes. Descreva o tipo de projeto e o que fez.

## Liderança (fatos confirmados)

- Nenhuma liderança formal. Mentorou 1 dev júnior na Agência Fictícia Um.

## Skills

### Tem (ATENDE)
- Magento 2, PHP, MySQL, JavaScript, Git, Docker, REST.

### Conhece, mas não é especialista (PARCIAL)
- GraphQL.

### NÃO tem (NÃO ATENDE)
- Java, .NET, mobile nativo.

### Idiomas (regras)
- Inglês intermediário: pode se candidatar a vaga que pede inglês intermediário.

## Formação e certificações

- Graduação: Sistemas de Informação, Universidade Exemplo, 2013 a 2016.

## Objetivo de carreira

- Quer: vagas de dev Magento/PHP pleno ou sênior.
- Não quer: vagas júnior, infra como função principal.

## Tom de voz (detalhes)

- Educado, direto e curto.
- Modelo de LinkedIn (sem vaga específica): "Oi, <nome>, tudo bem? Vi que você <papel da pessoa na empresa>. Sou dev Magento/PHP com 8 anos de experiência. Se surgir uma vaga em que eu possa ajudar, fico à disposição."

## Ex-clientes e casos especiais (decisões já tomadas)

- Nenhum.

## Pistas de contato já dadas (confirmar cada uma nas fontes; sem evidência = "pista sem evidência")

- Loja Exemplo 1: candidatura em 10/2026.
