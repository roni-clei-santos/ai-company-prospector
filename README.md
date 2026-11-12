<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/header-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/header-light.svg">
  <img src="assets/header-light.svg" alt="AI Company Prospector" width="100%">
</picture>

<h3 align="center">Pare de procurar vagas. Comece a procurar empresas.</h3>

<p align="center">
  Um agente para o Claude Code que monta a lista de empresas que usam a sua tecnologia, investiga uma por uma<br>
  e deixa os rascunhos de LinkedIn e e-mail prontos para <b>você</b> revisar e enviar.
</p>

<p align="center">
  <a href="https://roni-clei-santos.github.io/ai-company-prospector/demo/"><b>Demo ao vivo</b></a> ·
  <a href="#começo-rápido"><b>Começo rápido</b></a> ·
  <a href="docs/guia/01-instalacao.md"><b>Guia</b></a> ·
  <a href="ROADMAP.md"><b>Roadmap</b></a> ·
  <a href="README.en.md"><b>English</b></a>
</p>

<p align="center">
  <a href="LICENSE"><img alt="Licença MIT" src="https://img.shields.io/badge/licen%C3%A7a-MIT-FF7A1A?style=flat-square&labelColor=0B1F3A"></a>
  <a href="https://github.com/roni-clei-santos/ai-company-prospector/actions/workflows/test.yml"><img alt="Testes" src="https://img.shields.io/github/actions/workflow/status/roni-clei-santos/ai-company-prospector/test.yml?branch=main&style=flat-square&label=testes&labelColor=0B1F3A"></a>
  <a href="#começo-rápido"><img alt="macOS, Linux e Windows (beta)" src="https://img.shields.io/badge/plataformas-macOS%20%7C%20Linux%20%7C%20Windows%20beta-FF7A1A?style=flat-square&labelColor=0B1F3A"></a>
  <a href="https://code.claude.com/docs/en/overview"><img alt="Feito para o Claude Code" src="https://img.shields.io/badge/Claude%20Code-skills-FF7A1A?style=flat-square&labelColor=0B1F3A"></a>
</p>

https://github.com/user-attachments/assets/83a9fab9-625a-4bb9-b654-534508b5008c

<p align="center"><sub>Painel da demonstração, com dados 100% fictícios. <a href="https://roni-clei-santos.github.io/ai-company-prospector/demo/">Abra a demo ao vivo</a>.</sub></p>

## Antes × Depois

| Procurando vagas no escuro | Prospectando empresas com o agente |
|---|---|
| Espera a vaga certa aparecer num portal | Parte da lista de empresas que usam a sua tecnologia, com a fonte de cada uma |
| Manda o mesmo currículo para todo lado | Cada vaga recebe a nota de aderência e, se passar, um currículo ajustado |
| Não sabe quem é o recrutador nem o e-mail do RH | Levanta recrutadores, RH e e-mails, e confere o cargo atual de cada pessoa |
| Perde o fio: quem respondeu, quem precisa de follow-up | Memória entre rodadas: confere o que você enviou e marca os follow-ups com data |
| Esquece as agências e as chances de freela | Também abre conversa de parceria e white-label com agências da sua tecnologia |

## Recursos

<table>
  <tr>
    <td width="33%" valign="top"><img src="assets/icons/lista.svg" width="40" alt=""><br><b>Lista de empresas com fonte</b><br>O <code>/build-company-list</code> monta a planilha a partir de fontes públicas, com evidência e link para cada empresa.</td>
    <td width="33%" valign="top"><img src="assets/icons/rodadas.svg" width="40" alt=""><br><b>Rodadas de 10, com memória</b><br>O <code>/next-companies</code> processa 10 empresas por vez e retoma exatamente de onde parou.</td>
    <td width="33%" valign="top"><img src="assets/icons/leitura.svg" width="40" alt=""><br><b>LinkedIn só leitura</b><br>Abre convites, mensagens, vagas e páginas de empresas. Nunca envia, curte, segue nem retira convite.</td>
  </tr>
  <tr>
    <td width="33%" valign="top"><img src="assets/icons/rascunhos.svg" width="40" alt=""><br><b>Rascunhos que você revisa</b><br>Mensagens de LinkedIn e e-mails no seu tom de voz, salvos como rascunho para você ler e enviar.</td>
    <td width="33%" valign="top"><img src="assets/icons/painel.svg" width="40" alt=""><br><b>Painel automático</b><br>Ao fim de cada rodada abre um painel com a rodada, o projeto inteiro, quem respondeu e os follow-ups.</td>
    <td width="33%" valign="top"><img src="assets/icons/tokens.svg" width="40" alt=""><br><b>Economia de tokens com RTK</b><br>O instalador liga o <a href="https://github.com/rtk-ai/rtk">RTK</a>, que enxuga a saída dos comandos antes de ela chegar ao Claude.</td>
  </tr>
</table>

