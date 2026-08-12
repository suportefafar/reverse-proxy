# 🔒 Auditoria de Segurança — Reverse Proxy Caddy2

**Data:** 2026-07-14  
**Servidor:** `reverse-proxy-ct-1` — Ubuntu 22.04.3 LTS (LXC)  
**Kernel:** 6.8.12-10-pve  
**Caddy:** v2.7.6 (Docker)  
**Docker:** 25.0.3  

---

## Sumário Executivo

| Categoria | Findings Críticos | Findings Altos | Findings Médios | Findings Baixos |
|---|:---:|:---:|:---:|:---:|
| Docker | 1 | 1 | 1 | — |
| Caddy / HTTP | — | 3 | 2 | 1 |
| Firewall | — | 1 | — | — |
| Fail2Ban / Logs | — | 1 | 1 | — |
| Exposição Web | — | — | 1 | 1 |
| **TOTAL** | **1** | **6** | **5** | **2** |

---

## 1. Exposição Web

### 1.1 Arquivos Sensíveis no Sistema de Arquivos

| Item | Status |
|---|---|
| `.env` / `.env.*` | ✅ Nenhum encontrado (`.gitignore` protege) |
| `.git` | ⚠️ Presente em `/var/app/.git/` mas NÃO servido pelo Caddy |
| `.svn` | ✅ Não encontrado |
| `docker-compose.yml/yaml` | ✅ Não encontrado (usa `compose.yaml`) |
| `.dockerignore` | ⚠️ **Ausente** — sem filtro no build |
| `phpinfo.php` / `info.php` | ✅ Não encontrado |
| `server-status` / `server-info` | ✅ N/A (Caddy, não Apache) |
| `CHANGELOG` / `config` / `backup` | ✅ Não encontrado |
| Arquivos `.bak` / `.old` | ⚠️ `farmacia.ufmg.br.crt.old` e `.key.old` nos certs |
| Arquivos `.zip` / `.tar` / `.sql` | ✅ Não encontrado |
| Arquivos temporários | ✅ Não encontrado |

> [!NOTE]
> O Caddy opera apenas como reverse proxy (sem `file_server` nos blocos de domínio), portanto arquivos locais do host **não são diretamente acessíveis via HTTP**. O risco principal está na imagem Docker que copia tudo de `./certs/` sem filtro.

---

### FINDING #1 — Ausência de `.dockerignore`

| Campo | Detalhe |
|---|---|
| **Risco** | 🟡 Médio |
| **Prioridade** | P3 |
| **Evidência** | Nenhum `.dockerignore` em `/var/app/` ou `/var/app/web-server/` |
| **Impacto** | O `COPY ./certs/` no Dockerfile copia `*.old`, `ca_bundle.crt` e outros arquivos desnecessários para a imagem. Se a imagem Docker for vazada/publicada, chaves privadas antigas estarão expostas. |
| **Correção** | Criar `/var/app/web-server/.dockerignore`: |

```
*.old
*.bak
*.tmp
ca_bundle.crt
.keep
```

---

### FINDING #2 — Arquivos `.old` de Certificados

| Campo | Detalhe |
|---|---|
| **Risco** | 🟢 Baixo |
| **Prioridade** | P4 |
| **Evidência** | `farmacia.ufmg.br.crt.old` (2403B) e `farmacia.ufmg.br.key.old` (1704B) em `web-server/certs/` |
| **Impacto** | Chave privada antiga armazenada desnecessariamente. Se comprometida, possibilita decriptação de tráfego histórico. |
| **Correção** | Remover os arquivos `.old` e garantir que não entrem no build via `.dockerignore`. |

---

## 2. Path Traversal

> [!TIP]
> O Caddy possui **proteção nativa** contra path traversal. Ele normaliza URIs antes do processamento e não é vulnerável a `../`, `%2e%2e`, dupla codificação, CVE-2021-41773 ou CVE-2021-42013 (vulnerabilidades do Apache httpd, não do Caddy).

| Vetor | Status |
|---|---|
| `../` | ✅ Protegido nativamente |
| `%2e%2e` | ✅ Normalização de URI |
| Dupla codificação | ✅ Protegido |
| CVE-2021-41773 | ✅ N/A (Apache httpd) |
| CVE-2021-42013 | ✅ N/A (Apache httpd) |

**Resultado:** Sem vulnerabilidades de path traversal identificadas.

---

## 3. Cabeçalhos HTTP de Segurança

