"""
Public.com API Client — Standalone wrapper for the DVRR Autopilot skill.

Handles authentication, account data, positions, quotes, and order placement.
All secrets come from environment variables. Nothing is hardcoded or logged.
"""

import os
import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

try:
    import httpx
except ImportError:
    raise ImportError("httpx is required: pip install httpx")

logger = logging.getLogger(__name__)

BASE_URL = "https://api.public.com"
AUTH_URL = f"{BASE_URL}/userapiauthservice/personal/access-tokens"
GATEWAY_URL = f"{BASE_URL}/userapigateway"


@dataclass
class Position:
    """A portfolio position."""
    symbol: str
    quantity: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    side: str  # LONG or SHORT
    instrument_type: str  # EQUITY, OPTION, CRYPTO
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccountInfo:
    """Account summary."""
    account_id: str
    equity: float
    buying_power: float
    cash: float
    positions: List[Position] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderResult:
    """Result of an order placement."""
    order_id: str
    symbol: str
    side: str
    quantity: float
    status: str
    raw: Dict[str, Any] = field(default_factory=dict)


class PublicClient:
    """
    Minimal, self-contained Public.com API client.

    Usage:
        client = PublicClient()          # reads env vars
        account = client.get_account()
        positions = client.get_positions()
        result = client.place_order("AAPL", "BUY", quantity=10)
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        account_id: Optional[str] = None,
    ):
        self.secret_key = secret_key or os.environ.get("PUBLIC_API_SECRET", "")
        self.account_id = account_id or os.environ.get("PUBLIC_ACCOUNT_ID", "")
        if not self.secret_key:
            raise ValueError("PUBLIC_API_SECRET is required (env var or constructor arg)")
        if not self.account_id:
            raise ValueError("PUBLIC_ACCOUNT_ID is required (env var or constructor arg)")
        self._access_token: Optional[str] = None
        self._token_expires: float = 0
        self._http = httpx.Client(timeout=30)
        self._last_portfolio_payload: Optional[Dict[str, Any]] = None
        self._last_account_info: Optional[AccountInfo] = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _ensure_token(self) -> str:
        """Get or refresh the access token."""
        if self._access_token and time.time() < self._token_expires:
            return self._access_token

        resp = self._http.post(
            AUTH_URL,
            json={"validityInMinutes": 60, "secret": self.secret_key},
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["accessToken"]
        self._token_expires = time.time() + 55 * 60  # refresh 5 min early
        return self._access_token

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._ensure_token()}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        url = f"{GATEWAY_URL}{path}"
        resp = self._http.get(url, headers=self._headers(), params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, payload: Dict) -> Any:
        url = f"{GATEWAY_URL}{path}"
        resp = self._http.post(url, headers=self._headers(), json=payload)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _coerce_float(value: Any) -> float:
        """Best-effort numeric conversion for Public payloads."""
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.replace("$", "").replace(",", ""))
            except ValueError:
                return 0.0
        if isinstance(value, dict):
            for key in (
                "value",
                "amount",
                "cashOnlyBuyingPower",
                "buyingPower",
                "marketValue",
                "currentValue",
                "equity",
                "cash",
            ):
                if key in value:
                    coerced = PublicClient._coerce_float(value.get(key))
                    if coerced or value.get(key) in (0, 0.0, "0", "0.0"):
                        return coerced
            for candidate in value.values():
                coerced = PublicClient._coerce_float(candidate)
                if coerced or candidate in (0, 0.0, "0", "0.0"):
                    return coerced
        return 0.0

    def _fetch_portfolio_payload(self) -> Dict[str, Any]:
        """
        Fetch the most complete Public portfolio snapshot available.

        Prefer portfolio v2 because it usually includes positions and summary
        fields together. Fall back to the account overview if needed.
        """
        if self._last_portfolio_payload is not None:
            return self._last_portfolio_payload

        for path in (f"/trading/{self.account_id}/portfolio/v2", "/trading/account"):
            try:
                payload = self._get(path)
                if isinstance(payload, dict):
                    self._last_portfolio_payload = payload
                    return payload
            except httpx.HTTPStatusError as e:
                if e.response is not None and e.response.status_code == 404:
                    logger.debug("Public portfolio endpoint unavailable: %s", path)
                    continue
                raise
            except Exception as e:
                logger.debug("Public portfolio fetch failed for %s: %s", path, e.__class__.__name__)
                continue

        self._last_portfolio_payload = {}
        return {}

    def _select_account_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Pick the best account-shaped object from a portfolio payload."""
        if not isinstance(payload, dict):
            return {}

        accounts = payload.get("accounts")
        if isinstance(accounts, list) and accounts:
            for candidate in accounts:
                if not isinstance(candidate, dict):
                    continue
                if candidate.get("accountId") == self.account_id:
                    self.account_id = candidate.get("accountId", self.account_id)
                    return candidate
            first = next((candidate for candidate in accounts if isinstance(candidate, dict)), {})
            if first:
                self.account_id = first.get("accountId", self.account_id)
                return first

        return payload

    def _extract_position_payloads(
        self,
        payload: Dict[str, Any],
        account_payload: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Pull the first non-empty position list from known Public payload shapes."""
        sources = [account_payload, payload]
        for source in sources:
            if not isinstance(source, dict):
                continue
            for key in ("positions", "holdings", "portfolioPositions"):
                raw_positions = source.get(key)
                if isinstance(raw_positions, list) and raw_positions:
                    return [p for p in raw_positions if isinstance(p, dict)]
            nested = source.get("portfolio")
            if isinstance(nested, dict):
                for key in ("positions", "holdings"):
                    raw_positions = nested.get(key)
                    if isinstance(raw_positions, list) and raw_positions:
                        return [p for p in raw_positions if isinstance(p, dict)]
        return []

    def _build_position(self, payload: Dict[str, Any]) -> Optional[Position]:
        """Convert a raw Public position payload into a normalized Position."""
        if not isinstance(payload, dict):
            return None

        instrument = payload.get("instrument")
        if not isinstance(instrument, dict):
            instrument = {}

        symbol = (
            instrument.get("symbol")
            or payload.get("symbol")
            or payload.get("ticker")
            or ""
        )
        if not symbol:
            return None

        quantity = self._coerce_float(payload.get("quantity") or payload.get("qty") or payload.get("shares"))
        market_value = self._coerce_float(
            payload.get("currentValue")
            or payload.get("marketValue")
            or payload.get("value")
        )
        if market_value <= 0:
            last_price = self._coerce_float(
                payload.get("lastPrice")
                or payload.get("currentPrice")
                or payload.get("price")
            )
            if quantity > 0 and last_price > 0:
                market_value = quantity * last_price

        cost_basis = self._coerce_float(
            payload.get("costBasis")
            or payload.get("avgCost")
            or payload.get("averageCost")
            or payload.get("cost_basis")
        )
        pnl = market_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis else 0
        instrument_type = (
            payload.get("instrumentType")
            or payload.get("instrument_type")
            or instrument.get("type")
            or "EQUITY"
        )

        return Position(
            symbol=str(symbol),
            quantity=quantity,
            market_value=market_value,
            cost_basis=cost_basis,
            unrealized_pnl=round(pnl, 2),
            unrealized_pnl_pct=round(pnl_pct, 2),
            side="LONG" if quantity >= 0 else "SHORT",
            instrument_type=str(instrument_type),
            raw=payload,
        )

    def _normalize_portfolio(self, payload: Dict[str, Any]) -> AccountInfo:
        """Normalize Public portfolio/account payloads into AccountInfo."""
        account_payload = self._select_account_payload(payload)
        nested_portfolio = account_payload.get("portfolio")
        if not isinstance(nested_portfolio, dict):
            nested_portfolio = {}

        equity_raw = account_payload.get("equity")
        if equity_raw in (None, "") and "equity" in payload:
            equity_raw = payload.get("equity")
        if equity_raw in (None, "") and nested_portfolio:
            equity_raw = nested_portfolio.get("equity")

        buying_power_raw = (
            account_payload.get("buyingPower")
            or account_payload.get("cashOnlyBuyingPower")
            or account_payload.get("buying_power")
            or payload.get("buyingPower")
            or payload.get("cashOnlyBuyingPower")
            or payload.get("buying_power")
            or nested_portfolio.get("buyingPower")
            or nested_portfolio.get("cashOnlyBuyingPower")
            or nested_portfolio.get("buying_power")
        )

        cash_raw = (
            account_payload.get("cash")
            or account_payload.get("cashBalance")
            or account_payload.get("availableCash")
            or account_payload.get("cashOnlyBuyingPower")
            or account_payload.get("buying_power")
            or payload.get("cash")
            or payload.get("cashBalance")
            or payload.get("availableCash")
            or payload.get("cashOnlyBuyingPower")
            or payload.get("buying_power")
        )

        equity = 0.0
        if isinstance(equity_raw, list):
            for item in equity_raw:
                if isinstance(item, dict):
                    equity += self._coerce_float(item.get("value") or item.get("amount"))
                else:
                    equity += self._coerce_float(item)
        else:
            equity = self._coerce_float(equity_raw)

        buying_power = 0.0
        if isinstance(buying_power_raw, dict):
            buying_power = self._coerce_float(
                buying_power_raw.get("cashOnlyBuyingPower")
                or buying_power_raw.get("buyingPower")
                or buying_power_raw.get("value")
                or buying_power_raw.get("amount")
            )
        else:
            buying_power = self._coerce_float(buying_power_raw)

        cash = self._coerce_float(cash_raw)
        if cash <= 0 and buying_power > 0:
            cash = buying_power

        raw_positions = self._extract_position_payloads(payload, account_payload)
        positions: List[Position] = []
        for raw_position in raw_positions:
            position = self._build_position(raw_position)
            if position is not None:
                positions.append(position)

        if equity <= 0 and positions:
            equity = sum(pos.market_value for pos in positions) + cash
        if buying_power <= 0 and cash > 0:
            buying_power = cash

        return AccountInfo(
            account_id=self.account_id,
            equity=equity,
            buying_power=buying_power,
            cash=cash,
            positions=positions,
            raw=account_payload or payload,
        )

    # ------------------------------------------------------------------
    # Account & Positions
    # ------------------------------------------------------------------

    def get_account(self) -> AccountInfo:
        """Fetch account summary (equity, buying power, cash)."""
        payload = self._fetch_portfolio_payload()
        account = self._normalize_portfolio(payload)
        self._last_account_info = account
        return account

    def get_positions(self) -> List[Position]:
        """Fetch all open positions."""
        if self._last_account_info is not None:
            return self._last_account_info.positions
        return self.get_account().positions

    # ------------------------------------------------------------------
    # Market Data (quotes from Public)
    # ------------------------------------------------------------------

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get a real-time quote for a symbol."""
        data = self._get(f"/market-data/quote/{symbol}")
        return data

    def get_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get quotes for multiple symbols."""
        result = {}
        for sym in symbols:
            try:
                result[sym] = self.get_quote(sym)
            except Exception as e:
                logger.warning(f"Quote failed for {sym}: {e}")
        return result

    # ------------------------------------------------------------------
    # Order Placement
    # ------------------------------------------------------------------

    def preflight_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        limit_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Run preflight check before placing an order."""
        payload = {
            "accountId": self.account_id,
            "symbol": symbol,
            "side": side.upper(),
            "quantity": quantity,
            "orderType": order_type.upper(),
        }
        if limit_price is not None:
            payload["limitPrice"] = limit_price

        return self._post("/trading/preflight", payload)

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        limit_price: Optional[float] = None,
    ) -> OrderResult:
        """
        Place a trade order on Public.com.

        Args:
            symbol: Ticker symbol (e.g., "AAPL")
            side: "BUY" or "SELL"
            quantity: Number of shares (supports fractional)
            order_type: "MARKET" or "LIMIT"
            limit_price: Required if order_type is LIMIT
        """
        payload = {
            "accountId": self.account_id,
            "symbol": symbol,
            "side": side.upper(),
            "quantity": quantity,
            "orderType": order_type.upper(),
        }
        if limit_price is not None:
            payload["limitPrice"] = limit_price

        data = self._post("/trading/orders", payload)

        return OrderResult(
            order_id=data.get("orderId", ""),
            symbol=symbol,
            side=side.upper(),
            quantity=quantity,
            status=data.get("status", "SUBMITTED"),
            raw=data,
        )

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an open order."""
        return self._post(f"/trading/orders/{order_id}/cancel", {})

    def get_order_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent order history."""
        data = self._get(
            f"/trading/accounts/{self.account_id}/orders",
            params={"limit": limit},
        )
        return data.get("orders", [])
