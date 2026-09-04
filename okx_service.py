"""OKX exchange integration service using CCXT.
Handles balance queries, open positions tracking, and market order execution.
"""

import logging
from typing import Dict, List, Optional, Set
import ccxt
from config import settings

logger = logging.getLogger("crypto_bot.okx")


class OKXService:
    def __init__(self):
        self.is_demo = settings.okx_is_demo
        self.instrument_type = settings.instrument_type.upper()

        options = {
            'defaultType': 'swap' if self.instrument_type == 'SWAP' else 'spot',
            'adjustForTimeDifference': True,
        }
        
        headers = {}
        if settings.okx_subaccount_name:
            headers['OK-ACCESS-SUBACCOUNT'] = settings.okx_subaccount_name

        self.exchange = ccxt.okx({
            'apiKey': settings.okx_api_key,
            'secret': settings.okx_secret_key,
            'password': settings.okx_passphrase,
            'hostname': settings.okx_hostname,
            'enableRateLimit': True,
            'options': options,
            'headers': headers
        })

        if self.is_demo:
            self.exchange.set_sandbox_mode(True)
            logger.info("OKX client configured in DEMO / SANDBOX mode.")
        else:
            logger.warning("OKX client configured in REAL PRODUCTION mode.")

        self._markets_loaded = False

    def load_markets(self):
        """Cache exchange market definitions."""
        if not self._markets_loaded:
            try:
                self.exchange.load_markets()
                self._markets_loaded = True
                logger.info(f"Loaded {len(self.exchange.markets)} markets from OKX.")
            except Exception as e:
                logger.error(f"Error loading OKX markets: {e}")

    def get_total_equity(self) -> float:
        """Fetch total account equity in USDT.
        Falls back to FALLBACK_EQUITY_USDT if balance is 0 or API fails.
        """
        try:
            balance = self.exchange.fetch_balance()
            
            # 1. Unified Account Total Equity (preferred by OKX v5)
            if 'info' in balance and 'data' in balance['info'] and len(balance['info']['data']) > 0:
                account_info = balance['info']['data'][0]
                total_eq = float(account_info.get('totalEq', 0.0) or 0.0)
                if total_eq > 0:
                    return total_eq
                
                details = account_info.get('details', [])
                for d in details:
                    if d.get('ccy') == 'USDT':
                        usdt_eq = float(d.get('eq', 0.0) or 0.0)
                        if usdt_eq > 0:
                            return usdt_eq
                    eq_usd = float(d.get('eqUsd', 0.0) or 0.0)
                    if eq_usd > 0:
                        return eq_usd

            # 2. Total USDT in balance
            usdt_total = float(balance.get('total', {}).get('USDT', 0.0))
            if usdt_total > 0:
                return usdt_total

        except Exception as e:
            logger.error(f"Failed to fetch OKX balance: {e}")

        logger.warning(f"Using fallback equity: {settings.fallback_equity_usdt} USDT")
        return settings.fallback_equity_usdt

    def get_open_positions(self) -> Set[str]:
        """Return a set of base asset symbols that are currently open (e.g. {'SOL', 'BTC'}).
        Prevents opening duplicate trades on the same crypto.
        """
        open_assets: Set[str] = set()
        
        try:
            if self.instrument_type == "SWAP":
                # Fetch futures positions
                positions = self.exchange.fetch_positions()
                for pos in positions:
                    contracts = float(pos.get('contracts', 0.0) or 0.0)
                    if contracts > 0:
                        symbol = pos.get('symbol', '')  # e.g. "SOL/USDT:USDT"
                        base = symbol.split('/')[0] if '/' in symbol else symbol
                        open_assets.add(base)
            else:
                # Fetch spot balances
                balance = self.exchange.fetch_balance()
                total_balances = balance.get('total', {})
                for asset, amount in total_balances.items():
                    if asset in ['USDT', 'USDC', 'USD', 'EUR']:
                        continue
                    # Ignore tiny dust balances
                    if float(amount or 0.0) > 0.0001:
                        open_assets.add(asset)

        except Exception as e:
            logger.error(f"Error checking open positions: {e}")

        return open_assets

    def get_current_price(self, ccxt_symbol: str) -> Optional[float]:
        """Fetch latest market price for symbol."""
        try:
            ticker = self.exchange.fetch_ticker(ccxt_symbol)
            return float(ticker.get('last') or ticker.get('close') or 0.0)
        except Exception as e:
            logger.error(f"Error fetching ticker for {ccxt_symbol}: {e}")
            return None

    def setup_instrument(self, ccxt_symbol: str):
        """Set leverage and margin mode for SWAP instruments."""
        if self.instrument_type != "SWAP":
            return
            
        try:
            self.exchange.set_leverage(
                leverage=settings.leverage,
                symbol=ccxt_symbol,
                params={'marginMode': settings.margin_mode}
            )
            logger.info(f"Set leverage {settings.leverage}x ({settings.margin_mode}) for {ccxt_symbol}")
        except Exception as e:
            # Often OKX throws if leverage is already set to the same value
            logger.debug(f"Note setting leverage for {ccxt_symbol}: {e}")

    def execute_market_buy(
        self,
        ccxt_symbol: str,
        amount: float,
        price_hint: Optional[float] = None,
        sl_price: Optional[float] = None,
        tp_price: Optional[float] = None
    ) -> Dict:
        """Execute a market BUY order on OKX with optional Stop Loss and Take Profit brackets.
        Returns order result dict or raises Exception.
        """
        self.load_markets()
        self.setup_instrument(ccxt_symbol)

        market = self.exchange.market(ccxt_symbol)
        
        # Round amount according to exchange rules
        formatted_amount = self.exchange.amount_to_precision(ccxt_symbol, amount)
        float_amount = float(formatted_amount)
        
        min_amount = market.get('limits', {}).get('amount', {}).get('min', 0.0) or 0.0
        if float_amount < min_amount:
            raise ValueError(
                f"Calculated amount {float_amount} is below minimum {min_amount} for {ccxt_symbol}"
            )

        # Prepare bracket orders (SL and TP)
        is_contract = market.get('contract', False)
        params: dict = {
            'tdMode': settings.margin_mode if is_contract else 'cash'
        }
        
        attach_algo = []
        if sl_price is not None and sl_price > 0:
            attach_algo.append({
                'slTriggerPx': str(sl_price),
                'slOrdPx': '-1'  # -1 means market order upon trigger
            })
            logger.info(f"Attaching Stop Loss at {sl_price} for {ccxt_symbol}")

        if tp_price is not None and tp_price > 0:
            attach_algo.append({
                'tpTriggerPx': str(tp_price),
                'tpOrdPx': '-1'  # -1 means market order upon trigger
            })
            logger.info(f"Attaching Take Profit at {tp_price} for {ccxt_symbol}")

        if attach_algo:
            params['attachAlgoOrds'] = attach_algo

        logger.info(f"Sending MARKET BUY order: {ccxt_symbol} | Amount: {float_amount} | Params: {params}")
        
        order = self.exchange.create_order(
            symbol=ccxt_symbol,
            type='market',
            side='buy',
            amount=float_amount,
            params=params
        )
        return order


okx_service = OKXService()
