# Laboratório de navegadores (só no GitHub Actions)

Testa o **painel real** com um projeto fictício (`projeto_lab.py`). O painel é aberto como o `/painel` abre (`painel_lab.py` roda o `gerar_painel.py` e só troca o navegador do sistema pelo do teste).
- **A:** o `painel/index.html` aberto direto mostra só a instrução do `/painel`, sem checkbox. **C:** Feito grava, Desfazer volta e Relatório da empresa abre.
- **D:** auditoria de todos os botões e links de `inventario.md`. **E:** 70 s sem mexer, a tela não se redesenha sozinha.
- **F:** com o servidor encerrado e a página aberta, o Feito mostra "O painel foi encerrado…" uma vez só, e nada se redesenha em 40 s. **G:** ao fechar a aba, o servidor termina e apaga o `controle/.painel-servidor.json`: pelo aviso de aba fechada (até 20 s) ou pela falta de batimento (45 s no laboratório, até 60 s). O resultado diz qual dos dois aconteceu.
- **Status:** qualquer ❌ reprova o CI. AMBIENTE quer dizer que o teste não conseguiu rodar; ele tenta mais uma vez e, se continuar, vira aviso no resumo.
- **Safari:** o WebDriver dele não abre `file://`, então o A usa `open -a Safari` e AppleScript.
- **Modos:** RÁPIDO (padrão, em todo push: Ubuntu + Chrome sem janela) e COMPLETO (`gh workflow run browser-lab.yml -f modo=completo`, 11 navegadores). Se o painel não abrir em 10 s, o job para na hora e mostra a saída do servidor. Nunca rode no seu computador.
