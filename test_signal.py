"""Helper CLI script to simulate and test a TradingView webhook alert locally.
Usage:
    python test_signal.py [TICKER] [PRICE]
Example:
    python test_signal.py SOLUSDT.P 75.13
"""

import sys
import httpx
from config import settings


def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else "SOLUSDT.P"
    price = float(sys.argv[2]) if len(sys.argv) > 2 else 75.13

    url = f"http://127.0.0.1:{settings.server_port}/webhook"
    payload = {
        "secret": settings.webhook_secret,
        "ticker": ticker,
        "price": price,
        "action": "BUY"
    }

    print(f"📡 Enviant alerta simulada a {url}:")
    print(f"Payload: {payload}")

    try:
        response = httpx.post(url, json=payload, timeout=10.0)
        print(f"\nStatus Code: {response.status_code}")
        print("Resposta del Servidor:")
        print(response.json())
    except Exception as e:
        print(f"❌ Error connectant amb el servidor: {e}")
        print("Assegura't que el bot està funcionant amb: python server.py")


if __name__ == "__main__":
    main()
