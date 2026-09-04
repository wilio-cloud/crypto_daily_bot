"""Script to manually execute a trade on OKX with risk management and automatic SL/TP brackets.
Usage:
    ./venv/bin/python manual_trade.py [TICKER] [--sl STOP_LOSS] [--tp TAKE_PROFIT]

Example:
    ./venv/bin/python manual_trade.py GALA --sl 0.0015
"""

import sys
import argparse
from symbol_mapper import normalize_symbol
from okx_service import okx_service
from risk_manager import RiskManager
from config import settings


def main():
    parser = argparse.ArgumentParser(description="Executa una compra manual amb gestió de risc a OKX.")
    parser.add_argument("ticker", help="Crypto a comprar (ex: GALA, SOL, BTC)")
    parser.add_argument("--sl", type=float, default=None, help="Preu de Stop Loss (ex: 0.0015)")
    parser.add_argument("--tp", type=float, default=None, help="Preu de Take Profit (opcional)")
    parser.add_argument("--yes", "-y", action="store_true", help="Executa sense demanar confirmació")

    args = parser.parse_args()

    print("=" * 60)
    print("🚀 EXECUCIÓ DE COMPRA MANUAL AMB GESTIÓ DE RISC")
    print("=" * 60)
    print(f"• Mode: {'DEMO' if settings.okx_is_demo else 'REAL'}")
    print(f"• Mercat: {settings.instrument_type}")
    print(f"• Slots de capital: {settings.capital_slots} cryptos (1/{settings.capital_slots} per trade)")
    print(f"• Crypto: {args.ticker.upper()}")
    if args.sl:
        print(f"• Stop Loss (SL): {args.sl}")
    if args.tp:
        print(f"• Take Profit (TP): {args.tp}")
    print("-" * 60)

    # 1. Normalize Symbol
    symbol_info = normalize_symbol(args.ticker, settings.instrument_type)
    ccxt_symbol = symbol_info["ccxt_symbol"]
    print(f"Símbol OKX normalitzat: {ccxt_symbol} ({symbol_info['okx_id']})")

    # 2. Risk Evaluation & Sizing
    risk_manager = RiskManager(okx_service)
    decision = risk_manager.evaluate_buy_signal(symbol_info, sl_price=args.sl)

    if not decision.allowed:
        print(f"\n❌ L'ordre ha estat REBUTJADA pel motor de risc:")
        print(f"Motiu: {decision.reason}")
        return

    print("\n📊 Resum del càlcul de posició:")
    print(f"• Equity Total del Compte: ${decision.equity_usd:,.2f} {settings.quote_currency}")
    print(f"• Capital assignat: ${decision.capital_allocated_usd:,.2f} {settings.quote_currency}")
    print(f"• Preu actual de mercat: ${decision.current_price:,.6f}")
    print(f"• Quantitat a enviar a OKX: {decision.target_amount} contractes / unitats")
    if args.sl:
        dist = ((decision.current_price - args.sl) / decision.current_price) * 100
        risk_at_sl = decision.capital_allocated_usd * (dist / 100.0)
        print(f"• Distància fins al Stop Loss: {dist:.2f}% de caiguda")
        print(f"• Risc monetari si toca SL: ${risk_at_sl:,.2f} ({risk_at_sl / decision.equity_usd * 100:.1f}% de la cartera)")

    # 3. Confirmation
    if not args.yes:
        confirm = input("\nVols enviar aquesta ordre a OKX ara mateix? (s/n): ").strip().lower()
        if confirm not in ['s', 'si', 'y', 'yes']:
            print("❌ Operació cancel·lada per l'usuari.")
            return

    # 4. Execution
    try:
        print(f"\nEnviant ordre de compra a OKX...")
        order = okx_service.execute_market_buy(
            ccxt_symbol=ccxt_symbol,
            amount=decision.target_amount,
            price_hint=decision.current_price,
            sl_price=args.sl,
            tp_price=args.tp
        )
        print("\n🎉 ORDRE EXECUTADA AMB ÈXIT!")
        print(f"• Order ID: {order.get('id')}")
        print(f"• Quantitat: {order.get('amount') or decision.target_amount}")
        print(f"• Preu promig: ${order.get('price') or decision.current_price}")
        if args.sl:
            print(f"• Stop Loss col·locat a: {args.sl}")
        if args.tp:
            print(f"• Take Profit col·locat a: {args.tp}")

    except Exception as e:
        print(f"\n❌ ERROR d'execució a OKX: {e}")


if __name__ == "__main__":
    main()