## Como funciona

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/flow-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/flow-light.svg">
  <img src="assets/flow-light.svg" alt="perfil.local.md → /build-company-list → Planilha → /next-companies (rodadas de 10) → Rascunhos → Você revisa e envia → Painel; a próxima rodada confere o que você enviou" width="100%">
</picture>

O `perfil.local.md` é a única fonte de verdade sobre você (histórico com datas, skills, pisos salariais, tom de voz). O agente nunca afirma nada que não esteja nele, no seu currículo ou nas suas respostas.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/stats-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/stats-light.svg">
  <img src="assets/stats-light.svg" alt="Números do uso real do autor" width="100%">
</picture>
<p align="center"><sub>Números do uso real do autor.</sub></p>

## Dois jeitos de usar

| | **Só a planilha** | **Planilha + robô** |
|---|---|---|
| Comando | `/build-company-list` | `/build-company-list` e depois `/next-companies` a cada rodada |
| Precisa de LinkedIn? | Não | Sim, logado no Chrome (extensão Claude in Chrome) |
| O que você recebe | Empresas reais que usam a sua tecnologia, cada uma com evidência e link da fonte | O fluxo completo: rodadas de 10 empresas, vagas avaliadas, rascunhos de LinkedIn e e-mail e o painel |
| Quem faz o contato | Você, por conta própria | Você envia os rascunhos que o robô preparou |

## Começo rápido

<details open>
<summary><b>macOS</b></summary>

```bash
# 1. Claude Code (se ainda não tiver)
curl -fsSL https://claude.ai/install.sh | bash

# 2. Projeto
git clone https://github.com/roni-clei-santos/ai-company-prospector.git
cd ai-company-prospector
./install.sh
```

O `install.sh` usa o Homebrew para o Python e o RTK, instala as skills em `~/.claude/skills` e cria o seu `perfil.local.md`.
</details>

<details>
<summary><b>Linux</b></summary>

```bash
# 1. Claude Code (se ainda não tiver)
curl -fsSL https://claude.ai/install.sh | bash

# 2. Projeto
git clone https://github.com/roni-clei-santos/ai-company-prospector.git
cd ai-company-prospector
./install.sh
```

O `install.sh` instala `python3` e `pip` pelo `apt`, `dnf` ou `pacman` (pode pedir a sua senha de `sudo`), o RTK pelo script oficial e as skills em `~/.claude/skills`. Testado num Ubuntu 24.04 limpo.
</details>

<details>
<summary><b>Windows (beta)</b></summary>

