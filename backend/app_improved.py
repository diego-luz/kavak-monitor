#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kavak Monitor - Sistema de Monitoramento de Vendas (VERSÃO MELHORADA)
Backend API em Flask com proteção contra falsos positivos
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
from enum import Enum

from flask import Flask, request, jsonify
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
RECAPTCHA_SECRET_KEY = os.getenv('RECAPTCHA_SECRET_KEY', '')

# NOVAS CONFIGURAÇÕES DE PROTEÇÃO
FALHAS_PARA_VENDA = int(os.getenv('FALHAS_PARA_VENDA', '3'))  # 3 falhas consecutivas (era 2)
LIMITE_FALHAS_SISTEMICAS = int(os.getenv('LIMITE_FALHAS_SISTEMICAS', '70'))  # 70% de falhas = problema sistêmico
QUARENTENA_MINUTOS = int(os.getenv('QUARENTENA_MINUTOS', '30'))  # 30 minutos de quarentena

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

# ==================== ENUMS ====================

class TipoErro(Enum):
    """Tipos de erro ao verificar links"""
    SUCESSO = "sucesso"
    TIMEOUT = "timeout"
    DNS_ERROR = "dns_error"
    CONNECTION_ERROR = "connection_error"
    HTTP_404 = "http_404"
    HTTP_500 = "http_500"
    HTTP_OTHER = "http_other"
    UNKNOWN = "unknown"

# ==================== FLASK APP ====================

app = Flask(__name__)
CORS(app)
app.config['JSON_AS_ASCII'] = False

