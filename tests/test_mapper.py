"""Unit tests for symbol_mapper.py.
"""

from symbol_mapper import extract_base_and_quote, normalize_symbol


def test_extract_base_and_quote():
    assert extract_base_and_quote("SOLUSDT") == ("SOL", "USDT")
    assert extract_base_and_quote("SOLUSDT.P") == ("SOL", "USDT")
    assert extract_base_and_quote("BINANCE:SOLUSDT.P") == ("SOL", "USDT")
    assert extract_base_and_quote("OKX:SOL-USDT-SWAP") == ("SOL", "USDT")
    assert extract_base_and_quote("BTC/USDT") == ("BTC", "USDT")
    assert extract_base_and_quote("AVAX_USDT") == ("AVAX", "USDT")
    assert extract_base_and_quote("ETHUSDC") == ("ETH", "USDC")


def test_normalize_symbol_swap():
    res = normalize_symbol("BINANCE:SOLUSDT.P", instrument_type="SWAP", target_quote="USDT")
    assert res["base"] == "SOL"
    assert res["quote"] == "USDT"
    assert res["ccxt_symbol"] == "SOL/USDT:USDT"
    assert res["okx_id"] == "SOL-USDT-SWAP"
    assert res["instrument_type"] == "SWAP"


def test_normalize_symbol_spot():
    res = normalize_symbol("BINANCE:SOLUSDT", instrument_type="SPOT", target_quote="USDC")
    assert res["base"] == "SOL"
    assert res["quote"] == "USDC"
    assert res["ccxt_symbol"] == "SOL/USDC"
    assert res["okx_id"] == "SOL-USDC"
    assert res["instrument_type"] == "SPOT"