```powershell
# 1. Claude Code (se ainda não tiver)
irm https://claude.ai/install.ps1 | iex

# 2. Projeto
git clone https://github.com/roni-clei-santos/ai-company-prospector.git
cd ai-company-prospector
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

O `install.ps1` confere o Python (`py -3` ou `python`), instala o RTK com o `winget` e **copia** as skills para `%USERPROFILE%\.claude\skills`. Depois de cada `git pull`, rode `py -3 scripts\atualizar_skills.py` para copiar a versão nova.
</details>

Depois, nos três sistemas: preencha o `perfil.local.md`, abra o Claude Code na pasta (`claude`) e rode **`/build-company-list`** para receber a planilha (não precisa de LinkedIn). Para o modo "Planilha + robô": rode `/chrome`, entre no LinkedIn nesse Chrome e rode **`/next-companies`** a cada rodada.

## Requisitos

| Sistema | Você precisa de |
|---|---|
| Todos | [Claude Code](https://code.claude.com/docs/en/setup) logado e Git |
| Só no modo "Planilha + robô" | Google Chrome com a extensão Claude in Chrome ([guia](docs/guia/03-chrome.md)) e uma conta no LinkedIn logada nesse Chrome. O Gmail logado só é preciso se você escolher `modo_email: "gmail_rascunho"`; com `"arquivo"`, os e-mails ficam em `rascunhos/email/` |
| macOS 13+ | [Homebrew](https://brew.sh) (o instalador cuida do Python 3 e do RTK) |
| Linux | `sudo` e `apt`, `dnf` ou `pacman`, ou Python 3.9+ com `pip` já instalados |
| Windows 10+ (beta) | Python 3.9+ ([python.org](https://www.python.org/downloads/windows/) ou `winget install Python.Python.3.12`) |

Passo a passo completo: [docs/guia](docs/guia/01-instalacao.md).

## Princípios

<table>
  <tr><td width="48"><img src="assets/icons/decide.svg" width="32" alt=""></td><td><b>A IA rascunha, você decide.</b> Mensagens e e-mails são sempre rascunhos, e vaga de gestão nunca recebe candidatura automática.</td></tr>
  <tr><td><img src="assets/icons/leitura.svg" width="32" alt=""></td><td><b>No LinkedIn, só leitura.</b> Em ritmo humano. Se aparecer aviso de limite ou verificação, ele para.</td></tr>
  <tr><td><img src="assets/icons/memoria.svg" width="32" alt=""></td><td><b>Memória entre rodadas.</b> <code>controle/progresso.json</code> guarda o status de cada empresa; nada é refeito e nenhum contato se repete.</td></tr>
  <tr><td><img src="assets/icons/revisao.svg" width="32" alt=""></td><td><b>Nada sai sem revisão.</b> O e-mail fica em arquivo ou como rascunho no Gmail. Você lê, ajusta e envia.</td></tr>
  <tr><td><img src="assets/icons/verdade.svg" width="32" alt=""></td><td><b>Nunca inventa.</b> Toda afirmação sobre você sai do seu perfil, do currículo ou das suas respostas. Na dúvida, ele pergunta.</td></tr>
</table>

## Perguntas frequentes

<details>
<summary><b>É seguro para o meu LinkedIn?</b></summary>

O agente só lê, no seu Chrome já logado, telas que você mesmo veria: convites enviados, mensagens, vagas, páginas e perfis. Ele navega em ritmo humano e para de usar o LinkedIn na rodada se aparecer aviso de limite ou verificação. Mesmo assim, os termos do LinkedIn restringem automação (veja o aviso abaixo).
</details>

<details>
<summary><b>Posso usar sem conectar meu LinkedIn?</b></summary>

Sim, no modo "Só a planilha". O `/build-company-list` não precisa de LinkedIn: você recebe empresas reais que usam a sua tecnologia, cada uma com evidência e link da fonte, e faz o contato você mesmo. O LinkedIn logado no Chrome só é exigido no modo "Planilha + robô" (`/next-companies`), com rodadas de 10, rascunhos e painel.
</details>

<details>
<summary><b>Ele envia mensagem sozinho?</b></summary>

Não. Mensagens de LinkedIn e e-mails são sempre rascunhos. A única ação que ele pode fazer sozinho é a candidatura numa plataforma de vagas (Gupy, site da empresa), e só quando a vaga passa em todos os critérios (aderência de 75% ou mais e nenhum filtro eliminatório). Vaga de gestão fica sempre para você decidir.
</details>

<details>
<summary><b>Funciona para outra tecnologia além de Magento?</b></summary>

Sim. O `/build-company-list` pergunta a tecnologia e o país e monta a planilha `empresas-<tecnologia>-<país>.xlsx`, e as regras do agente são genéricas. Magento / Adobe Commerce é só o caso de uso do autor.
</details>

<details>
<summary><b>Quanto custa em tokens?</b></summary>

Ele usa a sua própria conta do Claude Code, e o gasto depende do seu plano e de quantas páginas cada empresa exige. Por isso o trabalho é dividido em rodadas de 10 empresas, e o RTK enxuga a saída dos comandos de terminal antes de ela chegar ao modelo. Não há custo extra do projeto.
</details>

<details>
<summary><b>Meus dados vão para algum lugar?</b></summary>

Seu perfil, planilhas, rascunhos, relatórios e currículos ficam só no seu computador (estão no `.gitignore`). O projeto não tem servidor. O que o Claude Code lê para trabalhar passa pela Anthropic, como em qualquer uso do Claude Code, e a navegação acontece no seu próprio Chrome.
</details>

<details>
<summary><b>Funciona no Windows?</b></summary>

Em beta. O `install.ps1` roda no PowerShell 5.1 e 7, copia as skills (o Windows exige permissão especial para links simbólicos) e é testado a cada push no GitHub Actions (`windows-latest`), junto com macOS e Linux. As skills em si não foram usadas num Windows real ainda; se algo falhar, [abra uma issue](https://github.com/roni-clei-santos/ai-company-prospector/issues).
</details>

## Aviso

Os termos do LinkedIn restringem automação. Este projeto só lê, no navegador logado da própria pessoa, telas que ela mesma veria. Use sob sua responsabilidade.

## Estrelas e contribuidores

<p align="center">
<a href="https://star-history.com/#roni-clei-santos/ai-company-prospector&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=roni-clei-santos/ai-company-prospector&type=Date&theme=dark">
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=roni-clei-santos/ai-company-prospector&type=Date">
    <img alt="Gráfico de estrelas" src="https://api.star-history.com/svg?repos=roni-clei-santos/ai-company-prospector&type=Date" width="640">
  </picture>
</a>
</p>

<p align="center">
<a href="https://github.com/roni-clei-santos/ai-company-prospector/graphs/contributors">
  <img alt="Contribuidores" src="https://contrib.rocks/image?repo=roni-clei-santos/ai-company-prospector">
</a>
</p>

Quer ajudar? Veja o [CONTRIBUTING.md](CONTRIBUTING.md) e o [ROADMAP.md](ROADMAP.md). Os testes rodam com `python3 -m pytest`.

## Autor

Feito por **Roni Clei J. Santos**, desenvolvedor Adobe Commerce / Magento: [linkedin.com/in/roni-clei-santos](https://www.linkedin.com/in/roni-clei-santos/).

Se este projeto te ajudou a achar uma empresa (ou a parar de procurar vaga no escuro), **deixe uma ⭐**. Isso ajuda outras pessoas a encontrarem o projeto.

Licença [MIT](LICENSE).
