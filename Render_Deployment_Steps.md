# Deploying AskiResearchLabs to Render

Render is a robust, developer-friendly Platform as a Service (PaaS) that offers fully managed databases and reliable web hosting.

## 💰 Cost Analysis

- **Web App Service:** 
  - **Free Tier:** Available, but the app goes to sleep after 15 minutes of inactivity (takes ~30 seconds to wake up on the next request).
  - **Starter Tier:** **$7/month** for 24/7 uptime.
- **Database Service (PostgreSQL):** 
  - Render provides a fully managed PostgreSQL database (automated daily backups, point-in-time recovery).
  - **Starter DB Tier:** **$7/month**.
- **Total Expected Cost:** $14.00 / month (for 24/7 web app + managed DB).
- **Security:** Render offers excellent secret management via **Secret Files** (allowing you to upload your `.env` file securely) and standard Environment Variables which are obfuscated after saving.

---

## 🚀 End-to-End Deployment Instructions

### Step 1: Create a PostgreSQL Database
1. Go to [render.com](https://render.com/) and sign in with GitHub.
2. Click **New** -> **PostgreSQL**.
3. Name your database (e.g., `aski-db`).
4. Select the **Starter ($7/mo)** or **Free** instance type.
5. Click **Create Database**.
6. Once created, scroll down to the **Connections** section and copy the **Internal Database URL** (e.g., `postgres://user:pass@host:5432/db`).

### Step 2: Create the Web Service
1. Click **New** -> **Web Service**.
2. Choose **Build and deploy from a Git repository**.
3. Connect your repository: `illindva72/AskiResearchLabs`.
4. Fill in the following details:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Select your plan (Free or $7/mo Starter).

### Step 3: Configure Environment Variables
1. Before clicking "Create Web Service", scroll down and expand **Advanced**.
2. Click **Add Environment Variable** and add your standard keys:
   - Key: `ANTHROPIC_API_KEY`, Value: `your-api-key`
   - Key: `DATABASE_URL`, Value: `[Paste the Internal Database URL you copied earlier]`
3. Alternatively, you can use **Secret Files** to upload your `.env` securely.

### Step 4: Deploy
1. Click **Create Web Service**.
2. Render will automatically clone your repo, install dependencies, and start the application.
3. Subsequent pushes to your `main` branch on GitHub will automatically trigger a new deployment.
4. Access your live app via the URL provided at the top of your service dashboard (e.g., `https://askiresearchlabs.onrender.com`).
