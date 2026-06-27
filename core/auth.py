import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import random
import time

try:
    import streamlit as st
except ImportError:
    st = None

from core import database as db

def send_otp_email(to_email: str, otp: str):
    admin_email = os.getenv("ADMIN_EMAIL", "admin@askitech.org")
    admin_pass = os.getenv("ADMIN_EMAIL_PASSWORD")
    
    # Just mock/console if no real credentials provided
    if not admin_pass:
        print(f"\n========== MOCK EMAIL ==========\nFrom: {admin_email}\nTo: {to_email}\nOTP: {otp}\n================================\n")
        return True

    try:
        msg = MIMEMultipart()
        msg['From'] = admin_email
        msg['To'] = to_email
        msg['Subject'] = "ResearchTrack - Your Login OTP"
        
        body = f"Your OTP for ResearchTrack login is: {otp}\nIt is valid for 10 minutes."
        msg.attach(MIMEText(body, 'plain'))
        
        # Adjust SMTP settings for your provider (e.g., smtp.zoho.com)
        smtp_host = os.getenv("SMTP_HOST", "smtp.zoho.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            server.set_debuglevel(1)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.set_debuglevel(1)
            server.ehlo()
            server.starttls()
            server.ehlo()
            
        server.login(admin_email, admin_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        # Always fallback to MOCK if real delivery fails to maintain development continuity
        print(f"\n========== MOCK EMAIL ==========\nTo: {to_email}\nOTP: {otp}\n================================\n")
        return True

def send_upgrade_email(user_email: str, user_name: str, db_size_mb: float):
    admin_email = os.getenv("ADMIN_EMAIL", "admin@askitech.org")
    admin_pass = os.getenv("ADMIN_EMAIL_PASSWORD")
    
    if not admin_pass:
        print(f"\n========== MOCK UPGRADE EMAIL ==========\nFrom: {user_email}\nTo: {admin_email}\nUser {user_name} ({user_email}) requested a storage upgrade. Current usage: {db_size_mb:.2f} MB.\n========================================\n")
        return True

    try:
        msg = MIMEMultipart()
        msg['From'] = admin_email
        msg['To'] = admin_email # Send to admin
        msg['Subject'] = f"ResearchTrack - Upgrade Request from {user_name}"
        
        body = f"User {user_name} ({user_email}) has exceeded the 150MB storage limit (Current usage: {db_size_mb:.2f} MB) and is requesting a plan upgrade to discuss pricing."
        msg.attach(MIMEText(body, 'plain'))
        
        smtp_host = os.getenv("SMTP_HOST", "smtp.zoho.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.ehlo()
            server.starttls()
            server.ehlo()
            
        server.login(admin_email, admin_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send upgrade email: {e}")
        return False


def require_auth():
    if "user" not in st.session_state:
        st.warning("You must be logged in to access this page. Please return to the Home page to log in.", icon="🔒")
        st.stop()

def require_admin():
    require_auth()
    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Admin access required.", icon="🚫")
        st.stop()

def render_feedback_button():
    if "user" in st.session_state:
        st.sidebar.markdown("---")
        if st.sidebar.button("💬 Send Feedback / Suggestions"):
            st.session_state["show_feedback"] = True

        if st.session_state.get("show_feedback"):
            with st.sidebar.form("feedback_form"):
                msg = st.text_area("Your Suggestion / Help request:")
                submitted = st.form_submit_button("Send")
                if submitted and msg:
                    db.create_feedback(st.session_state["user"]["id"], msg)
                    st.success("Feedback sent to admin!")
                    st.session_state["show_feedback"] = False
