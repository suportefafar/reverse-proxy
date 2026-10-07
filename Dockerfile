FROM caddy:2.7

EXPOSE 80

WORKDIR /etc/caddy/

COPY Caddyfile /etc/caddy/Caddyfile

RUN caddy fmt --overwrite