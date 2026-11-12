# Laboratório de navegadores (só no GitHub Actions)

Testa o **painel real** (`painel/index.html` + `scripts/servidor_painel.py`) com um projeto fictício (`projeto_lab.py`), em 11 navegadores com janela: Safari, Chrome, Edge, Firefox e Brave no macOS, Windows e Ubuntu.
- **A, arquivo com o servidor ligado:** Feito grava, Desfazer volta e Relatório da empresa abre.
- **B, arquivo com o servidor desligado:** o Feito mostra "Vou salvar…"; depois de ligar o servidor e recarregar, o clique fica salvo em até 15 s.
- **C, endereço http:** Feito, Desfazer e Relatório da empresa. **D, auditoria:** todos os botões e links de `inventario.md`.
- **Status:** qualquer ❌ reprova o CI. AMBIENTE quer dizer que o teste não conseguiu rodar; ele tenta mais uma vez e, se continuar, vira só aviso no resumo.
- **Safari:** o WebDriver dele não abre `file://`, então A e B abrem o arquivo com `open -a Safari` e clicam via AppleScript.
- **Como rodar:** `gh workflow run browser-lab.yml`. O resultado fica no artifact `browser-lab-resumo` e no resumo da execução. Nunca rode no seu computador.
