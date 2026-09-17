"""
Cashfree Subscriptions payments routes.

Flow:
  1. POST /create-order  → backend creates Cashfree subscription → returns auth_link
  2. Frontend redirects user to auth_link (Cashfree hosted page)
  3. User enters card/UPI, authorises ₹1 hold (free trial starts, no real charge)
  4. Cashfree redirects to success_url; webhook fires → plan activated
  5. After TRIAL_DAYS, Cashfree charges first real payment automatically

Cashfree Subscriptions API v2:
  Test base: https://test.cashfree.com/api/v2
  Prod base: https://api.cashfree.com/api/v2
  Auth headers: x-client-id, x-client-secret
"""
import base64
import hashlib
import hmac
import json
import sys
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import require_user
from app.models.models import User
from app.api.routes.solve import PLAN_LIMITS  # single source of truth — see solve.py

router = APIRouter(prefix="/payments", tags=["Payments"])

PLAN_IDS = {
    "student": settings.CASHFREE_STUDENT_PLAN_ID,
    "pro":     settings.CASHFREE_PRO_PLAN_ID,
}

TRIAL_DAYS = 2


# ── Cashfree helpers ──────────────────────────────────────────────────────────

def _cf_base() -> str:
    if settings.CASHFREE_ENV == "production":
        return "https://api.cashfree.com/api/v2"
    return "https://test.cashfree.com/api/v2"


def _cf_headers() -> dict:
    if not settings.CASHFREE_APP_ID or not settings.CASHFREE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Payments not configured yet. Set CASHFREE_APP_ID and CASHFREE_SECRET_KEY.")
    return {
        "x-client-id": settings.CASHFREE_APP_ID,
        "x-client-secret": settings.CASHFREE_SECRET_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _verify_webhook_signature(payload: bytes, timestamp: str, signature: str) -> bool:
    """
    Cashfree webhook signature verification.
    Signature = base64( HMAC-SHA256( timestamp + rawBody, secret_key ) )
    Caller must ensure CASHFREE_WEBHOOK_SECRET is configured before calling this.
    """
    body_str = timestamp + payload.decode("utf-8")
    computed = base64.b64encode(
        hmac.new(
            settings.CASHFREE_WEBHOOK_SECRET.encode(),
            body_str.encode(),
            hashlib.sha256,
        ).digest()
    ).decode()
    return hmac.compare_digest(computed, signature)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/config")
async def get_config():
    return {"env": settings.CASHFREE_ENV or "test"}


@router.get("/status")
async def get_status(current_user: User = Depends(require_user)):
    # Daily, rolling 24h window -- matches the actual gate enforced in
    # solve.py (daily_solves vs. PLAN_LIMITS). total_solves is tracked
    # separately as a lifetime stat only, not a gate.
    return {
        "plan": current_user.subscription_plan,
        "status": current_user.subscription_status,
        "solves_used": current_user.daily_solves or 0,
        "solves_limit": PLAN_LIMITS.get(current_user.subscription_plan, PLAN_LIMITS["free"]),
        "expires_at": current_user.subscription_expires_at,
    }


class OrderRequest(BaseModel):
    plan: str         # "student" | "pro"
    success_url: str
    cancel_url: str


@router.post("/create-order")
async def create_order(
    body: OrderRequest,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    plan_id = PLAN_IDS.get(body.plan)
    if not plan_id:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {body.plan}")

    now = datetime.now(timezone.utc)
    first_charge_date = (now + timedelta(days=TRIAL_DAYS)).strftime("%Y-%m-%d")
    expires_on = (now + timedelta(days=3650)).strftime("%Y-%m-%d %H:%M:%S")

    # Unique subscription ID tied to this user + timestamp
    sub_id = f"mvsub_{current_user.id}_{int(now.timestamp())}"

    # Cashfree requires a phone number; we use a placeholder since Google login
    # doesn't provide one. The Cashfree checkout page lets the user enter their own.
    customer_phone = "9999999999"

    payload = {
        "subscriptionId": sub_id,
        "planId": plan_id,
        "customerName": (current_user.name or current_user.email.split("@")[0])[:50],
        "customerEmail": current_user.email,
        "customerPhone": customer_phone,
        "returnUrl": body.success_url,
        "authAmount": 1,              # ₹1 authorisation — verifies card, not charged
        "firstChargeDate": first_charge_date,
        "expiresOn": expires_on,
        "subscriptionNote": f"MathVerse {body.plan.title()} – {TRIAL_DAYS}-day free trial",
        "subscriptionMeta": {
            "user_id": str(current_user.id),
            "plan": body.plan,
        },
    }

    print(f"[MathVerse] Cashfree create-order: {sub_id} plan={body.plan}", file=sys.stderr)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{_cf_base()}/subscriptions",
            json=payload,
            headers=_cf_headers(),
        )

    print(f"[MathVerse] Cashfree response {resp.status_code}: {resp.text[:300]}", file=sys.stderr)

    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"Cashfree error ({resp.status_code}): {resp.text[:200]}"
        )

    data = resp.json()
    auth_link = data.get("authLink") or data.get("shortUrl")
    if not auth_link:
        raise HTTPException(status_code=502, detail=f"No auth link from Cashfree: {data}")

    # Persist subscription ID so webhook can find this user
    current_user.payment_subscription_id = sub_id
    await db.commit()

    return {"checkout_url": auth_link, "plan": body.plan}


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    sub_id = current_user.payment_subscription_id
    if not sub_id:
        raise HTTPException(status_code=400, detail="No active subscription found")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{_cf_base()}/subscriptions/{sub_id}/cancel",
            headers=_cf_headers(),
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=400, detail=f"Cancel failed: {resp.text[:200]}")

    current_user.subscription_status = "canceled"
    await db.commit()
    return {"success": True, "message": "Subscription cancelled at end of current period"}


