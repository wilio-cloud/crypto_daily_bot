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
    max_positions: int
):
    """Notify when a trade is successfully opened on OKX."""
    msg = (
        f"🟢 *ORDRE EXECUTADA A OKX*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"• *Actiu:* `{ticker}` ({base})\n"
        f"• *Operació:* `{side.upper()}` ({instrument_type})\n"
        f"• *Preu Execució:* `${price:,.4f}`\n"
        f"• *Quantitat:* `{amount}`\n"
        f"• *Capital Assignat:* `${capital_allocated:,.2f} USDT`\n"
        f"• *Posicions Actives:* `{active_positions_count}/{max_positions}`\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ *ATENCIÓ:* Entra ara mateix al teu compte d'OKX per col·locar manualment el **Stop Loss (SL)** i el **Take Profit (TP)** segons la gràfica diària!"
    )
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
