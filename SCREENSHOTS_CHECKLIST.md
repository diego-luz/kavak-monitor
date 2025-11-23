# 📸 Checklist de Screenshots para Adicionar

Este arquivo lista todos os espaços preparados na documentação para você adicionar screenshots do sistema.

---

## 🎯 Resumo Rápido

**Total de espaços criados**: 7 screenshots

**Arquivos com espaços para imagens**:
- ✅ README.md (5 espaços)
- ✅ QUICKSTART_DOCKER.md (1 espaço)
- ✅ DOCKER_DEPLOY.md (1 espaço)

---

## 📋 Checklist Completo

### README.md

#### Seção: Screenshots (após "Início Rápido")

- [ ] **dashboard.png**
  - Localização: `docs/images/dashboard.png`
  - Descrição: Interface principal do dashboard
  - Tamanho sugerido: 1920x1080

- [ ] **novo-monitoramento.png**
  - Localização: `docs/images/novo-monitoramento.png`
  - Descrição: Formulário de criação de monitoramento
  - Tamanho sugerido: 1920x1080

- [ ] **lista-monitoramentos.png**
  - Localização: `docs/images/lista-monitoramentos.png`
  - Descrição: Lista com monitoramentos ativos/vendidos/expirados
  - Tamanho sugerido: 1920x1080

- [ ] **notificacao-telegram.png**
  - Localização: `docs/images/notificacao-telegram.png`
  - Descrição: Screenshot da notificação no Telegram
  - Tamanho sugerido: 800x600

#### Seção: Como Funciona

- [ ] **fluxo-sistema.png**
  - Localização: `docs/images/fluxo-sistema.png`
  - Descrição: Diagrama ou imagem explicando o fluxo
  - Tamanho sugerido: 1920x1080
  - Dica: Pode criar com draw.io, Figma, ou screenshot com anotações

---

### QUICKSTART_DOCKER.md

#### Seção: Pronto! 🎉

- [ ] **sistema-rodando.png**
  - Localização: `docs/images/sistema-rodando.png`
  - Descrição: Interface após primeiro acesso bem-sucedido
  - Tamanho sugerido: 1920x1080

---

### DOCKER_DEPLOY.md

#### Seção: Acessar Interface Web

- [ ] **interface-inicial.png**
  - Localização: `docs/images/interface-inicial.png`
  - Descrição: Tela principal após deploy completo
  - Tamanho sugerido: 1920x1080

---

## 🚀 Como Adicionar as Imagens

### Passo 1: Rode o sistema

```bash
docker compose up -d
```

### Passo 2: Acesse e capture

Abra: http://localhost:5004

Use **dados fictícios** para os screenshots:
- Link: `https://www.kavak.com/br/comprar/toyota-corolla-2020-exemplo`
- Marca: Toyota
- Modelo: Corolla
- Data: 15/01/2025
- Chat ID: 123456789

### Passo 3: Salve os arquivos

```bash
# Coloque as imagens na pasta correta
cp ~/Downloads/screenshot1.png docs/images/dashboard.png
cp ~/Downloads/screenshot2.png docs/images/novo-monitoramento.png
# ... e assim por diante
```

### Passo 4: Remova os comentários TODO

Nos arquivos de documentação, remova as linhas:
```
> **TODO**: Adicionar screenshot...
> **Espaço para screenshot**: ...
```

Deixe apenas:
```markdown
![Nome da Imagem](docs/images/nome-arquivo.png)
```

### Passo 5: Commit

```bash
git add docs/images/*.png
git add README.md QUICKSTART_DOCKER.md DOCKER_DEPLOY.md
git commit -m "Adiciona screenshots da interface do sistema"
```

---

## 💡 Dicas Importantes

### ✅ O que FAZER:
- Use dados fictícios realistas
- Capture em boa resolução (mínimo 1280x720)
- Use formato PNG para melhor qualidade
- Mostre a interface limpa e organizada

### ❌ O que NÃO fazer:
- Não inclua dados pessoais reais
- Não use tokens/secrets reais
- Não capture com resolução baixa
- Não deixe informações sensíveis visíveis

---

## 📖 Guia Detalhado

Para instruções completas sobre como capturar os screenshots, consulte:

**`docs/images/README.md`**

Este arquivo contém:
- Lista completa de todos os screenshots
- Instruções detalhadas de captura
- Dicas de qualidade
- Como ocultar dados sensíveis
- Exemplos de dados fictícios

---

## ✨ Opcional: Screenshots Extras

Se quiser deixar a documentação ainda mais completa, você pode adicionar:

- **Terminal com logs**: Mostrando sistema funcionando
- **Docker stats**: Mostrando uso de recursos
- **Múltiplas notificações**: Telegram mostrando histórico
- **Configuração do bot**: @BotFather criando o bot

Estes não têm espaços pré-definidos, mas podem ser úteis!

---

**Quando terminar de adicionar as imagens, você pode deletar este arquivo.**
