# Deploying AskiResearchLabs to Fly.io

Fly.io hosts your application on lightweight micro-VMs around the world. It is highly tailored for developers who are comfortable with command-line tools.

## 💰 Cost Analysis

- **Web App Service:** Generous **Free Tier**. You can run up to 3 small (shared 1 vCPU, 256MB RAM) virtual machines 24/7 for **$0/month**.
- **Database Service (PostgreSQL):** Fly offers "Fly Postgres", which provisions a database on one of those micro-VMs. 
  - If you use one of your free VMs for the database, it costs **$0/month**.
  - **Note:** Fly Postgres is *unmanaged*. You are responsible for configuring backups and scaling.
- **Total Expected Cost:** **$0.00 / month** (if utilizing the free tier limits).
- **Security:** Fly.io has best-in-class security. Secrets are injected via the CLI, instantly encrypted, and can NEVER be viewed in plain text again, even by account administrators.

---

## 🚀 End-to-End Deployment Instructions

### Step 1: Install the Fly CLI and Authenticate
1. Install `flyctl` on your local machine:
   - Windows (PowerShell): `pwsh -Command "iwr https://fly.io/install.ps1 -useb | iex"`
   - Mac/Linux: `curl -L https://fly.io/install.sh | sh`
2. Run `fly auth login` in your terminal to sign in via the browser.

### Step 2: Initialize the Fly App
1. Open your terminal and navigate to your project root: `cd c:\Users\AskiT\source\repos\AskiResearchLab`
2. Run the command: `fly launch`
3. Fly will detect your Python app.
4. Follow the interactive prompts:
   - **App Name:** Choose a name or leave blank for a random one.
   - **Region:** Choose a region close to you.
   - **Setup Postgres?** Answer **Yes**. Fly will automatically create a Postgres cluster and link it to your app by injecting a `DATABASE_URL` secret.
   - **Deploy now?** Answer **No** (we need to set secrets first).
5. This process creates a `fly.toml` configuration file in your directory.

### Step 3: Set Secure Environment Variables (Secrets)
Because we answered "No" to deploying immediately, we can now inject our API keys securely.
1. Run the following command to set your Anthropic API key:
   `fly secrets set ANTHROPIC_API_KEY="your-actual-api-key"`
2. These secrets are instantly encrypted and staged for your next deployment.

### Step 4: Deploy the Application
1. Run the deployment command:
   `fly deploy`
2. Fly will build a Docker image of your Python application (using their native builders), push it to their registry, and boot up your virtual machine.
3. Once the deployment finishes, run `fly open` to automatically open your live application in the browser!

### Step 5: Continuous Deployment (Optional)
If you want automatic deployments from GitHub:
1. Generate a Fly API token: `fly tokens create deploy -x 999999h`
2. Add this token as a GitHub Repository Secret (`FLY_API_TOKEN`).
3. Set up a standard GitHub Actions workflow (`.github/workflows/fly.yml`) to run `fly deploy` on `push` to `main`.
