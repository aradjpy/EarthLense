# EarthLense — Hosting and domain setup

EarthLense is **one Python FastAPI application**. The same server hosts both the HTML/CSS/JavaScript frontend (`/`, `/static/...`) and the NASA analysis API (`/api/...`). There is no Node build step and no database.

**Important:** Uploading HTML to a normal `public_html` folder alone does **not** make this Python app work. Your host must run Python applications using an ASGI server, a Docker container, or a Passenger/WSGI adapter.

## 0. Before you upload

The ZIP contains an `EarthLense/` folder. The **application root** is the directory that directly contains `app/`, `static/`, `data/`, `requirements.txt`, and `passenger_wsgi.py`. Don't accidentally point the host to the directory above it.

Use **Python 3.11 or newer** (3.11 is the tested Docker base).

The user-facing frontend AI-assistance acknowledgement is an HTML comment at the top of `static/index.html`, and a JavaScript comment at the top of `static/app.js`.

### Check locally

```bash
cd EarthLense
python -m pip install -r requirements.txt
python -m pytest -q
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` and verify `http://127.0.0.1:8000/health` responds `{"status":"ok"}`. The landing screen should show a **saved Toronto demonstration**; new searches and comparisons ask NASA POWER for data.

## 1. If you have cPanel/shared hosting

**First verify that your package has "Setup Python App" (sometimes called "Python App") or SSH/Application Manager.** Basic cPanel File Manager and `public_html` by themselves are not enough.

### Recommended cPanel arrangement

1. In cPanel, open **Domains** or **Subdomains** and set up a domain/subdomain such as `earthlense.example.com` (replace with your actual domain). For compatibility with the frontend's absolute `/api/...` URLs, install the app at the **domain root**, rather than `example.com/some-folder`.
2. In **File Manager**, create a folder such as `/home/USERNAME/earthlense` **outside `public_html`**. Upload the archive and extract it; move the contents of `EarthLense/` into `/home/USERNAME/earthlense` so `app/main.py` is at `/home/USERNAME/earthlense/app/main.py`.
3. Go to **Setup Python App** and create a new app using a modern Python version. Set **Application Root** to `earthlense`. Set **Application URL** to the selected domain's root (normally `/`). Use **Application Startup File** `passenger_wsgi.py` and **Application Entry Point** `application`.
4. Copy the **virtualenv activation command shown by cPanel** and run it using Terminal/SSH. In the app root, run:

   ```bash
   pip install -r requirements-cpanel.txt
   ```

   This installs FastAPI, NumPy/SciPy/Pandas, and the optional `a2wsgi` adapter that makes FastAPI compatible with Passenger's WSGI interface.
5. Click **Restart** in the Python App dashboard. If the host uses Passenger's restart file, run `mkdir -p tmp && touch tmp/restart.txt` in the app directory.
6. Open `https://earthlense.example.com/health` and then `https://earthlense.example.com/`. Check that CSS and JavaScript load, and press **Try our saved Toronto example**.
7. Test a live analysis. A hosting provider may block outbound HTTPS to `power.larc.nasa.gov`; in that case request outbound port 443 access or choose a different host.

### cPanel issues to watch

- Some cPanel plans support *only traditional WSGI* apps. The included `passenger_wsgi.py` plus `a2wsgi` is designed for that, but not every provider permits all dependencies or WSGI adapters. If **Setup Python App** does not exist, a normal shared hosting plan is **not suitable** for this backend.
- Installing NumPy/SciPy/Pandas can be difficult on old Python versions or plans without enough disk/memory. Try Python 3.11 and a host that supports standard Python wheels.
- If the host restricts WSGI app runtime or request duration, live comparisons involving two NASA requests might time out. Render, Railway or a VPS running ASGI directly is a more reliable option.
- Avoid serving a copy of `static/index.html` directly in `public_html`; its API endpoints will then not have a running backend.

## 2. If you have a managed Python hosting platform (e.g. Render)

This is usually the easiest option if you don't have Python support in cPanel.

