from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes import views, api, auth_views, admin_views
from dotenv import load_dotenv
import logging
import os
from datetime import datetime

load_dotenv()

# --- Logging Setup ---
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)

os.makedirs("logs", exist_ok=True)
date_str = datetime.now().strftime("%Y-%m-%d")
log_file_path = os.path.join("logs", f"app_{date_str}.log")

# Configure root logger
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path, mode="a", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"AskiResearchLabs Application starting up. Log level: {LOG_LEVEL_STR}")
# ---------------------

app = FastAPI(title="AskiResearchLabs API")

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.security import get_current_user_from_cookie, create_access_token, SESSION_EXPIRY_MINUTES

class SessionRefreshMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        if request.url.path.startswith("/static") or request.url.path.startswith("/auth/logout"):
            return response
            
        user = get_current_user_from_cookie(request)
        if user:
            token_data = {"sub": user.get("sub"), "id": user.get("id"), "role": user.get("role"), "name": user.get("name")}
            access_token = create_access_token(data=token_data)
            
            response.set_cookie(
                key="access_token",
                value=f"Bearer {access_token}",
                httponly=True,
                secure=False,
                samesite="lax",
                max_age=SESSION_EXPIRY_MINUTES * 60
            )
            
        return response

app.add_middleware(SessionRefreshMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(views.router)
app.include_router(api.router)
app.include_router(auth_views.router)
app.include_router(admin_views.router)

if __name__ == "__main__":
    import uvicorn
    from uvicorn.config import LOGGING_CONFIG
    
    # Configure uvicorn loggers to also write to our file
    LOGGING_CONFIG["handlers"]["file"] = {
        "class": "logging.FileHandler",
        "filename": log_file_path,
        "mode": "a",
        "encoding": "utf-8",
        "formatter": "default",
    }
    # Add the file handler to uvicorn's loggers
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        if logger_name in LOGGING_CONFIG["loggers"]:
            # 'access' formatter for access logs, 'default' for others
            fmt = "access" if logger_name == "uvicorn.access" else "default"
            LOGGING_CONFIG["loggers"][logger_name]["handlers"] = [fmt, "file"]
            
    # Make sure uvicorn also respects our log level
    # Use the Catalyst port if available, otherwise default to 8000
    port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT", 8000))
    host = "0.0.0.0" if os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") else "127.0.0.1"
    
    uvicorn.run("main:app", host=host, port=port, reload=True, log_level=LOG_LEVEL_STR.lower(), log_config=LOGGING_CONFIG)