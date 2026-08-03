# Deploy Staxxit on Hetzner (next to Note Mentor)

Always-on Node + Socket.IO behind nginx. Shares the same VPS as Note Mentor; uses a **different domain/subdomain** and port **3000**.

## Suggested URL

`staxxit.note-mentor.com` → same server IP as Note Mentor (`91.99.226.21`).

## 1. DNS

At your domain provider, add:

| Type | Name | Value |
|------|------|--------|
| A | `staxxit` | `91.99.226.21` |

Wait until `nslookup staxxit.note-mentor.com` shows that IP.

## 2. Server setup (SSH as root)

```bash
export DOMAIN="staxxit.note-mentor.com"
export BRANCH="main"
export REPO_URL="https://github.com/Keimpsk/staxxit.git"

curl -fsSL -o /tmp/setup-staxxit.sh \
  "https://raw.githubusercontent.com/Keimpsk/staxxit/${BRANCH}/deploy/hetzner/setup.sh"
bash /tmp/setup-staxxit.sh
```

## 3. HTTPS

```bash
apt-get install -y certbot python3-certbot-nginx
certbot --nginx -d staxxit.note-mentor.com
```

Open: `https://staxxit.note-mentor.com`

## 4. Update after git push

```bash
export BRANCH="main"
bash /var/www/staxxit/deploy/hetzner/update.sh
```

## Layout

| Path | Purpose |
|------|---------|
| `/var/www/staxxit` | App + `node_modules` |
| `/etc/systemd/system/staxxit.service` | Node service (port 3000) |
| `/etc/nginx/sites-available/staxxit` | Reverse proxy + WebSockets |

## Useful commands

```bash
systemctl status staxxit
journalctl -u staxxit -f
nginx -t && systemctl reload nginx
```

## Notes

- Online multiplayer needs WebSocket proxy (`/socket.io/`) — included in the nginx config.
- Rooms are **in-memory**: restart clears open online games.
- Free Render can be turned off after this works.