@router.post("/webhook")
async def cashfree_webhook(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
    x_webhook_timestamp: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()

    # Verify signature. A missing secret or missing/invalid headers must reject
    # the request — silently accepting an unsigned webhook would let anyone
    # activate or cancel any user's subscription by guessing a subscription id.
    if not settings.CASHFREE_WEBHOOK_SECRET:
        if settings.DEBUG:
            print("[MathVerse] WARNING: CASHFREE_WEBHOOK_SECRET not set — accepting unsigned webhook (debug only)", file=sys.stderr)
        else:
            raise HTTPException(status_code=503, detail="Webhook verification not configured")
    elif not x_webhook_signature or not x_webhook_timestamp:
        raise HTTPException(status_code=400, detail="Missing webhook signature")
    elif not _verify_webhook_signature(payload, x_webhook_timestamp, x_webhook_signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event = json.loads(payload)
    event_type = event.get("type", "")

    # Cashfree sends subscription data in different structures depending on event type
    data = event.get("data", event)
    sub_obj = data.get("subscription", data)
    sub_id = sub_obj.get("subscriptionId") or sub_obj.get("cf_subscription_id") or ""
    meta = sub_obj.get("subscriptionMeta", sub_obj.get("subscriptionTags", {})) or {}
    plan_name = meta.get("plan", "student")

    print(f"[MathVerse] Cashfree webhook: {event_type} sub={sub_id}", file=sys.stderr)

    if not sub_id:
        return {"received": True}

    result = await db.execute(select(User).where(User.payment_subscription_id == sub_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"received": True}

    # Activate plan
    if event_type in (
        "SUBSCRIPTION_ACTIVATED",
        "SUBSCRIPTION_NEW_PLAN",
        "SUBSCRIPTION_PAYMENT_SUCCESS",
        "SUBSCRIPTION_STATUS_CHANGE",
        "PAYMENT_SUCCESS",
    ):
        # Double-check status field if present
        status = sub_obj.get("status", "ACTIVE").upper()
        if status in ("ACTIVE", "PAID", "SUCCESS", "AUTHORIZED"):
            user.subscription_plan = plan_name
            user.subscription_status = "active"
            await db.commit()
            print(f"[MathVerse] Activated plan={plan_name} for user={user.id}", file=sys.stderr)

    elif event_type in ("SUBSCRIPTION_CANCELLED", "SUBSCRIPTION_EXPIRED", "SUBSCRIPTION_PAYMENT_FAILED"):
        user.subscription_plan = "free"
        user.subscription_status = "canceled"
        await db.commit()
        print(f"[MathVerse] Cancelled subscription for user={user.id}", file=sys.stderr)

    return {"received": True}
