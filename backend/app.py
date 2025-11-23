#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kavak Monitor - Sistema de Monitoramento de Vendas
Backend API em Flask com verificação automática e notificações
"""

import os
import sys
import sqlite3
import requests
import logging
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# ==================== CONFIGURAÇÕES ====================

# Variáveis de ambiente com defaults
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '5'))
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '50'))
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '5'))
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '10'))
MAX_MONITORAMENTOS_POR_IP = int(os.getenv('MAX_MONITORAMENTOS_POR_IP', '10'))
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# Prazo de pagamento da Kavak (dias corridos)
PRAZO_DAYS = 45  # 45 dias corridos conforme documentação

# Paths
DB_PATH = os.getenv('DB_PATH', '/app/data/kavak_monitor.db')
LOG_PATH = os.getenv('LOG_PATH', '/app/logs/kavak.log')

# Criar diretórios se não existirem
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

# ==================== LOGGING ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ==================== FLASK APP ====================

app = Flask(__name__)
CORS(app)
app.config['JSON_AS_ASCII'] = False

# ==================== BANCO DE DADOS ====================

def get_db_connection():
    """Cria conexão com o banco de dados SQLite"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa o banco de dados com as tabelas necessárias"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabela de monitoramentos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitoramentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_carro TEXT NOT NULL,
            data_venda DATE NOT NULL,
            contato TEXT NOT NULL,
            tipo_notificacao TEXT NOT NULL,
            status TEXT DEFAULT 'ativo',
            carro_vendido INTEGER DEFAULT 0,
            notificado_venda INTEGER DEFAULT 0,
            notificado_prazo INTEGER DEFAULT 0,
            ip_origem TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultima_verificacao TIMESTAMP,
            falhas_consecutivas INTEGER DEFAULT 0,
            image_url TEXT
        )
    ''')
    
    # Adicionar colunas novas se não existirem (para bancos já criados)
    new_columns = [
        ('image_url', 'TEXT'),
        ('notificado_expirado', 'INTEGER DEFAULT 0'),
        ('ultima_notificacao_semanal', 'TIMESTAMP'),
    ]
    
    for column_name, column_def in new_columns:
        try:
            cursor.execute(f'ALTER TABLE monitoramentos ADD COLUMN {column_name} {column_def}')
            logger.info(f'Coluna {column_name} adicionada com sucesso')
        except sqlite3.OperationalError:
            pass  # Coluna já existe

    # Índices para otimização
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON monitoramentos(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ip ON monitoramentos(ip_origem)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_data_venda ON monitoramentos(data_venda)')

    # Tabela de rate limiting
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rate_limit (
            ip TEXT PRIMARY KEY,
            tentativas INTEGER DEFAULT 0,
            ultima_tentativa TIMESTAMP,
            bloqueado_ate TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

# ==================== RATE LIMITING ====================

def check_rate_limit(ip: str) -> Tuple[bool, str]:
    """
    Verifica se o IP está dentro do limite de requisições
    Retorna: (permitido: bool, mensagem: str)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now()

    # Buscar informações do IP
    cursor.execute('SELECT * FROM rate_limit WHERE ip = ?', (ip,))
    row = cursor.fetchone()

    if row:
        bloqueado_ate = datetime.fromisoformat(row['bloqueado_ate']) if row['bloqueado_ate'] else None
        ultima_tentativa = datetime.fromisoformat(row['ultima_tentativa'])
        tentativas = row['tentativas']

        # Verificar se está bloqueado
        if bloqueado_ate and now < bloqueado_ate:
            tempo_restante = int((bloqueado_ate - now).total_seconds() / 60)
            conn.close()
            return False, f"IP bloqueado. Tente novamente em {tempo_restante} minutos"

        # Reset se passou 1 hora desde última tentativa
        if now - ultima_tentativa > timedelta(hours=1):
            cursor.execute('UPDATE rate_limit SET tentativas = 1, ultima_tentativa = ? WHERE ip = ?',
                         (now.isoformat(), ip))
            conn.commit()
            conn.close()
            return True, ""

        # Incrementar tentativas
        tentativas += 1

        if tentativas > 20:
            # Bloquear por 1 hora
            bloqueado_ate = now + timedelta(hours=1)
            cursor.execute('''UPDATE rate_limit
                            SET tentativas = ?, ultima_tentativa = ?, bloqueado_ate = ?
                            WHERE ip = ?''',
                         (tentativas, now.isoformat(), bloqueado_ate.isoformat(), ip))
            conn.commit()
            conn.close()
            return False, "Limite de 20 tentativas por hora excedido. Bloqueado por 1 hora"

        cursor.execute('UPDATE rate_limit SET tentativas = ?, ultima_tentativa = ? WHERE ip = ?',
                     (tentativas, now.isoformat(), ip))
    else:
        # Primeira tentativa deste IP
        cursor.execute('INSERT INTO rate_limit (ip, tentativas, ultima_tentativa) VALUES (?, 1, ?)',
                     (ip, now.isoformat()))

    conn.commit()
    conn.close()
    return True, ""

# ==================== EXTRAÇÃO DE IMAGEM ====================

def extrair_imagem_carro(link_carro: str) -> Optional[str]:
    """
    Extrai a URL da imagem do carro a partir do link da Kavak
    Usa múltiplas estratégias: tags img, JSON-LD, meta tags, JSON embutido, etc.
    Retorna None se não conseguir extrair
    """
    try:
        import re
        import json
        
        # Fazer requisição para obter o HTML da página
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.kavak.com/',
        }
        
        logger.info(f"🔍 Buscando imagem de: {link_carro}")
        response = requests.get(link_carro, headers=headers, timeout=15, allow_redirects=True)
        
        logger.info(f"📊 Status Code: {response.status_code}")
        logger.info(f"📏 Tamanho do HTML: {len(response.text)} chars")
        
        if response.status_code != 200:
            logger.warning(f"❌ Falha ao acessar {link_carro}: status {response.status_code}")
            return None
        
        html = response.text
        
        def normalize_url(url):
            """Normaliza URL para garantir que tenha protocolo"""
            if not url:
                return None
            url = url.strip().strip('"\'')
            if url.startswith('//'):
                return 'https:' + url
            if not url.startswith('http'):
                return 'https://' + url
            return url
        
        def is_valid_image_url(url):
            """Valida se a URL parece ser uma imagem válida"""
            if not url or len(url) < 20:
                return False
            # Deve ser do domínio Kavak ou ter extensão de imagem
            kavak_domains = ['images.prd.kavak.io', 'cdn.kavak.services', 'kavak.com', 'kavak.io']
            image_exts = ['.jpg', '.jpeg', '.png', '.webp']
            url_lower = url.lower()
            return (any(domain in url_lower for domain in kavak_domains) or
                    any(ext in url_lower for ext in image_exts))
        
        def is_main_car_image(url, html_context=""):
            """
            Tenta determinar se a imagem é a principal do carro (não logo, ícone, banner)
            URLs de imagens principais geralmente:
            - São longas (base64 encoded geralmente > 200 chars)
            - Não contêm palavras de logo/banner/icon
            - Estão em contexto de galeria/slider
            """
            if not url:
                return False
            
            url_lower = url.lower()
            html_context_lower = html_context.lower()
            
            # Filtrar imagens que são claramente não principais
            exclude_words = [
                'logo', 'icon', 'banner', 'avatar', 'badge', 'watermark',
                'favicon', 'social', 'share', 'placeholder', 'default',
                'spinner', 'loading', 'preloader', 'arrow', 'chevron',
                'facebook', 'instagram', 'twitter', 'youtube', 'linkedin'
            ]
            
            if any(word in url_lower for word in exclude_words):
                return False
            
            # Se o contexto HTML menciona essas palavras perto da imagem, provavelmente não é principal
            if any(word in html_context_lower for word in ['logo', 'icon', 'banner', 'social']):
                return False
            
            # URLs muito curtas geralmente são ícones
            if len(url) < 100:
                # Mas se for uma URL base64 muito curta, pode ser válida se não tiver palavras excluídas
                if not any(word in url_lower for word in exclude_words):
                    # Verificar se tem algum indicador de ser imagem principal
                    main_indicators = ['exterior', 'interior', 'front', 'side', 'rear', 'gallery', 'slider']
                    if any(indicator in html_context_lower for indicator in main_indicators):
                        return True
                    # Se não tem indicadores, é provável que seja ícone
                    return False
            
            # URLs longas (base64 encoded) são geralmente imagens principais
            # Geralmente imagens principais têm mais de 200 chars
            if len(url) > 200:
                return True
            
            # Verificar se está em contexto de galeria/slider (indica imagem principal)
            gallery_indicators = [
                'gallery', 'slider', 'carousel', 'main-image', 'hero-image',
                'product-image', 'featured-image', 'primary-image', 'thumbnail'
            ]
            if any(indicator in html_context_lower for indicator in gallery_indicators):
                return True
            
            # Se tem dimensões grandes no contexto ou atributos que indicam imagem principal
            if any(attr in html_context_lower for attr in ['width="', 'width:', 'height="', 'height:']):
                # Tentar extrair dimensões
                width_match = re.search(r'width["\']?\s*[:=]\s*["\']?(\d+)', html_context_lower)
                height_match = re.search(r'height["\']?\s*[:=]\s*["\']?(\d+)', html_context_lower)
                
                if width_match:
                    width = int(width_match.group(1))
                    # Imagens principais geralmente têm pelo menos 400px
                    if width >= 400:
                        return True
                    # Se for muito pequena (< 100px), provavelmente é ícone
                    if width < 100:
                        return False
            
            # Se passou todas as verificações negativas e é do domínio correto, considerar válida
            return True
        
        # Coletar todas as imagens candidatas primeiro, depois escolher a melhor
        candidate_images = []
        
        # ========== ESTRATÉGIA 1: Buscar tags <img> diretamente ==========
        # Muitas vezes a imagem principal está em uma tag img com src ou data-src
        img_patterns = [
            (r'<img[^>]+src=["\']([^"\']*images\.prd\.kavak\.io[^"\']+)["\']', 'src'),
            (r'<img[^>]+data-src=["\']([^"\']*images\.prd\.kavak\.io[^"\']+)["\']', 'data-src'),
            (r'<img[^>]+data-lazy-src=["\']([^"\']*images\.prd\.kavak\.io[^"\']+)["\']', 'data-lazy-src'),
            (r'<img[^>]+srcset=["\']([^"\']*images\.prd\.kavak\.io[^"\']+)["\']', 'srcset'),
            (r'<img[^>]+data-original=["\']([^"\']*images\.prd\.kavak\.io[^"\']+)["\']', 'data-original'),
        ]
        
        for pattern, attr_type in img_patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE)
            for match in matches:
                image_url = normalize_url(match.group(1))
                if image_url and is_valid_image_url(image_url):
                    # Extrair contexto HTML ao redor da tag (até 200 chars antes e depois)
                    start = max(0, match.start() - 200)
                    end = min(len(html), match.end() + 200)
                    context = html[start:end]
                    
                    # Obter a tag img completa para análise
                    tag_match = re.search(r'<img[^>]*>', context, re.IGNORECASE)
                    tag_html = tag_match.group(0) if tag_match else context
                    
                    if is_main_car_image(image_url, tag_html):
                        score = len(image_url)  # URLs mais longas = mais provável de ser principal
                        candidate_images.append((image_url, score, 'tag-img-' + attr_type, tag_html))
        
        # Buscar qualquer tag img com domínio Kavak (fallback)
        img_generic = re.finditer(
            r'<img[^>]+(?:src|data-src|data-lazy-src|data-original)=["\']([^"\']*(?:images\.prd\.kavak\.io|cdn\.kavak\.services)[^"\']+)["\']',
            html, re.IGNORECASE
        )
        for match in img_generic:
            image_url = normalize_url(match.group(1))
            if image_url and is_valid_image_url(image_url):
                start = max(0, match.start() - 200)
                end = min(len(html), match.end() + 200)
                context = html[start:end]
                tag_match = re.search(r'<img[^>]*>', context, re.IGNORECASE)
                tag_html = tag_match.group(0) if tag_match else context
                
                if is_main_car_image(image_url, tag_html):
                    score = len(image_url)
                    candidate_images.append((image_url, score, 'tag-img-generic', tag_html))
        
        # ========== ESTRATÉGIA 2: Extrair JSON embutido no HTML ==========
        # Muitos sites SPA colocam dados em scripts JSON
        json_scripts = [
            r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
            r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'window\.__APOLLO_STATE__\s*=\s*({.*?});',
        ]
        
        for pattern in json_scripts:
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                try:
                    json_data = match.group(1)
                    if json_data:
                        # Tentar parsear o JSON
                        data = json.loads(json_data)
                        
                        found_urls = []
                        def find_images_in_dict(obj, path="", visited=None, max_depth=10):
                            if visited is None:
                                visited = set()
                            if len(path.split('.')) > max_depth:
                                return
                            
                            obj_id = id(obj)
                            if obj_id in visited:
                                return
                            visited.add(obj_id)
                            
                            if isinstance(obj, dict):
                                image_keys = ['image', 'photo', 'picture', 'thumbnail', 'img', 'url', 'src', 'mainimage', 'primaryimage']
                                for key, value in obj.items():
                                    if isinstance(key, str):
                                        key_lower = key.lower()
                                        if any(ik in key_lower for ik in image_keys):
                                            if isinstance(value, str) and is_valid_image_url(value):
                                                result = normalize_url(value)
                                                if result and is_main_car_image(result, str(obj)):
                                                    found_urls.append((result, 850, 'json-embedded'))
                                    find_images_in_dict(value, f"{path}.{key}", visited, max_depth)
                            elif isinstance(obj, list):
                                for i, item in enumerate(obj[:50]):
                                    find_images_in_dict(item, f"{path}[{i}]", visited, max_depth)
                            elif isinstance(obj, str) and is_valid_image_url(obj):
                                result = normalize_url(obj)
                                if result and is_main_car_image(result, ""):
                                    found_urls.append((result, 600, 'json-embedded-string'))
                        
                        find_images_in_dict(data)
                        for url, base_score, source in found_urls:
                            score = base_score + len(url)
                            candidate_images.append((url, score, source, ''))
                except (json.JSONDecodeError, Exception) as e:
                    continue
        
        # ========== ESTRATÉGIA 3: JSON-LD (estrutura de dados) ==========
        # JSON-LD geralmente tem dados estruturados do produto
        jsonld_patterns = [
            (r'"image"\s*:\s*["\']([^"\']*images\.prd\.kavak\.io[^"\']+)["\']', 800),
            (r'image["\']\s*:\s*["\']([^"\']*images\.prd\.kavak\.io[^"\']+)["\']', 800),
            (r'thumbnailUrl["\']\s*:\s*["\']([^"\']*images\.prd\.kavak\.io[^"\']+)["\']', 700),
            (r'"@type"\s*:\s*["\']ImageObject["\'][^}]*"contentUrl"\s*:\s*["\']([^"\']+)["\']', 750),
        ]
        
        for pattern, base_score in jsonld_patterns:
            jsonld_match = re.search(pattern, html, re.IGNORECASE)
            if jsonld_match:
                image_url = normalize_url(jsonld_match.group(1))
                if image_url and is_valid_image_url(image_url):
                    start = max(0, jsonld_match.start() - 200)
                    end = min(len(html), jsonld_match.end() + 200)
                    context = html[start:end]
                    if is_main_car_image(image_url, context):
                        score = base_score + len(image_url)
                        candidate_images.append((image_url, score, 'json-ld', context))
        
        # ========== ESTRATÉGIA 4: Meta tags (og:image, twitter:image) ==========
        # Meta tags geralmente têm a imagem principal (alta prioridade)
        og_patterns = [
            (r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', 'og-image', 1000),  # Alta prioridade
            (r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:image["\']', 'og-image-alt', 1000),
            (r'<meta\s+name=["\']twitter:image["\']\s+content=["\']([^"\']+)["\']', 'twitter-image', 900),
        ]
        
        for pattern, tag_type, base_score in og_patterns:
            og_match = re.search(pattern, html, re.IGNORECASE)
            if og_match:
                image_url = normalize_url(og_match.group(1))
                if image_url and is_valid_image_url(image_url):
                    start = max(0, og_match.start() - 100)
                    end = min(len(html), og_match.end() + 100)
                    context = html[start:end]
                    if is_main_car_image(image_url, context):
                        score = base_score + len(image_url)
                        candidate_images.append((image_url, score, tag_type, context))
        
        # ========== ESTRATÉGIA 5: Buscar todas ocorrências de images.prd.kavak.io ==========
        # Base64 pode ter = em qualquer lugar e termina com =, == ou nenhum =
        all_prd_urls = re.findall(r'https?://images\.prd\.kavak\.io/[A-Za-z0-9+/=_-]+(?=["\'>\s<&\)]|$)', html, re.IGNORECASE)
        if all_prd_urls:
            for url in all_prd_urls:
                normalized = normalize_url(url)
                if normalized and is_valid_image_url(normalized) and len(normalized) > 100:
                    # Encontrar contexto (onde aparece no HTML)
                    url_pos = html.find(url)
                    if url_pos >= 0:
                        start = max(0, url_pos - 200)
                        end = min(len(html), url_pos + len(url) + 200)
                        context = html[start:end]
                        if is_main_car_image(normalized, context):
                            score = len(normalized)  # URLs mais longas = mais provável
                            candidate_images.append((normalized, score, 'prd-findall', context))
        
        # ========== ESTRATÉGIA 6: Buscar sem protocolo (fallback) ==========
        all_prd_urls_no_proto = re.findall(r'images\.prd\.kavak\.io/[A-Za-z0-9+/=_-]+(?=["\'>\s<&\)]|$)', html, re.IGNORECASE)
        for url in all_prd_urls_no_proto:
            normalized = normalize_url('https://' + url)
            if normalized and is_valid_image_url(normalized) and len(normalized) > 100:
                url_pos = html.find(url)
                if url_pos >= 0:
                    start = max(0, url_pos - 200)
                    end = min(len(html), url_pos + len(url) + 200)
                    context = html[start:end]
                    if is_main_car_image(normalized, context):
                        score = len(normalized)
                        candidate_images.append((normalized, score, 'prd-no-proto', context))
        
        # ========== ESTRATÉGIA 7: CDN Kavak ==========
        cdn_patterns = [
            r'https://cdn\.kavak\.services[^"\'>\s\)]+\.(jpg|jpeg|png|webp)',
            r'cdn\.kavak\.services[^"\'>\s\)]+\.(jpg|jpeg|png|webp)',
        ]
        for pattern in cdn_patterns:
            cdn_match = re.search(pattern, html, re.IGNORECASE)
            if cdn_match:
                image_url = normalize_url(cdn_match.group(0))
                if image_url and is_valid_image_url(image_url):
                    start = max(0, cdn_match.start() - 200)
                    end = min(len(html), cdn_match.end() + 200)
                    context = html[start:end]
                    if is_main_car_image(image_url, context):
                        score = 500 + len(image_url)
                        candidate_images.append((image_url, score, 'cdn', context))
        
        # ========== ESTRATÉGIA 8: Qualquer imagem do domínio Kavak ==========
        kavak_image = re.search(r'https://[^"\'>\s\)]*kavak[^"\'>\s\)]*\.(jpg|jpeg|png|webp)', html, re.IGNORECASE)
        if kavak_image:
            image_url = normalize_url(kavak_image.group(0))
            if image_url and is_valid_image_url(image_url):
                start = max(0, kavak_image.start() - 200)
                end = min(len(html), kavak_image.end() + 200)
                context = html[start:end]
                if is_main_car_image(image_url, context):
                    score = 300 + len(image_url)
                    candidate_images.append((image_url, score, 'kavak-domain', context))
        
        # ========== ESCOLHER A MELHOR IMAGEM CANDIDATA ==========
        if candidate_images:
            # Remover duplicatas mantendo apenas a com maior score
            unique_candidates = {}
            for url, score, source, context in candidate_images:
                if url not in unique_candidates or unique_candidates[url][1] < score:
                    unique_candidates[url] = (url, score, source, context)
            
            # Ordenar por score (maior primeiro)
            sorted_candidates = sorted(unique_candidates.values(), key=lambda x: x[1], reverse=True)
            
            if sorted_candidates:
                best_image = sorted_candidates[0]
                image_url, score, source, context = best_image
                logger.info(f"✅ Imagem extraída ({source}, score: {score}): {image_url[:100]}...")
                logger.info(f"   Total de {len(sorted_candidates)} candidatas encontradas, escolhida a melhor")
                return image_url
        
        # Debug final: verificar o que tem no HTML relacionado a imagens
        logger.warning(f"❌ Nenhuma imagem encontrada para {link_carro}")
        
        # Verificar se há alguma referência a images.prd.kavak.io no HTML
        if 'images.prd.kavak.io' in html.lower():
            logger.warning(f"⚠️ ATENÇÃO: 'images.prd.kavak.io' encontrado no HTML mas não capturado!")
            # Tentar pegar uma amostra onde aparece
            matches = re.finditer(r'images\.prd\.kavak\.io[^"\'>\s\)]{0,100}', html, re.IGNORECASE)
            for i, match in enumerate(list(matches)[:3]):  # Primeiras 3 ocorrências
                start = max(0, match.start() - 50)
                end = min(len(html), match.end() + 50)
                logger.warning(f"   Contexto {i+1}: ...{html[start:end]}...")
        
        # Verificar se há meta og:image de qualquer tipo
        if 'og:image' in html.lower():
            logger.warning(f"⚠️ 'og:image' encontrado no HTML mas não capturado!")
            og_matches = re.findall(r'og:image[^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if og_matches:
                logger.warning(f"   Possíveis URLs og:image: {og_matches[:3]}")
        
        return None
        
    except requests.Timeout:
        logger.error(f"✗ Timeout ao acessar {link_carro}")
        return None
    except Exception as e:
        logger.error(f"✗ Erro ao extrair imagem de {link_carro}: {str(e)}")
        return None

# ==================== CÁLCULO DE DATAS ====================

def calcular_dias_restantes(data_venda_str: str) -> Tuple[int, datetime]:
    """
    Calcula os dias restantes até o prazo de pagamento da Kavak (45 dias corridos)
    
    Args:
        data_venda_str: Data da venda no formato ISO (YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS)
    
    Returns:
        Tuple[int, datetime]: (dias_restantes, prazo_final)
    """
    # Converter data_venda para início do dia (00:00:00) para cálculo correto
    if 'T' in data_venda_str:
        data_venda = datetime.fromisoformat(data_venda_str.split('T')[0])
    else:
        data_venda = datetime.fromisoformat(data_venda_str)
    
    # Data de venda no início do dia
    data_venda = data_venda.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Usar apenas a DATA (sem hora) para evitar problemas de timezone
    # Isso garante que o cálculo seja baseado apenas em dias calendário
    data_venda_date = data_venda.date()
    hoje_date = datetime.now().date()
    
    # Calcular prazo final (data_venda + 45 dias corridos)
    prazo_final_date = data_venda_date + timedelta(days=PRAZO_DAYS)
    prazo_final = datetime.combine(prazo_final_date, datetime.min.time())
    
    # Calcular dias restantes usando apenas dates (mais preciso)
    # Exemplo: se hoje é 04/11 e prazo é 20/11
    # (20/11 - 04/11) = 16 dias
    dias_restantes = (prazo_final_date - hoje_date).days
    
    # Garantir que não retorne negativo
    dias_restantes = max(0, dias_restantes)
    
    return dias_restantes, prazo_final

# ==================== NOTIFICAÇÕES ====================

def enviar_notificacao_telegram(chat_id: str, mensagem: str) -> bool:
    """Envia mensagem via Telegram Bot API"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Telegram bot token not configured")
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': mensagem,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=payload, timeout=10)
        success = response.status_code == 200

        if success:
            logger.info(f"Telegram notification sent to {chat_id}")
        else:
            logger.error(f"Failed to send Telegram notification: {response.text}")

        return success
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        return False

def enviar_notificacao(tipo: str, contato: str, mensagem: str) -> bool:
    """Envia notificação via Telegram"""
    if tipo == 'telegram':
        return enviar_notificacao_telegram(contato, mensagem)
    else:
        logger.error(f"Unknown notification type: {tipo}")
        return False

# ==================== VERIFICAÇÃO DE LINKS ====================

@lru_cache(maxsize=500)
def verificar_link_com_cache(link: str, timestamp: int) -> bool:
    """
    Verifica se o link está online (com cache de 5 minutos)
    timestamp é usado para invalidar cache a cada 5 minutos
    """
    try:
        response = requests.get(
            link,
            timeout=REQUEST_TIMEOUT,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        return response.status_code == 200
    except Exception as e:
        logger.debug(f"Error checking link {link}: {e}")
        return False

def verificar_link(link: str) -> bool:
    """Verifica se o link está online"""
    # Cache timestamp em blocos de 5 minutos
    cache_timestamp = int(datetime.now().timestamp() / 300)
    return verificar_link_com_cache(link, cache_timestamp)

def processar_monitoramento(monitoramento: Dict) -> Optional[Dict]:
    """
    Processa um único monitoramento
    Retorna dict com atualizações necessárias ou None
    """
    mon_id = monitoramento['id']
    link = monitoramento['link_carro']
    
    logger.debug(f"Processing monitoring {mon_id}")

    updates = {
        'id': mon_id,
        'ultima_verificacao': datetime.now().isoformat()
    }

    # Calcular dias restantes usando função auxiliar
    dias_restantes, prazo_final = calcular_dias_restantes(monitoramento['data_venda'])
    
    # Converter data_venda para datetime para formatação
    if 'T' in monitoramento['data_venda']:
        data_venda = datetime.fromisoformat(monitoramento['data_venda'].split('T')[0])
    else:
        data_venda = datetime.fromisoformat(monitoramento['data_venda'])
    data_venda = data_venda.replace(hour=0, minute=0, second=0, microsecond=0)

    # Verificar expiração
    if dias_restantes <= 0:
        updates['status'] = 'expirado'
        # Notificar expiração se ainda não foi notificado
        if not monitoramento.get('notificado_expirado', 0):
            prazo_final_str = prazo_final.strftime('%d/%m/%Y')
            mensagem = (
                f"⏰ <b>Monitoramento Expirado</b>\n\n"
                f"O prazo de {PRAZO_DAYS} dias da Kavak foi atingido!\n\n"
                f"📅 Data da venda: {data_venda.strftime('%d/%m/%Y')}\n"
                f"📅 Prazo final: {prazo_final_str}\n"
                f"🔗 Link: {link}\n\n"
                f"O monitoramento foi desativado automaticamente.\n"
                f"Entre em contato com a Kavak para verificar o status do pagamento."
            )
            
            if enviar_notificacao(
                monitoramento['tipo_notificacao'],
                monitoramento['contato'],
                mensagem
            ):
                updates['notificado_expirado'] = 1
        return updates

    # Verificar se link está online
    link_online = verificar_link(link)

    if not link_online:
        # Link offline - incrementar falhas
        falhas = monitoramento['falhas_consecutivas'] + 1
        updates['falhas_consecutivas'] = falhas

        # 2 falhas consecutivas = carro vendido
        if falhas >= 2 and not monitoramento['carro_vendido']:
            updates['carro_vendido'] = 1

            # Enviar notificação de venda
            if not monitoramento['notificado_venda']:
                prazo_final_str = prazo_final.strftime('%d/%m/%Y')
                mensagem = (
                    f"🎉 <b>Carro Vendido!</b>\n\n"
                    f"Seu carro da Kavak foi vendido!\n\n"
                    f"📅 <b>Data da venda para Kavak:</b> {data_venda.strftime('%d/%m/%Y')}\n"
                    f"📆 <b>Prazo final para pagamento:</b> {prazo_final_str}\n"
                    f"⏰ <b>Dias restantes:</b> {dias_restantes} dias\n\n"
                    f"🔗 <b>Link do carro:</b> {link}\n\n"
                    f"✅ O monitoramento será desativado automaticamente quando o prazo expirar.\n"
                    f"Você não receberá mais notificações semanais deste monitoramento."
                )

                if enviar_notificacao(
                    monitoramento['tipo_notificacao'],
                    monitoramento['contato'],
                    mensagem
                ):
                    updates['notificado_venda'] = 1
    else:
        # Link voltou ao ar - resetar falhas
        if monitoramento['falhas_consecutivas'] > 0:
            updates['falhas_consecutivas'] = 0

    # Alerta de prazo (5 dias ou menos)
    if dias_restantes <= 5 and dias_restantes > 0 and not monitoramento['notificado_prazo']:
        prazo_final_str = prazo_final.strftime('%d/%m/%Y')
        mensagem = (
            f"⏰ <b>Alerta de Prazo!</b>\n\n"
            f"Faltam apenas <b>{dias_restantes} dias</b> para o prazo de {PRAZO_DAYS} dias da Kavak!\n\n"
            f"Link: {link}\n"
            f"Data da venda: {data_venda.strftime('%d/%m/%Y')}\n"
            f"Prazo expira em: {prazo_final_str}\n\n"
            f"🚨 Prepare-se para receber o pagamento ou entre em contato com a Kavak."
        )

        if enviar_notificacao(
            monitoramento['tipo_notificacao'],
            monitoramento['contato'],
            mensagem
        ):
            updates['notificado_prazo'] = 1

    # Notificação semanal - avisar que o carro ainda não foi vendido
    # Apenas se o carro ainda não foi vendido e o status é ativo
    if not monitoramento.get('carro_vendido', 0) and monitoramento.get('status') == 'ativo':
        # Calcular dias desde a venda
        dias_desde_venda = (datetime.now() - data_venda).days
        
        # Verificar se deve enviar notificação nas sextas-feiras às 10h
        agora = datetime.now()
        ultima_notificacao = monitoramento.get('ultima_notificacao_semanal')
        deve_notificar_semanal = False
        
        # Verificar se é sexta-feira (weekday() == 4) e se está entre 10h00 e 10h59
        if agora.weekday() == 4 and agora.hour == 10:
            if not ultima_notificacao:
                # Primeira notificação se já passou pelo menos 1 dia desde a venda
                if dias_desde_venda >= 1:
                    deve_notificar_semanal = True
            else:
                # Verificar se a última notificação não foi hoje
                try:
                    ultima_data = datetime.fromisoformat(ultima_notificacao)
                    # Só notificar se a última notificação foi em outra data
                    if ultima_data.date() < agora.date():
                        deve_notificar_semanal = True
                except (ValueError, TypeError):
                    # Se não conseguir parsear a data, enviar se já passou pelo menos 1 dia
                    if dias_desde_venda >= 1:
                        deve_notificar_semanal = True
        
        if deve_notificar_semanal and dias_restantes > 0:
            prazo_final_str = prazo_final.strftime('%d/%m/%Y')
            dias_percentual = round((dias_desde_venda / PRAZO_DAYS) * 100, 1)
            
            mensagem_semanal = (
                f"📊 <b>Atualização Semanal - Carro Ainda Disponível</b>\n\n"
                f"Seu carro ainda não foi vendido e está disponível na Kavak.\n\n"
                f"📅 <b>Dias desde a venda:</b> {dias_desde_venda} dias ({dias_percentual}% do prazo)\n"
                f"⏰ <b>Dias restantes:</b> {dias_restantes} dias\n"
                f"📆 <b>Prazo final para pagamento:</b> {prazo_final_str}\n\n"
                f"🔗 <b>Link do carro:</b> {link}\n\n"
                f"✅ O monitoramento continua ativo.\n"
                f"Você será notificado automaticamente quando:\n"
                f"• O carro for vendido\n"
                f"• Faltarem 5 dias para o prazo final"
            )
            
            if enviar_notificacao(
                monitoramento['tipo_notificacao'],
                monitoramento['contato'],
                mensagem_semanal
            ):
                updates['ultima_notificacao_semanal'] = datetime.now().isoformat()

    return updates

def verificar_monitoramentos():
    """
    Tarefa agendada: verifica monitoramentos ativos em lotes
    Executa a cada CHECK_INTERVAL minutos
    """
    logger.info("Starting monitoring check cycle")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Buscar monitoramentos ativos (os 50 mais antigos)
    cursor.execute('''
        SELECT * FROM monitoramentos
        WHERE status = 'ativo'
        ORDER BY ultima_verificacao ASC
        LIMIT ?
    ''', (BATCH_SIZE,))

    monitoramentos = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not monitoramentos:
        logger.info("No active monitorings to check")
        return

    logger.info(f"Checking {len(monitoramentos)} monitorings")

    # Processar em paralelo com ThreadPoolExecutor
    updates_list = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(processar_monitoramento, mon): mon
            for mon in monitoramentos
        }

        for future in as_completed(futures):
            try:
                updates = future.result()
                if updates:
                    updates_list.append(updates)
            except Exception as e:
                mon = futures[future]
                logger.error(f"Error processing monitoring {mon['id']}: {e}")

    # Aplicar atualizações no banco
    if updates_list:
        conn = get_db_connection()
        cursor = conn.cursor()

        for updates in updates_list:
            mon_id = updates.pop('id')

            set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
            values = list(updates.values()) + [mon_id]

            cursor.execute(f'UPDATE monitoramentos SET {set_clause} WHERE id = ?', values)

        conn.commit()
        conn.close()

        logger.info(f"Updated {len(updates_list)} monitorings")

    logger.info("Monitoring check cycle completed")

# ==================== API ENDPOINTS ====================

@app.route('/health', methods=['GET'])
def health_check_simple():
    """Simple health check endpoint"""
    return "healthy\n", 200

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/')
def index():
    """Serve index.html"""
    return send_file('/app/frontend/index.html')

@app.route('/guia_telegram.html')
def guia_telegram():
    """Serve guia_telegram.html"""
    return send_file('/app/frontend/guia_telegram.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Retorna estatísticas gerais"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) as total FROM monitoramentos WHERE status = "ativo"')
    ativos = cursor.fetchone()['total']

    cursor.execute('SELECT COUNT(*) as total FROM monitoramentos WHERE carro_vendido = 1')
    vendidos = cursor.fetchone()['total']

    cursor.execute('SELECT COUNT(*) as total FROM monitoramentos WHERE status = "expirado"')
    expirados = cursor.fetchone()['total']

    conn.close()

    return jsonify({
        'ativos': ativos,
        'vendidos': vendidos,
        'expirados': expirados,
        'total': ativos + expirados
    })

@app.route('/api/monitoramentos', methods=['GET'])
def listar_monitoramentos():
    """Lista todos os monitoramentos com paginação"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    status = request.args.get('status', None)

    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor()

    # Query com filtro opcional de status
    if status:
        cursor.execute('''
            SELECT * FROM monitoramentos
            WHERE status = ?
            ORDER BY data_criacao DESC
            LIMIT ? OFFSET ?
        ''', (status, per_page, offset))
        monitor_rows = cursor.fetchall()

        cursor.execute('SELECT COUNT(*) as total FROM monitoramentos WHERE status = ?', (status,))
    else:
        cursor.execute('''
            SELECT * FROM monitoramentos
            ORDER BY data_criacao DESC
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        monitor_rows = cursor.fetchall()

        cursor.execute('SELECT COUNT(*) as total FROM monitoramentos')

    monitoramentos = []
    for row in monitor_rows:
        mon = dict(row)

        # Calcular dias restantes usando função auxiliar
        dias_restantes, _ = calcular_dias_restantes(mon['data_venda'])
        mon['dias_restantes'] = dias_restantes

        # DEBUG: Log image_url
        logger.debug(f"Monitoramento {mon['id']}: image_url = {mon.get('image_url', 'NÃO EXISTE')}")

        monitoramentos.append(mon)

    total = cursor.fetchone()['total']
    conn.close()

    return jsonify({
        'monitoramentos': monitoramentos,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })

