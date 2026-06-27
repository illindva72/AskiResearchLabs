# EXECUTION GUIDE — AskiResearchLabs (FastAPI)

Step-by-step instructions for running AskiResearchLabs locally and deploying it to Zoho Catalyst AppSail.

---

## 1. Prerequisites

| Requirement | Version / Notes |
|---|---|
| Python | 3.10 or higher |
| pip | Bundled with Python 3.10+ |
| Node.js / npm | Required only for Zoho Catalyst CLI and deployment |
| Zoho Catalyst account | Required for AppSail deployment |
| Anthropic API key | Required for AI evaluation features |
| Internet access | Required for paper search and AI evaluation |

### Verify Python

```powershell
python --version
```

---

## 2. Install Python Dependencies

Open a terminal in the project root and install the Python dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If you prefer a standard shell:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 3. Configure Environment Variables

Copy the example `.env` file:

```powershell
copy .env.example .env
```

Then edit `.env` and set the required values.

### Required variables

```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Recommended variables

```env
ANTHROPIC_BASE_URL=https://agent-proxy.perplexity.ai/anthropic
DB_NAME=askiresearchlabs.db
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_EMAIL_PASSWORD=your-smtp-password
SMTP_HOST=smtp.zoho.com
SMTP_PORT=587
```

> If `ADMIN_EMAIL` and `ADMIN_EMAIL_PASSWORD` are not set, the app will still run, but OTP delivery is mocked and printed to the console.

---

## 4. Run Locally

Start the FastAPI app with Uvicorn:

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Or run the module directly:

```powershell
python main.py
```

Open the app in your browser:

```
http://127.0.0.1:8000
```

---

## 5. Local Application Flow

1. Open the browser and visit `/` to access the home page.
2. Sign up or log in using the authentication pages.
3. Use the search page to enter your research topic and select sources.
4. Browse the saved search history and paper details.
5. Generate an AI **Summary of Dimensions**, **Model Execution Factors**, or a **Model Opportunity Score** (requires `ANTHROPIC_API_KEY` to be configured).

---

## 6. Deploy to Zoho Catalyst AppSail

This app can be deployed to **Zoho Catalyst AppSail**, which is Catalyst's managed PaaS for web services.

### Catalyst deployment prerequisites

- A Zoho Catalyst account
- Node.js and npm installed
- Catalyst CLI installed globally

### Install Zoho Catalyst CLI

```powershell
npm install -g zcatalyst-cli
```

### Authenticate with Catalyst

```powershell
catalyst login
```

### Initialize Catalyst Project

If the project is not yet configured for Catalyst, initialize it using the CLI in the project directory:

```powershell
catalyst init
```

During initialization:
1. Choose **New-Project** and follow the browser prompt.
2. When asked *"Which are the features you want to setup for this folder?"*, use your **spacebar** to select **AppSail: Configure and deploy AppSails**, then press **Enter**.
3. Follow any subsequent prompts to name your AppSail service (you can point it to the current directory `.` or let it create a new folder and move your files into it).

### Deploy the app

Once the AppSail service is added or initialized, deploy the app with:

```powershell
catalyst deploy
```

The Catalyst CLI deploys the configured AppSail service and prints the generated AppSail URL.

### Local AppSail testing

Before deployment, you can test the AppSail app locally using the Catalyst CLI local serve command:

```powershell
catalyst serve
```

This verifies that the service behaves correctly before pushing it to Catalyst.

---

## 7. Key Files for Deployment

| File | Purpose |
|---|---|
| `main.py` | FastAPI entrypoint |
| `app/` | Jinja2 templates, static assets, routes |
| `core/` | Database, data fetching, AI evaluation logic |
| `.env.example` | Environment variable template |
| `requirements.txt` | Python dependencies for Catalyst runtime |

---

## 8. Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude AI evaluation key |
| `ANTHROPIC_BASE_URL` | No | Alternate Anthropic endpoint (Perplexity proxy) |
| `DB_NAME` | No | SQLite filename, defaults to `askiresearchlabs.db` |
| `ADMIN_EMAIL` | No | SMTP sender address for OTP emails |
| `ADMIN_EMAIL_PASSWORD` | No | SMTP password for OTP email delivery |
| `SMTP_HOST` | No | SMTP host, default is `smtp.zoho.com` |
| `SMTP_PORT` | No | SMTP port, default is `587` |

---

## 9. Troubleshooting

### Uvicorn fails to start

- Confirm your virtual environment is activated.
- Confirm `requirements.txt` is installed.
- Check `python --version` is 3.10 or higher.

### AI evaluation fails

- Verify `ANTHROPIC_API_KEY` is set in `.env`.
- Restart the app after editing `.env`.
- If using a proxy key, set `ANTHROPIC_BASE_URL`.

### SMTP login or OTP issues

- Make sure `ADMIN_EMAIL` and `ADMIN_EMAIL_PASSWORD` are correct.
- If email sending fails, the app will fallback to console output.

### Catalyst CLI errors

- Ensure `zcatalyst-cli` is installed and you are logged in.
- Run `catalyst login` again if token expiration occurs.
- Use `catalyst deploy` from the project root.

### Python 3.9 or lower

The app uses `list[str]` type hints (Python 3.10+). On Python 3.9, run:

```bash
pip install future
```

Or upgrade to Python 3.10+.

### Windows: `activate.ps1 cannot be loaded`

Run this once in PowerShell as Administrator:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 8. Quick-Start Summary

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Anthropic API key
cp .env.example .env
# edit .env and add: ANTHROPIC_API_KEY=sk-ant-your-key-here

# 3. Run
streamlit run app.py

# 4. Open browser
# http://localhost:8501
```

---

## 9. Project Structure

```
askiresearchlabs-streamlit/
├── app.py                      Entry point — run this with streamlit
├── pages/
│   ├── 1_Research_Search.py    Search form + paper results
│   ├── 2_Summary_of_Dimensions.py  AI evaluation (7 tabs)
│   └── 3_Search_History.py     Past searches browser
├── core/
│   ├── __init__.py
│   ├── database.py             SQLite layer (searches, papers, evaluations)
│   ├── fetchers.py             API callers: OpenAlex, CrossRef, arXiv
│   └── evaluate.py             Claude AI evaluation
├── .env                        Your local secrets (not committed)
├── .env.example                Template
├── <DB_NAME>.db                     Auto-created SQLite file
├── requirements.txt            Python package list
├── README.md                   What this app is
└── EXECUTION.md                This file
```
