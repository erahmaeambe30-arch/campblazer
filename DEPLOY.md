# Deploying CampBlazer for free

| Option | What it gives you | Cost | Best for |
|---|---|---|---|
| A. GitHub | Your code online, version history, shareable repo link | Free | Submitting / sharing the source |
| B. Laptop + Cloudflare Quick Tunnel | A public `https://….trycloudflare.com` link to the app running on YOUR laptop: 4 workers, PostgreSQL, Redis, live WebSockets | Free, no account | The panel demo (full PDC features) |
| D. GitHub Codespaces | The whole app (backend + frontend + PostgreSQL + Redis) runs in GitHub's cloud; a public `…app.github.dev` link | Free monthly hours on a personal account | Deploying from GitHub without your laptop running it |
| C. Render (1 web service) + Neon | Always-reachable website, no laptop needed | Free tiers (sleeps when idle; can hit account limits) | Leaving it online after the defense |

---

## A. Put the code on GitHub

1. Create an empty repository on github.com (New → name it `campblazer` → **don't** add a README).
2. In the VS Code terminal, inside the `campblazer` folder:

```bash
git init
git add .
git commit -m "CampBlazer capstone"
git branch -M main
git remote add origin https://github.com/<your-username>/campblazer.git
git push -u origin main
```

`.gitignore` already keeps out `.env` (secrets), `.venv`, `node_modules`, uploaded media and test results.
Check with `git status` before committing: **`.env` must never appear**. If it does, stop and run `git rm --cached backend/.env`.

GitHub stores the code only; it doesn't run Django. Use B or C to run it.

---

## B. Laptop as the server + Cloudflare Quick Tunnel (recommended for the demo)

Everything runs on your laptop exactly as in the setup guide; Cloudflare gives it a temporary public HTTPS link.

1. Install `cloudflared`. On Windows: `winget install --id Cloudflare.cloudflared`, then reopen VS Code.
2. In `backend/.env` set:

```
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,.trycloudflare.com
SERVE_MEDIA=1
```

   (DEBUG off so visitors never see error pages with your settings; `SERVE_MEDIA=1` keeps the photos working.)
3. Start PostgreSQL + Redis and the backend as usual:

```powershell
docker compose up -d
cd backend; .venv\Scripts\activate
python run_server_windows.py --workers 4
```

4. Build and serve the frontend (new terminal):

```powershell
cd frontend
npm run build
npm run preview          # http://localhost:4173 — proxies /api, /media and /ws to Django
```

**Shortcut:** after the one-time setup, `powershell -ExecutionPolicy Bypass -File .\start-public.ps1` (in the `campblazer` folder) does steps 3–5 for you in separate windows.

5. Open the tunnel (new terminal):

```powershell
cloudflared tunnel --url http://localhost:4173
```

   It prints a link like `https://random-words.trycloudflare.com`. Anyone can open it on their phone or laptop. Bookings, approvals and live updates all work through it.

Notes:
- The link changes every time you restart `cloudflared`, and it stops when you press Ctrl + C or the laptop sleeps.
- Keep the laptop plugged in and set sleep to "Never" during the demo.
- Quick Tunnels are meant for testing and demos, not permanent hosting.

---

## C. Always online: ONE Render web service + Neon (PostgreSQL)

`render.yaml` creates **one web service** (`campblazer`) that runs everything: the Django REST API, the WebSockets,
the compiled React/TypeScript site and the photos. It also creates a free Redis (Key Value) for live updates
between the 2 worker processes. Nothing is a static copy: every page reads from the API, and the API reads
from PostgreSQL.

**Where the data lives:** destinations, services, availability, reservations, users **and uploaded photos**
are all rows in the Neon PostgreSQL database. Photos are stored as bytes (`bytea`) in the
`photostore_storedphoto` table and served from `/api/photos/<id>/`. Render's disk is wiped on every
restart, so nothing important is kept on it.

### One-time: commit the migration files (do this on your laptop)

```bash
cd backend
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt     # adds whitenoise
python manage.py makemigrations accounts destinations bookings
python manage.py migrate            # also creates the new photostore table
python manage.py test photostore    # 7 tests: upload -> PostgreSQL -> served back
cd ..
git add backend/*/migrations render.yaml backend/render-build.sh backend/render-start.sh
git add -A && git commit -m "Store photos in PostgreSQL; single Render web service" && git push
```

### Deploy

1. **Neon** (neon.com) → free project → copy the **direct** connection string (`postgresql://…?sslmode=require`,
   the one *without* `-pooler`).
2. **Render** (render.com) → sign in with GitHub → **New → Blueprint** → pick the repo.
   If you deployed the old blueprint before, delete the old `campblazer-api` and static `campblazer` services first.
3. Render asks for one value: `DATABASE_URL` = the Neon string. Click **Apply**.
4. Wait for the build (installs Python packages, runs `npm run build`, collects static files). Open
   `https://campblazer.onrender.com` (or the address Render shows). Log in as `admin_demo`; the password is the
   `DEMO_PASSWORD` value in the service's **Environment** tab.

What runs on each start (`backend/render-start.sh`): `migrate`, then `bootstrap`, which seeds the 18 approved
destinations, starter photos and demo accounts **only when the database is empty**. After the first boot, the
database belongs to the admins: destinations you add, toggles you switch and photos you upload are never reset
by a restart. (`python manage.py bootstrap --force` re-runs the seeders and removes destinations outside the
approved list — use it only to reset a demo.)

### Uploading photos (admin)

Admin dashboard → **Destinations** → click the photo thumbnail (or the 🖼 icon) of a row → **Upload photo**.
For a new destination, save it first; the drawer stays open on the photo section. The first photo becomes the
cover automatically; ★ makes another photo the cover. Limit: JPG/PNG/WEBP up to 5 MB. Neon's free database is
0.5 GB, which fits a few hundred compressed photos.

Free-tier limits to know before the defense:
- The free web service **sleeps after 15 minutes without traffic** and takes about a minute to wake. Open the site a few minutes before presenting.
- It runs on a small shared CPU (2 workers), so do the **speedup / load tests on your laptop**, not on Render.
- Render's own free PostgreSQL expires after 30 days, which is why this setup uses Neon instead.

---

## D. Run it on GitHub Codespaces (from your GitHub repo, no laptop needed while it runs)

GitHub Pages can't run Django (static files only), but **Codespaces** gives you a free Linux machine in GitHub's cloud that can run everything.

1. Do **A** first (code on GitHub).
2. On the repo page: **Code → Codespaces → Create codespace on main** (2-core machine). VS Code opens in the browser.
3. In its terminal:

```bash
docker compose up -d                       # PostgreSQL + Redis inside the codespace
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

4. Edit `backend/.env`: paste a secret key, and set
   `DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,.app.github.dev` and `SERVE_MEDIA=1`, `DJANGO_DEBUG=False`.
5. Load the data and start 4 workers:

```bash
python manage.py makemigrations accounts destinations bookings && python manage.py migrate
python manage.py seed_destinations && python manage.py seed_photos --reset && python manage.py seed_demo
gunicorn -c gunicorn.conf.py config.asgi:application
```

6. New terminal: `cd frontend && npm install && npm run build && npm run preview`
7. Open the **Ports** tab → port **4173** → right-click → **Port Visibility → Public**. Copy its `https://…-4173.app.github.dev` link and share it.

Notes:
- Free personal accounts get a monthly allowance of Codespaces core-hours. A 2-core codespace uses 2 core-hours per hour, so **stop the codespace when you're done** (Codespaces page → ⋯ → Stop).
- A codespace stops itself after a period of inactivity, and the link stops working then. Restart it and re-run steps 5–7 (the database is kept).
