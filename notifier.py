"""Notification module to send status updates and reminders to Telegram.
"""

import logging
from typing import Optional
import httpx
from config import settings

logger = logging.getLogger("crypto_bot.notifier")


async def send_telegram_message(message: str) -> bool:
    """Send a markdown-formatted message to Telegram channel or chat."""
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    if not token or not chat_id:
        logger.info(f"[TELEGRAM DISABLED] {message}")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                logger.info("Telegram notification sent successfully.")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        return False


async def notify_trade_executed(
    ticker: str,
    base: str,
    side: str,
    price: float,
    amount: float,
    capital_allocated: float,
    instrument_type: str,
    active_positions_count: int,
    max_positions: int,
    sl_price: Optional[float] = None,
    tp_price: Optional[float] = None,
    algo_placed: bool = False
):
    """Notify when a trade is successfully opened on OKX."""
    lines = [
        f"🟢 *ORDRE EXECUTADA A OKX*",
        f"━━━━━━━━━━━━━━━━━━━",
        f"• *Actiu:* `{ticker}` ({base})",
        f"• *Operació:* `{side.upper()}` ({instrument_type})",
        f"• *Preu Execució:* `${price:,.4f}`",
        f"• *Quantitat:* `{amount}`",
        f"• *Capital Invertit:* `${capital_allocated:,.2f} {settings.quote_currency}`",
        f"• *Posicions Actives:* `{active_positions_count}/{max_positions}`",
    ]

    if sl_price:
        dist = abs((price - sl_price) / price) * 100
        risk_usd = capital_allocated * (dist / 100.0)
        lines.append(f"• *Stop Loss (SL):* `${sl_price:,.4f}` (-{dist:.2f}%)")
        lines.append(f"• *Risc a SL:* `${risk_usd:,.2f}` (~2.0% del compte)")
    if tp_price:
        gain = abs((tp_price - price) / price) * 100
        lines.append(f"• *Take Profit (TP):* `${tp_price:,.4f}` (+{gain:.2f}%)")

    lines.append(f"━━━━━━━━━━━━━━━━━━━")

    if algo_placed:
        lines.append(f"🛡️ *Protecció:* Ordre OCO (SL + TP) activada automàticament a OKX.")
    elif sl_price or tp_price:
        lines.append(f"⚠️ *Nota:* Comprova a OKX que l'ordre bracket SL/TP s'hagi registrat.")
    else:
        lines.append(f"⚠️ *ATENCIÓ:* Entra a OKX per col·locar manualment el Stop Loss (SL) i Take Profit (TP).")

    msg = "\n".join(lines)
    logger.info(msg)
    await send_telegram_message(msg)


async def notify_trade_skipped(ticker: str, reason: str):
    """Notify when a trade signal is skipped."""
    msg = (
        f"⚠️ *SENYAL IGNORADA PER A {ticker}*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"• *Motiu:* {reason}\n"
    )
    logger.warning(msg)
    await send_telegram_message(msg)
