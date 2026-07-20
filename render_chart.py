from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


JPY_SYMBOL = "¥"
USD_SYMBOL = "$"


def currency_symbol(code: str) -> str:
    code = code.lower()
    if code == "usd":
        return USD_SYMBOL
    if code == "jpy":
        return JPY_SYMBOL
    return f"{code.upper()} "


def render_btc_chart(
    points: Iterable[Tuple[float, float]],
    current_price: float,
    change_24h: float,
    vs_currency: str,
    output_path: str,
) -> str:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    times = [datetime.utcfromtimestamp(ts / 1000) for ts, _ in points]
    prices = [price for _, price in points]
    symbol = currency_symbol(vs_currency)
    change_color = "#16a34a" if change_24h >= 0 else "#dc2626"

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 7), dpi=160)
    fig.patch.set_facecolor("#0b1220")
    ax.set_facecolor("#111827")

    ax.plot(times, prices, color="#f59e0b", linewidth=2.8)
    ax.fill_between(times, prices, color="#f59e0b", alpha=0.15)

    ax.set_title("Bitcoin 24H Price", fontsize=20, pad=18, color="white", weight="bold")
    ax.grid(True, alpha=0.18)
    ax.tick_params(colors="#cbd5e1")
    for spine in ax.spines.values():
        spine.set_color("#334155")

    fig.text(0.05, 0.91, f"Price: {symbol}{current_price:,.2f}", fontsize=18, color="white", weight="bold")
    fig.text(0.05, 0.865, f"24H Change: {change_24h:+.2f}%", fontsize=16, color=change_color, weight="bold")
    fig.text(0.05, 0.03, "Source: CoinGecko | Auto-posted by bot", fontsize=10, color="#94a3b8")

    plt.tight_layout(rect=(0, 0.05, 1, 0.88))
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return str(output)
