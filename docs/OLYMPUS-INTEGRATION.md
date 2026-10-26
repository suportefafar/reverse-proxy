# Proxy domains by environment

The Olympus Compose environment includes Compose fragments from this repository, which choose a distinct Caddyfile:

- `olymctl dev` mounts `web-server/Caddyfile.olympus.dev`. It serves `*.farmacia.local` with Caddy's internal development certificates.
- `olymctl prod` mounts `web-server/Caddyfile.olympus.prod`. It serves `*.farmacia.ufmg.br` with the installed production certificate from `.env`.

The local development command registers only `*.farmacia.local` in `/etc/hosts`. Olympus manages these entries as part of dev environment setup. Production `*.farmacia.ufmg.br` names must use normal DNS and resolve to the production VM. Earlier Olympus versions also mapped official `.ufmg.br` names to `127.0.0.1`; the updated `olymctl dev up` removes only those Olympus-managed stale mappings, preserves `.local`, and saves a backup before editing `/etc/hosts`. If passwordless sudo is unavailable, it asks for confirmation before invoking sudo interactively to remove stale mappings or add missing local hostnames. Without a terminal, or if permission is declined, it lists the required manual changes and leaves those mappings untouched.

The active production proxy was compared with the previous production Caddyfile and validates successfully on the VM. Its host routes point at services on the shared Docker edge network. Dike is an internal service and intentionally has no hostname in either environment.

## Production access controls and logs

The production Caddyfile is configured to allow `hermes.farmacia.ufmg.br` and `design-system.farmacia.ufmg.br` only from `150.164.110.0/24` and `150.164.111.0/24`; Caddy returns HTTP 403 to other source addresses. This uses the direct peer address seen by Caddy. If a load balancer or another reverse proxy is added in front, configure and restrict Caddy's trusted proxies before relying on client IP allowlists.

`intranet.farmacia.local` routes to the WordPress service `intranet-website:80` in development; `intranet-stage.farmacia.local` routes to the Rails service `intranet:80`. In production, `intranet-stage.farmacia.ufmg.br` routes to `intranet:80`; the intranet deployment prepares the matching proxy checkout and recreates Caddy to activate the route. The existing `intranet.farmacia.ufmg.br` hostname continues to route to the legacy WordPress service `intranet-website:80`.

The production Caddyfile applies HSTS, `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy` to each published site. CSP is intentionally left to each application because a global policy can break application assets and integrations. The HSTS policy does not include `includeSubDomains`, so it does not impose HTTPS on unrelated subdomains.

Caddy access logs are JSON, stored in the persistent Docker volume `caddy-logs` and split into one file per hostname under `/var/log/caddy` in the proxy container. Each file rotates daily or at 100 MiB; Caddy keeps at most 30 rotated files and removes files older than 30 days. The file-count limit can shorten retention if traffic produces more than 30 rotations in a month. These are proxy access logs; application and container output remains available through Docker's logging driver.

The proxy Compose fragments and route files are maintained in this repository. Olympus owns orchestration and the local `/etc/hosts` setup needed to resolve development hostnames.

## Ports exposed in development

The dev Compose override publishes only on loopback: Dike `3002`, PostgreSQL `5432`, MySQL `3306`, and MongoDB `27017`. They are reachable from tools on the development host without opening them to the LAN. Production Compose has no host port mappings for Dike or the databases; it keeps access on Docker networks only.

## Athenas local

`athenas.farmacia.local` em HTTP e HTTPS aponta para `athenas:3000` na rede `edge`, em desenvolvimento. `athenas.farmacia.ufmg.br` usa TLS e aponta para o mesmo serviço na produção. O Olympus mantém web/worker/Ollama e usa PostgreSQL com pgvector. Depois de atualizar os serviços, `olymctl` recarrega o Caddy para aplicar o arquivo montado sem depender de mudanças na imagem.
