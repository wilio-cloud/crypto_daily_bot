"""Integration tests for FastAPI endpoints.
"""

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import pytest
from server import app
from config import settings


@pytest.fixture
def client():
    return TestClient(app)


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["bot"] == "Crypto Daily Trading Bot"


def test_webhook_unauthorized(client):
    payload = {
        "secret": "invalid_secret_xyz",
        "ticker": "SOLUSDT.P",
        "price": 80.0,
        "action": "BUY"
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 401


@patch("server.risk_manager.evaluate_buy_signal")
@patch("server.okx_service.execute_market_buy")
@patch("server.send_telegram_message")
def test_webhook_successful_buy(mock_tg, mock_buy, mock_eval, client):
    # Mock risk approval
    decision = MagicMock()
    decision.allowed = True
    decision.target_amount = 1.5
    decision.capital_allocated_usd = 71.42
    decision.current_price = 80.0
    decision.active_positions_count = 3
    mock_eval.return_value = decision

    # Mock OKX order execution
    mock_buy.return_value = {
        "id": "123456789",
        "price": 80.0,
        "amount": 1.5
    }

    payload = {
        "secret": settings.webhook_secret,
        "ticker": "SOLUSDT.P",
        "price": 80.0,
        "action": "BUY"
    }

    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["order_id"] == "123456789"
    assert data["amount"] == 1.5


@patch("server.risk_manager.evaluate_buy_signal")
@patch("server.send_telegram_message")
def test_webhook_skipped_buy(mock_tg, mock_eval, client):
    # Mock risk rejection (duplicate)
    decision = MagicMock()
    decision.allowed = False
    decision.reason = "Crypto SOL ja té una posició oberta a OKX."
    decision.active_positions_count = 4
    mock_eval.return_value = decision

    payload = {
        "secret": settings.webhook_secret,
        "ticker": "SOLUSDT.P",
        "price": 80.0,
        "action": "BUY"
    }

    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "skipped"
    assert "ja té una posició oberta" in data["reason"]
