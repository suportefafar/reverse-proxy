# Reverse Proxy - Faculdade de Farmácia UFMG

Este repositório contém a infraestrutura de Proxy Reverso utilizada pela Faculdade de Farmácia da UFMG, baseada em **Caddy** e **Docker Compose**.

## Descrição

O sistema gerencia o roteamento de diversos subdomínios da FAFAR (farmacia.ufmg.br), oferecendo:
- **Roteamento Inteligente**: Encaminhamento de tráfego para diferentes backends (PHP, Rails, Node.js, etc.).
- **Ambientes Dinâmicos**: Roteamento baseado no IP de origem para facilitar o desenvolvimento e homologação (Dev/Homol).
- **Alta Disponibilidade**: Sistema de fallback automático para uma página de manutenção (`web-temp`) caso os backends principais estejam indisponíveis.
- **Segurança**: Gerenciamento Centralizado de certificados SSL.
- **Gerenciamento**: Integração com Portainer Agent para monitoramento remoto.

## Estrutura do Projeto

- `/web-server`: Configurações do Caddy (Dockerfile, Caddyfile e certificados).
- `/web-server/public/`: Página de manutenção/fallback servida pelo Caddy.
- `compose.yaml`: Orquestração dos serviços Docker.

## Como Usar

### Pré-requisitos
- Docker e Docker Compose instalados.
- Certificados SSL válidos localizados em `./web-server/certs/`.

### Instalação
1. Clone o repositório:
   ```bash
   git clone https://github.com/suportefafar/reverse-proxy.git
   cd reverse-proxy
   ```

2. Certifique-se de que os certificados estão nos caminhos corretos:
   - `./web-server/certs/farmacia.ufmg.br.crt`
   - `./web-server/certs/farmacia.ufmg.br.key`

3. (Opcional) Ajuste as definições de IP no `Caddyfile` para corresponder à sua infraestrutura de rede.

4. Inicie os serviços:
   ```bash
   docker compose up -d --build
   ```

## Infraestrutura Recomendada

Para garantir a melhor performance e compatibilidade, recomenda-se:

- **Sistema Operacional**: Linux (Ubuntu 22.04 LTS ou Debian 12 preferencialmente).
- **Rede**:
  - O Caddy está configurado com `network_mode: "host"` para máxima performance e acesso direto à rede do host.
  - Certifique-se de que as portas **80** e **443** estejam abertas no firewall.
  - A porta **9001** deve estar acessível se desejar utilizar o Portainer Agent.
- **Recursos**:
  - Mínimo de 1GB de RAM.
  - 1 vCPU é suficiente para a maioria das cargas de trabalho do Caddy.
- **Configuração de Rede Interna**: O projeto assume que os servidores de backend estão na rede `10.10.10.0/24`. Se sua rede interna for diferente, você deve atualizar os IPs no arquivo `web-server/Caddyfile`.

---
*Mantido pela equipe de TI da Faculdade de Farmácia - UFMG.*
