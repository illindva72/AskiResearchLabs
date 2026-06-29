from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.core.security import get_current_user_from_cookie
from core import database as db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")

def get_admin_user(request: Request):
    user = get_current_user_from_cookie(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return user

@router.get("/database")
async def admin_database_page(request: Request, table: str = None):
    user = get_admin_user(request)
    tables = db.get_all_tables()
    
    selected_table = table if table and table in tables else (tables[0] if tables else None)
    
    schema = []
    if selected_table:
        schema = db.get_table_schema(selected_table)
        
    return templates.TemplateResponse(request, "admin/database.html", {
        "request": request,
        "user": user,
        "tables": tables,
        "selected_table": selected_table,
        "schema": schema
    })

@router.get("/api/table/{table_name}")
async def get_table_data_api(request: Request, table_name: str, limit: int = 100):
    user = get_admin_user(request)
    tables = db.get_all_tables()
    if table_name not in tables:
        return JSONResponse({"error": "Table not found"}, status_code=404)
        
    schema = db.get_table_schema(table_name)
    data = db.get_table_data(table_name, limit=limit)
    return JSONResponse({"schema": schema, "data": data})

@router.get("/users")
async def admin_users_page(request: Request):
    user = get_admin_user(request)
    users_with_stats = db.get_all_users_with_stats()
    
    return templates.TemplateResponse(request, "admin/users.html", {
        "request": request,
        "user": user,
        "users": users_with_stats
    })

@router.post("/users/{user_id}/toggle")
async def toggle_user_status(request: Request, user_id: int):
    user = get_admin_user(request)
    form = await request.form()
    is_active_str = form.get("is_active", "1")
    is_active = 1 if is_active_str == "1" else 0
    
    db.toggle_user_status(user_id, is_active)
    return RedirectResponse(url="/admin/users", status_code=302)