@app.route('/api/monitoramentos', methods=['POST'])
def criar_monitoramento():
    """Cria novo monitoramento"""
    data = request.get_json()

    # Validações
    required_fields = ['link_carro', 'data_venda', 'contato', 'tipo_notificacao']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo obrigatório: {field}'}), 400

    # Validar domínio Kavak
    link = data['link_carro']
    if 'kavak.com' not in link.lower():
        return jsonify({'error': 'Link deve ser da plataforma Kavak (kavak.com)'}), 400

    # Validar tipo de notificação
    tipo = data['tipo_notificacao']
    if tipo != 'telegram':
        return jsonify({'error': 'Tipo de notificação deve ser "telegram"'}), 400

    # Validar data
    try:
        data_venda = datetime.fromisoformat(data['data_venda'])
        if data_venda > datetime.now():
            return jsonify({'error': 'Data da venda não pode ser no futuro'}), 400
    except ValueError:
        return jsonify({'error': 'Data inválida'}), 400

    # Obter IP real (considerando proxy)
    ip_origem = request.headers.get('X-Real-IP', request.remote_addr)

    # Verificar rate limiting
    permitido, mensagem = check_rate_limit(ip_origem)
    if not permitido:
        return jsonify({'error': mensagem}), 429

    # Verificar limite de monitoramentos por IP
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT COUNT(*) as total FROM monitoramentos
        WHERE ip_origem = ? AND status = 'ativo'
    ''', (ip_origem,))

    total = cursor.fetchone()['total']

    if total >= MAX_MONITORAMENTOS_POR_IP:
        conn.close()
        return jsonify({
            'error': f'Limite de {MAX_MONITORAMENTOS_POR_IP} monitoramentos ativos por IP atingido'
        }), 429

    # Extrair imagem do carro
    logger.info(f"🔍 Tentando extrair imagem do link: {link}")
    image_url = extrair_imagem_carro(link)
    
    if image_url:
        logger.info(f"✅ Imagem extraída com sucesso: {image_url[:100]}...")
    else:
        logger.warning(f"⚠️ Não foi possível extrair imagem de: {link}")
    
    # Inserir monitoramento
    cursor.execute('''
        INSERT INTO monitoramentos
        (link_carro, data_venda, contato, tipo_notificacao, ip_origem, ultima_verificacao, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        link,
        data_venda.isoformat(),
        data['contato'],
        tipo,
        ip_origem,
        datetime.now().isoformat(),
        image_url
    ))

    mon_id = cursor.lastrowid
    conn.commit()
    
    # Verificar o que foi salvo
    cursor.execute('SELECT image_url FROM monitoramentos WHERE id = ?', (mon_id,))
    saved_image = cursor.fetchone()['image_url']
    logger.info(f"💾 Image URL salva no banco (ID {mon_id}): {saved_image if saved_image else 'NULL'}")
    
    conn.close()

    logger.info(f"✅ New monitoring created: {mon_id} from IP {ip_origem}")

    # Enviar mensagem de boas-vindas
    dias_restantes, prazo_final = calcular_dias_restantes(data_venda.isoformat())
    prazo_expira = prazo_final.strftime('%d/%m/%Y')

    mensagem_boas_vindas = (
        f"✅ <b>Monitoramento Ativado!</b>\n\n"
        f"Obrigado por usar o Kavak Monitor!\n\n"
        f"<b>Como funciona:</b>\n"
        f"• Verifico seu link a cada 10 minutos\n"
        f"• Quando o carro for vendido (link sair do ar), você será notificado\n"
        f"• Quando faltarem 5 dias para o prazo, envio um alerta\n\n"
        f"<b>Seu monitoramento:</b>\n"
        f"📅 Prazo de {PRAZO_DAYS} dias expira em: {prazo_expira}\n"
        f"⏰ Dias restantes: {dias_restantes} dias\n\n"
        f"Fique tranquilo, estou monitorando! 🚗"
    )

    # Tentar enviar mensagem de boas-vindas (não bloqueia se falhar)
    try:
        enviar_notificacao(tipo, data['contato'], mensagem_boas_vindas)
        logger.info(f"Welcome message sent for monitoring {mon_id}")
    except Exception as e:
        logger.warning(f"Failed to send welcome message for monitoring {mon_id}: {e}")

    return jsonify({
        'success': True,
        'id': mon_id,
        'message': 'Monitoramento criado com sucesso'
    }), 201

