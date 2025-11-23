# Otimização para Raspberry Pi

Guia completo de otimização do Kavak Monitor para rodar eficientemente no Raspberry Pi 3 (ou superior).

## Índice

1. [Capacidade e Limites](#capacidade-e-limites)
2. [Configurações Otimizadas](#configurações-otimizadas)
3. [Monitoramento de Recursos](#monitoramento-de-recursos)
4. [Otimização do Sistema Operacional](#otimização-do-sistema-operacional)
5. [Gestão de Temperatura](#gestão-de-temperatura)
6. [Troubleshooting Performance](#troubleshooting-performance)

---

## Capacidade e Limites

### Raspberry Pi 3 Model B/B+

**Especificações:**
- CPU: Quad-core ARM Cortex-A53 @ 1.2-1.4 GHz
- RAM: 1GB
- Armazenamento: microSD

**Capacidade do Kavak Monitor:**

| Monitoramentos | CPU Médio | RAM Uso | Temp. | Status |
|----------------|-----------|---------|-------|--------|
| 0-100          | 5-10%     | 80-100MB| 45-50°C | ✅ Ótimo |
| 100-250        | 10-15%    | 100-130MB | 50-55°C | ✅ Bom |
| 250-500        | 15-20%    | 130-150MB | 55-60°C | ✅ Aceitável |
| 500-750        | 20-30%    | 150-180MB | 60-65°C | ⚠️ Limite |
| 750-1000       | 30-40%    | 180-220MB | 65-70°C | ❌ Não recomendado |

**Recomendação:** Até **500 monitoramentos** no RPi 3.

### Raspberry Pi 4 Model B

**Especificações:**
- CPU: Quad-core ARM Cortex-A72 @ 1.5 GHz
- RAM: 2GB/4GB/8GB

**Capacidade:** Até **2000 monitoramentos** (com 4GB+ RAM).

---

## Configurações Otimizadas

### Configuração para Raspberry Pi 3

Edite o arquivo `.env`:

```env
# === OTIMIZADO PARA RASPBERRY PI 3 ===

# Reduzir workers paralelos
MAX_WORKERS=5

# Verificar 50 sites por ciclo
BATCH_SIZE=50

# Timeout agressivo (5s)
REQUEST_TIMEOUT=5

# Intervalo entre verificações (10 minutos)
CHECK_INTERVAL=10

# Limite por IP
MAX_MONITORAMENTOS_POR_IP=10
```

### Perfis de Performance

#### Perfil Econômico (Temperatura < 55°C)

```env
MAX_WORKERS=3
BATCH_SIZE=30
REQUEST_TIMEOUT=5
CHECK_INTERVAL=15
```

**Ideal para:**
- Raspberry Pi sem cooler
- Ambiente quente
- Até 200 monitoramentos

#### Perfil Balanceado (Padrão)

```env
MAX_WORKERS=5
BATCH_SIZE=50
REQUEST_TIMEOUT=5
CHECK_INTERVAL=10
```

**Ideal para:**
- Raspberry Pi com cooler
- Até 500 monitoramentos
- Temperatura controlada

#### Perfil Performance (Raspberry Pi 4)

```env
MAX_WORKERS=10
BATCH_SIZE=100
REQUEST_TIMEOUT=5
CHECK_INTERVAL=5
```

**Ideal para:**
- Raspberry Pi 4 (4GB+)
- Com cooler ativo
- Até 2000 monitoramentos

---

## Monitoramento de Recursos

### Monitorar Uso em Tempo Real

```bash
# CPU e RAM dos containers
docker stats

# Temperatura do Raspberry Pi
vcgencmd measure_temp

# Monitoramento contínuo
watch -n 2 'vcgencmd measure_temp && docker stats --no-stream'
```

### Script de Monitoramento Automático

Criar arquivo `monitor_resources.sh`:

```bash
#!/bin/bash
echo "=== Kavak Monitor - Status do Sistema ==="
echo ""
echo "Temperatura CPU:"
vcgencmd measure_temp
echo ""
echo "Uso de Recursos:"
docker stats --no-stream kavak-backend kavak-frontend
echo ""
echo "Monitoramentos Ativos:"
docker exec kavak-backend sqlite3 /app/data/kavak_monitor.db \
  "SELECT COUNT(*) FROM monitoramentos WHERE status='ativo';"
```

Tornar executável:

```bash
chmod +x monitor_resources.sh
./monitor_resources.sh
```

### Alertas de Temperatura

Criar `check_temp.sh`:

```bash
#!/bin/bash
TEMP=$(vcgencmd measure_temp | grep -oP '\d+\.\d+')
TEMP_INT=${TEMP%.*}

if [ $TEMP_INT -gt 70 ]; then
    echo "ALERTA: Temperatura crítica: ${TEMP}°C"
    # Reduzir workers automaticamente
    docker exec kavak-backend sh -c 'echo "MAX_WORKERS=3" >> /app/.env'
    docker compose restart backend
fi
```

Adicionar ao crontab (verificar a cada 10 minutos):

```bash
crontab -e

# Adicionar:
*/10 * * * * /home/pi/kavak-monitor/check_temp.sh
```

---

## Otimização do Sistema Operacional

### 1. Atualizar Sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Desabilitar Serviços Desnecessários

```bash
# Desabilitar Bluetooth (se não usar)
sudo systemctl disable bluetooth
sudo systemctl stop bluetooth

# Desabilitar Wi-Fi (se usar ethernet)
sudo systemctl disable wpa_supplicant

# Desabilitar som
sudo systemctl disable alsa-state
```

### 3. Configurar Swap

```bash
# Aumentar swap para 1GB (ajuda com picos de RAM)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile

# Alterar:
CONF_SWAPSIZE=1024

# Aplicar
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### 4. Otimizar microSD

```bash
# Reduzir escritas no SD (aumenta vida útil)
sudo nano /etc/fstab

# Adicionar:
tmpfs /tmp tmpfs defaults,noatime,nosuid,size=100m 0 0
tmpfs /var/tmp tmpfs defaults,noatime,nosuid,size=30m 0 0
tmpfs /var/log tmpfs defaults,noatime,nosuid,mode=0755,size=100m 0 0
```

**Atenção:** Logs serão perdidos ao reiniciar!

### 5. Configurar Log Rotation para Docker

Criar `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Reiniciar Docker:

```bash
sudo systemctl restart docker
```

---

## Gestão de Temperatura

### 1. Instalar Cooler (Recomendado)

Tipos de cooler para RPi:

- **Passivo**: Dissipador de alumínio (~R$ 10)
- **Ativo**: Ventilador 5V (~R$ 15)
- **Case com Cooler**: Case + ventilador (~R$ 30)

**Redução esperada:** 10-15°C

### 2. Melhorar Ventilação

- Não encaixote o Raspberry Pi
- Mantenha espaço ao redor (mín. 5cm)
- Evite luz solar direta
- Use em ambiente com ar condicionado se possível

### 3. Overclock Reverso (Se Necessário)

Se temperatura estiver consistentemente >65°C:

```bash
sudo nano /boot/config.txt

# Adicionar (reduz clock de 1.4 GHz para 1.2 GHz)
arm_freq=1200
core_freq=400
sdram_freq=450
over_voltage=0
```

Reiniciar:

```bash
sudo reboot
```

**Trade-off:** -10°C temperatura, -15% performance

### 4. Throttling Automático

Verificar se há throttling:

```bash
vcgencmd get_throttled
```

Resultado:
- `0x0` = OK
- Outro valor = Há throttling

---

## Troubleshooting Performance

### Performance Lenta

**Sintomas:**
- Containers lentos
- Timeouts frequentes
- Interface web travando

**Soluções:**

1. **Reduzir workers**:
   ```env
   MAX_WORKERS=3
   ```

2. **Aumentar intervalo**:
   ```env
   CHECK_INTERVAL=15
   ```

3. **Reduzir batch size**:
   ```env
   BATCH_SIZE=30
   ```

4. **Verificar temperatura**:
   ```bash
   vcgencmd measure_temp
   ```
   Se >65°C, instale cooler.

### Alto Uso de RAM

```bash
# Ver uso detalhado
docker stats

# Se backend >200MB:
docker compose restart backend

# Se persistir, reduzir workers:
MAX_WORKERS=3
```

### Banco de Dados Grande

```bash
# Ver tamanho do banco
docker exec kavak-backend ls -lh /app/data/kavak_monitor.db

# Se >100MB, limpar expirados:
docker exec kavak-backend sqlite3 /app/data/kavak_monitor.db \
  "DELETE FROM monitoramentos WHERE status='expirado';"

# Vacuum (compactar):
docker exec kavak-backend sqlite3 /app/data/kavak_monitor.db "VACUUM;"
```

### microSD Lento

Sintomas de SD card ruim:

- Operações de I/O lentas
- Logs com erros de leitura/escrita
- Containers reiniciando sozinhos

**Teste de velocidade:**

```bash
# Teste de escrita
sudo dd if=/dev/zero of=/tmp/test bs=1M count=100 oflag=direct

# Deve ser >10 MB/s
```

**Solução:**
- Use cartão **Classe 10** ou **UHS-I**
- Recomendado: SanDisk Extreme (90MB/s)

---

## Melhores Práticas

### ✅ Fazer

- Usar cartão SD rápido (Classe 10+)
- Instalar cooler (ativo ou passivo)
- Monitorar temperatura regularmente
- Fazer backup do banco semanalmente
- Manter sistema atualizado
- Usar fonte de alimentação oficial (5V 2.5A+)

### ❌ Evitar

- Não usar cartões SD genéricos/lentos
- Não encaixotar o Raspberry Pi
- Não fazer overclock (desnecessário)
- Não logar excessivamente
- Não ignorar avisos de temperatura
- Não usar fonte de celular (pode causar instabilidade)

---

## Benchmark

### Teste de Performance

Script `benchmark.sh`:

```bash
#!/bin/bash
echo "=== Kavak Monitor - Benchmark ==="

# Tempo para verificar 50 links
START=$(date +%s)
docker exec kavak-backend python -c "
from app import verificar_link
import time
start = time.time()
for i in range(50):
    verificar_link('https://www.kavak.com/br/comprar/test')
print(f'Tempo: {time.time() - start:.2f}s')
"
END=$(date +%s)
DIFF=$(( $END - $START ))

echo "Tempo total: ${DIFF}s"
echo ""
echo "Performance:"
if [ $DIFF -lt 60 ]; then
    echo "✅ Excelente (<60s)"
elif [ $DIFF -lt 120 ]; then
    echo "✅ Bom (<120s)"
elif [ $DIFF -lt 180 ]; then
    echo "⚠️ Aceitável (<180s)"
else
    echo "❌ Ruim (>180s) - Otimize!"
fi
```

**Resultados esperados (RPi 3):**

- Excelente: <60s (10-15% CPU)
- Bom: 60-120s (15-20% CPU)
- Aceitável: 120-180s (20-30% CPU)
- Ruim: >180s (>30% CPU ou throttling)

---

## Conclusão

Com as otimizações corretas, o Raspberry Pi 3 pode facilmente gerenciar:

- ✅ 500 monitoramentos simultâneos
- ✅ Verificação a cada 10 minutos
- ✅ Temperatura <60°C (com cooler)
- ✅ Uso de CPU <20%
- ✅ Uso de RAM <150MB

Para mais de 500 monitoramentos, considere:

- **Raspberry Pi 4 (4GB)** - Até 2000 monitoramentos
- **VPS econômico** - Sem limites práticos
- **Múltiplas instâncias** - Dividir carga entre RPis

---

**Sistema otimizado? Aproveite seu Raspberry Pi monitorando 24/7! 🚀**
