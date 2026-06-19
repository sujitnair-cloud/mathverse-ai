"""
Stripe payments routes.
POST /api/v1/payments/create-checkout  — create Stripe Checkout session
POST /api/v1/payments/webhook          — handle Stripe webhook events
GET  /api/v1/payments/portal           — customer billing portal URL
GET  /api/v1/payments/status           — current user subscription info
GET  /api/v1/payments/config           — publishable key for frontend
"""
import stripe
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import require_user
from app.models.models import User

router = APIRouter(prefix="/payments", tags=["Payments"])

PLAN_PRICES = {
    "student": settings.STRIPE_STUDENT_PRICE_ID,
    "pro":     settings.STRIPE_PRO_PRICE_ID,
}

PLAN_LIMITS = {
    "free":    10,   # solves per day
    "student": 9999,
    "pro":     9999,
    "school":  9999,
}


def _stripe_client():
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Payments not configured yet")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


@router.get("/config")
async def get_config():
    return {"publishable_key": settings.STRIPE_PUBLISHABLE_KEY or ""}


@router.get("/status")
async def get_status(current_user: User = Depends(require_user)):
    return {
        "plan": current_user.subscription_plan,
        "status": current_user.subscription_status,
        "daily_solves_used": current_user.daily_solves or 0,
        "daily_solves_limit": PLAN_LIMITS.get(current_user.subscription_plan, 10),
        "expires_at": current_user.subscription_expires_at,
    }


class CheckoutRequest(BaseModel):
    plan: str          # "student" | "pro"
    success_url: str
    cancel_url: str


@router.post("/create-checkout")
async def create_checkout(
    body: CheckoutRequest,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    _stripe = _stripe_client()
    price_id = PLAN_PRICES.get(body.plan)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {body.plan}")

    # Get or create Stripe customer
    customer_id = current_user.stripe_customer_id
    if not customer_id:
        customer = _stripe.Customer.create(
            email=current_user.email,
            name=current_user.name,
            metadata={"user_id": str(current_user.id)},
        )
        customer_id = customer.id
        current_user.stripe_customer_id = customer_id
        await db.commit()

    session = _stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=body.success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=body.cancel_url,
        metadata={"user_id": str(current_user.id), "plan": body.plan},
        allow_promotion_codes=True,
    )
    return {"checkout_url": session.url}


@router.get("/portal")
async def billing_portal(
    return_url: str,
    current_user: User = Depends(require_user),
):
    _stripe = _stripe_client()
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found")
    session = _stripe.billing_portal.Session.create(
        customer=current_user.stripe_customer_id,
        return_url=return_url,
    )
    return {"portal_url": session.url}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    _stripe = _stripe_client()
    payload = await request.body()

    try:
        event = _stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    data = event["data"]["object"]

    if event["type"] == "checkout.session.completed":
        user_id = int(data.get("metadata", {}).get("user_id", 0))
        plan = data.get("metadata", {}).get("plan", "student")
        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                user.subscription_plan = plan
                user.subscription_status = "active"
                user.stripe_subscription_id = data.get("subscription")
                await db.commit()

    elif event["type"] in ("customer.subscription.deleted", "customer.subscription.paused"):
        sub_id = data.get("id")
        result = await db.execute(select(User).where(User.stripe_subscription_id == sub_id))
        user = result.scalar_one_or_none()
        if user:
            user.subscription_plan = "free"
            user.subscription_status = "canceled"
            await db.commit()

    elif event["type"] == "customer.subscription.updated":
        sub_id = data.get("id")
        result = await db.execute(select(User).where(User.stripe_subscription_id == sub_id))
        user = result.scalar_one_or_none()
        if user:
            user.subscription_status = data.get("status", "active")
            await db.commit()

    return {"received": True}
