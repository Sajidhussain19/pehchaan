# Deploying Pehchaan on AWS (EC2 + CloudFront for HTTPS)

**Why this setup:** browsers only allow the microphone on **https://** pages (or on localhost). The simplest way to get
HTTPS without buying a domain is **Amazon CloudFront** in front of one small EC2 server. CloudFront gives a URL like
`https://d1234abcd.cloudfront.net` with a valid certificate. It talks to the server over plain HTTP on port 8000, and
the server only accepts traffic from CloudFront.

```
browser --HTTPS--> CloudFront (dxxxx.cloudfront.net) --HTTP :8000--> EC2 t3.small (Docker: uvicorn + Pehchaan)
```

**Cost:** a t3.small is about $0.02 per hour (about $0.50 per day). CloudFront is free at demo traffic.
The app has an approximate $2/day cap on OpenAI spending, configurable with `DAILY_BUDGET_USD`.
**Secrets:** the OpenAI key lives ONLY in `/etc/pehchaan.env` on the server. It is never in git, never in the image.

Region for everything below: **us-west-2 (Oregon)**. Replace `<...>` placeholders with your values.

---

## 0. Put the code on GitHub (once, on your laptop)

The repo is **public**: `https://github.com/<your-user>/pehchaan`. In PowerShell, in the project folder:

```powershell
gh auth login                                   # once: GitHub.com -> HTTPS -> log in with a web browser
git ls-files | Select-String "\.env$"           # must print NOTHING (.env is never committed)
gh repo create pehchaan --public --source . --push
git push --tags                                 # final-eval-v1, final-eval-v1.1
```

- The Svarah real-speech **audio is not in the repo or its history** (it was removed before the first push).
  Manifest, attribution, transcripts and results are included. On the server the demo simply doesn't offer the
  real clips; to have them, put `HF_TOKEN` in `/etc/pehchaan.env` and run `python scripts/fetch_real_speech.py`
  (optional).
- A public repo clones without any token: `git clone https://github.com/<your-user>/pehchaan.git`.

## 1. Security group (EC2 console → Security Groups → Create)

Name `pehchaan-sg`, VPC: default. **Inbound rules** (nothing else):

| Type | Port | Source | Why |
|---|---|---|---|
| Custom TCP | 8000 | **Prefix list** `com.amazonaws.global.cloudfront.origin-facing` | only CloudFront can reach the app |
| SSH | 22 | **My IP** | for you to log in (or skip it and use EC2 Instance Connect / Session Manager) |

To find the prefix list id (the console also lets you pick it by name in the Source box):

```bash
aws ec2 describe-managed-prefix-lists --region us-west-2 \
  --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing \
  --query "PrefixLists[0].PrefixListId" --output text
```

Outbound: leave the default (all). The server must reach api.openai.com and GitHub.

## 2. Launch the server (EC2 console → Launch instance)

- Name `pehchaan`, AMI **Amazon Linux 2023** (x86_64), type **t3.small**
- Key pair: create or choose one (needed only for SSH)
- Network: default VPC, **auto-assign public IP: enabled**, security group **pehchaan-sg**
- Storage: 16 GiB gp3 (Docker images need some room)
- Launch. Then copy the instance's **Public IPv4 DNS**, e.g. `ec2-35-90-1-2.us-west-2.compute.amazonaws.com`.

## 3. Install Docker and get the code (on the server)

Log in (EC2 console → Connect → EC2 Instance Connect, or `ssh -i <key.pem> ec2-user@<public-dns>`), then:

```bash
sudo dnf install -y docker git
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user && newgrp docker      # run docker without sudo
git clone https://github.com/<your-user>/pehchaan.git
cd pehchaan
docker build -t pehchaan .
```

## 4. The secret environment file (on the server)

Open an editor, so the key never lands in your shell history:

```bash
sudo nano /etc/pehchaan.env
```

Paste (fill in your key; `ALLOWED_ORIGINS` gets its value in step 6):

```
OPENAI_API_KEY=sk-...
TRUST_PROXY=true
DAILY_BUDGET_USD=2
RATE_LIMIT_REQUESTS=20
RATE_LIMIT_WINDOW_SECONDS=600
ALLOWED_ORIGINS=
# Optional password for the public link (the page asks for it once):
# DEMO_KEY=choose-something
```

