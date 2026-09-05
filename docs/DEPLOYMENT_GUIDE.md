# 🚀 PayRoute AI — Complete Deployment Guide

This guide covers all options for deploying **PayRoute AI** (FastAPI Backend + Streamlit Customer Shield Dashboard + SQLite Persistence + AI Routing Models) to production or cloud environments.

---

## 📋 Table of Contents
1. [Option 1: Docker & Docker Compose (Recommended for Any Cloud / VPS)](#option-1-docker--docker-compose)
2. [Option 2: Free / Low-Cost Cloud Deployment (Render / Railway)](#option-2-render--railway)
3. [Option 3: Streamlit Community Cloud + Render/Railway API](#option-3-streamlit-community-cloud)
4. [Option 4: Google Cloud Run (Serverless Container)](#option-4-google-cloud-run)
5. [Option 5: AWS EC2 / DigitalOcean Droplet (Linux VPS)](#option-5-aws-ec2--digitalocean-vps)
6. [Option 6: Windows Server / Local Background Production Service](#option-6-windows-local--production)
7. [Environment Variables Reference](#environment-variables-reference)

---

## 🐳 Option 1: Docker & Docker Compose (Recommended)

### Prerequisites
- Docker & Docker Compose installed.

### Steps
1. **Clone or Copy your repository**:
   ```bash
   cd payroute-ai
   ```

2. **Build and Run**:
   ```bash
   docker compose up -d --build
   ```

3. **Access Services**:
   - **Customer Shield Dashboard**: [http://localhost:8501](http://localhost:8501)
   - **FastAPI Backend & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

4. **Stop or Restart**:
   ```bash
   docker compose down
   docker compose logs -f
   ```

---

## ☁️ Option 2: Render / Railway (1-Click Free / Managed Cloud)

### A. Deploy on Render (render.com)
1. Push your `payroute-ai` code to **GitHub** or **GitLab**.
2. Go to [Render Dashboard](https://dashboard.render.com/) and click **New + > Web Service**.
3. Connect your repository.
4. Select **Docker** environment (Render will automatically detect `Dockerfile` and `start.sh`) OR **Python** environment with:
   - **Build Command**: `pip install -r requirements.txt && python database/init_db.py`
   - **Start Command**: `bash start.sh`
5. Add Environment Variables:
   - `PAYROUTE_API_URL`: `http://localhost:8000`
   - `PORT`: `8501` (or use default assigned by Render)
6. Click **Create Web Service**. Your public live URL (e.g. `https://payroute-ai.onrender.com`) will be active in minutes!

---

### B. Deploy on Railway (railway.app)
1. Go to [Railway Dashboard](https://railway.app/).
2. Click **New Project > Deploy from GitHub Repo**.
3. Select your `payroute-ai` repository.
4. Railway will automatically detect the `Dockerfile` and build it.
5. In Settings > Networking, generate a public domain for port `8501`.

---

## 🌐 Option 3: Streamlit Community Cloud

If you want to host the frontend on Streamlit Cloud for free:

1. Deploy the **FastAPI Backend** on Render or Railway first to get a public backend URL (e.g. `https://payroute-api.onrender.com`).
2. Go to [share.streamlit.io](https://share.streamlit.io/).
3. Connect your GitHub repository:
   - **Main file path**: `dashboard/app.py`
4. In Advanced Settings > Secrets / Environment Variables:
   ```toml
   PAYROUTE_API_URL = "https://payroute-api.onrender.com"
   ```
5. Click **Deploy**.

---

## ☁️ Option 4: Google Cloud Run

Deploy as a scalable, serverless container on GCP:

1. Authenticate with Google Cloud:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_GCP_PROJECT_ID
   ```

2. Build and push image to Google Artifact Registry / Container Registry:
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_GCP_PROJECT_ID/payroute-ai:latest
   ```

3. Deploy to Cloud Run:
   ```bash
   gcloud run deploy payroute-ai \
     --image gcr.io/YOUR_GCP_PROJECT_ID/payroute-ai:latest \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --port 8501 \
     --memory 1Gi \
     --cpu 1
   ```

---

## 🖥️ Option 5: AWS EC2 / DigitalOcean VPS (Linux Ubuntu/Debian)

1. SSH into your VPS:
   ```bash
   ssh ubuntu@YOUR_SERVER_IP
   ```

2. Clone repository & install dependencies:
   ```bash
   git clone https://github.com/your-username/payroute-ai.git
   cd payroute-ai
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python database/init_db.py
   ```

3. Run with **systemd** service or **PM2** / **Docker**:
   ```bash
   # Using PM2
   npm install -g pm2
   pm2 start "uvicorn api.main:app --host 0.0.0.0 --port 8000" --name "payroute-api"
   pm2 start "streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0" --name "payroute-ui"
   pm2 save
   pm2 startup
   ```

4. (Optional) Set up Nginx Reverse Proxy with SSL (Certbot / Let's Encrypt).

---

## 🪟 Option 6: Windows Local / Production Service

1. **One-Click Launch**:
   - Double-click `start_all.bat` in the project root.
   - It will initialize the database, start the FastAPI server on port 8000 in one terminal window, and start the Streamlit UI on port 8501 in a second terminal window.

2. **Windows Service (NSSM - Non-Sucking Service Manager)**:
   - To keep PayRoute AI running continuously on Windows Server:
   ```cmd
   nssm install PayRouteAI "C:\path\to\payroute-ai\start_all.bat"
   nssm start PayRouteAI
   ```

---

## ⚙️ Environment Variables Reference

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PAYROUTE_API_URL` | `http://localhost:8000` | URL where Streamlit connects to the FastAPI backend |
| `PORT` | `8501` | Public web server port for Streamlit UI |
| `ENVIRONMENT` | `production` | Runtime mode (`development` / `production`) |
| `LOG_LEVEL` | `INFO` | Application log verbosity (`DEBUG`, `INFO`, `WARNING`) |
| `RAZORPAY_KEY_ID` | `rzp_test_...` | (Optional) Razorpay Live/Test API Key |
| `RAZORPAY_KEY_SECRET` | `...` | (Optional) Razorpay Key Secret |
| `PHONEPE_MERCHANT_ID` | `M22...` | (Optional) PhonePe Merchant Identifier |
| `GOOGLE_PAY_MERCHANT_ID` | `BCR...` | (Optional) Google Pay Merchant Identifier |