### FINDING #3 — Ausência Total de Security Headers

| Campo | Detalhe |
|---|---|
| **Risco** | 🔴 Alto |
| **Prioridade** | P1 |
| **Evidência** | Nenhuma diretiva `header` no Caddyfile. A configuração Caddy ativa (via Admin API) confirma ausência de handlers de header. |
| **Impacto** | Sem proteção contra clickjacking, XSS, MIME sniffing, downgrade attacks. Facilita ataques de engenharia social e injeção de conteúdo. |

| Header | Status | Esperado |
|---|---|---|
| `Server` | ⚠️ Expõe "Caddy" | Remover ou ofuscar |
| `X-Powered-By` | ✅ Caddy não envia | — |
| Version leakage | ⚠️ Caddy v2.7.6 exposto via Admin API | Desabilitar Admin API |
| `Strict-Transport-Security` | ❌ **Ausente** | `max-age=63072000; includeSubDomains; preload` |
| `Content-Security-Policy` | ❌ **Ausente** | Definir política por aplicação |
| `X-Frame-Options` | ❌ **Ausente** | `DENY` ou `SAMEORIGIN` |
| `X-Content-Type-Options` | ❌ **Ausente** | `nosniff` |
| `Referrer-Policy` | ❌ **Ausente** | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | ❌ **Ausente** | Restringir features |

**Correção** — Adicionar snippet global no Caddyfile:

```caddyfile
(securityHeaders) {
    header {
        Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "SAMEORIGIN"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "camera=(), microphone=(), geolocation=()"
        -Server
    }
}
```

E importar em **cada bloco de domínio**: `import securityHeaders`

---

## 4. Métodos HTTP

> [!NOTE]
> O Caddy por padrão aceita todos os métodos HTTP e os repassa ao backend via `reverse_proxy`. Não há restrição de métodos configurada. Métodos como `TRACE`, `OPTIONS`, `DELETE`, `PUT` são aceitos.
> 
> **Risco:** Baixo — pois o Caddy é apenas proxy e os backends devem validar. Porém, `TRACE` pode facilitar XST (Cross-Site Tracing).

---

## 5. Análise do Caddyfile

### FINDING #4 — PHPMyAdmin/Mongo Express Expostos Sem Restrição de IP

| Campo | Detalhe |
|---|---|
| **Risco** | 🔴 Alto |
| **Prioridade** | P1 |
| **Evidência** | `phpmyadmin.farmacia.ufmg.br` (linha 141-145) e `mongo-express.farmacia.ufmg.br` (linha 174-178) acessíveis de qualquer IP |
| **Impacto** | PHPMyAdmin e Mongo Express são alvos primários de scanners. Dão acesso direto aos bancos de dados. Qualquer vulnerabilidade ou credencial fraca = comprometimento total dos dados. |

**Correção** — Restringir acesso por IP:

```caddyfile
phpmyadmin.farmacia.ufmg.br {
    import tlsConfig
    @allowed remote_ip 150.164.0.0/16
    handle @allowed {
        reverse_proxy 10.10.10.2:8081
    }
    respond "Forbidden" 403
}
```

Aplicar o mesmo padrão para `mongo-express` e `monitor`.

---

### FINDING #5 — Monitor Exposto Sem Restrição de IP

| Campo | Detalhe |
|---|---|
| **Risco** | 🔴 Alto |
| **Prioridade** | P1 |
| **Evidência** | `monitor.farmacia.ufmg.br` (linha 166-170) acessível de qualquer IP |
| **Impacto** | Expõe painel de monitoramento (Portainer/outro na porta 9000) publicamente. Permite reconhecimento da infraestrutura e possível acesso administrativo. |
| **Correção** | Mesmo padrão de restrição por IP do finding anterior. |

---

### FINDING #6 — Sem Access Logs no Caddy

| Campo | Detalhe |
|---|---|
| **Risco** | 🟡 Médio |
| **Prioridade** | P2 |
| **Evidência** | Nenhuma diretiva `log` no Caddyfile. Apenas logs de erro do container (`docker logs`) estão disponíveis. |
| **Impacto** | Impossibilidade de auditoria forense, detecção de intrusão, correlação de eventos. Sem access logs, ataques passam despercebidos. |

**Correção:**

```caddyfile
{
    log {
        output file /var/log/caddy/access.log {
            roll_size 100mb
            roll_keep 10
        }
        format json
        level INFO
    }
}
```

---

### FINDING #7 — Sem Rate Limiting

