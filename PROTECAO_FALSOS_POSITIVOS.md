# Proteção Contra Falsos Positivos

Documentação sobre as proteções implementadas contra falsos positivos no Kavak Monitor.

## Problema

Quando o site da Kavak sai do ar ou o servidor perde conexão com a internet, o sistema original poderia:

1. **Marcar TODOS os carros como vendidos** incorretamente
2. **Enviar notificações falsas** em massa
3. **Causar pânico** nos usuários

## Cenários Problemáticos

### Cenário 1: Site Kavak Fora do Ar

```
Site Kavak: ❌ OFFLINE
Resultado: Todos os 500 links falham
Problema: Sistema marca tudo como vendido
```

### Cenário 2: Servidor Sem Internet

```
Servidor: ❌ SEM CONEXÃO
Resultado: Todas as requisições falham (DNS/timeout)
Problema: 100% de falhas simultâneas
```

### Cenário 3: Manutenção Temporária

```
Kavak: 🔧 Manutenção por 15 minutos
Resultado: Múltiplas falhas consecutivas
Problema: Notificações prematuras
```

---

## Solução Implementada

Criei uma versão melhorada (`backend/app_improved.py`) com múltiplas camadas de proteção.

### 1. Verificação de Conectividade do Servidor

**Antes** de verificar qualquer link, o sistema testa se tem internet:

```python
def verificar_conectividade_servidor():
    # Testa conexão com Google, Cloudflare, 1.1.1.1
    # Se NENHUM funcionar = servidor sem internet
    # ABORTA o ciclo completamente
```

**Resultado:**
- ✅ Tem internet → Continua
- ❌ Sem internet → **PARA TUDO** (evita 100% falhas falsas)

### 2. Health Check do Site Kavak

**Antes** de processar monitoramentos, verifica se Kavak está no ar:

```python
def verificar_saude_kavak():
    # Testa www.kavak.com/br e www.kavak.com
    # Se AMBOS falharem = Kavak fora do ar
```

**Resultado:**
- ✅ Kavak online → Continua normalmente
- ❌ Kavak offline → **ATIVA QUARENTENA**

### 3. Sistema de Quarentena

Quando detecta problema no site Kavak:

```
QUARENTENA ATIVADA
├─ Duração: 30 minutos (configurável)
├─ Verificações continuam normalmente
└─ Notificações são BLOQUEADAS ⛔
```

**Vantagens:**
- Sistema continua coletando dados
- Não envia notificações falsas
- Se auto-desativa após período
- Registra tudo em logs

### 4. Detecção de Problema Sistêmico

Analisa porcentagem de falhas simultâneas:

```python
total_falhas / total_verificados = porcentagem

Se porcentagem >= 70%:
    🚨 PROBLEMA SISTÊMICO DETECTADO
    🛡️ ATIVA QUARENTENA AUTOMÁTICA
```

**Exemplo:**
```
Verificados: 100 monitoramentos
Falhas: 75 (75%)
Decisão: PROBLEMA SISTÊMICO → Quarentena
```

### 5. Classificação de Erros

O sistema agora identifica o **tipo** de erro:

```python
class TipoErro:
    SUCESSO       # 200 OK
    HTTP_404      # Link removido (provável venda)
    HTTP_500      # Erro servidor Kavak
    TIMEOUT       # Timeout de rede
    DNS_ERROR     # DNS não resolve
    CONNECTION_ERROR  # Conexão recusada
```

**Uso inteligente:**

| Erro | Interpretação | Ação |
|------|---------------|------|
| `HTTP_404` | Provável venda | Falha conta normal |
| `HTTP_500` | Problema Kavak | Exige +1 falha |
| `TIMEOUT` | Rede instável | Exige +1 falha |
| `DNS_ERROR` | Problema grave | Exige +1 falha |

### 6. Threshold de Falhas Aumentado

**Versão original:** 2 falhas consecutivas = vendido
**Versão protegida:** 3+ falhas consecutivas = vendido

**Lógica adaptativa:**
```python
if erro_suspeito (timeout, DNS, 500):
    falhas_necessarias = 4  # Mais conservador
else:
    falhas_necessarias = 3  # Normal
```

