from __future__ import annotations

import argparse
import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from bitcoin_data import fetch_bitcoin_snapshot
from karotter_client import KarotterClient
from render_chart import render_btc_chart


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_post_text(price: float, change_24h: float, vs_currency: str, now_local: datetime) -> str:
    symbol = "$" if vs_currency.lower() == "usd" else ("¥" if vs_currency.lower() == "jpy" else f"{vs_currency.upper()} ")
    arrow = "📈" if change_24h >= 0 else "📉"
    sign = "+" if change_24h >= 0 else ""
    return (
        f"₿ Bitcoin 定点報告 {now_local:%Y-%m-%d %H:%M}\n"
        f"現在価格: {symbol}{price:,.2f}\n"
        f"24時間変動: {arrow} {sign}{change_24h:.2f}%\n"
        f"#BTC #Bitcoin"
    )


async def post_once() -> None:
    load_dotenv()

    username = os.getenv("KAROTTER_USERNAME", "")
    password = os.getenv("KAROTTER_PASSWORD", "")
    if not username or not password:
        raise RuntimeError("KAROTTER_USERNAME と KAROTTER_PASSWORD を設定してください。")

    vs_currency = os.getenv("BTC_VS_CURRENCY", "usd")
    tz_name = os.getenv("TZ", "Asia/Tokyo")
    visibility = os.getenv("KAROTTER_VISIBILITY", "PUBLIC")
    reply_restriction = os.getenv("KAROTTER_REPLY_RESTRICTION", "EVERYONE")
    post_with_image = env_bool("POST_WITH_IMAGE", True)
    dry_run = env_bool("DRY_RUN", False)

    snapshot = await fetch_bitcoin_snapshot(vs_currency=vs_currency)
    now_local = datetime.now(ZoneInfo(tz_name))
    text = build_post_text(snapshot.price, snapshot.change_24h, snapshot.vs_currency, now_local)

    image_path = None
    if post_with_image and snapshot.points:
        tmp_dir = tempfile.mkdtemp(prefix="btc_chart_")
        image_path = render_btc_chart(
            points=snapshot.points,
            current_price=snapshot.price,
            change_24h=snapshot.change_24h,
            vs_currency=snapshot.vs_currency,
            output_path=os.path.join(tmp_dir, "btc_24h.png"),
        )

    if dry_run:
        print("[DRY RUN] post body:\n")
        print(text)
        if image_path:
            print(f"\n[DRY RUN] image: {image_path}")
        return

    async with KarotterClient(
        username=username,
        password=password,
        client_type=os.getenv("KAROTTER_CLIENT_TYPE", "web"),
        device_name=os.getenv("KAROTTER_DEVICE_NAME", "Chrome on Linux"),
    ) as client:
        await client.login()
        if image_path:
            try:
                resp = await client.create_post(
                    content=text,
                    image_path=image_path,
                    image_alt="Bitcoin 24 hour price chart",
                    visibility=visibility,
                    reply_restriction=reply_restriction,
                )
                print(f"Posted with image: {resp}")
                return
            except Exception as exc:
                print(f"Image post failed, retrying text-only: {exc}")

        resp = await client.create_post(
            content=text,
            visibility=visibility,
            reply_restriction=reply_restriction,
        )
        print(f"Posted text-only: {resp}")


async def run_forever() -> None:
    while True:
        now = datetime.now()
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        sleep_seconds = (next_hour - now).total_seconds()
        print(f"Sleeping until next hour: {next_hour.isoformat()}")
        await asyncio.sleep(sleep_seconds)
        try:
            await post_once()
        except Exception as exc:
            print(f"Posting failed: {exc}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run a single post immediately")
    return parser.parse_args()


async def amain():
    args = parse_args()
    if args.once:
        await post_once()
    else:
        await run_forever()


if __name__ == "__main__":
    asyncio.run(amain())