@app.route('/api/test-image-extraction', methods=['POST'])
def test_image_extraction():
    """Endpoint de teste para extração de imagem"""
    data = request.get_json()
    
    if 'link_carro' not in data:
        return jsonify({'error': 'Campo link_carro é obrigatório'}), 400
    
    link_carro = data['link_carro']
    
    if 'kavak.com' not in link_carro.lower():
        return jsonify({'error': 'Link deve ser da plataforma Kavak'}), 400
    
    logger.info(f"🔬 Testando extração de imagem para: {link_carro}")
    
    # Fazer requisição e pegar HTML
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        response = requests.get(link_carro, headers=headers, timeout=15, allow_redirects=True)
        html = response.text
        
        # Contar ocorrências de images.prd.kavak.io
        prd_count = html.lower().count('images.prd.kavak.io')
        og_count = html.lower().count('og:image')
        
        # Extrair imagem
        image_url = extrair_imagem_carro(link_carro)
        
        return jsonify({
            'link_carro': link_carro,
            'image_url': image_url,
            'success': image_url is not None,
            'debug': {
                'html_size': len(html),
                'status_code': response.status_code,
                'prd_count': prd_count,
                'og_image_count': og_count,
                'html_sample': html[:500] if len(html) > 0 else 'HTML vazio'
            }
        })
    except Exception as e:
        logger.error(f"Erro no teste: {str(e)}")
        return jsonify({
            'link_carro': link_carro,
            'image_url': None,
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/monitoramentos/<int:mon_id>', methods=['DELETE'])
def deletar_monitoramento(mon_id):
    """Deleta um monitoramento e envia notificação"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Buscar dados do monitoramento antes de deletar para enviar notificação
    cursor.execute('SELECT * FROM monitoramentos WHERE id = ?', (mon_id,))
    monitoramento = cursor.fetchone()

    if not monitoramento:
        conn.close()
        return jsonify({'error': 'Monitoramento não encontrado'}), 404

    mon_dict = dict(monitoramento)
    
    # Deletar o monitoramento
    cursor.execute('DELETE FROM monitoramentos WHERE id = ?', (mon_id,))
    conn.commit()
    conn.close()

    logger.info(f"Monitoring deleted: {mon_id}")

    # Enviar notificação de exclusão
    try:
        dias_restantes, prazo_final = calcular_dias_restantes(mon_dict['data_venda'])
        
        # Converter data_venda para datetime para formatação
        if 'T' in mon_dict['data_venda']:
            data_venda = datetime.fromisoformat(mon_dict['data_venda'].split('T')[0])
        else:
            data_venda = datetime.fromisoformat(mon_dict['data_venda'])
        data_venda = data_venda.replace(hour=0, minute=0, second=0, microsecond=0)
        
        mensagem_exclusao = (
            f"🗑️ <b>Monitoramento Excluído</b>\n\n"
            f"O monitoramento do seu carro foi excluído.\n\n"
            f"📅 <b>Data da venda:</b> {data_venda.strftime('%d/%m/%Y')}\n"
            f"🔗 <b>Link:</b> {mon_dict['link_carro']}\n"
        )
        
        if dias_restantes > 0:
            prazo_final_str = prazo_final.strftime('%d/%m/%Y')
            mensagem_exclusao += (
                f"⏰ <b>Dias restantes:</b> {dias_restantes} dias\n"
                f"📆 <b>Prazo final:</b> {prazo_final_str}\n\n"
            )
        
        mensagem_exclusao += (
            f"Se precisar monitorar novamente, crie um novo monitoramento."
        )
        
        enviar_notificacao(
            mon_dict['tipo_notificacao'],
            mon_dict['contato'],
            mensagem_exclusao
        )
        logger.info(f"Notification sent for deleted monitoring {mon_id}")
    except Exception as e:
        logger.warning(f"Failed to send deletion notification for monitoring {mon_id}: {e}")

    return jsonify({'success': True, 'message': 'Monitoramento deletado com sucesso'})

@app.route('/api/monitoramentos/<int:mon_id>/update-image', methods=['POST'])
def atualizar_imagem_monitoramento(mon_id):
    """Re-extrai a imagem de um monitoramento específico"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar monitoramento
    cursor.execute('SELECT link_carro FROM monitoramentos WHERE id = ?', (mon_id,))
    monitoramento = cursor.fetchone()
    
    if not monitoramento:
        conn.close()
        return jsonify({'error': 'Monitoramento não encontrado'}), 404
    
    link_carro = monitoramento['link_carro']
    
    # Extrair imagem
    logger.info(f"🔄 Re-extraindo imagem para monitoramento {mon_id}: {link_carro}")
    image_url = extrair_imagem_carro(link_carro)
    
    # Atualizar no banco
    cursor.execute('UPDATE monitoramentos SET image_url = ? WHERE id = ?', (image_url, mon_id))
    conn.commit()
    conn.close()
    
    if image_url:
        logger.info(f"✅ Imagem atualizada com sucesso para monitoramento {mon_id}")
        return jsonify({
            'success': True,
            'image_url': image_url,
            'message': 'Imagem atualizada com sucesso'
        })
    else:
        logger.warning(f"⚠️ Não foi possível extrair imagem para monitoramento {mon_id}")
        return jsonify({
            'success': False,
            'image_url': None,
            'message': 'Não foi possível extrair a imagem'
        })

@app.route('/api/monitoramentos/update-all-images', methods=['POST'])
def atualizar_todas_imagens():
    """Re-extrai imagens de todos os monitoramentos que não têm imagem"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar monitoramentos sem imagem
    cursor.execute('''
        SELECT id, link_carro 
        FROM monitoramentos 
        WHERE image_url IS NULL OR image_url = '' OR image_url = 'None'
        ORDER BY id
    ''')
    
    monitoramentos_sem_imagem = cursor.fetchall()
    conn.close()
    
    if not monitoramentos_sem_imagem:
        return jsonify({
            'success': True,
            'updated': 0,
            'message': 'Todos os monitoramentos já têm imagens'
        })
    
    logger.info(f"🔄 Iniciando atualização de {len(monitoramentos_sem_imagem)} imagens...")
    
    atualizados = 0
    falhas = 0
    
    for mon in monitoramentos_sem_imagem:
        try:
            mon_id = mon['id']
            link_carro = mon['link_carro']
            
            logger.info(f"🔄 Processando monitoramento {mon_id}...")
            image_url = extrair_imagem_carro(link_carro)
            
            # Atualizar no banco
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE monitoramentos SET image_url = ? WHERE id = ?', (image_url, mon_id))
            conn.commit()
            conn.close()
            
            if image_url:
                atualizados += 1
                logger.info(f"✅ Imagem atualizada para monitoramento {mon_id}")
            else:
                falhas += 1
                logger.warning(f"⚠️ Não foi possível extrair imagem para monitoramento {mon_id}")
        except Exception as e:
            falhas += 1
            logger.error(f"❌ Erro ao atualizar imagem do monitoramento {mon.get('id', 'unknown')}: {e}")
    
    logger.info(f"✅ Concluído: {atualizados} atualizadas, {falhas} falhas")
    
    return jsonify({
        'success': True,
        'updated': atualizados,
        'failed': falhas,
        'total': len(monitoramentos_sem_imagem),
        'message': f'{atualizados} imagens atualizadas com sucesso, {falhas} falhas'
    })

# ==================== SCHEDULER ====================

def iniciar_scheduler():
    """Inicializa o scheduler de tarefas"""
    scheduler = BackgroundScheduler()

    # Agendar verificação a cada CHECK_INTERVAL minutos
    scheduler.add_job(
        func=verificar_monitoramentos,
        trigger=IntervalTrigger(minutes=CHECK_INTERVAL),
        id='verificar_monitoramentos',
        name='Verificar monitoramentos ativos',
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"Scheduler started - checking every {CHECK_INTERVAL} minutes")

    return scheduler

# ==================== MAIN ====================

if __name__ == '__main__':
    logger.info("Starting Kavak Monitor Backend")
    logger.info(f"Configuration: MAX_WORKERS={MAX_WORKERS}, BATCH_SIZE={BATCH_SIZE}, "
                f"CHECK_INTERVAL={CHECK_INTERVAL}min, MAX_PER_IP={MAX_MONITORAMENTOS_POR_IP}")

    # Inicializar banco
    init_db()

    # Iniciar scheduler
    scheduler = iniciar_scheduler()

    try:
        # Executar verificação inicial após 30 segundos
        logger.info("First check will run in 30 seconds")

        # Rodar Flask na porta 5004
        app.run(host='0.0.0.0', port=5004, debug=False)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
        scheduler.shutdown()
