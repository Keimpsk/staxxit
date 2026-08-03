#!/usr/bin/env bash
# Pull latest code and restart Staxxit on the VPS.
# Run as root:  bash /var/www/staxxit/deploy/hetzner/update.sh

set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/staxxit}"
BRANCH="${BRANCH:-main}"

git config --global --add safe.directory "${APP_DIR}" || true

cd "${APP_DIR}"
git fetch origin
git checkout "${BRANCH}"
git pull origin "${BRANCH}"

npm install --omit=dev

chown -R www-data:www-data "${APP_DIR}"
systemctl restart staxxit
systemctl --no-pager --full status staxxit || true
echo "Updated ${BRANCH}."
