FROM nginx:alpine

# Copiar arquivos HTML para o diretório de servir do nginx
COPY index.html /usr/share/nginx/html/
COPY guia_telegram.html /usr/share/nginx/html/

# Health check
HEALTHCHECK --interval=60s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Expor porta 80
EXPOSE 80

# Nginx já tem um CMD padrão, não precisa sobrescrever
