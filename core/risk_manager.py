"""
Risk Manager.
Handles position sizing, risk calculations, and risk limits.
"""
from typing import Optional
from PyQt5.QtCore import QObject

from data.models import Symbol, Order, EAConfig
from utils.logger import logger


class RiskManager(QObject):
    """
    Centralized risk management for Expert Advisors.
    Calculates position sizes, validates risk limits, and monitors exposure.
    """
    
    _instance = None
    
    def __new__(cls, account_balance: float = 10000.0):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            QObject.__init__(cls._instance)
        return cls._instance
        
    def __init__(self, account_balance: float = 10000.0):
        """
        Initialize Risk Manager.
        
        Args:
            account_balance: Initial account balance
        """
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        
        # Account info
        self.account_balance = account_balance
        self.account_equity = account_balance
        
        # Risk settings
        self.default_risk_percent = 2.0
        self.max_risk_per_trade = 2.0
        self.max_daily_loss = 5.0
        
        # Tracking
        self.daily_loss = 0.0
        self.total_exposure = 0.0
        
        logger.info(f"Risk Manager initialized with balance: ${account_balance}")
        
    def update_account_balance(self, balance: float, equity: float):
        """
        Update account balance and equity.
        
        Args:
            balance: Account balance
            equity: Account equity
        """
        self.account_balance = balance
        self.account_equity = equity
        
    def calculate_position_size(
        self,
        config: EAConfig,
        entry_price: float,
        stop_loss: float,
        symbol: Optional[Symbol] = None
    ) -> float:
        """
        Calculate position size based on risk parameters.
        
        Args:
            config: EA configuration
            entry_price: Entry price
            stop_loss: Stop loss price
            symbol: Symbol info (for pip value)
            
        Returns:
            Lot size
        """
        if config.use_dynamic_sizing:
            # Risk-based position sizing
            risk_amount = self.account_balance * (config.risk_percent / 100)
            
            # Calculate stop loss in pips
            sl_pips = abs(entry_price - stop_loss) * 10000
            
            if sl_pips == 0:
                logger.warning("Stop loss is 0 pips, using fixed lot size")
                return config.lot_size
                
            # Assuming $10 per pip for 1 standard lot
            pip_value = 10.0
            
            # Position size = Risk Amount / (SL in pips * pip value)
            lot_size = risk_amount / (sl_pips * pip_value)
            
            # Round to 2 decimals
            lot_size = round(lot_size, 2)
            
            # Ensure minimum lot size
            lot_size = max(0.01, lot_size)
            
            logger.info(f"Calculated lot size: {lot_size} (Risk: ${risk_amount:.2f}, SL: {sl_pips:.1f} pips)")
            
            return lot_size
        else:
            # Fixed lot size
            return config.lot_size
            
    def calculate_stop_loss(
        self,
        entry_price: float,
        is_buy: bool,
        stop_loss_pips: float
    ) -> float:
        """
        Calculate stop loss price.
        
        Args:
            entry_price: Entry price
            is_buy: True if buy order
            stop_loss_pips: Stop loss in pips
            
        Returns:
            Stop loss price
        """
        pip_value = 0.0001  # For 4-digit quote
        
        if is_buy:
            sl = entry_price - (stop_loss_pips * pip_value)
        else:
            sl = entry_price + (stop_loss_pips * pip_value)
            
        return round(sl, 5)
        
    def calculate_take_profit(
        self,
        entry_price: float,
        is_buy: bool,
        take_profit_pips: float
    ) -> float:
        """
        Calculate take profit price.
        
        Args:
            entry_price: Entry price
            is_buy: True if buy order
            take_profit_pips: Take profit in pips
            
        Returns:
            Take profit price
        """
        pip_value = 0.0001  # For 4-digit quote
        
        if is_buy:
            tp = entry_price + (take_profit_pips * pip_value)
        else:
            tp = entry_price - (take_profit_pips * pip_value)
            
        return round(tp, 5)
        
    def can_open_position(
        self,
        ea_name: str,
        risk_percent: float,
        lot_size: float
    ) -> tuple[bool, str]:
        """
        Check if a new position can be opened.
        
        Args:
            ea_name: EA name
            risk_percent: Risk percentage for this trade
            lot_size: Lot size
            
        Returns:
            (can_open, reason) tuple
        """
        # Check daily loss limit
        if self.daily_loss < 0:
            loss_percent = abs(self.daily_loss / self.account_balance) * 100
            
            if loss_percent >= self.max_daily_loss:
                return False, f"Daily loss limit reached: {loss_percent:.2f}%"
                
        # Check per-trade risk
        if risk_percent > self.max_risk_per_trade:
            return False, f"Risk {risk_percent}% exceeds max {self.max_risk_per_trade}%"
            
        # Check account equity
        if self.account_equity <= self.account_balance * 0.5:
            return False, "Account equity below 50% of balance"
            
        return True, "OK"
        
    def update_daily_loss(self, profit: float):
        """
        Update daily loss tracking.
        
        Args:
            profit: Profit/loss from closed trade
        """
        self.daily_loss += profit
        
        loss_percent = abs(self.daily_loss / self.account_balance) * 100 if self.daily_loss < 0 else 0
        
        if loss_percent > 0:
            logger.info(f"Daily loss: ${self.daily_loss:.2f} ({loss_percent:.2f}%)")
            
    def reset_daily_loss(self):
        """Reset daily loss counter (call at start of new trading day)."""
        self.daily_loss = 0.0
        logger.info("Daily loss counter reset")
        
    def calculate_risk_reward_ratio(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float
    ) -> float:
        """
        Calculate risk:reward ratio.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Risk:reward ratio
        """
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        
        if risk == 0:
            return 0.0
            
        return round(reward / risk, 2)
        
    def validate_order(
        self,
        order: Order,
        config: EAConfig
    ) -> tuple[bool, str]:
        """
        Validate order before placement.
        
        Args:
            order: Order to validate
            config: EA configuration
            
        Returns:
            (is_valid, reason) tuple
        """
        # Check volume
        if order.volume <= 0:
            return False, "Invalid volume"
            
        if order.volume > 10:  # Max 10 lots
            return False, "Volume exceeds maximum (10 lots)"
            
        # Check SL/TP
        if order.sl > 0 and order.tp > 0:
            rr_ratio = self.calculate_risk_reward_ratio(order.open_price, order.sl, order.tp)
            
            if rr_ratio < 0.5:  # Minimum 1:2 risk:reward
                logger.warning(f"Poor risk:reward ratio: 1:{rr_ratio}")
                
        # Check if can open position
        can_open, reason = self.can_open_position(
            config.name,
            config.risk_percent,
            order.volume
        )
        
        if not can_open:
            return False, reason
            
        return True, "OK"
        
    def get_risk_summary(self) -> dict:
        """Get risk management summary."""
        daily_loss_pct = abs(self.daily_loss / self.account_balance) * 100 if self.daily_loss < 0 else 0
        
        return {
            "account_balance": self.account_balance,
            "account_equity": self.account_equity,
            "daily_loss": self.daily_loss,
            "daily_loss_percent": round(daily_loss_pct, 2),
            "daily_loss_limit": self.max_daily_loss,
            "risk_per_trade": self.default_risk_percent,
            "max_risk_per_trade": self.max_risk_per_trade
        }


# Global risk manager instance
risk_manager = RiskManager()
