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
    parser.add_argument("ticker", help="Crypto a comprar o tancar (ex: GALA, SOL, BTC, XRP)")
    parser.add_argument("--close", "--sell", action="store_true", help="Tanca la posició oberta a mercat i cancel·la ordres OCO")
    parser.add_argument("--limit", type=float, default=None, help="Preu d'ordre límit (opcional, per defecte a mercat)")
    parser.add_argument("--sl", type=float, default=None, help="Preu de Stop Loss (ex: 0.0015)")
    parser.add_argument("--tp", type=float, default=None, help="Preu de Take Profit (opcional)")
    parser.add_argument("--yes", "-y", action="store_true", help="Executa sense demanar confirmació")

    args = parser.parse_args()

    # 1. Normalize Symbol
    symbol_info = normalize_symbol(args.ticker, settings.instrument_type)
    ccxt_symbol = symbol_info["ccxt_symbol"]

    # Close Position Flow
    if args.close:
        print("=" * 60)
        print(f"🔴 TANCAMENT DE POSICIÓ A MERCAT: {symbol_info['base']}")
        print("=" * 60)
        print(f"Símbol OKX: {ccxt_symbol} ({symbol_info['okx_id']})")
        if not args.yes:
            confirm = input(f"\nVols cancel·lar els SL/TP i vendre tot {symbol_info['base']} a mercat? (s/n): ").strip().lower()
            if confirm not in ['s', 'si', 'y', 'yes']:
                print("❌ Operació cancel·lada.")
                return

        try:
            print(f"Cancel·lant OCOs i executant ordre de venda a OKX...")
            res = okx_service.close_position(ccxt_symbol)
            print("\n🎉 POSICIÓ TANCADA AMB ÈXIT!")
            print(f"• Order ID: {res.get('id')}")
            print(f"• Quantitat: {res.get('amount')}")
            print(f"• Preu: ${res.get('price') or 'Mercat'}")
            return
        except Exception as e:
            print(f"\n❌ Error tancant la posició: {e}")
            return

    print("=" * 60)
    print("🚀 EXECUCIÓ DE COMPRA MANUAL AMB GESTIÓ DE RISC")
    print("=" * 60)
    print(f"• Mode: {'DEMO' if settings.okx_is_demo else 'REAL'}")
    print(f"• Mercat: {settings.instrument_type}")
    print(f"• Slots de capital: {settings.capital_slots} cryptos (1/{settings.capital_slots} per trade)")
    print(f"• Crypto: {args.ticker.upper()}")
    if args.limit:
        print(f"• Tipus d'ordre: LÍMIT a ${args.limit}")
    else:
        print(f"• Tipus d'ordre: MERCAT")
    if args.sl:
        print(f"• Stop Loss (SL): {args.sl}")
    if args.tp:
        print(f"• Take Profit (TP): {args.tp}")
    print("-" * 60)
    print(f"Símbol OKX normalitzat: {ccxt_symbol} ({symbol_info['okx_id']})")

    # 2. Risk Evaluation & Sizing
    risk_manager = RiskManager(okx_service)
    decision = risk_manager.evaluate_buy_signal(symbol_info, alert_price=args.limit, sl_price=args.sl)

    if not decision.allowed:
        print(f"\n❌ L'ordre ha estat REBUTJADA pel motor de risc:")
        print(f"Motiu: {decision.reason}")
        return

    print("\n📊 Resum del càlcul de posició:")
    print(f"• Equity Total del Compte: ${decision.equity_usd:,.2f} {settings.quote_currency}")
    print(f"• Capital assignat: ${decision.capital_allocated_usd:,.2f} {settings.quote_currency}")
    print(f"• Preu de referència: ${decision.current_price:,.6f}")
    print(f"• Quantitat a enviar a OKX: {decision.target_amount} contractes / unitats")
    if args.sl:
        dist = ((decision.current_price - args.sl) / decision.current_price) * 100
        risk_at_sl = decision.capital_allocated_usd * (dist / 100.0)
        print(f"• Distància fins al Stop Loss: {dist:.2f}% de caiguda")
        print(f"• Risc monetari si toca SL: ${risk_at_sl:,.2f} ({risk_at_sl / decision.equity_usd * 100:.1f}% de la cartera)")
    if args.tp:
        gain = ((args.tp - decision.current_price) / decision.current_price) * 100
        profit_at_tp = decision.capital_allocated_usd * (gain / 100.0)
        print(f"• Distància fins al Take Profit: +{gain:.2f}% de pujada")
        print(f"• Benefici si toca TP: +${profit_at_tp:,.2f}")
        if args.sl and dist > 0:
            rr = gain / dist
            print(f"• Ràtio Risc / Benefici (R:R): 1 : {rr:.2f}")

    # 3. Confirmation
    if not args.yes:
        action_desc = f"ordre LÍMIT a ${args.limit}" if args.limit else "ordre a MERCAT"
        confirm = input(f"\nVols enviar aquesta {action_desc} a OKX ara mateix? (s/n): ").strip().lower()
        if confirm not in ['s', 'si', 'y', 'yes']:
            print("❌ Operació cancel·lada per l'usuari.")
            return

    # 4. Execution
    try:
        if args.limit:
            print(f"\nEnviant ordre LÍMIT de compra a OKX a ${args.limit}...")
            order = okx_service.execute_limit_buy(
                ccxt_symbol=ccxt_symbol,
                amount=decision.target_amount,
                price=args.limit,
                sl_price=args.sl,
                tp_price=args.tp
            )
            print("\n🎉 ORDRE LÍMIT REGISTRADA AL LLIBRE D'OKX!")
            print(f"• Order ID: {order.get('id')}")
            print(f"• Quantitat: {order.get('amount') or decision.target_amount} {symbol_info['base']}")
            print(f"• Preu límit: ${args.limit}")
            if args.sl:
                print(f"• Stop Loss vinculat a: {args.sl} (s'activarà en omplir-se)")
            if args.tp:
                print(f"• Take Profit vinculat a: {args.tp} (s'activarà en omplir-se)")
        else:
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
