# 📚 Guia de Documentação do Kavak Monitor

Este projeto possui documentação completa organizada em múltiplos arquivos. Use este guia para navegar pela documentação conforme sua necessidade.

---

## 🚀 Para Começar Rapidamente

### **[QUICKSTART_DOCKER.md](QUICKSTART_DOCKER.md)** - 5 minutos
**Quando usar**: Você quer colocar o sistema rodando o mais rápido possível.

**O que contém**:
- ✅ Pré-requisitos básicos
- ✅ 5 passos simples para deploy
- ✅ Como obter Telegram Bot Token em 1 minuto
- ✅ Troubleshooting rápido
- ✅ Comandos úteis básicos

**Ideal para**: Primeira instalação, testes rápidos, ou quando você já sabe o que está fazendo.

---

## 📖 Entendendo o Projeto

### **[README.md](README.md)** - Visão Geral Completa
**Quando usar**: Você quer entender como o sistema funciona antes de instalar.

**O que contém**:
- 📋 Visão geral do projeto e funcionalidades
- 🏗️ Estrutura do projeto e tecnologias utilizadas
- ⚙️ Como funciona o monitoramento (fluxo detalhado)
- 🔒 Camadas de segurança implementadas
- 📊 Capacidade do sistema e uso de recursos
- 🛠️ Comandos Docker para gerenciamento
- 🐛 Troubleshooting comum
- 📈 Tabela de performance no Raspberry Pi

**Ideal para**: Novos usuários, desenvolvedores querendo contribuir, ou para entender a arquitetura.

---

## 🔧 Deploy Detalhado

### **[DOCKER_DEPLOY.md](DOCKER_DEPLOY.md)** - Guia Completo de Deploy
**Quando usar**: Você quer um deploy profissional com todos os detalhes.

**O que contém**:
- ⚙️ Instalação passo a passo do Docker em diferentes sistemas
- 🔑 Como obter e configurar Telegram Bot Token (tutorial detalhado)
- 📦 Build e deploy das imagens Docker
- ✅ Verificação completa de todos os componentes
- 💾 Backup manual e automatizado (com script pronto)
- 🔄 Restauração de backups
- 🛡️ Gerenciamento avançado de containers
- 🐛 Troubleshooting profundo
- 📋 Checklist de próximos passos

**Ideal para**: Deploy em produção, ambientes profissionais, ou quando precisa de backup/restore.

---

## ⚡ Otimização para Raspberry Pi

### **[otimizacao_raspberry_pi.md](otimizacao_raspberry_pi.md)** - Performance no RPi
**Quando usar**: Você está rodando o sistema em Raspberry Pi 3 ou hardware limitado.

**O que contém**:
- 🎯 Configurações otimizadas para RPi 3
- 📊 Testes de performance e benchmarks
- 🔧 Ajustes de workers, batch size e timeouts
- 🌡️ Monitoramento de temperatura e recursos
- 📈 Capacidade máxima (até 500 monitoramentos)
- ⚠️ Sintomas de sobrecarga e como resolver
- 💡 Dicas de otimização avançada

**Ideal para**: Usuários de Raspberry Pi, ambientes com recursos limitados, ou quando o sistema está lento.

---

## 🛡️ Proteção Contra Falsos Positivos

### **[PROTECAO_FALSOS_POSITIVOS.md](PROTECAO_FALSOS_POSITIVOS.md)** - Sistema de Detecção
**Quando usar**: Você quer entender como o sistema evita falsos alarmes.

**O que contém**:
- ❗ O problema dos falsos positivos
- ✅ Sistema de falhas consecutivas (2 falhas = vendido)
- 📊 Exemplos práticos de cenários
- 🔧 Como funciona o contador de falhas
- 📈 Testes e validação do sistema
- ⚙️ Configurações avançadas

**Ideal para**: Entender a lógica de detecção, ajustar sensibilidade, ou resolver falsos alarmes.

---

## 🤖 Configuração do Telegram

### **[frontend/guia_telegram.html](frontend/guia_telegram.html)** - Tutorial Visual
**Quando usar**: Você precisa criar um bot no Telegram.

**O que contém**:
- 📱 Tutorial passo a passo com imagens
- 🤖 Como criar bot com @BotFather
- 🔑 Como obter o Token
- 💬 Como obter seu Chat ID
- ✅ Como testar o bot
- 📸 Capturas de tela de cada etapa

**Ideal para**: Primeira vez configurando Telegram Bot, ou quando está tendo problemas com notificações.

**Como acessar**:
- Pelo navegador: `http://seu-ip:5004/guia_telegram.html`
- Ou abrir o arquivo diretamente no navegador

---

## 🔐 Segurança e reCAPTCHA (Referência)

### **[guia_recaptcha.md](guia_recaptcha.md)** - Tutorial reCAPTCHA
**Status**: ⚠️ **ARQUIVO DE REFERÊNCIA APENAS**

