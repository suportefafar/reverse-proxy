# Reverse Proxy - Faculdade de Farmácia UFMG

Este repositório contém a infraestrutura de Proxy Reverso utilizada pela Faculdade de Farmácia da UFMG, baseada em **Caddy** e **Docker Compose**.

## Descrição

O sistema gerencia o roteamento de diversos subdomínios da FAFAR (farmacia.ufmg.br), oferecendo:
- **Roteamento Interno**: Encaminhamento para os serviços pelo DNS da rede do Docker Compose, sem depender de IPs ou portas publicadas pelo host.
- **Ambientes Dinâmicos**: Uso de `*.local` em desenvolvimento e `*.ufmg.br` em produção a partir do mesmo `Caddyfile`.
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

3. Defina o ambiente do Caddy no Docker Compose:
   - Desenvolvimento: `CADDY_ENVIRONMENT=development` e `DOMAIN_SUFFIX=local`.
   - Produção: `CADDY_ENVIRONMENT=production` e `DOMAIN_SUFFIX=ufmg.br`.

4. Inicie os serviços:
   ```bash
   docker compose up -d --build
   ```

## Infraestrutura Recomendada

Para garantir a melhor performance e compatibilidade, recomenda-se:

- **Sistema Operacional**: Linux (Ubuntu 22.04 LTS ou Debian 12 preferencialmente).
- **Rede**:
  - O Caddy utiliza a rede bridge do Docker, com publicação explícita das portas necessárias.
  - O proxy deve compartilhar a rede do Docker Compose com os serviços de aplicação para resolvê-los pelos nomes de serviço, como `institutional-website` e `stagemanager`.
  - Certifique-se de que as portas **80**, **443** e **3478** estejam abertas no firewall. As portas HTTPS também são publicadas via UDP para suporte a HTTP/3.
  - A porta **9001** deve estar acessível se desejar utilizar o Portainer Agent.
- **Recursos**:
  - Mínimo de 1GB de RAM.
  - 1 vCPU é suficiente para a maioria das cargas de trabalho do Caddy.
- **Configuração de Rede Interna**: Os serviços de aplicação são acessados diretamente pela rede do Docker. Apenas o serviço externo de monitoramento ainda utiliza um endereço da rede `10.10.10.0/24`.

---
*Mantido pela equipe de TI da Faculdade de Farmácia - UFMG.*
