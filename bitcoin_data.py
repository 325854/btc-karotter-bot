from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple

import httpx


@dataclass
class BitcoinSnapshot:
    price: float
    change_24h: float
    points: List[Tuple[float, float]]
    vs_currency: str
    fetched_at: datetime


async def fetch_bitcoin_snapshot(vs_currency: str = "usd") -> BitcoinSnapshot:
    headers = {"User-Agent": "btc-karotter-bot/1.0"}
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        price_resp = await client.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": "bitcoin",
                "vs_currencies": vs_currency,
                "include_24hr_change": "true",
                "include_last_updated_at": "true",
            },
        )
        price_resp.raise_for_status()
        price_data = price_resp.json()["bitcoin"]

        chart_resp = await client.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
            params={
                "vs_currency": vs_currency,
                "days": "1",
                "interval": "hourly",
            },
        )
        chart_resp.raise_for_status()
        chart_data = chart_resp.json()

    points = chart_data.get("prices", [])
    fetched_at = datetime.utcfromtimestamp(price_data.get("last_updated_at") or 0)
    return BitcoinSnapshot(
        price=float(price_data[vs_currency]),
        change_24h=float(price_data.get(f"{vs_currency}_24h_change") or 0.0),
        points=[(float(ts), float(price)) for ts, price in points],
        vs_currency=vs_currency,
        fetched_at=fetched_at,
    )