| Campo | Detalhe |
|---|---|
| **Risco** | 🟡 Médio |
| **Prioridade** | P2 |
| **Evidência** | Nenhum módulo de rate limiting configurado |
| **Impacto** | Vulnerável a brute force, credential stuffing, DDoS na camada de aplicação |
| **Correção** | Instalar e configurar o módulo `caddy-ratelimit` ou implementar rate limiting nos backends. |

---

### FINDING #8 — Sem Compressão (encode)

| Campo | Detalhe |
|---|---|
| **Risco** | 🟢 Baixo (performance, não segurança) |
| **Prioridade** | P4 |
| **Evidência** | Nenhuma diretiva `encode` no Caddyfile |
| **Impacto** | Desperdício de banda. Como é reverse proxy, a compressão pode ser feita no backend, mas idealmente o proxy deveria comprimir. |
| **Correção** | Adicionar `encode zstd gzip` nos blocos de domínio ou como snippet global. |

---

### Outros pontos do Caddyfile

| Item | Status | Observação |
|---|---|---|
| `file_server` | ✅ Apenas no `handle_errors` (manutenção) | Seguro |
| `browse` | ✅ Não utilizado | Seguro |
| `auto_https` | ⚠️ Desabilitado implicitamente (usa TLS manual) | Aceitável |
| `trusted_proxies` | ⚠️ Não configurado | Se estiver atrás de CDN/LB, necessário |
| `cloud` → `10.10.10.5:443` | ⚠️ Reverse proxy para HTTPS sem `transport` | Pode causar erros de certificado |

---

## 6. Análise de Logs

### FINDING #9 — Atividade Maliciosa Detectada nos Logs

| Campo | Detalhe |
|---|---|
| **Risco** | 🔴 Alto |
| **Prioridade** | P1 |
| **Evidência** | Logs do container Caddy mostram atividade de scanners e bots: |

**Ataques Identificados:**

| Tipo | IP | URI/Alvo | Detalhe |
|---|---|---|---|
| **Scan de `.env`** | `94.154.43.185` | `/.env` | Scanner procurando credenciais vazadas |
| **wp-login brute force** | `94.154.43.177` | `/wp-login.php` (intranet) | Tentativa de acesso ao WordPress |
| **Bot scraping** | `51.59.48.*` | Múltiplos documentos | ChatGPT-User bot (crawling agressivo) |
| **Bot scraping** | `216.73.217.150` | `/ACT/Programaact.doc` | ClaudeBot (crawling) |

> [!WARNING]
> Os IPs `94.154.43.*` estão realizando scanning ativo contra a infraestrutura. Sem Fail2Ban ou firewall, esses IPs continuarão suas tentativas indefinidamente.

---

## 7. Docker

### FINDING #10 — Portainer Agent com Acesso Root ao Host (CRÍTICO)

| Campo | Detalhe |
|---|---|
| **Risco** | 🔴🔴 **CRÍTICO** |
| **Prioridade** | **P0** |
| **Evidência** | `compose.yaml` linhas 22-25 |

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock   # Controle total do Docker
  - /var/lib/docker/volumes:/var/lib/docker/volumes  # Acesso a todos os volumes
  - /:/host   # ⚠️ FILESYSTEM INTEIRO DO HOST MONTADO
```

| **Impacto** | O bind mount `/:/host` dá ao container acesso de **leitura e escrita** a TODO o filesystem do host (incluindo `/etc/shadow`, `/etc/ssh/`, chaves privadas, etc.). Combinado com o Docker socket, equivale a acesso root completo. A porta 9001 está exposta em `0.0.0.0` — acessível de qualquer IP. |

**Correção URGENTE:**

```yaml
portainer_agent:
  image: portainer/agent:2.27.7
  container_name: portainer_agent
  restart: always
  ports:
    - "127.0.0.1:9001:9001"  # Apenas localhost
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro  # Read-only
    - /var/lib/docker/volumes:/var/lib/docker/volumes:ro
    # REMOVER: - /:/host
```

> [!CAUTION]
> Este é o finding mais grave da auditoria. Se um atacante acessar a porta 9001 (exposta publicamente), terá controle total do servidor via Portainer Agent. **Corrigir imediatamente.**

---

### FINDING #11 — Web Server com `network_mode: host`

| Campo | Detalhe |
|---|---|
| **Risco** | 🔴 Alto |
| **Prioridade** | P2 |
| **Evidência** | `compose.yaml` linha 14: `network_mode: "host"` |
| **Impacto** | O container Caddy compartilha o namespace de rede do host. Pode acessar todos os serviços do host (incluindo o Admin API Caddy na porta 2019). Anula o isolamento de rede do Docker. |

**Correção:**

```yaml
web-server:
  # ...
  ports:
    - "80:80"
    - "443:443"
    - "443:443/udp"
  # Remover: network_mode: "host"