### 7. Histórico de Saúde do Sistema

Nova tabela no banco registra cada ciclo:

```sql
CREATE TABLE system_health (
    timestamp,
    total_verificados,
    total_falhas,
    porcentagem_falhas,
    sistema_saudavel,
    observacoes
)
```

**Permite:**
- Análise histórica de problemas
- Identificar padrões
- Auditar notificações
- Debug de falsos positivos

---

## Configuração

### Variáveis de Ambiente Adicionais

Adicione no `.env`:

```env
# Número de falhas consecutivas para marcar como vendido (padrão: 3)
FALHAS_PARA_VENDA=3

# Porcentagem de falhas que indica problema sistêmico (padrão: 70)
LIMITE_FALHAS_SISTEMICAS=70

# Duração da quarentena em minutos (padrão: 30)
QUARENTENA_MINUTOS=30
```

### Perfis Recomendados

#### Conservador (Menos falsos positivos)
```env
FALHAS_PARA_VENDA=5
LIMITE_FALHAS_SISTEMICAS=50
QUARENTENA_MINUTOS=60
```

#### Balanceado (Recomendado)
```env
FALHAS_PARA_VENDA=3
LIMITE_FALHAS_SISTEMICAS=70
QUARENTENA_MINUTOS=30
```

#### Agressivo (Mais rápido, mais risco)
```env
FALHAS_PARA_VENDA=2
LIMITE_FALHAS_SISTEMICAS=85
QUARENTENA_MINUTOS=15
```

---

## Como Usar a Versão Protegida

### Opção 1: Substituir Arquivo

```bash
cd ~/kavak-monitor/backend
cp app.py app_original.py  # Backup
cp app_improved.py app.py  # Usar versão protegida

# Rebuild
docker-compose down
docker-compose up -d --build
```

### Opção 2: Testar Paralelamente

```bash
# Modificar docker-compose.yml para usar app_improved.py
# Ou rodar localmente para teste
cd backend
python3 app_improved.py
```

---

## Monitoramento

### Ver Status de Quarentena

```bash
# Via API
curl http://localhost/api/health

# Resposta:
{
  "status": "healthy",
  "quarentena": true,
  "quarentena_ate": "2025-01-15T14:30:00",
  "minutos_restantes": 25
}
```

### Ver Histórico de Saúde

```bash
curl http://localhost/api/system-health

# Mostra últimas 50 verificações:
{
  "historico": [
    {
      "timestamp": "2025-01-15T14:00:00",
      "total_verificados": 100,
      "total_falhas": 75,
      "porcentagem_falhas": 75.0,
      "sistema_saudavel": 0,
      "observacoes": "Problema sistêmico - 75.0% falhas"
    }
  ]
}
```

### Logs Detalhados

```bash
# Ver logs com filtro
docker-compose logs backend | grep "QUARENTENA"
docker-compose logs backend | grep "PROBLEMA SISTÊMICO"
docker-compose logs backend | grep "Conectividade"
```

**Exemplo de log protegido:**

```
2025-01-15 14:00:00 - INFO - ============================================================
2025-01-15 14:00:00 - INFO - Starting PROTECTED monitoring check cycle
2025-01-15 14:00:00 - INFO - ✓ Conectividade OK (testado com https://www.google.com)
2025-01-15 14:00:00 - ERROR - ✗ SITE DA KAVAK FORA DO AR!
2025-01-15 14:00:00 - ERROR - ✗ ATIVANDO QUARENTENA: Site da Kavak inacessível
2025-01-15 14:00:00 - ERROR - Sistema em quarentena por 30 minutos
2025-01-15 14:00:00 - ERROR - Verificações continuarão, mas SEM notificações
2025-01-15 14:00:05 - INFO - Checking 50 monitorings
2025-01-15 14:00:15 - INFO - Falhas detectadas: 48/50 (96.0%)
2025-01-15 14:00:15 - ERROR - ✗ PROBLEMA SISTÊMICO DETECTADO: 96.0% de falhas!
2025-01-15 14:00:15 - ERROR - ATIVANDO QUARENTENA DE 30 MINUTOS
2025-01-15 14:00:15 - WARNING - Sistema em quarentena - notificação de venda 123 BLOQUEADA
2025-01-15 14:00:15 - INFO - Monitoring check cycle completed
2025-01-15 14:00:15 - INFO - ============================================================
```

