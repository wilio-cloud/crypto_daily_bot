"""Diagnostic script to test your OKX API connection and credentials.
Usage:
    ./venv/bin/python check_okx.py
"""

from config import settings
from okx_service import okx_service


def main():
    print("=" * 50)
    print("🔍 COMPROVACIÓ DE CONNEXIÓ AMB OKX")
    print("=" * 50)
    print(f"• Mode: {'DEMO / SIMULACIÓ' if settings.okx_is_demo else 'REAL (Producció)'}")
    print(f"• Tipus d'Instrument: {settings.instrument_type}")
    print(f"• Slots configurats: {settings.capital_slots} cryptos")
    print(f"• API Key: {settings.okx_api_key[:6]}...{settings.okx_api_key[-4:] if len(settings.okx_api_key) > 10 else ''}")
    print("-" * 50)

    if not settings.okx_api_key or not settings.okx_secret_key:
        print("❌ ERROR: No s'ha trobat l'API Key o el Secret Key al fitxer .env!")
        print("Edita el fitxer .env i posa-hi les teves credencials d'OKX.")
        return

    try:
        print("1. Carregant mercats d'OKX...")
        okx_service.load_markets()
        print("   ✅ Mercats carregats correctament.")

        print("2. Consultant balanç d'equity...")
        equity = okx_service.get_total_equity()
        print(f"   ✅ Balanç Total (Equity): ${equity:,.2f} USDT")

        slot_capital = equity / settings.capital_slots
        print(f"   📊 Capital per cada trade (1/{settings.capital_slots}): ${slot_capital:,.2f} USDT")

        print("3. Consultant posicions obertes...")
        positions = okx_service.get_open_positions()
        print(f"   ✅ Posicions actualment actives ({len(positions)}/{settings.max_open_positions}): {list(positions)}")

        print("\n🎉 TOT CORRECTE! Les teves credencials d'OKX funcionen perfectament.")
        print("Ja pots arrencar el bot amb: ./venv/bin/python server.py")

    except Exception as e:
        print(f"\n❌ Error connectant amb OKX: {e}")
        print("\nRevisa que:")
        print("1. L'API Key, Secret Key i Passphrase siguin exactes.")
        print("2. Si estàs en compte Real, posa OKX_IS_DEMO=false al .env.")
        print("3. Si les claus pertanyen a un subcompte, assegura't que tinguin permís de 'Read' i 'Trade'.")


if __name__ == "__main__":
    main()
