import asyncio
import json
import os
from dataclasses import dataclass
from typing import Dict, Optional

from pywebpush import WebPushException, webpush

from ..models import PushSubscription


class PushConfigError(RuntimeError):
    """Raised when VAPID configuration is missing or invalid."""


class PushDeliveryError(RuntimeError):
    """Raised when a push notification cannot be delivered."""


@dataclass(frozen=True)
class VapidConfig:
    public_key: str
    private_key: str
    subject: str


def get_vapid_configuration() -> VapidConfig:
    public_key = os.getenv("VAPID_PUBLIC_KEY")
    private_key = os.getenv("VAPID_PRIVATE_KEY")

    if not public_key or not private_key:
        raise PushConfigError("VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY must be set to send push notifications.")

    subject = os.getenv("VAPID_SUBJECT", "mailto:admin@example.com")
    return VapidConfig(public_key=public_key, private_key=private_key, subject=subject)


async def send_web_push(
    subscription: PushSubscription,
    payload: Dict,
    config: Optional[VapidConfig] = None,
) -> None:
    if not subscription.endpoint or not subscription.p256dh or not subscription.auth:
        raise PushDeliveryError("Subscription is missing required endpoint or keys.")

    vapid_config = config or get_vapid_configuration()
    subscription_info = {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh,
            "auth": subscription.auth,
        },
    }

    data = json.dumps(payload)

    def _send():
        try:
            webpush(
                subscription_info=subscription_info,
                data=data,
                vapid_private_key=vapid_config.private_key,
                vapid_claims={"sub": vapid_config.subject},
            )
        except WebPushException as exc:
            raise PushDeliveryError(str(exc)) from exc

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _send)
