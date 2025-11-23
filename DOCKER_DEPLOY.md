# Guia Completo de Deploy com Docker

Este guia detalha o processo completo de deploy do Kavak Monitor usando Docker e Docker Compose.

## Índice

1. [Pré-requisitos](#pré-requisitos)
2. [Instalação do Docker](#instalação-do-docker)
3. [Configuração do Projeto](#configuração-do-projeto)
4. [Configuração de Tokens](#configuração-de-tokens)
5. [Build e Deploy](#build-e-deploy)
6. [Verificação](#verificação)
7. [Gerenciamento](#gerenciamento)
8. [Backup e Restore](#backup-e-restore)
9. [Troubleshooting](#troubleshooting)

---

## Pré-requisitos

### Hardware Mínimo

- **RAM**: 512MB (recomendado: 1GB+)
- **CPU**: 1 core (recomendado: 2+ cores)
- **Disco**: 2GB livres (recomendado: 5GB+)
- **Rede**: Conexão internet estável

### Software

- **Sistema Operacional**: Linux (Ubuntu, Debian, Raspbian) ou macOS
- **Docker**: versão 20.10+
- **Docker Compose**: versão 1.29+

### Serviços Externos

- **Telegram Bot Token** (obrigatório)

---

## Instalação do Docker

### Ubuntu/Debian

```bash
# Atualizar pacotes
sudo apt update && sudo apt upgrade -y

# Instalar dependências
sudo apt install -y ca-certificates curl gnupg lsb-release

# Adicionar chave GPG do Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Adicionar repositório
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Adicionar usuário ao grupo docker
sudo usermod -aG docker $USER

# Aplicar mudanças (ou faça logout/login)
newgrp docker

# Verificar instalação
docker --version
docker compose version
```

### Raspberry Pi (Raspbian)

```bash
# Script oficial do Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Adicionar usuário ao grupo docker
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo apt install -y docker-compose

# Verificar
docker --version
docker-compose --version
```

### macOS

```bash
# Instalar Docker Desktop
# Baixe de: https://www.docker.com/products/docker-desktop

# Ou use Homebrew
brew install --cask docker

# Verificar
docker --version
docker compose version
```

---

## Configuração do Projeto

### 1. Obter o Código

```bash
# Navegue até o diretório desejado
cd ~

# Se o projeto está em um repositório Git
git clone <URL_DO_REPOSITORIO> kavak-monitor

# Ou se você tem os arquivos localmente
# Copie todos os arquivos para ~/kavak-monitor

cd kavak-monitor
```

### 2. Verificar Estrutura

```bash
# Verificar se todos os arquivos estão presentes
ls -la

# Deve mostrar:
# - docker-compose.yml
# - Dockerfile
# - .env.example
# - .gitignore
# - backend/
# - frontend/
# - README.md
# - etc.
```

---

## Configuração de Tokens

### 1. Criar Arquivo de Ambiente

```bash
# Copiar exemplo
cp .env.example .env

# Editar configurações
nano .env
```

### 2. Obter Telegram Bot Token

#### Passo a Passo:

1. **Abra o Telegram** no celular ou computador

2. **Busque por @BotFather**

3. **Envie** `/start`

4. **Crie um bot** com `/newbot`

5. **Defina um nome**: exemplo "Kavak Monitor Bot"

6. **Defina um username**: deve terminar com "bot", exemplo "kavak_monitor_bot"

7. **Copie o token** que aparece na mensagem:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

8. **Cole no .env**:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

9. **Inicie conversa com seu bot**: Busque @kavak_monitor_bot e envie `/start`

### 3. Configurações Opcionais

No arquivo `.env`, você pode ajustar:

```env
# Porta HTTP (padrão: 80)
PORT=80

# Performance (defaults são otimizados para RPi 3)
MAX_WORKERS=5
BATCH_SIZE=50
REQUEST_TIMEOUT=5
CHECK_INTERVAL=10

# Segurança
MAX_MONITORAMENTOS_POR_IP=10
```

---

## Build e Deploy

### 1. Build das Imagens

```bash
# Build de todos os serviços
docker compose build

# Ou build sem cache (se houver problemas)
docker compose build --no-cache
```

### 2. Iniciar Containers

```bash
# Iniciar em modo detached (background)
docker compose up -d

# Ou iniciar em foreground (para ver logs)
docker compose up
```

### 3. Aguardar Inicialização

```bash
# Aguardar containers ficarem healthy
watch docker compose ps

# Ou verificar manualmente
docker compose ps
```

Aguarde até todos os containers mostrarem status `healthy`.

---

## Verificação

### 1. Verificar Containers

```bash
# Ver status
docker compose ps

# Deve mostrar algo como:
# NAME              STATUS           PORTS
# kavak-backend     Up (healthy)
# kavak-frontend    Up (healthy)     0.0.0.0:80->80/tcp
```

### 2. Verificar Logs

```bash
# Logs de todos os serviços
docker compose logs

# Logs apenas do backend
docker compose logs backend

# Logs apenas do frontend
docker compose logs frontend

# Logs em tempo real
docker compose logs -f
```

### 3. Testar Endpoints

```bash
# Health check do backend
curl http://localhost:5004/health

# Deve retornar:
# {"status":"healthy","timestamp":"2025-..."}
```

### 4. Acessar Interface Web

Abra o navegador e acesse:

- **Localhost**: http://localhost:5004
- **Rede local**: http://IP_DO_SERVIDOR:5004
- **Exemplo**: http://192.168.1.100:5004

Você deve ver a interface do Kavak Monitor.

**Nota**: Se você alterou a variável `PORT` no `.env`, use a porta configurada.

### 📸 Interface Inicial
> **Espaço para screenshot**: Tela principal do sistema após deploy

![Interface Inicial](docs/images/interface-inicial.png)

---

## Gerenciamento

### Comandos Básicos

```bash
# Parar containers
docker compose stop

# Iniciar containers parados
docker compose start

# Reiniciar containers
docker compose restart

# Parar e remover containers
docker compose down

# Parar e remover containers + volumes (CUIDADO: apaga dados!)
docker compose down -v
```

### Ver Recursos

```bash
# Uso de CPU e memória em tempo real
docker stats

# Ou apenas dos containers do Kavak
docker stats kavak-backend kavak-frontend
```

### Acessar Shell

```bash
# Shell do backend
docker exec -it kavak-backend /bin/bash

# Shell do frontend (Alpine Linux)
docker exec -it kavak-frontend /bin/sh

# Executar comando SQLite no backend
docker exec kavak-backend sqlite3 /app/data/kavak_monitor.db "SELECT COUNT(*) FROM monitoramentos;"
```

### Atualizar Sistema

```bash
# 1. Parar containers
docker compose down

# 2. Atualizar código (se usar git)
git pull

# 3. Rebuild
docker compose build

# 4. Iniciar novamente
docker compose up -d
```

---

## Backup e Restore

### Backup Manual

```bash
# Backup do banco de dados
docker cp kavak-backend:/app/data/kavak_monitor.db ~/backup_kavak_$(date +%Y%m%d_%H%M%S).db

# Backup dos logs
docker cp kavak-backend:/app/logs ~/backup_logs_$(date +%Y%m%d_%H%M%S)

# Backup completo dos volumes
docker run --rm -v kavak-data:/data -v $(pwd):/backup alpine tar czf /backup/kavak-data-backup.tar.gz -C /data .
```

### Backup Automatizado

Criar script `backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/home/$(whoami)/backups/kavak"
mkdir -p $BACKUP_DIR

# Backup com timestamp
DATE=$(date +%Y%m%d_%H%M%S)
docker cp kavak-backend:/app/data/kavak_monitor.db $BACKUP_DIR/kavak_$DATE.db

# Manter apenas últimos 7 backups
ls -t $BACKUP_DIR/kavak_*.db | tail -n +8 | xargs -r rm

echo "Backup criado: kavak_$DATE.db"
```

Adicionar ao crontab:

```bash
# Editar crontab
crontab -e

# Adicionar linha (backup diário às 3h da manhã)
0 3 * * * /home/seu_usuario/kavak-monitor/backup.sh
```

### Restore

```bash
# Parar backend
docker compose stop backend

# Restaurar banco
docker cp ~/backup_kavak_20250101.db kavak-backend:/app/data/kavak_monitor.db

# Reiniciar backend
docker compose start backend
```

---

## Troubleshooting

### Container não inicia

```bash
# Ver logs detalhados
docker compose logs backend

# Verificar configuração
docker compose config

# Rebuild completo
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Erro de permissão

```bash
# Verificar se usuário está no grupo docker
groups

# Se não estiver, adicionar
sudo usermod -aG docker $USER

# Aplicar (ou fazer logout/login)
newgrp docker
```

### Porta 80 já em uso

```bash
# Verificar o que está usando a porta
sudo lsof -i :80

# Ou mudar porta no .env
echo "PORT=8080" >> .env

# Rebuild
docker compose down
docker compose up -d

# Acessar em http://localhost:8080
```

### Banco de dados corrompido

```bash
# Backup do corrompido
docker cp kavak-backend:/app/data/kavak_monitor.db ~/corrupted.db

# Remover banco
docker exec kavak-backend rm /app/data/kavak_monitor.db

# Reiniciar (criará novo banco vazio)
docker compose restart backend
```

### Performance lenta

```bash
# Verificar recursos
docker stats

# Se CPU/RAM alto:
# 1. Editar .env
nano .env

# 2. Reduzir workers
MAX_WORKERS=3

# 3. Aumentar intervalo
CHECK_INTERVAL=15

# 4. Reiniciar
docker compose restart
```

### Notificações não chegam

```bash
# Verificar logs do backend
docker compose logs backend | grep -i telegram

# Verificar token no .env
cat .env | grep TELEGRAM

# Testar manualmente
docker exec kavak-backend python -c "
import requests
token = 'SEU_TOKEN'
chat_id = 'SEU_CHAT_ID'
url = f'https://api.telegram.org/bot{token}/sendMessage'
r = requests.post(url, json={'chat_id': chat_id, 'text': 'Teste'})
print(r.json())
"
```

---

## Próximos Passos

Após o deploy bem-sucedido:

1. **Criar primeiro monitoramento** pela interface web
2. **Configurar backup automatizado** (veja seção Backup)
3. **Monitorar logs** regularmente
4. **Otimizar performance** se necessário (veja `otimizacao_raspberry_pi.md`)
5. **Configurar firewall** se exposto à internet

---

## Recursos Adicionais

- `README.md` - Visão geral do projeto
- `QUICKSTART_DOCKER.md` - Quick start de 5 minutos
- `guia_telegram.html` - Tutorial Telegram visual
- `otimizacao_raspberry_pi.md` - Otimizar para RPi

---

**Deploy bem-sucedido? O sistema agora está monitorando 24/7!**