1. Put the **contents of `EarthLense/`** into a Git repository and push to GitHub/GitLab, or choose the platform's Docker deployment option.
2. Create a **Web Service**, not a Static Site. Set your repository's root directory to the folder containing `requirements.txt`.
3. For a Python Web Service, set:

   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers`
   - **Health check:** `/health`
   - **Python:** 3.11+ (where selectable)

   The package also includes an optional `render.yaml` configuration.
4. Deploy and test the platform-provided hostname first. Go to `/health`, `/`, `/api/variables`, and test a live analysis.
5. In the platform's **Settings → Custom Domains**, add the domain you bought. The platform will give you the **exact CNAME/A records** to enter at your registrar's DNS page. Follow their values rather than guessing an IP address.
6. Wait for domain verification and HTTPS certificate issuance before sharing the website. Browser geolocation typically needs HTTPS on public websites.

**Note:** Some free/low-cost plans sleep when idle, and ephemeral disks may clear the NASA cache when redeploying. The built-in Toronto example is part of the application and survives redeploys.

Official Render instructions: https://render.com/docs/deploy-fastapi and https://render.com/docs/web-services

## 3. If you have a VPS (Ubuntu/Linux with sudo + SSH)

Use these instructions only if you control the actual server and its firewall. Replace `ubuntu`, `/home/ubuntu/EarthLense`, and `example.com` with your own values.

### A. Install the app

Upload/extract the `EarthLense/` directory to `/home/ubuntu/EarthLense` via SFTP or SCP, then SSH into the VPS:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip nginx
cd /home/ubuntu/EarthLense
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

### B. Run Uvicorn as a persistent systemd service

Create `/etc/systemd/system/earthlense.service` (requires sudo):

```ini
[Unit]
Description=EarthLense FastAPI
After=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/EarthLense
ExecStart=/home/ubuntu/EarthLense/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Activate it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now earthlense
sudo systemctl status earthlense
curl http://127.0.0.1:8000/health
```

### C. Put Nginx in front and connect the domain

Create `/etc/nginx/sites-available/earthlense`:

```nginx
server {
    listen 80;
    server_name example.com www.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90s;
    }
}
```

Then:

```bash
sudo ln -s /etc/nginx/sites-available/earthlense /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

At the **DNS registrar** for your domain, create an **A record** pointing the chosen hostname to your VPS's **public IP address**. Use an `AAAA` record only if you've configured IPv6 on the server. Allow inbound TCP ports **80 and 443** through your VPS firewall and cloud security rules; keep port **8000 private**.

### D. Enable HTTPS

Once the domain resolves to your VPS:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d example.com -d www.example.com
```

Only include `www` if DNS for `www.example.com` also points to this VPS. Certbot should set up HTTPS and renewal. Test `https://example.com/health` and the full site.

### E. Updates and logs

```bash
sudo journalctl -u earthlense -n 100 --no-pager
sudo systemctl restart earthlense
```

## 4. If the host provides Docker

From the application root:

```bash
docker build -t earthlense .
docker run --rm -p 8000:8000 earthlense
```

Test `http://localhost:8000/health`. The included Dockerfile runs as a non-root user and starts Uvicorn. Attach your domain and HTTPS through the host's container ingress/reverse proxy dashboard.

## 5. Smoke-test checklist after launch

1. `https://YOUR-DOMAIN/health` returns `{"status":"ok"}`.
2. `https://YOUR-DOMAIN/` loads the **EarthLense** interface with styling, and `/static/app.js` serves JavaScript.
3. The **saved Toronto example** loads and clearly says it is *saved data*.
4. `https://YOUR-DOMAIN/api/variables` lists `T2M`, `RH2M`, `WS2M`, `CLOUD_AMT`, and `AOD_55`.
5. A live search for Toronto, `T2M`, 2001–2024 succeeds. Note: this *depends on NASA POWER being reachable*.
6. Cloud cover (`CLOUD_AMT`) and aerosols (`AOD_55`) issue live NASA requests for 2001 or later; verify availability for your chosen years and place.
7. Comparing Toronto and New York returns a slope for each place. The interface **does not claim the difference itself is statistically significant**.
8. HTTPS has a valid certificate and the domain points to the deployment (not merely to an empty `public_html`).

### Important scope and data caveats

- The saved Toronto example is *not* a live NASA API result. Live results and comparison requests rely on the NASA POWER service and your host allowing outbound HTTPS.
- Ozone is a **planned** feature, not implemented here. Cloud cover and aerosol optical depth are powered by NASA POWER / CERES SYN1deg. The three weather variables are from NASA POWER / MERRA-2.
- AOD measures atmospheric light attenuation, not surface air-quality or health risk. Geographic comparison shows two independently fitted trends; it does **not** test whether the two slopes are statistically different.
- OLS trend significance assumes residual independence and constant variance. Autocorrelation may invalidate simple p-values and confidence intervals.
- The app stores a best-effort file cache (`data/cache/`) for NASA responses. Disposable hosting disks lose cached requests, but not bundled demo data.
- Site visitors' approximate browser location is requested only with permission, rounded to two decimal places and sent to the API for NASA data; the app doesn't need a street address.
