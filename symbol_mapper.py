"""Symbol mapping utility to normalize tickers from TradingView to OKX exchange formats.
Supports both SPOT and USDT-margined PERPETUAL SWAPS.
"""

import re
from typing import Dict, Optional


def extract_base_and_quote(raw_ticker: str) -> tuple[str, str]:
    """Extract base and quote assets from various TradingView ticker formats.
    
    Examples:
        - "SOLUSDT" -> ("SOL", "USDT")
        - "SOLUSDT.P" -> ("SOL", "USDT")
        - "BINANCE:SOLUSDT.P" -> ("SOL", "USDT")
        - "OKX:SOL-USDT-SWAP" -> ("SOL", "USDT")
        - "SOL/USDT" -> ("SOL", "USDT")
        - "BTC-USDT" -> ("BTC", "USDT")
    """
    clean = raw_ticker.strip().upper()
    
    # Remove exchange prefix if present (e.g. "BINANCE:", "OKX:")
    if ":" in clean:
        clean = clean.split(":")[-1]
        
    # Remove common derivatives suffixes
    clean = re.sub(r'(\.P|\.PERP|-SWAP|_PERP)$', '', clean)
    
    # Replace separators with slash
    clean = clean.replace('-', '/').replace('_', '/')
    
    if '/' in clean:
        parts = clean.split('/')
        return parts[0], parts[1]
        
    # If no separator, check for common quotes (USDT, USDC, USD)
    for quote in ["USDT", "USDC", "USD", "EUR"]:
        if clean.endswith(quote):
            base = clean[:-len(quote)]
            return base, quote
            
    # Fallback default quote to USDT
    return clean, "USDT"


def normalize_symbol(
    raw_ticker: str,
    instrument_type: str = "SPOT",
    target_quote: Optional[str] = None
) -> Dict[str, str]:
    """Convert raw TradingView ticker into normalized exchange formats.
    
    Returns a dictionary with:
        - 'base': Base coin (e.g. 'SOL')
        - 'quote': Quote currency (e.g. 'USDC' or 'USDT')
        - 'ccxt_symbol': Standard CCXT symbol (e.g. 'SOL/USDC' or 'SOL/USDT:USDT')
        - 'okx_id': Native OKX instrument ID (e.g. 'SOL-USDC' or 'SOL-USDT-SWAP')
    """
    from config import settings
    base, raw_quote = extract_base_and_quote(raw_ticker)
    inst_type = instrument_type.upper()
    quote = (target_quote or settings.quote_currency or raw_quote or "USDC").upper()
    
    if inst_type == "SWAP":
        return {
            "base": base,
            "quote": quote,
            "ccxt_symbol": f"{base}/{quote}:{quote}",
            "okx_id": f"{base}-{quote}-SWAP",
            "instrument_type": "SWAP"
        }
    else:  # SPOT
        return {
            "base": base,
            "quote": quote,
            "ccxt_symbol": f"{base}/{quote}",
            "okx_id": f"{base}-{quote}",
            "instrument_type": "SPOT"
        }
