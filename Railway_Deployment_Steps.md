# Deploying AskiResearchLabs to Railway

Railway is one of the easiest and most modern platforms for deploying Python web applications and databases. It is highly recommended for projects transitioning from local SQLite to a cloud database.

## 💰 Cost Analysis

- **Web App Service:** Handled by their **$5/month Hobby Plan**. It operates on usage-based pricing, but $5 is typically more than enough for small to medium traffic.
- **Database Service (PostgreSQL):** Usage-based and draws from the same $5 pool as your web app. A low-traffic PostgreSQL database on Railway typically costs a few cents to $1-2 per month.
- **Total Expected Cost:** ~$5.00 / month.
- **Security:** Environment variables are securely managed in the Railway dashboard. Sensitive variables can be marked as hidden and are injected directly into your running container.

---

## 🚀 End-to-End Deployment Instructions

### Step 1: Connect GitHub to Railway
1. Go to [railway.app](https://railway.app/) and sign in with your GitHub account.
2. Click **New Project** in the dashboard.
3. Select **Deploy from GitHub repo**.
4. Select your repository: `illindva72/AskiResearchLabs`.
5. Click **Deploy Now**. Railway will automatically detect that this is a Python app.

### Step 2: Configure Environment Variables
1. Click on your newly created web service on the Railway canvas.
2. Go to the **Variables** tab.
3. Click **New Variable** or use the **Raw Editor** to paste your `.env` contents.
4. Add your API keys (e.g., `ANTHROPIC_API_KEY`). Note that the values will be obfuscated.

### Step 3: Add a PostgreSQL Database
1. Go back to your project canvas.
2. Click **New** (or Cmd/Ctrl + K) and select **Database**.
3. Choose **Add PostgreSQL**.
4. Railway will provision a Postgres database instantly on your canvas.

### Step 4: Connect the Database to Your App
1. Click on your PostgreSQL database service on the canvas.
2. Go to the **Connect** tab. You will see a `DATABASE_URL`.
3. Go back to your Web Service -> **Variables** tab.
4. Add a new variable called `DATABASE_URL` and paste the connection string.
5. Railway will automatically trigger a redeploy of your web service with the new database credentials.

### Step 5: Start Command Configuration (If needed)
Railway is usually smart enough to find `main.py` or `Procfile`, but if the build fails, you can specify the start command:
1. Go to your Web Service -> **Settings** -> **Deploy**.
2. Under **Custom Start Command**, enter:
   `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Step 6: Access Your Live App
1. Go to the **Settings** tab of your Web Service.
2. Under **Environment**, click **Generate Domain**.
3. Your application is now securely hosted and live!
