# Quick Start - Deploy em 5 Minutos

Guia rápido para colocar o Kavak Monitor rodando em 5 minutos.

## Pré-requisitos

Antes de começar, você precisa ter:

- ✅ Docker e Docker Compose instalados
- ✅ Telegram Bot Token ([veja como obter](#telegram-bot-token))

## Passo a Passo

### 1. Navegue até o projeto

```bash
cd ~/kavak-monitor
```

### 2. Configure as variáveis de ambiente

```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar configurações
nano .env
```

Preencha **apenas** a linha obrigatória:

```env
TELEGRAM_BOT_TOKEN=seu_token_aqui
```

Salve com `Ctrl+O`, `Enter`, `Ctrl+X`.

### 3. Inicie o sistema

```bash
# Build e start em um comando
docker compose up -d --build
```

### 4. Aguarde containers ficarem prontos

```bash
# Verificar status (aguarde aparecer "healthy")
docker compose ps
```

### 5. Acesse a interface

Abra o navegador em:

- **Localhost**: http://localhost:5004
- **Rede local**: http://IP_DO_SERVIDOR:5004

Exemplo: `http://192.168.1.100:5004`

**Nota**: Se você alterou a variável `PORT` no `.env`, use a porta configurada.

---

## Pronto! 🎉

### 📸 Sistema Rodando
> **Espaço para screenshot**: Interface após login bem-sucedido

![Sistema Rodando](docs/images/sistema-rodando.png)

---

O sistema está rodando. Agora você pode:

1. Clicar em **"Novo Monitoramento"**
2. Preencher os dados do carro
3. Escolher notificação por Telegram
4. Informar seu Chat ID
5. Criar o monitoramento

O sistema vai verificar automaticamente a cada 10 minutos.

---

## Como Obter os Tokens

### Telegram Bot Token

**1 minuto:**

1. Abra o Telegram
2. Busque `@BotFather`
3. Envie `/newbot`
4. Defina nome e username
5. Copie o token que aparece
6. Cole no `.env`

**Precisa de ajuda?** Veja o tutorial completo em `frontend/guia_telegram.html`

---

## Comandos Úteis

```bash
# Ver logs em tempo real
docker compose logs -f

# Parar sistema
docker compose stop

# Reiniciar sistema
docker compose restart

# Ver status
docker compose ps

# Backup do banco de dados
docker cp kavak-backend:/app/data/kavak_monitor.db ~/backup.db
```

---

## Troubleshooting Rápido

### Erro: porta já em uso

```bash
# Mudar porta no .env
nano .env
# Altere PORT=5004 para PORT=8080

# Reiniciar
docker compose down
docker compose up -d

# Acessar em http://localhost:8080
```

### Containers não ficam "healthy"

```bash
# Ver o que está acontecendo
docker compose logs

# Rebuild completo
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Notificações não chegam

1. Verifique se o token no `.env` está correto
2. Confirme que você enviou `/start` para o bot
3. Veja os logs: `docker compose logs backend | grep -i telegram`

---

## Próximos Passos

- 📖 Leia o `README.md` para entender melhor o sistema
- 🔧 Consulte `DOCKER_DEPLOY.md` para deploy detalhado
- ⚡ Veja `otimizacao_raspberry_pi.md` se estiver no RPi
- 💾 Configure backup automatizado (veja `DOCKER_DEPLOY.md`)

---

**Tudo funcionando? Comece a monitorar seus carros da Kavak! 🚗**
