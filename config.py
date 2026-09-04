"""Configuration module for crypto_daily_bot.
Loads settings from environment variables and .env file.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # OKX Credentials
    okx_api_key: str = Field(default="", alias="OKX_API_KEY")
    okx_secret_key: str = Field(default="", alias="OKX_SECRET_KEY")
    okx_passphrase: str = Field(default="", alias="OKX_PASSPHRASE")
    okx_is_demo: bool = Field(default=False, alias="OKX_IS_DEMO")
    okx_subaccount_name: Optional[str] = Field(default=None, alias="OKX_SUBACCOUNT_NAME")
    okx_hostname: str = Field(default="my.okx.com", alias="OKX_HOSTNAME")

    # Strategy & Risk Configuration
    instrument_type: str = Field(default="SPOT", alias="INSTRUMENT_TYPE")  # "SWAP" or "SPOT"
    quote_currency: str = Field(default="USDC", alias="QUOTE_CURRENCY")    # "USDC" or "USDT"
    max_open_positions: int = Field(default=11, alias="MAX_OPEN_POSITIONS")
    capital_slots: int = Field(default=11, alias="CAPITAL_SLOTS")
    leverage: int = Field(default=2, alias="LEVERAGE")
    margin_mode: str = Field(default="isolated", alias="MARGIN_MODE")  # "isolated" or "cross"
    fallback_equity_usdt: float = Field(default=1000.0, alias="FALLBACK_EQUITY_USDT")
    safety_reserve_pct: float = Field(default=5.0, alias="SAFETY_RESERVE_PCT")
    risk_per_trade_pct: float = Field(default=2.0, alias="RISK_PER_TRADE_PCT")  # Exact 2% risk per trade
    risk_mode: str = Field(default="STRICT_2_PCT", alias="RISK_MODE")            # "STRICT_2_PCT" or "SLOT_BALANCED"
    max_position_equity_pct: float = Field(default=20.0, alias="MAX_POSITION_EQUITY_PCT")  # Max cap per trade (20% of account)

    # Security
    webhook_secret: str = Field(default="secret_token_123", alias="WEBHOOK_SECRET")

    # Telegram
    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(default=None, alias="TELEGRAM_CHAT_ID")

    # Server
    server_host: str = Field(default="0.0.0.0", alias="SERVER_HOST")
    server_port: int = Field(default=8000, validation_alias=AliasChoices("PORT", "SERVER_PORT"))


settings = Settings()
