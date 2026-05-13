"""
PainSignal — FastAPI Backend
Run: uvicorn backend.main:app --reload --port 8000
"""

import os
import re
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, Request, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

from . import database as db
from . import auth
from . import email_sender
from . import stripe_handler
from . import pain_data

# ─── App Setup ────────────────────────────────────────────────────
app = FastAPI(
    title="PainSignal API",
    description="AI Market Intelligence Backend",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

PROJECT_ROOT = Path(__file__).parent.parent


# ─── Pydantic Models ──────────────────────────────────────────────
class SubscribeRequest(BaseModel):
    email: EmailStr

class SignupRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class CheckoutRequest(BaseModel):
    plan: str  # starter / builder / agency


# ─── Static HTML Pages ────────────────────────────────────────────
@app.get("/")
async def root():
    return FileResponse(PROJECT_ROOT / "index.html")

@app.get("/index.html")
async def index():
    return FileResponse(PROJECT_ROOT / "index.html")

@app.get("/dashboard.html")
async def dashboard():
    return FileResponse(PROJECT_ROOT / "dashboard.html")

@app.get("/login.html")
async def login_page():
    return FileResponse(PROJECT_ROOT / "login.html")

@app.get("/signup.html")
async def signup_page():
    return FileResponse(PROJECT_ROOT / "signup.html")


# ─── Email Subscription ───────────────────────────────────────────
@app.post("/api/subscribe")
async def subscribe(req: SubscribeRequest):
    """Capture email from landing page form."""
    success = db.add_subscriber(req.email)

    if success:
        email_sender.send_welcome_email(req.email)
        return {"success": True, "message": "Subscribed! Check your inbox."}
    else:
        return {"success": True, "message": "You're already on our list — we'll see you Monday!"}


@app.get("/api/subscribers/count")
async def subscriber_count():
    """Public stat — how many subscribers."""
    return {"count": db.get_subscriber_count()}


# ─── Auth Endpoints ───────────────────────────────────────────────
@app.post("/api/signup")
async def signup(req: SignupRequest):
    """Create a new user account."""
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    existing = db.get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered. Try logging in.")

    pwd_hash = auth.hash_password(req.password)
    user_id = db.create_user(req.email, pwd_hash, plan="free")

    # Also add to newsletter
    db.add_subscriber(req.email, source="signup")

    # Welcome email
    email_sender.send_welcome_email(req.email)

    token = auth.create_access_token(user_id, req.email)
    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user_id, "email": req.email, "plan": "free"}
    }


@app.post("/api/login")
async def login(req: LoginRequest):
    """Login an existing user."""
    user = db.get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not auth.verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    db.update_user_login(user["id"])
    token = auth.create_access_token(user["id"], user["email"])

    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user["id"], "email": user["email"], "plan": user["plan"]}
    }


@app.get("/api/me")
async def get_me(current_user: dict = Depends(auth.get_current_user)):
    """Get current logged-in user."""
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "plan": current_user["plan"],
        "created_at": current_user["created_at"]
    }


# ─── Pain Points Data (tier-gated) ────────────────────────────────
@app.get("/api/pain-points")
async def list_pain_points(current_user: dict = Depends(auth.get_current_user)):
    """Return pain points based on user's plan."""
    points = pain_data.get_pain_points_for_plan(current_user["plan"])
    total_available = len(pain_data.load_pain_points())

    return {
        "plan": current_user["plan"],
        "shown": len(points),
        "total_available": total_available,
        "locked": total_available - len(points),
        "pain_points": points
    }


@app.get("/api/pain-points/preview")
async def preview_pain_points():
    """Public preview — no auth needed. Top 3 only."""
    points = pain_data.get_pain_points_for_plan("free")
    return {"pain_points": points, "total_available": len(pain_data.load_pain_points())}


@app.get("/api/stats")
async def get_stats():
    """Public stats for the landing page."""
    return pain_data.get_stats()


# ─── Stripe Checkout ──────────────────────────────────────────────
@app.post("/api/checkout")
async def create_checkout(
    req: CheckoutRequest,
    current_user: dict = Depends(auth.get_current_user)
):
    """Create a Stripe Checkout session."""
    result = stripe_handler.create_checkout_session(
        plan=req.plan,
        user_email=current_user["email"],
        user_id=current_user["id"]
    )

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request, stripe_signature: Optional[str] = Header(None)):
    """Handle Stripe webhook events (subscription created/cancelled/etc)."""
    payload = await request.body()
    event = stripe_handler.verify_webhook_signature(payload, stripe_signature)

    if not event:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event["type"]

    # Handle subscription created
    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = int(session.get("metadata", {}).get("user_id", 0))
        plan = session.get("metadata", {}).get("plan", "builder")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        if user_id:
            db.update_user_plan(user_id, plan, customer_id, subscription_id)
            db.log_payment_event(
                user_id=user_id,
                event_type="subscription_started",
                stripe_event_id=event["id"],
                amount=session.get("amount_total"),
                currency=session.get("currency")
            )

            user = db.get_user_by_id(user_id)
            if user:
                email_sender.send_payment_confirmation(user["email"], plan)

    # Handle subscription cancelled
    elif event_type == "customer.subscription.deleted":
        sub = event["data"]["object"]
        user_id = int(sub.get("metadata", {}).get("user_id", 0))
        if user_id:
            db.update_user_plan(user_id, "free", None, None)
            db.log_payment_event(
                user_id=user_id,
                event_type="subscription_cancelled",
                stripe_event_id=event["id"]
            )

    return {"received": True}


# ─── Mock Checkout (for testing without real Stripe) ──────────────
@app.post("/api/mock-upgrade")
async def mock_upgrade(req: CheckoutRequest, current_user: dict = Depends(auth.get_current_user)):
    """Instant upgrade for testing — only available in mock mode."""
    if stripe_handler.STRIPE_READY:
        raise HTTPException(status_code=400, detail="Real Stripe is configured. Use /api/checkout instead.")

    if req.plan not in ("starter", "builder", "agency"):
        raise HTTPException(status_code=400, detail="Invalid plan")

    db.update_user_plan(current_user["id"], req.plan, None, None)
    db.log_payment_event(
        user_id=current_user["id"],
        event_type="mock_upgrade",
        metadata=f"plan={req.plan}"
    )
    email_sender.send_payment_confirmation(current_user["email"], req.plan)

    return {"success": True, "plan": req.plan, "message": f"Upgraded to {req.plan} (mock mode)"}


# ─── Health Check ─────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "stripe_ready": stripe_handler.STRIPE_READY,
        "resend_ready": email_sender.RESEND_READY,
        "subscribers": db.get_subscriber_count()
    }
