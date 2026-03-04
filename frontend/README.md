# requirements

install Caddy and Docker.

test locally using caddy.


npm run build
caddy run --config Caddyfile


docker build -t papertrail-site .
docker run -p 3000:3000 papertrail-site