FROM python:3.12-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    sqlite3 \
    supervisor \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root
RUN useradd -m -u 1000 -s /bin/bash appuser

# Configurar diretório de trabalho
WORKDIR /app

# Copiar e instalar dependências Python
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código do backend
COPY backend/app.py .

# Copiar arquivos do frontend
RUN mkdir -p /app/frontend
COPY frontend/index.html /app/frontend/
COPY frontend/guia_telegram.html /app/frontend/

# Criar diretórios para dados e logs
RUN mkdir -p /app/data /app/logs /var/log/supervisor && \
    chown -R appuser:appuser /app

# Criar arquivo de configuração do supervisord
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expor porta 5004
EXPOSE 5004

# Health check
HEALTHCHECK --interval=60s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5004/health || exit 1

# Comando para executar supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
