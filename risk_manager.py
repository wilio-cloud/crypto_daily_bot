"""Risk and capital management engine.
Ensures portfolio is divided into 14 slots, prevents duplicates,
and calculates exact position sizes for SPOT and SWAP markets.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Set
from config import settings
from okx_service import OKXService

logger = logging.getLogger("crypto_bot.risk")


@dataclass
class TradeDecision:
    allowed: bool
    reason: str
    symbol_info: Optional[dict] = None
    target_amount: float = 0.0
    capital_allocated_usd: float = 0.0
    current_price: float = 0.0
    equity_usd: float = 0.0
    active_positions_count: int = 0


class RiskManager:
    def __init__(self, okx_service: OKXService):
        self.okx = okx_service
        self.max_positions = settings.max_open_positions
        self.capital_slots = settings.capital_slots
        self.leverage = settings.leverage
        self.safety_reserve_pct = settings.safety_reserve_pct

    def evaluate_buy_signal(
        self,
        symbol_info: dict,
        alert_price: Optional[float] = None,
        sl_price: Optional[float] = None
    ) -> TradeDecision:
        """Evaluate incoming BUY alert against portfolio risk limits."""
        base_asset = symbol_info["base"]
        ccxt_symbol = symbol_info["ccxt_symbol"]
        inst_type = symbol_info["instrument_type"]

        # 1. Fetch current open positions
        open_positions: Set[str] = self.okx.get_open_positions()
        active_count = len(open_positions)
        logger.info(f"Active positions ({active_count}/{self.max_positions}): {list(open_positions)}")

        # 2. Check duplicate trade
        if base_asset in open_positions:
            msg = f"Crypto {base_asset} ja té una posició oberta a OKX. Senyal ignorada."
            logger.warning(msg)
            return TradeDecision(
                allowed=False,
                reason=msg,
                symbol_info=symbol_info,
                active_positions_count=active_count
            )

        # 3. Check max concurrent positions limit
        if active_count >= self.max_positions:
            msg = f"S'ha assolit el límit màxim de {self.max_positions} posicions obertes simultànies."
            logger.warning(msg)
            return TradeDecision(
                allowed=False,
                reason=msg,
                symbol_info=symbol_info,
                active_positions_count=active_count
            )

        # 4. Fetch total account equity
        total_equity = self.okx.get_total_equity()
        if total_equity <= 0:
            msg = "El balanç d'equity del compte és 0 o inferior."
            logger.error(msg)
            return TradeDecision(
                allowed=False,
                reason=msg,
                symbol_info=symbol_info,
                active_positions_count=active_count
            )

        # 5. Calculate base capital per slot (Guaranteeing funds for all 11 cryptos)
        usable_equity = total_equity * (1.0 - (self.safety_reserve_pct / 100.0))
        capital_per_slot = usable_equity / self.capital_slots

        # 6. Fetch current market price
        price = alert_price or self.okx.get_current_price(ccxt_symbol)
        if not price or price <= 0:
            msg = f"No s'ha pogut obtenir un preu vàlid de mercat per a {ccxt_symbol}"
            logger.error(msg)
            return TradeDecision(
                allowed=False,
                reason=msg,
                symbol_info=symbol_info,
                active_positions_count=active_count
            )

        # 7. Calculate position sizing
        capital_per_slot = usable_equity / self.capital_slots

        if sl_price is not None and sl_price > 0 and sl_price < price:
            dist_pct = (price - sl_price) / price
            risk_usd = total_equity * (settings.risk_per_trade_pct / 100.0)  # Exactly 2% of total equity
            ideal_notional = risk_usd / dist_pct

            if settings.risk_mode == "STRICT_2_PCT":
                # In Strict 2% mode, calculate exact position size to lose exactly 2% at Stop Loss
                # Cap at max_position_equity_pct (e.g. max 20% of account = ~$200) to protect diversification
                max_trade_cap = total_equity * (settings.max_position_equity_pct / 100.0)
                target_notional_usd = min(ideal_notional, max_trade_cap)
                logger.info(
                    f"[STRICT 2% RISK] Price={price}, SL={sl_price}, Dist={dist_pct*100:.2f}%, "
                    f"Risk=${risk_usd:.2f} -> Sized at ${target_notional_usd:.2f}"
                )
            else:  # SLOT_BALANCED
                target_notional_usd = min(ideal_notional, capital_per_slot)
        else:
            # If no SL is provided, use guaranteed slot capital
            target_notional_usd = capital_per_slot

        if inst_type == "SWAP":
            target_notional_usd = target_notional_usd * self.leverage

        # Units of base cryptocurrency (e.g. 1.25 SOL)
        units = target_notional_usd / price

        # Convert to contracts if required by OKX swaps
        final_amount = self._adjust_amount_for_market(ccxt_symbol, units, price)

        return TradeDecision(
            allowed=True,
            reason="Aprovat pels controls de risc.",
            symbol_info=symbol_info,
            target_amount=final_amount,
            capital_allocated_usd=capital_per_slot,
            current_price=price,
            equity_usd=total_equity,
            active_positions_count=active_count
        )

    def _adjust_amount_for_market(
        self,
        ccxt_symbol: str,
        units: float,
        price: float
    ) -> float:
        """Adjust raw coin units to exchange contract units or precision."""
        try:
            self.okx.load_markets()
            market = self.okx.exchange.market(ccxt_symbol)
            
            # For OKX SWAP contracts
            if market.get('contract', False):
                contract_size = float(market.get('contractSize') or 1.0)
                # In CCXT, OKX swaps can take amount in contracts
                contracts = units / contract_size
                # Round to integer contracts if contract lot size is 1
                precision = market.get('precision', {}).get('amount')
                if precision == 1.0 or precision == 0:
                    contracts = round(contracts)
                    if contracts < 1:
                        contracts = 1
                    return float(contracts)
                else:
                    return max(units, float(market.get('limits', {}).get('amount', {}).get('min', 0.0) or 0.0))

            return units
        except Exception as e:
            logger.warning(f"Using raw units {units} due to market info lookup: {e}")
            return units