# Variável global para controle de quarentena
sistema_em_quarentena = False
quarentena_ate = None

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

    # Tabela de monitoramentos (COM NOVO CAMPO: ultimo_erro)
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
            ultimo_erro TEXT DEFAULT NULL
        )
    ''')

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

    # NOVA TABELA: Histórico de verificações do sistema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_health (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_verificados INTEGER,
            total_falhas INTEGER,
            porcentagem_falhas REAL,
            sistema_saudavel INTEGER DEFAULT 1,
            observacoes TEXT
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

# ==================== VERIFICAÇÃO DE CONECTIVIDADE ====================

def verificar_conectividade_servidor() -> Tuple[bool, str]:
    """
    Verifica se o servidor tem conexão com a internet
    Retorna: (tem_conexao: bool, mensagem: str)
    """
    sites_teste = [
        'https://www.google.com',
        'https://www.cloudflare.com',
        'https://1.1.1.1'
    ]

    for site in sites_teste:
        try:
            response = requests.get(site, timeout=5)
            if response.status_code == 200:
                logger.info(f"✓ Conectividade OK (testado com {site})")
                return True, "Conexão OK"
        except:
            continue

    logger.error("✗ SERVIDOR SEM INTERNET!")
    return False, "Servidor sem conexão com a internet"

def verificar_saude_kavak() -> Tuple[bool, str]:
    """
    Verifica se o site da Kavak está no ar
    Retorna: (esta_online: bool, mensagem: str)
    """
    urls_teste = [
        'https://www.kavak.com/br',
        'https://www.kavak.com'
    ]

    for url in urls_teste:
        try:
            response = requests.get(url, timeout=10,
                                  headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code == 200:
                logger.info(f"✓ Site Kavak OK ({url})")
                return True, "Kavak online"
        except Exception as e:
            logger.warning(f"Falha ao acessar {url}: {e}")
            continue

    logger.error("✗ SITE DA KAVAK FORA DO AR!")
    return False, "Site da Kavak inacessível"

# ==================== VERIFICAÇÃO DE LINKS MELHORADA ====================

def verificar_link_detalhado(link: str) -> Tuple[bool, TipoErro]:
    """
    Verifica link e retorna status + tipo de erro
    Retorna: (online: bool, tipo_erro: TipoErro)
    """
    try:
        response = requests.get(
            link,
            timeout=REQUEST_TIMEOUT,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )

        if response.status_code == 200:
            return True, TipoErro.SUCESSO
        elif response.status_code == 404:
            return False, TipoErro.HTTP_404
        elif response.status_code >= 500:
            return False, TipoErro.HTTP_500
        else:
            return False, TipoErro.HTTP_OTHER

    except requests.exceptions.Timeout:
        return False, TipoErro.TIMEOUT
    except requests.exceptions.ConnectionError as e:
        if 'Name or service not known' in str(e) or 'getaddrinfo failed' in str(e):
            return False, TipoErro.DNS_ERROR
        return False, TipoErro.CONNECTION_ERROR
    except Exception as e:
        logger.debug(f"Error checking link {link}: {e}")
        return False, TipoErro.UNKNOWN

@lru_cache(maxsize=500)
def verificar_link_com_cache(link: str, timestamp: int) -> Tuple[bool, str]:
    """Cache de 5 minutos para verificações"""
    online, tipo_erro = verificar_link_detalhado(link)
    return online, tipo_erro.value

def verificar_link(link: str) -> Tuple[bool, str]:
    """Wrapper para verificação com cache"""
    cache_timestamp = int(datetime.now().timestamp() / 300)
    return verificar_link_com_cache(link, cache_timestamp)

# ==================== PROCESSAMENTO MELHORADO ====================

def processar_monitoramento(monitoramento: Dict) -> Optional[Dict]:
    """
    Processa um único monitoramento com proteção contra falsos positivos
    """
    mon_id = monitoramento['id']
    link = monitoramento['link_carro']
    data_venda = datetime.fromisoformat(monitoramento['data_venda'])

    logger.debug(f"Processing monitoring {mon_id}")

    updates = {
        'id': mon_id,
        'ultima_verificacao': datetime.now().isoformat()
    }

    # Calcular dias restantes
    dias_restantes = (data_venda + timedelta(days=45) - datetime.now()).days

    # Verificar expiração
    if dias_restantes < 0:
        updates['status'] = 'expirado'
        return updates

    # Verificar link com detalhamento de erro
    link_online, tipo_erro = verificar_link(link)

    if not link_online:
        # Link offline - incrementar falhas
        falhas = monitoramento['falhas_consecutivas'] + 1
        updates['falhas_consecutivas'] = falhas
        updates['ultimo_erro'] = tipo_erro

        # Análise do tipo de erro
        erros_suspeitos = [TipoErro.TIMEOUT.value, TipoErro.DNS_ERROR.value,
                          TipoErro.CONNECTION_ERROR.value, TipoErro.HTTP_500.value]

        erro_indica_problema_sistemico = tipo_erro in erros_suspeitos

        # PROTEÇÃO: Se erro é suspeito (timeout, DNS, etc), exigir mais falhas
        falhas_necessarias = FALHAS_PARA_VENDA + 1 if erro_indica_problema_sistemico else FALHAS_PARA_VENDA

        # Marcar como vendido apenas após falhas suficientes
        if falhas >= falhas_necessarias and not monitoramento['carro_vendido']:
            # PROTEÇÃO ADICIONAL: Não notificar se sistema em quarentena
            global sistema_em_quarentena

            if not sistema_em_quarentena:
                updates['carro_vendido'] = 1

                # Enviar notificação de venda
                if not monitoramento['notificado_venda']:
                    mensagem = (
                        f"🎉 <b>Carro Vendido!</b>\n\n"
                        f"Seu carro da Kavak foi vendido!\n"
                        f"Link: {link}\n"
                        f"Data da venda: {data_venda.strftime('%d/%m/%Y')}\n"
                        f"Prazo de 45 dias expira em: {(data_venda + timedelta(days=45)).strftime('%d/%m/%Y')}\n\n"
                        f"⏰ Faltam {dias_restantes} dias para o prazo de pagamento.\n\n"
                        f"<i>Falhas detectadas: {falhas}</i>"
                    )

                    from backend.app_improved import enviar_notificacao
                    if enviar_notificacao(
                        monitoramento['tipo_notificacao'],
                        monitoramento['contato'],
                        mensagem
                    ):
                        updates['notificado_venda'] = 1
            else:
                logger.warning(f"Sistema em quarentena - notificação de venda {mon_id} BLOQUEADA")
    else:
        # Link voltou ao ar - resetar falhas
        if monitoramento['falhas_consecutivas'] > 0:
            updates['falhas_consecutivas'] = 0
            updates['ultimo_erro'] = None

    # Alerta de prazo (5 dias ou menos)
    if dias_restantes <= 5 and dias_restantes > 0 and not monitoramento['notificado_prazo']:
        mensagem = (
            f"⏰ <b>Alerta de Prazo!</b>\n\n"
            f"Faltam apenas <b>{dias_restantes} dias</b> para o prazo de 45 dias da Kavak!\n\n"
            f"Link: {link}\n"
            f"Data da venda: {data_venda.strftime('%d/%m/%Y')}\n"
            f"Prazo expira em: {(data_venda + timedelta(days=45)).strftime('%d/%m/%Y')}\n\n"
            f"🚨 Prepare-se para receber o pagamento ou entre em contato com a Kavak."
        )

        from backend.app_improved import enviar_notificacao
        if enviar_notificacao(
            monitoramento['tipo_notificacao'],
            monitoramento['contato'],
            mensagem
        ):
            updates['notificado_prazo'] = 1

    return updates

# ==================== VERIFICAÇÃO COM PROTEÇÃO ====================

def verificar_monitoramentos():
    """
    Tarefa agendada com proteção contra falsos positivos
    """
    global sistema_em_quarentena, quarentena_ate

    logger.info("=" * 60)
    logger.info("Starting PROTECTED monitoring check cycle")

    # PASSO 1: Verificar se sistema está em quarentena
    if sistema_em_quarentena and quarentena_ate:
        if datetime.now() < quarentena_ate:
            tempo_restante = int((quarentena_ate - datetime.now()).total_seconds() / 60)
            logger.warning(f"⚠️  SISTEMA EM QUARENTENA - {tempo_restante} minutos restantes")
            logger.warning("Verificações continuam, mas notificações estão BLOQUEADAS")
        else:
            logger.info("✓ Quarentena expirada - sistema normalizado")
            sistema_em_quarentena = False
            quarentena_ate = None

    # PASSO 2: Verificar conectividade do servidor
    tem_internet, msg_internet = verificar_conectividade_servidor()
    if not tem_internet:
        logger.error(f"✗ ABORTANDO CICLO: {msg_internet}")
        logger.error("Sistema sem internet - todas verificações seriam falhas!")
        return

    # PASSO 3: Verificar saúde do site Kavak
    kavak_online, msg_kavak = verificar_saude_kavak()
    if not kavak_online:
        logger.error(f"✗ ATIVANDO QUARENTENA: {msg_kavak}")
        sistema_em_quarentena = True
        quarentena_ate = datetime.now() + timedelta(minutes=QUARENTENA_MINUTOS)
        logger.error(f"Sistema em quarentena por {QUARENTENA_MINUTOS} minutos")
        logger.error("Verificações continuarão, mas SEM notificações")
        # NÃO retorna - continua verificando para coletar dados

    # PASSO 4: Buscar monitoramentos ativos
    conn = get_db_connection()
    cursor = conn.cursor()

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

    # PASSO 5: Processar em paralelo
    updates_list = []
    total_falhas = 0

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
                    # Contar falhas
                    if updates.get('falhas_consecutivas', 0) > 0:
                        total_falhas += 1
            except Exception as e:
                mon = futures[future]
                logger.error(f"Error processing monitoring {mon['id']}: {e}")

    # PASSO 6: Análise de saúde do sistema
    porcentagem_falhas = (total_falhas / len(monitoramentos)) * 100 if monitoramentos else 0

    logger.info(f"Falhas detectadas: {total_falhas}/{len(monitoramentos)} ({porcentagem_falhas:.1f}%)")

    # PROTEÇÃO: Se muitas falhas simultâneas = problema sistêmico
    if porcentagem_falhas >= LIMITE_FALHAS_SISTEMICAS:
        logger.error(f"✗ PROBLEMA SISTÊMICO DETECTADO: {porcentagem_falhas:.1f}% de falhas!")
        logger.error(f"ATIVANDO QUARENTENA DE {QUARENTENA_MINUTOS} MINUTOS")

        sistema_em_quarentena = True
        quarentena_ate = datetime.now() + timedelta(minutes=QUARENTENA_MINUTOS)

        # Registrar no banco
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO system_health
            (total_verificados, total_falhas, porcentagem_falhas, sistema_saudavel, observacoes)
            VALUES (?, ?, ?, 0, ?)
        ''', (len(monitoramentos), total_falhas, porcentagem_falhas,
              f"Problema sistêmico - {porcentagem_falhas:.1f}% falhas"))
        conn.commit()
        conn.close()
    else:
        logger.info(f"✓ Sistema saudável ({porcentagem_falhas:.1f}% falhas)")

    # PASSO 7: Aplicar atualizações no banco
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
    logger.info("=" * 60)

