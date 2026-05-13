"""
Stripe Checkout integration for PainSignal.
Falls back to mock mode if no STRIPE_SECRET_KEY is configured.
"""

import os
from typing import Optional

STRIPE_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", "http://localhost:8000/dashboard.html?payment=success")
CANCEL_URL = os.getenv("STRIPE_CANCEL_URL", "http://localhost:8000/index.html?payment=cancelled")

try:
    import stripe
    if STRIPE_KEY:
        stripe.api_key = STRIPE_KEY
        STRIPE_READY = True
    else:
        STRIPE_READY = False
except ImportError:
    STRIPE_READY = False
    stripe = None


# Plan config (you can replace these with real Stripe Price IDs after creating them)
PLAN_CONFIG = {
    "starter": {
        "name": "PainSignal Starter",
        "price_cents": 2900,  # $29
        "interval": "month",
        "price_id": os.getenv("STRIPE_PRICE_STARTER", "")  # fill in after creating in Stripe Dashboard
    },
    "builder": {
        "name": "PainSignal Builder",
        "price_cents": 9900,  # $99
        "interval": "month",
        "price_id": os.getenv("STRIPE_PRICE_BUILDER", "")
    },
    "agency": {
        "name": "PainSignal Agency",
        "price_cents": 29900,  # $299
        "interval": "month",
        "price_id": os.getenv("STRIPE_PRICE_AGENCY", "")
    }
}


def create_checkout_session(plan: str, user_email: str, user_id: int) -> dict:
    """
    Create a Stripe Checkout Session for a subscription.
    Returns {"url": <checkout_url>} on success, or {"error": ...}
    """

    if plan not in PLAN_CONFIG:
        return {"error": f"Unknown plan: {plan}"}

    config = PLAN_CONFIG[plan]

    # ── Mock mode (no Stripe key) ────────────────────────────────
    if not STRIPE_READY:
        return {
            "url": f"{SUCCESS_URL}&mock=true&plan={plan}&user_id={user_id}",
            "mock": True,
            "message": "Mock mode — set STRIPE_SECRET_KEY to use real Stripe"
        }

    try:
        # If a real Stripe Price ID was provided, use that.
        # Otherwise, create the line item inline.
        if config["price_id"]:
            line_items = [{"price": config["price_id"], "quantity": 1}]
        else:
            line_items = [{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": config["name"]},
                    "unit_amount": config["price_cents"],
                    "recurring": {"interval": config["interval"]}
                },
                "quantity": 1
            }]

        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=line_items,
            customer_email=user_email,
            success_url=f"{SUCCESS_URL}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=CANCEL_URL,
            metadata={"user_id": str(user_id), "plan": plan},
            subscription_data={"metadata": {"user_id": str(user_id), "plan": plan}}
        )

        return {"url": session.url, "session_id": session.id}

    except Exception as e:
        return {"error": str(e)}


def verify_webhook_signature(payload: bytes, sig_header: str) -> Optional[dict]:
    """Verify Stripe webhook signature. Returns the event or None."""
    if not STRIPE_READY or not STRIPE_WEBHOOK_SECRET:
        return None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        return event
    except Exception as e:
        print(f"[WEBHOOK ERROR] {e}")
        return None
