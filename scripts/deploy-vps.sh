#!/usr/bin/env bash
set -Eeuo pipefail

DOMAIN="${1:-brench.singularitydev.xyz}"
EMAIL="${2:-}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE_NAME="brench"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo: sudo $0 [domain] [email-for-certificate]" >&2
  exit 1
fi
if [[ ! -f "${APP_DIR}/docker-compose.yml" ]]; then
  echo "Run this script from the app checkout; docker-compose.yml was not found." >&2
  exit 1
fi
if [[ -z "${EMAIL}" ]]; then
  read -r -p "Email for Let's Encrypt certificate notices: " EMAIL
fi
if [[ ! "${DOMAIN}" =~ ^[A-Za-z0-9.-]+$ || "${DOMAIN}" != *.* || -z "${EMAIL}" ]]; then
  echo "Provide a valid domain and certificate email." >&2
  exit 1
fi

source /etc/os-release
if [[ "${ID}" != "ubuntu" ]]; then
  echo "This installer supports Ubuntu. Detected: ${PRETTY_NAME:-unknown}" >&2
  exit 1
fi

echo "Installing Docker Engine and Compose, Nginx, Certbot, and htpasswd..."
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl nginx certbot apache2-utils

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  UBUNTU_CODENAME="${UBUNTU_CODENAME:-${VERSION_CODENAME}}"
  printf 'Types: deb\nURIs: https://download.docker.com/linux/ubuntu\nSuites: %s\nComponents: stable\nArchitectures: %s\nSigned-By: /etc/apt/keyrings/docker.asc\n' \
    "${UBUNTU_CODENAME}" "$(dpkg --print-architecture)" > /etc/apt/sources.list.d/docker.sources
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

systemctl enable --now docker nginx

read -r -p "HTTP Basic Auth username [brench]: " AUTH_USER
AUTH_USER="${AUTH_USER:-brench}"
read -r -s -p "HTTP Basic Auth password (at least 12 characters): " AUTH_PASSWORD
printf '\n'
if [[ "${#AUTH_PASSWORD}" -lt 12 ]]; then
  echo "Password must be at least 12 characters." >&2
  exit 1
fi
read -r -s -p "Confirm password: " AUTH_PASSWORD_CONFIRM
printf '\n'
if [[ "${AUTH_PASSWORD}" != "${AUTH_PASSWORD_CONFIRM}" ]]; then
  echo "Passwords do not match." >&2
  exit 1
fi
printf '%s\n' "${AUTH_PASSWORD}" | htpasswd -B -i -c /etc/nginx/.htpasswd "${AUTH_USER}"
unset AUTH_PASSWORD AUTH_PASSWORD_CONFIRM
chown root:www-data /etc/nginx/.htpasswd
chmod 0640 /etc/nginx/.htpasswd

mkdir -p /var/www/letsencrypt
cat > "/etc/nginx/sites-available/${SITE_NAME}" <<NGINX_HTTP
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    location ^~ /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
        default_type "text/plain";
    }

    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        proxy_read_timeout 300s;
        auth_basic "Brench";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
NGINX_HTTP

ln -sfn "/etc/nginx/sites-available/${SITE_NAME}" "/etc/nginx/sites-enabled/${SITE_NAME}"
nginx -t
systemctl reload nginx

echo "Building and starting Brench (host port 8765 stays private on loopback)..."
cd "${APP_DIR}"
docker compose up -d --build

echo "Requesting Let's Encrypt certificate for ${DOMAIN}..."
certbot certonly --non-interactive --agree-tos --email "${EMAIL}" \
  --webroot -w /var/www/letsencrypt -d "${DOMAIN}"

cat > "/etc/nginx/sites-available/${SITE_NAME}" <<NGINX_HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    location ^~ /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
        default_type "text/plain";
    }
    location / { return 301 https://\$host\$request_uri; }
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name ${DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        proxy_read_timeout 300s;
        auth_basic "Brench";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
NGINX_HTTPS

nginx -t
systemctl reload nginx
mkdir -p /etc/letsencrypt/renewal-hooks/deploy
cat > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx <<'HOOK'
#!/usr/bin/env sh
nginx -t && systemctl reload nginx
HOOK
chmod 0755 /etc/letsencrypt/renewal-hooks/deploy/reload-nginx
systemctl enable --now certbot.timer

echo
echo "Brench is live at https://${DOMAIN} (HTTP Basic Auth enabled)."
echo "Allow inbound TCP 80 and 443 in your VPS firewall/security group. Do not expose 8765."
