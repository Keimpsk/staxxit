#!/usr/bin/env bash
# First-time setup on Ubuntu Hetzner VPS (can share the box with Note Mentor).
# Run as root:  bash setup.sh
#
#   export DOMAIN="staxxit.note-mentor.com"
#   export BRANCH="main"
#   export REPO_URL="https://github.com/Keimpsk/staxxit.git"
#   bash setup.sh

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Keimpsk/staxxit.git}"
BRANCH="${BRANCH:-main}"
APP_DIR="${APP_DIR:-/var/www/staxxit}"
DOMAIN="${DOMAIN:-}"

echo "==> Installing Node.js (NodeSource 20.x if needed)"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y curl ca-certificates gnupg nginx git

if ! command -v node >/dev/null 2>&1 || ! node -v | grep -qE 'v(1[8-9]|[2-9][0-9])'; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi
node -v
npm -v

echo "==> Cloning app to ${APP_DIR}"
if [[ -d "${APP_DIR}/.git" ]]; then
  git config --global --add safe.directory "${APP_DIR}" || true
  git -C "${APP_DIR}" fetch origin
  git -C "${APP_DIR}" checkout "${BRANCH}"
  git -C "${APP_DIR}" pull origin "${BRANCH}"
else
  mkdir -p "$(dirname "${APP_DIR}")"
  git clone --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
  git config --global --add safe.directory "${APP_DIR}" || true
fi

echo "==> npm install (production)"
cd "${APP_DIR}"
npm install --omit=dev

echo "==> Permissions (www-data)"
chown -R www-data:www-data "${APP_DIR}"

echo "==> systemd service"
cp "${APP_DIR}/deploy/hetzner/staxxit.service" /etc/systemd/system/staxxit.service
systemctl daemon-reload
systemctl enable staxxit
systemctl restart staxxit
systemctl --no-pager --full status staxxit || true

echo "==> nginx"
if [[ -n "${DOMAIN}" ]]; then
  sed "s/YOUR_DOMAIN/${DOMAIN}/g" \
    "${APP_DIR}/deploy/hetzner/nginx-staxxit.conf" \
    > /etc/nginx/sites-available/staxxit
else
  sed "s/server_name YOUR_DOMAIN;/server_name _;/" \
    "${APP_DIR}/deploy/hetzner/nginx-staxxit.conf" \
    > /etc/nginx/sites-available/staxxit
fi

ln -sfn /etc/nginx/sites-available/staxxit /etc/nginx/sites-enabled/staxxit
# Keep other sites (e.g. Note Mentor); only remove default if present
if [[ -L /etc/nginx/sites-enabled/default ]]; then
  rm -f /etc/nginx/sites-enabled/default
fi

nginx -t
systemctl reload nginx

echo ""
echo "==> Done (HTTP)."
echo "    App dir:  ${APP_DIR}"
echo "    Service:  systemctl status staxxit"
echo "    Logs:     journalctl -u staxxit -f"
echo ""

if [[ -n "${DOMAIN}" ]]; then
  echo "==> HTTPS with Let's Encrypt:"
  echo "    apt-get install -y certbot python3-certbot-nginx"
  echo "    certbot --nginx -d ${DOMAIN}"
  echo ""
  echo "    Open: https://${DOMAIN}"
else
  IP="$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')"
  echo "==> No DOMAIN set — test via Host header or set DOMAIN and re-run."
  echo "    Local: curl -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:3000/"
fi