# ==================== NOTIFICAÇÕES (IGUAL AO ORIGINAL) ====================

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

def enviar_notificacao_whatsapp(numero: str, mensagem: str) -> bool:
    """Placeholder para WhatsApp"""
    logger.info(f"WhatsApp notification (not implemented): {numero} - {mensagem}")
    return True

def enviar_notificacao(tipo: str, contato: str, mensagem: str) -> bool:
    """Envia notificação baseada no tipo configurado"""
    if tipo == 'telegram':
        return enviar_notificacao_telegram(contato, mensagem)
    elif tipo == 'whatsapp':
        return enviar_notificacao_whatsapp(contato, mensagem)
    else:
        logger.error(f"Unknown notification type: {tipo}")
        return False

# ==================== API ENDPOINTS (MESMOS DO ORIGINAL + NOVOS) ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    global sistema_em_quarentena, quarentena_ate

    status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'quarentena': sistema_em_quarentena
    }

    if sistema_em_quarentena and quarentena_ate:
        status['quarentena_ate'] = quarentena_ate.isoformat()
        status['minutos_restantes'] = int((quarentena_ate - datetime.now()).total_seconds() / 60)

    return jsonify(status)

@app.route('/api/system-health', methods=['GET'])
def system_health():
    """Retorna histórico de saúde do sistema"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM system_health
        ORDER BY timestamp DESC
        LIMIT 50
    ''')

    historico = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify({'historico': historico})

# [DEMAIS ENDPOINTS IGUAIS AO ORIGINAL - omitidos por brevidade]
# ... (copiar do app.py original)

# ==================== SCHEDULER ====================

def iniciar_scheduler():
    """Inicializa o scheduler de tarefas"""
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        func=verificar_monitoramentos,
        trigger=IntervalTrigger(minutes=CHECK_INTERVAL),
        id='verificar_monitoramentos',
        name='Verificar monitoramentos ativos (PROTEGIDO)',
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"Scheduler started - checking every {CHECK_INTERVAL} minutes")
    logger.info(f"PROTEÇÕES ATIVAS: {FALHAS_PARA_VENDA} falhas, {LIMITE_FALHAS_SISTEMICAS}% limite sistêmico")

    return scheduler

# ==================== MAIN ====================

if __name__ == '__main__':
    logger.info("Starting Kavak Monitor Backend (PROTECTED VERSION)")
    logger.info(f"Configuration: MAX_WORKERS={MAX_WORKERS}, BATCH_SIZE={BATCH_SIZE}")
    logger.info(f"Protection: FALHAS={FALHAS_PARA_VENDA}, LIMITE_SISTEMICO={LIMITE_FALHAS_SISTEMICAS}%")

    # Inicializar banco
    init_db()

    # Iniciar scheduler
    scheduler = iniciar_scheduler()

    try:
        logger.info("First check will run in 30 seconds")
        app.run(host='0.0.0.0', port=5000, debug=False)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
        scheduler.shutdown()
