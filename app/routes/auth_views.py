from fastapi import APIRouter, Request, Form, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from core import database as db
from app.core.security import create_access_token
from core import auth as auth_helper
from typing import Optional
import random
import time

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "auth/login.html", {"request": request})

@router.post("/login")
async def login(
    request: Request,
    response: Response,
    email: str = Form(...),
    otp: Optional[str] = Form(None),
    login_type: str = Form("user"),
    password: Optional[str] = Form(None)
):
    import os
    admin_email = os.getenv("ADMIN_LOGIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if admin_email and login_type == "admin":
        if email != admin_email:
            return templates.TemplateResponse(request, "auth/login.html", {
                "request": request,
                "error": "Invalid admin email.",
                "email": email,
                "login_type": "admin"
            })
            
        if password == admin_password:
            token_data = {"sub": email, "id": 0, "role": "admin", "name": "System Admin"}
            access_token = create_access_token(data=token_data)
            redirect = RedirectResponse(url="/", status_code=302)
            from app.core.security import SESSION_EXPIRY_MINUTES
            redirect.set_cookie(
                key="access_token",
                value=f"Bearer {access_token}",
                httponly=True,
                secure=False,
                samesite="lax",
                max_age=SESSION_EXPIRY_MINUTES * 60
            )
            return redirect
        else:
            return templates.TemplateResponse(request, "auth/login.html", {
                "request": request,
                "error": "Invalid admin password.",
                "email": email,
                "login_type": "admin"
            })

    user = db.get_user_by_email(email)
    if not user:
        return templates.TemplateResponse(request, "auth/login.html", {
            "request": request,
            "error": "Email not registered. Please sign up first.",
            "email": email
        })
        
    if user.get("is_active") == 0:
        return templates.TemplateResponse(request, "auth/login.html", {
            "request": request,
            "error": "Account has been disabled by an administrator.",
            "email": email
        })

    if not otp:
        otp_code = str(random.randint(100000, 999999))
        expiry = int(time.time() * 1000) + 10 * 60 * 1000
        db.update_user_otp(email, otp_code, expiry)
        auth_helper.send_otp_email(email, otp_code)
        return templates.TemplateResponse(request, "auth/login.html", {
            "request": request,
            "message": f"OTP sent to {email}.",
            "email": email,
            "otp_sent": True
        })

    current_time = int(time.time() * 1000)
    if user.get("otp") != otp or user.get("otp_expiry", 0) < current_time:
        db.increment_failed_logins(user["id"])
        return templates.TemplateResponse(request, "auth/login.html", {
            "request": request,
            "error": "Invalid or expired OTP. Please request a new code.",
            "email": email,
            "otp_sent": True
        })

    db.increment_successful_logins(user["id"])

    token_data = {"sub": user["email"], "id": user["id"], "role": user["role"], "name": user["name"]}
    access_token = create_access_token(data=token_data)

    redirect = RedirectResponse(url="/", status_code=302)
    from app.core.security import SESSION_EXPIRY_MINUTES
    redirect.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=SESSION_EXPIRY_MINUTES * 60
    )
    return redirect

@router.get("/signup")
async def signup_page(request: Request):
    return templates.TemplateResponse(request, "auth/signup.html", {"request": request})

@router.post("/signup")
async def signup(
    request: Request,
    email: str = Form(...),
    name: str = Form(...),
    university: str = Form(...),
    area_interest_select: str = Form(...),
    area_interest_other: str = Form(""),
    domain_interest_select: str = Form(...),
    domain_interest_other: str = Form(""),
    specialization: str = Form("")
):
    existing = db.get_user_by_email(email)
    if existing:
        return templates.TemplateResponse(request, "auth/signup.html", {
            "request": request,
            "error": "Email already registered",
            "name": name,
            "email": email,
            "university": university,
            "area_interest_select": area_interest_select,
            "area_interest_other": area_interest_other,
            "domain_interest_select": domain_interest_select,
            "domain_interest_other": domain_interest_other,
            "specialization": specialization
        })

    area_interest = area_interest_other.strip() if area_interest_select == "Other" else area_interest_select
    domain_interest = domain_interest_other.strip() if domain_interest_select == "Other" else domain_interest_select

    if not area_interest or not domain_interest or not university.strip():
        return templates.TemplateResponse(request, "auth/signup.html", {
            "request": request,
            "error": "Area of Interest, Domain of Interest, and University are required.",
            "name": name,
            "email": email,
            "university": university,
            "area_interest_select": area_interest_select,
            "area_interest_other": area_interest_other,
            "domain_interest_select": domain_interest_select,
            "domain_interest_other": domain_interest_other,
            "specialization": specialization
        })

    user = db.create_user(
        email=email,
        name=name,
        university=university,
        area_interest=area_interest,
        domain_interest=domain_interest,
        specialization=specialization,
        role="user",
        hashed_password=None
    )

    return RedirectResponse(url="/auth/login?msg=success", status_code=302)

@router.get("/logout")
async def logout():
    redirect = RedirectResponse(url="/auth/login", status_code=302)
    redirect.delete_cookie("access_token")
    return redirect

@router.get("/session-config")
async def session_config():
    from app.core.security import SESSION_EXPIRY_MINUTES
    return {"expiry_minutes": SESSION_EXPIRY_MINUTES}

@router.post("/refresh")
async def refresh_session(request: Request):
    from app.core.security import get_current_user_from_cookie, create_access_token, SESSION_EXPIRY_MINUTES
    user = get_current_user_from_cookie(request)
    if not user:
        return Response(status_code=401)
        
    token_data = {"sub": user.get("sub"), "id": user.get("id"), "role": user.get("role"), "name": user.get("name")}
    access_token = create_access_token(data=token_data)
    
    response = Response(status_code=200)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=SESSION_EXPIRY_MINUTES * 60
    )
    return response