```

---

### FINDING #12 — Container Rodando como Root

| Campo | Detalhe |
|---|---|
| **Risco** | 🟡 Médio |
| **Prioridade** | P3 |
| **Evidência** | `docker inspect` mostra `User: ""` (root). Sem `read_only: true`, sem `security_opt`, sem `cap_drop`. |
| **Impacto** | Se houver escape do container, o atacante será root no host. |

**Correção** — no Dockerfile ou compose:

```yaml
web-server:
  read_only: true
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
```

---

### Resumo Docker

| Item | Status |
|---|---|
| Portas expostas | ⚠️ 9001 em 0.0.0.0, 80/443 via host network |
| Volumes perigosos | ❌ `/:/host` no Portainer Agent |
| Docker socket | ⚠️ Montado no Portainer Agent |
| Privileged | ✅ `false` em ambos |
| Capabilities | ⚠️ Nenhuma removida |
| Network mode | ⚠️ `host` no web-server |
| Log rotation | ⚠️ Não configurado (`json-file` sem limites) |
| User | ⚠️ Root em ambos |
| Read-only FS | ⚠️ Não configurado |

---

## 8. Firewall

### FINDING #13 — Firewall Inexistente

| Campo | Detalhe |
|---|---|
| **Risco** | 🔴 Alto |
| **Prioridade** | P1 |
| **Evidência** | `iptables`: INPUT policy ACCEPT sem regras. `nftables`: policy accept em todas as chains. `ufw`: Status inactive. |
| **Impacto** | Todas as portas do LXC estão acessíveis sem filtro. A porta 9001 (Portainer Agent), 22 (SSH), 2019 (Caddy Admin), 25 (SMTP) estão expostas. |

**Portas detectadas abertas:**

| Porta | Serviço | Exposição |
|---|---|---|
| 22 | SSH | `0.0.0.0` — público |
| 25 | Postfix | `127.0.0.1` — local ✅ |
| 80 | Caddy HTTP | `*` — público (esperado) |
| 443 | Caddy HTTPS | `*` — público (esperado) |
| 2019 | Caddy Admin API | `127.0.0.1` — local ✅ |
| 3478 | Signaling | `*` — público |
| 9001 | Portainer Agent | `0.0.0.0` — **público ⚠️** |

**Correção:**

```bash
# Ativar UFW
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw allow 443/udp comment 'HTTP/3'
ufw allow 3478/tcp comment 'Signaling'
# Portainer apenas da rede interna
ufw allow from 10.10.10.0/24 to any port 9001 comment 'Portainer Agent'
ufw enable
```

> [!IMPORTANT]
> Em LXC, o firewall pode ser gerenciado também no nível do Proxmox. Verificar se há regras no host PVE.

---

## 9. Fail2Ban

### FINDING #14 — Fail2Ban Não Instalado

| Campo | Detalhe |
|---|---|
| **Risco** | 🔴 Alto |
| **Prioridade** | P2 |
| **Evidência** | `which fail2ban-client` retorna vazio. Não instalado. |
| **Impacto** | Sem proteção contra brute force SSH, scanning de aplicações web, tentativas automatizadas. Os logs já mostram scanning ativo (`.env`, `wp-login.php`). |

**Faz sentido usar Fail2Ban neste servidor? SIM, absolutamente.**

Justificativa:
1. SSH está exposto na porta 22
2. Logs mostram scanning ativo de bots
3. PHPMyAdmin e Mongo Express estão públicos
4. Não há rate limiting no Caddy
5. Não há firewall ativo

**Correção:**

```bash
apt install fail2ban -y

# /etc/fail2ban/jail.local
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
banaction = ufw

[sshd]
enabled = true
port = 22
logpath = /var/log/auth.log

# Criar jail customizado para Caddy quando access logs estiverem habilitados
EOF

