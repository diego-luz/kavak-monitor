# Guia: Como Configurar Google reCAPTCHA v3

Este guia mostra como obter e configurar as chaves do Google reCAPTCHA v3 para o Kavak Monitor.

## O que é reCAPTCHA v3?

O reCAPTCHA v3 é um sistema de proteção anti-spam do Google que funciona **invisível ao usuário**. Ele analisa o comportamento do visitante e atribui um score de 0 a 1 (quanto maior, mais provável que seja humano).

No Kavak Monitor, usamos para:
- Prevenir bots criando monitoramentos falsos
- Proteger o sistema contra abuso
- Garantir que apenas usuários legítimos usem o sistema

## Passo a Passo

### 1. Acessar o Console do reCAPTCHA

Acesse: https://www.google.com/recaptcha/admin

Faça login com sua conta Google.

### 2. Criar um Novo Site

Clique no botão **"+" (Adicionar)** no canto superior direito.

### 3. Configurar o Site

Preencha o formulário:

#### **Label** (Nome do site)
```
Kavak Monitor
```
*Ou qualquer nome para identificar internamente*

#### **Tipo de reCAPTCHA**
Selecione: **reCAPTCHA v3**

#### **Domínios**
Adicione os domínios onde o sistema vai rodar:

**Para uso local:**
```
localhost
```

**Para uso em rede local (Raspberry Pi):**
```
192.168.1.100
```
*Substitua pelo IP real do seu servidor*

**Para domínio público:**
```
kavak-monitor.seudominio.com
```

**Dica**: Você pode adicionar múltiplos domínios, um por linha:
```
localhost
192.168.1.100
meuservidor.local
```

#### **Proprietários**
Deixe como está (seu email será adicionado automaticamente).

#### **Aceitar Termos**
Marque: ✅ Aceito os Termos de Serviço do reCAPTCHA

### 4. Enviar

Clique em **"Enviar"**.

### 5. Copiar as Chaves

Após criar, você verá uma tela com duas chaves:

#### **Site Key** (Chave do Site)
```
6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI
```
*Esta chave vai no frontend (visível publicamente)*

#### **Secret Key** (Chave Secreta)
```
6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe
```
*Esta chave vai no backend (mantida em segredo)*

**⚠️ Importante:** Nunca compartilhe ou exponha a Secret Key publicamente!

---

## Configuração no Kavak Monitor

### 1. Configurar Secret Key no Backend

Edite o arquivo `.env`:

```bash
nano .env
```

Adicione a Secret Key:

```env
RECAPTCHA_SECRET_KEY=6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe
```

### 2. Configurar Site Key no Frontend

Edite o arquivo `frontend/index.html`:

```bash
nano frontend/index.html
```

**Linha ~8** - Atualizar o script do reCAPTCHA:

```html
<script src="https://www.google.com/recaptcha/api.js?render=6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"></script>
```

**Linha ~282** - Atualizar a constante JavaScript:

```javascript
const RECAPTCHA_SITE_KEY = '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI';
```

### 3. Reiniciar o Sistema

```bash
docker compose down
docker compose up -d --build
```

---

## Testando a Configuração

### 1. Acessar a Interface

Abra: http://localhost (ou IP do servidor)

### 2. Tentar Criar Monitoramento

1. Clique em "Novo Monitoramento"
2. Preencha os dados
3. Clique em "Criar"

### 3. Verificar nos Logs

```bash
docker compose logs backend | grep -i recaptcha
```

Deve mostrar algo como:
```
reCAPTCHA verification: True, score: 0.9
```

### 4. Verificar no Console do Google

Volte para: https://www.google.com/recaptcha/admin

Clique no seu site → **Analytics**

Você deve ver gráficos com as requisições e scores.

---

## Ajuste do Score Mínimo

O sistema está configurado para aceitar score **≥ 0.5** (padrão recomendado).

Para ajustar, edite `backend/app.py`:

```python
# Linha ~105
success = result.get('success', False) and result.get('score', 0) >= 0.5
```

**Valores recomendados:**

- `0.3` - Mais permissivo (pode deixar passar alguns bots)
- `0.5` - **Recomendado** (balanceado)
- `0.7` - Mais rigoroso (pode bloquear alguns usuários legítimos)
- `0.9` - Muito rigoroso (apenas usuários com certeza humanos)

Após alterar, reinicie:
```bash
docker compose restart backend
```

---

## Chaves de Teste do Google

Para **desenvolvimento/teste** apenas, você pode usar as chaves de teste oficiais do Google:

**Site Key:**
```
6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI
```

**Secret Key:**
```
6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe
```

**⚠️ Atenção:** Estas chaves **sempre retornam sucesso**! Use apenas para testes.

Para produção, você **DEVE** criar suas próprias chaves.

---

## Troubleshooting

### Erro: "Failed to verify reCAPTCHA"

**Causas comuns:**

1. **Secret Key incorreta** → Verifique o `.env`
2. **Domínio não autorizado** → Adicione no console do Google
3. **Timeout de rede** → Verifique conexão internet do servidor

**Solução:**

```bash
# Verificar Secret Key
cat .env | grep RECAPTCHA

# Ver logs detalhados
docker compose logs backend | grep -i recaptcha

# Testar manualmente
docker exec kavak-backend python -c "
import requests
token = 'TOKEN_DE_TESTE'
secret = 'SUA_SECRET_KEY'
r = requests.post('https://www.google.com/recaptcha/api/siteverify',
                  data={'secret': secret, 'response': token})
print(r.json())
"
```

### Badge do reCAPTCHA aparece no canto da tela

Isso é **normal** no reCAPTCHA v3. Para ocultar (opcional):

Adicione no CSS do `frontend/index.html`:

```css
.grecaptcha-badge {
    visibility: hidden;
}
```

**Importante:** Se ocultar o badge, você **deve** incluir o texto:

```html
This site is protected by reCAPTCHA and the Google
<a href="https://policies.google.com/privacy">Privacy Policy</a> and
<a href="https://policies.google.com/terms">Terms of Service</a> apply.
```

### Score sempre baixo

**Possíveis causas:**

- Site novo (sem histórico)
- Muitas requisições do mesmo IP
- Comportamento automatizado detectado

**Soluções:**

- Aguarde alguns dias para o sistema "aprender"
- Reduza o score mínimo temporariamente
- Use navegador em modo normal (não incógnito)

---

## Perguntas Frequentes

### É gratuito?

Sim, o reCAPTCHA v3 é **100% gratuito** para a maioria dos sites.

Existe limite de 1 milhão de requisições/mês no plano gratuito, mais que suficiente para este projeto.

### Preciso de conta Google?

Sim, você precisa de uma conta Google para criar e gerenciar as chaves.

### Posso usar com múltiplos domínios?

Sim! Adicione todos os domínios necessários na configuração do site.

### Onde vejo estatísticas de uso?

No console: https://www.google.com/recaptcha/admin

Clique no seu site → **Analytics**

### Posso ter múltiplos sites?

Sim, você pode criar quantos sites quiser na mesma conta Google.

---

## Recursos Adicionais

- **Documentação oficial**: https://developers.google.com/recaptcha/docs/v3
- **Console Admin**: https://www.google.com/recaptcha/admin
- **FAQ oficial**: https://developers.google.com/recaptcha/docs/faq

---

**Configuração concluída? O sistema agora está protegido contra spam! 🛡️**
