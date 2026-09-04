"""FastAPI Webhook Server for TradingView -> OKX automated orders.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, Field
import uvicorn

from config import settings
from symbol_mapper import normalize_symbol
from okx_service import okx_service
from risk_manager import RiskManager
from notifier import notify_trade_executed, notify_trade_skipped, send_telegram_message

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("crypto_bot.server")

risk_manager = RiskManager(okx_service)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("==========================================")
    logger.info("Starting Crypto Daily Trading Bot")
    logger.info(f"Mode: {'DEMO / SANDBOX' if settings.okx_is_demo else 'REAL PRODUCTION'}")
    logger.info(f"Instrument Type: {settings.instrument_type}")
    logger.info(f"Max Concurrent Positions: {settings.max_open_positions}")
    logger.info(f"Capital Allocation Slots: {settings.capital_slots}")
    logger.info("==========================================")
    
    # Preload OKX markets in background
    try:
        okx_service.load_markets()
    except Exception as e:
        logger.warning(f"Could not preload markets on startup: {e}")

    await send_telegram_message(
        f"🚀 *Crypto Daily Bot Iniciat*\n"
        f"• Mode: `{'DEMO (Paper Trading)' if settings.okx_is_demo else 'REAL'}`\n"
        f"• Mercat: `{settings.instrument_type}`\n"
        f"• Slots màxims: `{settings.max_open_positions}` cryptos"
    )
    yield
    logger.info("Shutting down Crypto Daily Bot...")


app = FastAPI(
    title="Crypto Daily Trading Bot (TradingView -> OKX)",
    version="1.0.0",
    lifespan=lifespan
)


class WebhookPayload(BaseModel):
    secret: str = Field(..., description="Secret authentication token")
    ticker: str = Field(..., description="TradingView ticker e.g. SOLUSDT, SOLUSDT.P")
    price: Optional[float] = Field(default=None, description="Current price from {{close}}")
    action: str = Field(default="BUY", description="Action to perform (BUY)")
    sl: Optional[float] = Field(default=None, description="Stop Loss trigger price")
    tp: Optional[float] = Field(default=None, description="Take Profit trigger price")


@app.get("/")
def read_root():
    return {
        "status": "online",
        "bot": "Crypto Daily Trading Bot",
        "instrument_type": settings.instrument_type,
        "is_demo": settings.okx_is_demo,
        "max_positions": settings.max_open_positions
    }


@app.get("/health")
def health_check():
    equity = okx_service.get_total_equity()
    open_positions = list(okx_service.get_open_positions())
    return {
        "status": "healthy",
        "equity_usdt": equity,
        "active_positions_count": len(open_positions),
        "max_positions": settings.max_open_positions,
        "active_positions": open_positions
    }


@app.post("/webhook")
async def handle_webhook(payload: WebhookPayload, request: Request):
    logger.info(f"Received webhook payload: ticker={payload.ticker}, action={payload.action}, price={payload.price}")

    # 1. Security Check
    if payload.secret != settings.webhook_secret:
        logger.warning("Rejected webhook request: Invalid secret token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Secret token does not match."
        )

    # 2. Action Check (Currently focused on BUY signals)
    if payload.action.upper() != "BUY":
        logger.info(f"Action '{payload.action}' is not BUY. Skipping.")
        return {"status": "ignored", "reason": f"Action {payload.action} not supported in current phase."}

    # 3. Normalize ticker
    symbol_info = normalize_symbol(payload.ticker, settings.instrument_type)
    logger.info(f"Normalized symbol: {symbol_info}")

    # 4. Evaluate Risk & Sizing (11 slots guarantee and 2% risk if SL present)
    decision = risk_manager.evaluate_buy_signal(
        symbol_info,
        alert_price=payload.price,
        sl_price=payload.sl
    )

    if not decision.allowed:
        await notify_trade_skipped(payload.ticker, decision.reason)
        return {
            "status": "skipped",
            "reason": decision.reason,
            "ticker": payload.ticker,
            "active_positions": decision.active_positions_count
        }

    # 5. Execute Order on OKX
    try:
        order_result = okx_service.execute_market_buy(
            ccxt_symbol=symbol_info["ccxt_symbol"],
            amount=decision.target_amount,
            price_hint=decision.current_price,
            sl_price=payload.sl,
            tp_price=payload.tp
        )
        
        exec_price = float(order_result.get('price') or decision.current_price)
        filled_amount = float(order_result.get('amount') or decision.target_amount)

        algo_placed = bool(order_result.get('algo_order') or (order_result.get('info', {}).get('attachAlgoOrds')))
        # 6. Notify via Telegram and Console with SL/TP status
        await notify_trade_executed(
            ticker=symbol_info["ccxt_symbol"],
            base=symbol_info["base"],
            side="BUY",
            price=exec_price,
            amount=filled_amount,
            capital_allocated=decision.capital_allocated_usd,
            instrument_type=symbol_info["instrument_type"],
            active_positions_count=decision.active_positions_count + 1,
            max_positions=settings.max_open_positions,
            sl_price=payload.sl,
            tp_price=payload.tp,
            algo_placed=algo_placed
        )

        return {
            "status": "success",
            "order_id": order_result.get('id'),
            "symbol": symbol_info["ccxt_symbol"],
            "amount": filled_amount,
            "price": exec_price,
            "capital_allocated_usd": decision.capital_allocated_usd
        }

    except Exception as e:
        err_msg = f"Error executing order on OKX for {symbol_info['ccxt_symbol']}: {str(e)}"
        logger.exception(err_msg)
        await notify_trade_skipped(payload.ticker, f"Error d'execució OKX: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=err_msg
        )


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=False
    )