systemctl enable --now fail2ban
```

---

## 10. Infraestrutura Complementar

### FINDING #15 — Caddy Desatualizado

| Campo | Detalhe |
|---|---|
| **Risco** | 🟡 Médio |
| **Prioridade** | P2 |
| **Evidência** | Caddy v2.7.6 — a versão estável atual é v2.9.x |
| **Impacto** | Possíveis vulnerabilidades corrigidas em versões mais recentes. |
| **Correção** | Atualizar Dockerfile: `FROM caddy:2.9` |

---

## Matriz de Prioridades

| Prioridade | Finding | Ação |
|:---:|---|---|
| **P0** | #10 — Portainer `/:/host` + porta 9001 pública | Remover bind mount, restringir porta |
| **P1** | #3 — Sem security headers | Adicionar snippet global |
| **P1** | #4 — PHPMyAdmin público | Restringir por IP |
| **P1** | #5 — Monitor público | Restringir por IP |
| **P1** | #9 — Ataques ativos nos logs | Bloquear IPs, instalar Fail2Ban |
| **P1** | #13 — Sem firewall | Configurar UFW |
| **P2** | #6 — Sem access logs | Configurar logging |
| **P2** | #7 — Sem rate limiting | Avaliar módulo |
| **P2** | #11 — network_mode host | Migrar para port mapping |
| **P2** | #14 — Sem Fail2Ban | Instalar e configurar |
| **P2** | #15 — Caddy desatualizado | Atualizar imagem |
| **P3** | #1 — Sem .dockerignore | Criar arquivo |
| **P3** | #12 — Container como root | Hardening Docker |
| **P4** | #2 — Arquivos .old | Remover |
| **P4** | #8 — Sem compressão | Adicionar encode |

---

## Nota Geral de Segurança

```
╔══════════════════════════════════════════╗
║                                          ║
║         NOTA GERAL:  4.5 / 10           ║
║                                          ║
╚══════════════════════════════════════════╝
```

### Justificativa da Nota

| Aspecto | Nota | Peso |
|---|:---:|:---:|
| Exposição Web (arquivos sensíveis) | 7/10 | 10% |
| Path Traversal | 9/10 | 10% |
| Cabeçalhos HTTP | 1/10 | 15% |
| Configuração Caddy | 4/10 | 15% |
| Segurança Docker | 2/10 | 20% |
| Firewall | 1/10 | 15% |
| Logging & Monitoramento | 2/10 | 15% |

**Pontos Positivos:**
- ✅ Caddy nativamente seguro contra path traversal
- ✅ TLS configurado corretamente com certificados institucionais
- ✅ Arquitetura de separação por LXC (proxy, apps, banco)
- ✅ Sem arquivos sensíveis expostos via web
- ✅ `.gitignore` bem configurado
- ✅ `auto_https` com redirect HTTP→HTTPS funcionando
- ✅ Containers não são privilegiados

**Pontos Críticos:**
- ❌ Portainer Agent com acesso total ao host E porta pública
- ❌ Nenhum firewall ativo
- ❌ Nenhum security header
- ❌ Ferramentas admin (PHPMyAdmin, Mongo Express, Monitor) sem restrição de IP
- ❌ Sem Fail2Ban, sem rate limiting, sem access logs
- ❌ Ataques ativos sendo ignorados (scanning de `.env`, `wp-login`)

---

## Plano de Ação Sugerido (Ordem de Execução)

### Fase 1 — Emergencial (Fazer AGORA)
1. Remover `/:/host` do Portainer Agent
2. Restringir porta 9001 para `127.0.0.1` ou rede interna
3. Ativar UFW com regras básicas
4. Restringir PHPMyAdmin, Mongo Express e Monitor por IP

### Fase 2 — Urgente (Esta Semana)
5. Adicionar security headers globais no Caddyfile
6. Instalar e configurar Fail2Ban
7. Habilitar access logs no Caddy
8. Atualizar Caddy para v2.9.x

### Fase 3 — Importante (Este Mês)
9. Migrar web-server de `network_mode: host` para port mapping
10. Criar `.dockerignore`
11. Hardening Docker (read_only, cap_drop, no-new-privileges)
12. Configurar rate limiting
13. Remover arquivos `.old`
14. Adicionar compressão (encode gzip)

---

> [!CAUTION]
> **O finding #10 (Portainer Agent) é uma vulnerabilidade crítica que deve ser corrigida imediatamente.** O bind mount `/:/host:rw` combinado com a porta 9001 exposta publicamente permite que qualquer pessoa na internet que descubra a porta obtenha acesso completo de leitura e escrita ao filesystem do servidor. Isso equivale a entregar a chave root do servidor.