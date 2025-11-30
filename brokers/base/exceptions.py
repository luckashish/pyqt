"""
Common Broker Exceptions
"""


class BrokerException(Exception):
    """Base exception for broker errors."""
    pass


class AuthenticationError(BrokerException):
    """Authentication failed."""
    pass


class ConnectionError(BrokerException):
    """Connection error."""
    pass


class OrderRejectedError(BrokerException):
    """Order was rejected."""
    pass


class InsufficientFundsError(BrokerException):
    """Insufficient funds for order."""
    pass


class InvalidSymbolError(BrokerException):
    """Invalid trading symbol."""
    pass


class MarketClosedError(BrokerException):
    """Market is closed."""
    pass


class RateLimitError(BrokerException):
    """API rate limit exceeded."""
    pass


class SessionExpiredError(BrokerException):
    """Session has expired."""
    pass


class ValidationError(BrokerException):
    """Order validation failed."""
    pass