Then lock it down: only root can read it.

```bash
sudo chmod 600 /etc/pehchaan.env && sudo chown root:root /etc/pehchaan.env
```

## 5. Start the app (on the server)

```bash
sudo docker run -d --name pehchaan --restart unless-stopped \
  -p 8000:8000 --env-file /etc/pehchaan.env -v pehchaan-state:/app/state pehchaan
curl -s localhost:8000/health        # -> {"status":"ok","project":"Pehchaan"}
```

- `--restart unless-stopped`: Docker starts the app again after a crash or a reboot.
- `-v pehchaan-state:/app/state`: reminders and learned preferences survive updates.
- `sudo` because only root can read `/etc/pehchaan.env`.

## 6. CloudFront in front (CloudFront console → Create distribution)

- **Origin domain:** paste the EC2 **Public IPv4 DNS** (not the IP). **Protocol: HTTP only**, **HTTP port: 8000**.
- **Default cache behavior:**
  - Viewer protocol policy: **Redirect HTTP to HTTPS**
  - Allowed HTTP methods: **GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE** (uploads and the API need POST/DELETE)
  - Cache policy: **CachingDisabled** (simplest: nothing is cached, so `/api/*` is always live and the page updates at once)
  - Origin request policy: **AllViewerExceptHostHeader** (forwards every header the app needs: `Content-Type` for
    uploads, `Origin`, `X-Visitor-Id`, `X-Demo-Key`, plus query strings such as `?book=B`)
- Web Application Firewall: **Do not enable** (not needed for a demo; it costs extra)
- Price class: **Use North America, Europe, Asia, Middle East, and Africa** (includes India)
- Create. Wait about 5 minutes until "Last modified" shows a date, then copy the **Distribution domain name**,
  e.g. `d1234abcd.cloudfront.net`.

Now tell the app its public origin, so the browser's requests are accepted:

```bash
sudo sed -i 's|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=https://<dxxxx>.cloudfront.net|' /etc/pehchaan.env
sudo docker rm -f pehchaan && sudo docker run -d --name pehchaan --restart unless-stopped \
  -p 8000:8000 --env-file /etc/pehchaan.env -v pehchaan-state:/app/state pehchaan
```

Open **https://\<dxxxx\>.cloudfront.net**. The page loads, clips run, and the mic asks for permission. Uploads
are at most 5 MB / 30 s; CloudFront's 30 s origin timeout is enough (a request takes about 2–5 s).

## 7. Everyday operations (on the server)

| Task | Command |
|---|---|
| See logs (live) | `sudo docker logs -f --tail 100 pehchaan` |
| Restart | `sudo docker restart pehchaan` |
| Status / health | `sudo docker ps` and `curl -s localhost:8000/health` |
| Stop | `sudo docker stop pehchaan` |
| Reset demo data | open the page → "Reset demo" to clear that browser’s reminders and reset its selected book’s preferences |
| Update after a `git push` | `cd ~/pehchaan && ./deploy/update.sh` |

`deploy/update.sh` pulls the code, rebuilds the image and replaces the container (state is kept in the volume).

## 8. Fallback if AWS has trouble: run on the presenting laptop

The mic works on **localhost** without HTTPS:

```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --port 8000
# open http://localhost:8000 in Chrome or Edge on THIS laptop
```

(Or, with Docker Desktop: `docker build -t pehchaan .` then
`docker run --rm -p 8000:8000 --env-file .env -v pehchaan-state:/app/state pehchaan`.)

Without CloudFront, other people can't use the mic over plain `http://<ip>:8000` (the browser blocks it), but clips
and typed sentences still work. For the stage, the laptop + projector + localhost is enough. The backup screen
recording is described in `DEMO_SCRIPT.md`.

## 9. After the hackathon: clean up (to stop paying)

CloudFront: **Disable**, wait, then **Delete** the distribution. EC2: **Terminate** the instance. Delete `pehchaan-sg`.
Rotate the OpenAI key if it was ever shared.
