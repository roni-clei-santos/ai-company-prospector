# Laboratório de navegadores (só no GitHub Actions)

Mede, com dados fictícios, como cada navegador trata o painel aberto **direto do arquivo** (`file://`) e **pelo endereço http** (`http://127.0.0.1`).
- **Grava:** a página consegue um POST com token para o servidor local. Só vale ✅ se a página recebeu 200 **e** o `server-log.json` registrou o POST.
- **Guarda clique:** o `localStorage` grava e o valor continua lá ao recarregar. **Persiste ao reabrir:** o valor continua lá depois de fechar o navegador e abrir de novo com o mesmo perfil.
- **Outro arquivo lê:** o `outra-pasta/leitor.html` enxerga o mesmo armazenamento.
- **Painel real:** `scripts/gerar_painel.py` + `scripts/servidor_painel.py` sobre um projeto fictício (`.github/ci/projeto_demo.py`). O teste clica em Feito e depois em Desfazer, e confere o `progresso.json` temporário.
- **Status:** ✅ ou ❌ são resultado do navegador. AMBIENTE quer dizer que o teste não conseguiu rodar (driver, navegador ausente, instalação). **Safari:** os cenários de arquivo e http abrem pelo `open -a Safari`, porque o WebDriver dele não abre `file://`, e a página devolve o resultado em `/relato`. O painel real abre pelo WebDriver.
- **Como rodar:** `gh workflow run browser-lab.yml`. O resultado fica no artifact `browser-lab-resumo` e no resumo da execução. Nunca rode no seu computador.
