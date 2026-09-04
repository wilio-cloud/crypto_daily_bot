"""Unit tests for risk_manager.py.
"""

from unittest.mock import MagicMock
import pytest
from risk_manager import RiskManager
from symbol_mapper import normalize_symbol


@pytest.fixture
def mock_okx():
    mock = MagicMock()
    mock.get_total_equity.return_value = 1000.0
    mock.get_free_balance.return_value = 1000.0
    mock.get_open_positions.return_value = set()
    mock.get_current_price.return_value = 50.0
    mock.load_markets.return_value = None
    mock.exchange.market.return_value = {
        'contract': False,
        'limits': {'amount': {'min': 0.01}}
    }
    return mock


def test_slot_capital_division(mock_okx):
    rm = RiskManager(mock_okx)
    rm.safety_reserve_pct = 0.0  # 100% usable
    rm.capital_slots = 11
    rm.max_positions = 11
    rm.leverage = 1

    sym_info = normalize_symbol("SOLUSDT", instrument_type="SPOT")
    decision = rm.evaluate_buy_signal(sym_info, alert_price=50.0)

    assert decision.allowed is True
    # 1000 / 11 = 90.909 USDT per slot
    expected_capital = 1000.0 / 11
    assert pytest.approx(decision.capital_allocated_usd, 0.01) == expected_capital
    # Units = 90.909 / 50.0 = 1.818
    assert pytest.approx(decision.target_amount, 0.01) == (expected_capital / 50.0)


def test_reject_duplicate_position(mock_okx):
    # SOL is already active
    mock_okx.get_open_positions.return_value = {"SOL", "BTC"}
    rm = RiskManager(mock_okx)

    sym_info = normalize_symbol("SOLUSDT", instrument_type="SPOT")
    decision = rm.evaluate_buy_signal(sym_info, alert_price=50.0)

    assert decision.allowed is False
    assert "ja té una posició oberta" in decision.reason


def test_reject_max_11_positions(mock_okx):
    # Already 11 positions open
    mock_okx.get_open_positions.return_value = {f"COIN_{i}" for i in range(11)}
    rm = RiskManager(mock_okx)
    rm.max_positions = 11

    sym_info = normalize_symbol("NEWCOINUSDT", instrument_type="SPOT")
    decision = rm.evaluate_buy_signal(sym_info, alert_price=10.0)

    assert decision.allowed is False
    assert "límit màxim de 11 posicions" in decision.reason


def test_leverage_in_swap(mock_okx):
    rm = RiskManager(mock_okx)
    rm.safety_reserve_pct = 0.0
    rm.capital_slots = 11
    rm.leverage = 2

    sym_info = normalize_symbol("SOLUSDT.P", instrument_type="SWAP")
    decision = rm.evaluate_buy_signal(sym_info, alert_price=100.0)

    assert decision.allowed is True
    # Capital margin allocated is 1000/11 = 90.909
    # Notional size with 2x leverage = 90.909 * 2 = 181.818
    # At $100 price, units = 1.818
    assert pytest.approx(decision.target_amount, 0.01) == (1000.0 / 11 * 2) / 100.0


def test_strict_2_pct_risk(mock_okx):
    rm = RiskManager(mock_okx)
    sym_info = normalize_symbol("SOLUSDT", instrument_type="SPOT", target_quote="USDC")
    # Entry at 100, SL at 90 (10% drop). 2% risk of $1000 = $20.
    # Required position size: $20 / 0.10 = $200.
    decision = rm.evaluate_buy_signal(sym_info, alert_price=100.0, sl_price=90.0)
    assert decision.allowed is True
    # Target notional should be $200
    assert pytest.approx(decision.target_amount, 0.01) == 2.0  # 2.0 SOL at $100 = $200
    assert pytest.approx(decision.capital_allocated_usd, 0.01) == 200.0
    # If SL is hit at $90: loss = 2.0 * (100 - 90) = $20 (exact 2% of $1000!)


def test_liquidity_cap_and_rejection(mock_okx):
    rm = RiskManager(mock_okx)
    sym_info = normalize_symbol("SOLUSDT", instrument_type="SPOT", target_quote="USDC")

    # Case 1: Free balance is only $100 (less than ideal $200) -> should cap to ~$99.50
    mock_okx.get_free_balance.return_value = 100.0
    decision = rm.evaluate_buy_signal(sym_info, alert_price=100.0, sl_price=90.0)
    assert decision.allowed is True
    assert pytest.approx(decision.capital_allocated_usd, 0.1) == 99.5

    # Case 2: Free balance is near 0 (< $5) -> should reject
    mock_okx.get_free_balance.return_value = 2.0
    decision = rm.evaluate_buy_signal(sym_info, alert_price=100.0, sl_price=90.0)
    assert decision.allowed is False
    assert "insuficient" in decision.reason.lower()

