# Deployment Guide: Free-Tier Production Setup (Render + Neon)

This guide documents the end-to-end procedure for deploying the **HR Assessment Portal** on **Render Free Web Service** and **Neon Serverless PostgreSQL (Free Tier)**.

---

## 1. Prerequisites & Accounts

1. **GitHub Account**: A repository containing this project codebase.
2. **Neon Account** ([neon.tech](https://neon.tech)): Free Tier provides 0.5 GiB storage, scalable compute with automatic scale-to-zero when idle.
3. **Render Account** ([render.com](https://render.com)): Free Tier provides 512 MB RAM, 0.1 CPU, automatic SSL on `onrender.com`.

---

## 2. Step 1: Provision Neon PostgreSQL Database

1. Log in to [Neon Console](https://console.neon.tech).
2. Click **Create Project**:
   - **Project Name**: `hr-assessment`
   - **Postgres Version**: `16` (or `15`)
   - **Region**: Choose the region closest to your users (e.g., `AWS ap-southeast-1` or `AWS eu-central-1`).
3. In the Neon Dashboard, copy the connection string under **Connection Details**:
   - Select **Connection string** > **Pooled connection** or **Direct connection**.
   - Make sure `sslmode=require` is present in the URI:
     ```text
     postgresql://<user>:<password>@<ep-xyz>.neon.tech/neondb?sslmode=require
     ```
4. Save this URI; you will pass it as `DATABASE_URL`.

---

## 3. Step 2: Configure Environment Variables

Prepare your environment variables. Never commit actual secret keys to git.

| Variable | Required | Description | Example / Recommendation |
| :--- | :---: | :--- | :--- |
| `DATABASE_URL` | **Yes** | Neon connection string with SSL | `postgresql://...neon.tech/neondb?sslmode=require` |
| `SECRET_KEY` | **Yes** | 64-char hex key for signing JWTs | Generate via `openssl rand -hex 32` |
| `PEPPER` | **Yes** | Secret string for Argon2 password hashing | Random 32+ character passphrase |
| `ENV` | **Yes** | Environment mode | `production` |
| `PORT` | Render sets | Service listening port | `10000` (Render default) |
| `WEB_CONCURRENCY` | No | Uvicorn worker count | `1` (Crucial for in-process WebSocket state) |
| `ANTHROPIC_API_KEY`| Optional | For AI assessment candidate summaries | `sk-ant-api03-...` |
| `STUN_URLS` | No | WebRTC STUN relay servers | `stun:stun.l.google.com:19302,stun:stun1.l.google.com:19302` |
| `RETENTION_DAYS` | No | Default data retention limit | `90` |

---

## 4. Step 3: Deploy to Render Free Web Service

### Option A: Blueprint Deployment (Recommended)
This repository includes a production-ready `render.yaml` specification:

1. In the Render Dashboard, click **New +** > **Blueprint**.
2. Connect your GitHub repository.
3. Render detects `render.yaml` and will prompt for the declared secret environment variables (`DATABASE_URL`, `SECRET_KEY`, `PEPPER`).
4. Click **Apply**.

### Option B: Manual Web Service Creation
1. In Render Dashboard, click **New +** > **Web Service**.
2. Connect your repository.
3. Configure the service settings:
   - **Name**: `hr-assessment-portal`
   - **Region**: Same region as your Neon database.
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `./build.sh` (or `pip install -r requirements.txt && cd frontend && npm install && npm run build && cd .. && cp -r frontend/dist/* backend/app/static/`)
   - **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free` (512 MB RAM, 0.1 CPU)
4. Under **Advanced** > **Health Check Path**, enter `/healthz`.
5. Enter all Environment Variables from Section 3.
6. Click **Create Web Service**.

---

## 5. Step 4: Run Database Migrations and Seed Data

Once the Render service is deployed, open the **Render Shell** (or run locally with `DATABASE_URL` pointing to Neon):

```bash
# 1. Run Alembic migrations (creates 'assess' schema and all tables)
alembic upgrade head

# 2. Parse and import 50 questions from docx with checksum validation
python -m scripts.import_questions --docx data/HR_Team_Professional_Assessment.docx

# 3. Seed Monitor and Admin staff accounts
python -m scripts.seed_admins

# 4. Upload initial candidate roster
python -m scripts.import_roster --csv data/roster_template.csv
```

### Verification in Terminal
```text
[INFO] Parsed 50 questions across 7 sections.
[INFO] Answer key checksum verified: 1A 2C 3B 4B 5C 6D 7C 8D 9B 10B... MATCH!
[INFO] Questions and options loaded into schema 'assess'.
[INFO] Seeded Staff Accounts:
  - MONITOR: HR_MONITOR_01 (PIN: 654321)
  - ADMIN:   HR_ADMIN_01   (PIN: 987123)
[INFO] Loaded 3 candidate records from roster_template.csv.
```

---

## 6. Step 5: Post-Deployment Smoke Verification Checklist

1. [ ] **Health Endpoint**: Navigate to `https://<your-app>.onrender.com/healthz`. Confirm JSON:
   ```json
   { "status": "healthy", "database": "connected" }
   ```
2. [ ] **Single Origin Delivery**: Navigate to `https://<your-app>.onrender.com/`. Confirm the React application loads with modern UI.
3. [ ] **Admin Login Test**:
   - Select **Admin / Proctor Login**.
   - Code: `HR_ADMIN_01`, PIN: `987123`.
   - Confirm Admin Console displays Assessment Dashboard, Question Bank, and Export buttons.
4. [ ] **Monitor Login Test**:
   - Code: `HR_MONITOR_01`, PIN: `654321`.
   - Confirm Monitor Wall opens with 0 active feeds, ready for incoming candidates.
5. [ ] **Candidate Flow Test**:
   - Code: `EMP001`, Name: `Aarav Sharma`.
   - Complete rules consent, camera check, and verify question palette renders 50 questions with 60-minute countdown.

---

## 7. Operational Guidelines for Free-Tier Hosting

1. **Pre-Warm Instance 15 Minutes Before Exam**:
   Render Free Web Services sleep after 15 minutes of inactivity. Neon Postgres also scales to zero compute. Open `https://<your-app>.onrender.com/healthz` 15 minutes before the exam window to wake both services.
2. **Strictly 1 Instance**:
   WebRTC signalling and active socket connections are managed in-process. Do not scale beyond 1 instance on the free tier.
3. **Download Results Immediately Post-Exam**:
   Use the **Download Backup Dump** and **Export Results (Excel)** buttons in the Admin Console once all submissions are collected to retain a permanent offline archive.
