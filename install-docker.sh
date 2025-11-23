#!/bin/bash

# ==================== Kavak Monitor - Installation Script ====================
# Este script automatiza a instalação do Docker e configuração do projeto
# Compatível com: Ubuntu, Debian, Raspberry Pi OS
# ==============================================================================

set -e  # Sair se algum comando falhar

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Banner
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          KAVAK MONITOR - INSTALAÇÃO AUTOMÁTICA          ║"
echo "║           Sistema de Monitoramento de Vendas            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Verificar se está rodando como root
if [[ $EUID -eq 0 ]]; then
   log_error "Este script NÃO deve ser executado como root!"
   log_info "Execute: ./install-docker.sh"
   exit 1
fi

# ==================== 1. Detectar Sistema Operacional ====================

log_info "Detectando sistema operacional..."

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
    log_success "Sistema detectado: $PRETTY_NAME"
else
    log_error "Sistema operacional não suportado"
    exit 1
fi

# ==================== 2. Verificar Docker ====================

log_info "Verificando instalação do Docker..."

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d ' ' -f3 | cut -d ',' -f1)
    log_success "Docker já instalado: v$DOCKER_VERSION"
    DOCKER_INSTALLED=true
else
    log_warning "Docker não encontrado. Será instalado."
    DOCKER_INSTALLED=false
fi

# ==================== 3. Verificar Docker Compose ====================

log_info "Verificando Docker Compose..."

if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    log_success "Docker Compose já instalado"
    COMPOSE_INSTALLED=true
else
    log_warning "Docker Compose não encontrado. Será instalado."
    COMPOSE_INSTALLED=false
fi

# ==================== 4. Instalação do Docker (se necessário) ====================

if [ "$DOCKER_INSTALLED" = false ]; then
    log_info "Instalando Docker..."

    # Atualizar pacotes
    log_info "Atualizando lista de pacotes..."
    sudo apt-get update

    # Instalar dependências
    log_info "Instalando dependências..."
    sudo apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    # Adicionar chave GPG
    log_info "Adicionando chave GPG do Docker..."
    sudo mkdir -p /etc/apt/keyrings

    if [ "$OS" = "raspbian" ] || [ "$OS" = "debian" ]; then
        curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    else
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    fi

    # Adicionar repositório
    log_info "Adicionando repositório do Docker..."

    if [ "$OS" = "raspbian" ] || [ "$OS" = "debian" ]; then
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
          $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    else
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    fi

    # Instalar Docker
    log_info "Instalando pacotes do Docker..."
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    log_success "Docker instalado com sucesso!"
fi

# ==================== 5. Configurar Permissões ====================

log_info "Configurando permissões do Docker..."

if groups $USER | grep -q '\bdocker\b'; then
    log_success "Usuário já está no grupo docker"
else
    log_info "Adicionando usuário ao grupo docker..."
    sudo usermod -aG docker $USER
    log_success "Usuário adicionado ao grupo docker"
    log_warning "IMPORTANTE: Faça logout e login novamente para aplicar as mudanças!"
fi

# ==================== 6. Instalar Docker Compose (se necessário) ====================

if [ "$COMPOSE_INSTALLED" = false ]; then
    log_info "Instalando Docker Compose..."
    sudo apt-get install -y docker-compose
    log_success "Docker Compose instalado com sucesso!"
fi

# ==================== 7. Configurar Projeto ====================

log_info "Configurando projeto Kavak Monitor..."

# Verificar se .env existe
if [ -f .env ]; then
    log_warning "Arquivo .env já existe. Mantendo configuração atual."
else
    log_info "Criando arquivo .env..."

    if [ -f .env.example ]; then
        cp .env.example .env
        log_success "Arquivo .env criado a partir de .env.example"

        echo ""
        log_warning "ATENÇÃO: Você precisa configurar os tokens no arquivo .env!"
        log_info "Execute: nano .env"
        log_info "Preencha: TELEGRAM_BOT_TOKEN e RECAPTCHA_SECRET_KEY"
        echo ""
    else
        log_error ".env.example não encontrado!"
        exit 1
    fi
fi

# ==================== 8. Criar Diretórios ====================

log_info "Criando diretórios necessários..."

mkdir -p backend/data backend/logs
log_success "Diretórios criados"

# ==================== 9. Configuração Interativa (Opcional) ====================

echo ""
read -p "Deseja configurar os tokens agora? (s/n): " CONFIGURE_NOW

if [ "$CONFIGURE_NOW" = "s" ] || [ "$CONFIGURE_NOW" = "S" ]; then
    echo ""
    log_info "=== Configuração de Tokens ==="
    echo ""

    # Telegram Bot Token
    read -p "Digite seu Telegram Bot Token (ou Enter para pular): " TELEGRAM_TOKEN
    if [ ! -z "$TELEGRAM_TOKEN" ]; then
        sed -i "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=$TELEGRAM_TOKEN|" .env
        log_success "Token do Telegram configurado"
    fi

    # reCAPTCHA Secret Key
    read -p "Digite seu reCAPTCHA Secret Key (ou Enter para pular): " RECAPTCHA_SECRET
    if [ ! -z "$RECAPTCHA_SECRET" ]; then
        sed -i "s|^RECAPTCHA_SECRET_KEY=.*|RECAPTCHA_SECRET_KEY=$RECAPTCHA_SECRET|" .env
        log_success "reCAPTCHA Secret Key configurado"
    fi

    # Porta
    read -p "Porta HTTP [80]: " HTTP_PORT
    HTTP_PORT=${HTTP_PORT:-80}
    if ! grep -q "^PORT=" .env; then
        echo "PORT=$HTTP_PORT" >> .env
    else
        sed -i "s|^PORT=.*|PORT=$HTTP_PORT|" .env
    fi
    log_success "Porta configurada: $HTTP_PORT"
fi

# ==================== 10. Resumo ====================

echo ""
log_success "╔══════════════════════════════════════════════════════════╗"
log_success "║            INSTALAÇÃO CONCLUÍDA COM SUCESSO!             ║"
log_success "╚══════════════════════════════════════════════════════════╝"
echo ""

log_info "Próximos passos:"
echo ""
echo "  1. Configure os tokens (se ainda não fez):"
echo "     ${BLUE}nano .env${NC}"
echo ""
echo "  2. Edite o frontend com sua reCAPTCHA Site Key:"
echo "     ${BLUE}nano frontend/index.html${NC}"
echo "     (Procure por RECAPTCHA_SITE_KEY)"
echo ""
echo "  3. Inicie o sistema:"
echo "     ${BLUE}docker compose up -d --build${NC}"
echo ""
echo "  4. Verifique os containers:"
echo "     ${BLUE}docker compose ps${NC}"
echo ""
echo "  5. Acesse a interface web:"
echo "     ${BLUE}http://localhost${NC} (ou http://IP_DO_SERVIDOR)"
echo ""

log_info "Documentação disponível:"
echo "  - README.md                      - Visão geral"
echo "  - QUICKSTART_DOCKER.md           - Quick start"
echo "  - DOCKER_DEPLOY.md               - Deploy completo"
echo "  - guia_recaptcha.md              - Configurar reCAPTCHA"
echo "  - otimizacao_raspberry_pi.md     - Otimização RPi"
echo ""

if [ "$DOCKER_INSTALLED" = false ] || groups $USER | grep -q '\bdocker\b'; then
    log_warning "IMPORTANTE: Faça logout e login novamente (ou execute 'newgrp docker')"
    log_warning "            para aplicar as permissões do Docker!"
fi

echo ""
log_success "Instalação concluída! 🚗"
echo ""
