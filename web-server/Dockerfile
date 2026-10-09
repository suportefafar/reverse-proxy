FROM caddy:2.7

EXPOSE 443
EXPOSE 80

WORKDIR /etc/caddy/

COPY Caddyfile /etc/caddy/Caddyfile

COPY ./tls/ /etc/caddy/tls/


COPY ./public/ /srv/

RUN caddy fmt --overwrite