---

## Comparação: Original vs Protegido

### Cenário: Kavak Offline por 20 minutos

**Versão Original:**
```
00:00 - Ciclo 1: 100 falhas → Marca 50 vendidos
00:10 - Ciclo 2: 100 falhas → Marca +50 vendidos
00:20 - Kavak volta
Resultado: 100 notificações FALSAS enviadas ❌
```

**Versão Protegida:**
```
00:00 - Detecta Kavak offline
00:00 - ATIVA QUARENTENA (30 min)
00:00 - Ciclo 1: Verifica, mas NÃO notifica
00:10 - Ciclo 2: Verifica, mas NÃO notifica
00:20 - Kavak volta
00:20 - Falhas resetam para 0
Resultado: 0 notificações falsas ✅
```

---

## Testes Recomendados

### Teste 1: Simular Kavak Offline

```bash
# Bloquear acesso temporário (Linux)
sudo iptables -A OUTPUT -d kavak.com -j DROP

# Aguardar ciclo de verificação
# Ver logs: deve ativar quarentena

# Desbloquear
sudo iptables -D OUTPUT -d kavak.com -j DROP
```

### Teste 2: Simular Servidor Sem Internet

```bash
# Desconectar rede
sudo ifconfig eth0 down

# Ver logs: deve abortar ciclo
# Não deve processar nenhum monitoramento

# Reconectar
sudo ifconfig eth0 up
```

### Teste 3: Verificar Threshold

```bash
# Criar 100 monitoramentos de teste
# Modificar 70+ para links inválidos
# Próximo ciclo deve detectar problema sistêmico
```

---

## Perguntas Frequentes

### Q: A versão protegida é mais lenta?

**R:** Não. Adiciona apenas 2-3 segundos no início do ciclo para verificações de saúde.

### Q: Posso ajustar a sensibilidade?

**R:** Sim! Configure `FALHAS_PARA_VENDA` e `LIMITE_FALHAS_SISTEMICAS` no `.env`.

### Q: E se a quarentena for falso alarme?

**R:** A quarentena expira automaticamente após o tempo configurado. Verificações continuam coletando dados.

### Q: Notificações antigas podem ser enviadas após quarentena?

**R:** Não. A flag `notificado_venda` previne duplicatas. Cada notificação é enviada apenas uma vez.

### Q: Como sei se sistema está funcionando?

**R:** Verifique `/api/health` regularmente ou monitore logs com `grep "Sistema saudável"`.

---

## Recomendações

✅ **Fazer:**
- Usar versão protegida em produção
- Monitorar `/api/system-health` semanalmente
- Configurar alertas para `quarentena: true`
- Testar cenários de falha periodicamente
- Manter logs por pelo menos 30 dias

❌ **Evitar:**
- Desabilitar proteções em produção
- Configurar `FALHAS_PARA_VENDA=1` (muito agressivo)
- Ignorar logs de quarentena
- Definir `LIMITE_FALHAS_SISTEMICAS=100` (inútil)

---

## Conclusão

A versão protegida adiciona **múltiplas camadas de segurança** sem comprometer a funcionalidade:

| Proteção | Efetividade | Custo |
|----------|-------------|-------|
| Verificação Conectividade | ⭐⭐⭐⭐⭐ | ~2s |
| Health Check Kavak | ⭐⭐⭐⭐⭐ | ~1s |
| Sistema Quarentena | ⭐⭐⭐⭐⭐ | 0s |
| Detecção Sistêmica | ⭐⭐⭐⭐ | 0s |
| Classificação Erros | ⭐⭐⭐ | 0s |
| Threshold Aumentado | ⭐⭐⭐⭐ | 0s |

**Resultado:** Sistema robusto, confiável e à prova de falsos positivos!

---

**Versão protegida ativada? Durma tranquilo sabendo que não haverá surpresas! 🛡️**
