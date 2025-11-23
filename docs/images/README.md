# 📸 Screenshots do Kavak Monitor

Este diretório contém as imagens/screenshots usados na documentação do projeto.

## Como Adicionar Screenshots

### 1. Tire os screenshots do sistema rodando

Certifique-se de:
- ✅ Remover/ocultar dados pessoais sensíveis
- ✅ Usar dados de exemplo realistas
- ✅ Capturar telas em boa resolução (mínimo 1280x720)
- ✅ Formato PNG para melhor qualidade

### 2. Nomeie os arquivos conforme o padrão

```
dashboard.png                - Tela principal do dashboard
novo-monitoramento.png       - Formulário de criação de monitoramento
lista-monitoramentos.png     - Lista com monitoramentos ativos
notificacao-telegram.png     - Screenshot da notificação no Telegram
```

### 3. Adicione os arquivos neste diretório

```bash
# Copie suas imagens para este diretório
cp ~/Downloads/screenshot.png docs/images/dashboard.png
```

### 4. As imagens serão automaticamente exibidas no README.md

O README.md principal já está configurado para exibir as imagens deste diretório.

---

## 📋 Screenshots Necessários

### README.md Principal

- [ ] **dashboard.png** - Interface principal do sistema
  - **Onde**: README.md → Seção "Screenshots" → "Interface Principal"
  - **Deve mostrar**: Dashboard limpo, menu lateral, área principal
  - **Resolução sugerida**: 1920x1080

- [ ] **novo-monitoramento.png** - Formulário de criação
  - **Onde**: README.md → Seção "Screenshots" → "Criação de Monitoramento"
  - **Deve mostrar**: Formulário preenchido com dados de exemplo
  - **Link de exemplo**: `https://www.kavak.com/br/comprar/chevrolet-onix-exemplo`
  - **Resolução sugerida**: 1920x1080

- [ ] **lista-monitoramentos.png** - Lista de monitoramentos
  - **Onde**: README.md → Seção "Screenshots" → "Lista de Monitoramentos Ativos"
  - **Deve mostrar**: Pelo menos 2-3 monitoramentos ativos
  - **Status diferentes**: "Ativo", "Vendido", "Expirado"
  - **Resolução sugerida**: 1920x1080

- [ ] **notificacao-telegram.png** - Notificação recebida
  - **Onde**: README.md → Seção "Screenshots" → "Notificação no Telegram"
  - **Deve mostrar**: Mensagem completa do bot no Telegram
  - **Origem**: Screenshot do celular ou Telegram Desktop
  - **Resolução sugerida**: 800x600 (recorte da mensagem)

- [ ] **fluxo-sistema.png** - Diagrama do fluxo
  - **Onde**: README.md → Seção "Como Funciona" → "Fluxo Visual do Sistema"
  - **Deve mostrar**: Diagrama ou imagem explicando o fluxo completo
  - **Sugestão**: Criar com draw.io, Figma ou similar
  - **Resolução sugerida**: 1920x1080

### QUICKSTART_DOCKER.md

- [ ] **sistema-rodando.png** - Sistema após inicialização
  - **Onde**: QUICKSTART_DOCKER.md → "Pronto! 🎉" → "Sistema Rodando"
  - **Deve mostrar**: Interface logo após o primeiro acesso
  - **Resolução sugerida**: 1920x1080

### DOCKER_DEPLOY.md

- [ ] **interface-inicial.png** - Tela principal pós-deploy
  - **Onde**: DOCKER_DEPLOY.md → Seção "Acessar Interface Web" → "Interface Inicial"
  - **Deve mostrar**: Tela principal após deploy completo
  - **Resolução sugerida**: 1920x1080

---

## Dicas para Screenshots de Qualidade

### Para Interface Web:
1. Abra o sistema no navegador
2. Pressione `F12` para abrir DevTools
3. Clique no ícone de responsividade (ou `Ctrl+Shift+M`)
4. Escolha dimensões adequadas (ex: 1920x1080)
5. Use `Win+Shift+S` (Windows) ou `Cmd+Shift+4` (Mac) para capturar

### Para Telegram:
1. Aguarde receber uma notificação real
2. Capture a tela do app/desktop
3. Recorte apenas a mensagem relevante
4. Remova/oculte números de telefone ou informações sensíveis

### Para Ocultar Dados Sensíveis:
- Use um editor de imagens (Paint, GIMP, Photoshop)
- Cubra com um retângulo preto/cinza
- Ou use dados fictícios desde o início

---

## Exemplo de Dados Fictícios para Screenshots

Use estes dados ao criar monitoramentos de exemplo:

```
Link do Carro: https://www.kavak.com/br/comprar/toyota-corolla-2020-exemplo
Marca: Toyota
Modelo: Corolla
Data da Venda: 15/01/2025
Chat ID: 123456789
Status: Ativo
```

```
Link do Carro: https://www.kavak.com/br/comprar/honda-civic-2019-exemplo
Marca: Honda
Modelo: Civic
Data da Venda: 10/01/2025
Chat ID: 987654321
Status: Vendido
```

---

**Quando adicionar as imagens, remova os comentários TODO do README.md principal!**