Este arquivo permanece no projeto como referência, mas **o reCAPTCHA não está implementado** na versão atual do código.

Se você planeja adicionar proteção anti-spam no futuro, este guia mostra como configurar.

---

## 🐳 Instalação do Docker

### **[install-docker.sh](install-docker.sh)** - Script de Instalação
**Quando usar**: Você precisa instalar Docker automaticamente.

**O que contém**:
- 🔧 Script automatizado para Ubuntu/Debian
- 📦 Instalação do Docker e Docker Compose
- 👤 Configuração de permissões de usuário
- ✅ Verificação pós-instalação

**Como usar**:
```bash
chmod +x install-docker.sh
./install-docker.sh
```

---

## 🗂️ Resumo: Qual Arquivo Ler?

| Situação | Arquivo Recomendado |
|----------|-------------------|
| Quero instalar rapidamente | [QUICKSTART_DOCKER.md](QUICKSTART_DOCKER.md) |
| Primeira vez usando o sistema | [README.md](README.md) |
| Deploy profissional/produção | [DOCKER_DEPLOY.md](DOCKER_DEPLOY.md) |
| Usando Raspberry Pi | [otimizacao_raspberry_pi.md](otimizacao_raspberry_pi.md) |
| Configurar Telegram Bot | [frontend/guia_telegram.html](frontend/guia_telegram.html) |
| Sistema lento ou travando | [otimizacao_raspberry_pi.md](otimizacao_raspberry_pi.md) |
| Muitos falsos alarmes | [PROTECAO_FALSOS_POSITIVOS.md](PROTECAO_FALSOS_POSITIVOS.md) |
| Fazer backup dos dados | [DOCKER_DEPLOY.md](DOCKER_DEPLOY.md) (seção Backup) |
| Instalar Docker | [install-docker.sh](install-docker.sh) ou [DOCKER_DEPLOY.md](DOCKER_DEPLOY.md) |

---

## 📂 Estrutura de Arquivos do Projeto

```
kavak-monitor/
├── DOCUMENTACAO.md              ← 📍 Você está aqui!
├── README.md                    ← Visão geral completa
├── QUICKSTART_DOCKER.md         ← Deploy rápido em 5 minutos
├── DOCKER_DEPLOY.md             ← Deploy detalhado e profissional
├── PROTECAO_FALSOS_POSITIVOS.md ← Lógica de detecção
├── otimizacao_raspberry_pi.md   ← Performance no RPi
├── guia_recaptcha.md            ← Referência (não implementado)
├── install-docker.sh            ← Script instalação Docker
├── docker-compose.yml           ← Configuração Docker
├── Dockerfile                   ← Build do container
├── .env.example                 ← Exemplo variáveis ambiente
├── .gitignore                   ← Proteção Git
├── supervisord.conf             ← Supervisor config
├── backend/
│   ├── app.py                   ← API Flask completa
│   └── requirements.txt         ← Dependências Python
└── frontend/
    ├── index.html               ← Interface web
    └── guia_telegram.html       ← Tutorial Telegram visual
```

---

## 💡 Fluxo Recomendado de Leitura

### Para Iniciantes:
1. **[README.md](README.md)** - Entenda o que é o sistema
2. **[QUICKSTART_DOCKER.md](QUICKSTART_DOCKER.md)** - Instale em 5 minutos
3. **[frontend/guia_telegram.html](frontend/guia_telegram.html)** - Configure o bot

### Para Deploy Profissional:
1. **[README.md](README.md)** - Visão geral
2. **[DOCKER_DEPLOY.md](DOCKER_DEPLOY.md)** - Deploy completo
3. **[otimizacao_raspberry_pi.md](otimizacao_raspberry_pi.md)** - Se usar RPi
4. **[DOCKER_DEPLOY.md](DOCKER_DEPLOY.md)** (Backup) - Configure backups

### Para Resolver Problemas:
1. **[QUICKSTART_DOCKER.md](QUICKSTART_DOCKER.md)** - Troubleshooting rápido
2. **[DOCKER_DEPLOY.md](DOCKER_DEPLOY.md)** - Troubleshooting detalhado
3. **[PROTECAO_FALSOS_POSITIVOS.md](PROTECAO_FALSOS_POSITIVOS.md)** - Se tiver falsos alarmes
4. **[otimizacao_raspberry_pi.md](otimizacao_raspberry_pi.md)** - Se estiver lento

---

## 🆘 Precisa de Ajuda?

1. **Primeiro**: Consulte a seção de Troubleshooting no arquivo apropriado acima
2. **Logs**: Use `docker compose logs -f` para ver o que está acontecendo
3. **Issues**: Abra uma issue no repositório do GitHub com:
   - Descrição do problema
   - Logs relevantes
   - Sistema operacional e versão do Docker
   - Arquivo de configuração (sem tokens!)

---

**Boa sorte com seu Kavak Monitor! 🚗📊**
