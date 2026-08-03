# Staxxit on Hetzner — baby steps (same server as Note Mentor)

You already have a Hetzner VPS for Note Mentor. We add Staxxit as a **second site** on that same machine.

**Result:** `https://staxxit.note-mentor.com` always on (no Render sleep).  
**Time:** ~20–40 minutes (mostly DNS wait).

---

## Overview

| Step | What |
|------|------|
| 1 | DNS: subdomain → server IP |
| 2 | SSH into the server |
| 3 | Run setup script |
| 4 | HTTPS (certbot) |
| 5 | Test multiplayer |
| later | Optional: turn off Render |

Server IP (Note Mentor): **`91.99.226.21`**

---

## Step 1 — DNS

At the place where you manage **note-mentor.com** (same panel as before):

Add an **A** record:

| Type | Name / host | Value |
|------|-------------|--------|
| A | `staxxit` | `91.99.226.21` |

That creates **`staxxit.note-mentor.com`**.

On your PC (PowerShell), wait until this shows the right IP:

```powershell
nslookup staxxit.note-mentor.com
```

---

## Step 2 — SSH

```powershell
ssh root@91.99.226.21
```

---

## Step 3 — Install Staxxit (on the server)

Copy-paste:

```bash
export DOMAIN="staxxit.note-mentor.com"
export BRANCH="main"
export REPO_URL="https://github.com/Keimpsk/staxxit.git"

curl -fsSL -o /tmp/setup-staxxit.sh \
  "https://raw.githubusercontent.com/Keimpsk/staxxit/${BRANCH}/deploy/hetzner/setup.sh"
bash /tmp/setup-staxxit.sh
```

If git says **dubious ownership**, run:

```bash
git config --global --add safe.directory /var/www/staxxit
```

and re-run the setup script if needed.

Check:

```bash
systemctl status staxxit --no-pager
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/
```

Expect: **active (running)** and **200**.

Note Mentor keeps working: its nginx site is separate (`midi-oefenapp`).

---

## Step 4 — HTTPS

Only after DNS points to the server:

```bash
apt-get install -y certbot python3-certbot-nginx
certbot --nginx -d staxxit.note-mentor.com
```

Choose redirect to HTTPS if asked (**2**).

Open: **https://staxxit.note-mentor.com**

---

## Step 5 — Quick test

1. Homepage loads.  
2. **Quick Random Setup (Hotseat)** works.  
3. **Create Online Game** → open second browser/incognito → **Join Online Game** with the code.

---

## Later: update after code change

```bash
export BRANCH="main"
bash /var/www/staxxit/deploy/hetzner/update.sh
```

---

## Turn off free Render (optional)

When Hetzner works:

1. Open [Render Dashboard](https://dashboard.render.com/)  
2. Find the Staxxit service  
3. Suspend or delete it  

Old URL `staxxit.onrender.com` will stop; use the new domain.

---

## If something breaks

```bash
systemctl status staxxit --no-pager
journalctl -u staxxit -n 50 --no-pager
nginx -t
systemctl status nginx --no-pager
```

Paste that output when asking for help.
