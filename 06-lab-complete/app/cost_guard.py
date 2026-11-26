from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException

from .config import settings
from .redis_client import r

NANODOLLARS = 1_000_000_000
INPUT_TOKEN_COST = 150
OUTPUT_TOKEN_COST = 600


def budget_periods():
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    return (
        (f"day14:budget:day:{now:%Y-%m-%d}", tomorrow, settings.daily_budget),
        (f"day14:budget:month:{now:%Y-%m}", next_month, settings.monthly_budget),
    )


def check_budget(periods) -> None:
    totals = r.mget([key for key, _, _ in periods])
    for total, (_, _, budget) in zip(totals, periods):
        if int(total or 0) >= budget * NANODOLLARS:
            raise HTTPException(status_code=402, detail="Budget exhausted")


def record_cost(input_tokens: int, output_tokens: int, periods) -> Decimal:
    cost = input_tokens * INPUT_TOKEN_COST + output_tokens * OUTPUT_TOKEN_COST
    with r.pipeline() as transaction:
        for key, expiry, _ in periods:
            transaction.incrby(key, cost)
            transaction.expireat(key, expiry)
        transaction.execute()
    return Decimal(cost) / NANODOLLARS
