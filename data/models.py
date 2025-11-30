"""Data models for the trading application."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class OrderType(Enum):
    """Order type enumeration."""
    BUY = "buy"
    SELL = "sell"
    BUY_LIMIT = "buy limit"
    SELL_LIMIT = "sell limit"
    BUY_STOP = "buy stop"
    SELL_STOP = "sell stop"


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    FILLED = "filled"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class OHLCData:
    """OHLC (Open, High, Low, Close) candlestick data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    
    def __post_init__(self):
        """Validate OHLC data."""
        if self.high < max(self.open, self.close, self.low):
            self.high = max(self.open, self.close, self.low)
        if self.low > min(self.open, self.close, self.high):
            self.low = min(self.open, self.close, self.high)


@dataclass
class Symbol:
    """Trading symbol information."""
    name: str
    bid: float = 0.0
    ask: float = 0.0
    last_tick_time: datetime = field(default_factory=datetime.now)
    
    @property
    def spread(self) -> float:
        """Calculate spread in pips (assuming 4-digit quote)."""
        return round((self.ask - self.bid) * 10000, 1)
    
    @property
    def trend(self) -> str:
        """Simple trend indicator based on bid/ask."""
        # This is placeholder logic - in real app would use historical data
        return "up" if self.bid > self.ask - self.spread / 10000 else "down"


@dataclass
class Order:
    """Trading order."""
    ticket: int
    symbol: str
    order_type: OrderType
    volume: float  # lot size
    open_price: float
    open_time: datetime
    sl: float = 0.0  # stop loss
    tp: float = 0.0  # take profit
    status: OrderStatus = OrderStatus.ACTIVE
    close_price: Optional[float] = None
    close_time: Optional[datetime] = None
    comment: str = ""
    rejection_reason: str = ""
    
    def calculate_profit(self, current_price: float, pip_value: float = 10.0) -> float:
        """
        Calculate current profit/loss.
        pip_value: value of 1 pip in account currency (default $10 for standard lot)
        """
        if self.status == OrderStatus.CLOSED and self.close_price:
            price_diff = self.close_price - self.open_price
        else:
            price_diff = current_price - self.open_price
        
        # Invert for sell orders
        if self.order_type in [OrderType.SELL, OrderType.SELL_LIMIT, OrderType.SELL_STOP]:
            price_diff = -price_diff
        
        # Convert to pips and multiply by volume
        pips = price_diff * 10000  # Assuming 4-digit quote
        profit = pips * pip_value * self.volume
        
        return round(profit, 2)
    
    @property
    def is_buy(self) -> bool:
        """Check if order is a buy order."""
        return self.order_type in [OrderType.BUY, OrderType.BUY_LIMIT, OrderType.BUY_STOP]
    
    @property
    def duration(self) -> str:
        """Get order duration as string."""
        if self.close_time:
            delta = self.close_time - self.open_time
        else:
            delta = datetime.now() - self.open_time
        
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        return f"{delta.days}d {hours}h {minutes}m"


@dataclass
class Position:
    """Simplified position model (aggregated orders)."""
    symbol: str
    volume: float
    entry_price: float
    current_price: float
    profit: float
    is_long: bool


@dataclass
class NewsItem:
    """Market news item."""
    headline: str
    source: str
    timestamp: datetime
    impact: str  # "high", "medium", "low"
    content: str = ""
    currency: str = ""


@dataclass
class CalendarEvent:
    """Economic calendar event."""
    date: datetime
    currency: str
    event: str
    impact: str  # "high", "medium", "low"
    forecast: str = ""
    previous: str = ""
    actual: str = ""


@dataclass
class Alert:
    """Price alert."""
    symbol: str
    condition: str  # "above", "below"
    price: float
    enabled: bool = True
    triggered: bool = False
    created_time: datetime = field(default_factory=datetime.now)
