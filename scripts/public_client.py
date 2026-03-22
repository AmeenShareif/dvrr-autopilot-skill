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

    # ------------------------------------------------------------------
    # Account & Positions
    # ------------------------------------------------------------------

    def get_account(self) -> AccountInfo:
        """Fetch account summary (equity, buying power, cash)."""
        data = self._get("/trading/account")
        accounts = data.get("accounts", [])
        acct = None
        for a in accounts:
            if a.get("accountId") == self.account_id:
                acct = a
                break
        if not acct and accounts:
            acct = accounts[0]

        # Get balances
        balances = self._get(f"/trading/accounts/{self.account_id}/balances")
        equity = float(balances.get("equity", 0))
        buying_power = float(balances.get("buyingPower", 0))
        cash = float(balances.get("cash", 0))

        return AccountInfo(
            account_id=self.account_id,
            equity=equity,
            buying_power=buying_power,
            cash=cash,
            raw=balances,
        )

    def get_positions(self) -> List[Position]:
        """Fetch all open positions."""
        data = self._get(f"/trading/accounts/{self.account_id}/positions")
        positions = []
        for p in data.get("positions", []):
            quantity = float(p.get("quantity", 0))
            market_value = float(p.get("marketValue", 0))
            cost_basis = float(p.get("costBasis", 0))
            pnl = market_value - cost_basis
            pnl_pct = (pnl / cost_basis * 100) if cost_basis else 0

            positions.append(Position(
                symbol=p.get("symbol", ""),
                quantity=quantity,
                market_value=market_value,
                cost_basis=cost_basis,
                unrealized_pnl=round(pnl, 2),
                unrealized_pnl_pct=round(pnl_pct, 2),
                side="LONG" if quantity > 0 else "SHORT",
                instrument_type=p.get("instrumentType", "EQUITY"),
                raw=p,
            ))
        return positions

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
