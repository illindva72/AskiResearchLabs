# Deploying AskiResearchLabs to Zoho Catalyst AppSail via Web GUI

If the Catalyst CLI is causing issues on your local machine, you can easily bypass it and deploy your FastAPI application entirely through the Zoho Catalyst Web Console using a ZIP file.

Here is the step-by-step guide to deploying AskiResearchLabs from scratch using the GUI.

---

## Step 1: Prepare Your Code (Create a ZIP)

To upload via the web console, you must package your source code into a `.zip` file. **The structure inside the zip must be flat** (i.e., `main.py` and `requirements.txt` must be at the very top level of the zip, not inside a subfolder).

1. Open your `AskiResearchLab` folder in File Explorer.
2. **Select all the required files and folders**:
   - `app/` (folder)
   - `core/` (folder)
   - `main.py`
   - `requirements.txt`
3. **DO NOT include** the following to keep the file size small and secure:
   - `.venv/` or `venv/`
   - `.git/`
   - `.env` (we will set these securely in the GUI)
   - `askiresearchlabs.db` (a fresh one will be created, or you can include it if you want to migrate existing data)
   - `__pycache__/`
   - `logs/`
4. Right-click the selected files -> **Compress to ZIP file** (name it `AskiResearchLabs_Source.zip`).

---

## Step 2: Create a Fresh Catalyst Project

1. Go to the [Zoho Catalyst Console](https://console.catalyst.zoho.in) (or `.com` based on your region) and log in.
2. Click the **Create Project** button on the top right.
3. Name your project **AskiResearchLabs** and accept the terms to create it.
4. Once the project dashboard loads, you are ready to set up AppSail.

---

## Step 3: Create the AppSail Service

1. In the left-hand menu, click on **Compute** and then select **AppSail**.
2. Click the **Create Service** (or "Get Started") button in the center of the screen.
3. You will be presented with a configuration screen for your new service:

### AppSail Configuration Settings:

| Setting | Value to enter / select |
|---------|-------------------------|
| **Service Name** | `AskiResearchApp` (No spaces allowed) |
| **Build Source** | Select **ZIP / WAR** |
| **Upload File** | Click and browse to upload your `AskiResearchLabs_Source.zip` file |
| **Stack** | Select **Python 3.10** (or highest Python 3.x available) |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $X_ZOHO_CATALYST_LISTEN_PORT` |
| **Memory** | `256 MB` or `512 MB` is sufficient for this application |

> [!IMPORTANT]
> The **Start Command** is critical. Catalyst dynamically assigns a port for security, and the `$X_ZOHO_CATALYST_LISTEN_PORT` environment variable tells Uvicorn to listen on that exact port. If you skip this, the deployment will fail health checks.

---

## Step 4: Configure Environment Variables

Before clicking Create, scroll down on the same setup page to find the **Environment Variables** section. You must add the variables from your local `.env` file so the deployed app can access the AI and Email features.

Add the following keys and your corresponding values:

- `ANTHROPIC_API_KEY` = `sk-ant-your-api-key`
- `ADMIN_EMAIL` = `admin@askitech.org`
- `ADMIN_EMAIL_PASSWORD` = `your-smtp-password`
- `SMTP_HOST` = `smtp.zoho.com` (or `smtp.zoho.in`)
- `SMTP_PORT` = `587`

---

## Step 5: Deploy and Access

1. Once the ZIP is uploaded and variables are set, click **Create** (or **Deploy**) at the bottom right.
2. Catalyst will take a few minutes to build the Docker image, install your `requirements.txt`, and start the Uvicorn server.
3. Once the status turns **🟢 Active / Running**, your application is live!
4. Click on the generated **App URL** provided on the service dashboard to open AskiResearchLabs in your browser.

> [!TIP]
> If the app crashes on boot, you can click on the **Logs** tab inside the AppSail service dashboard to read the exact Python error trace. This is incredibly helpful for troubleshooting missing dependencies or environment variables.
