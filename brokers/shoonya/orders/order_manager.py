"""
Shoonya Order Manager
Handles order placement, modification, and cancellation
"""
from typing import Optional, List
from datetime import datetime
from data.models import Order, OrderType, OrderStatus
from utils.ticket_generator import ticket_generator
from utils.logger import logger


class ShoonyaOrderManager:
    """Manages orders with Shoonya API."""
    
    def __init__(self, auth_manager):
        self.auth_manager = auth_manager
        self.open_orders: List[Order] = []
        self.closed_orders: List[Order] = []
    
    def place_order(
        self,
        symbol: str,
        order_type: OrderType,
        volume: float,
        price: Optional[float] = None,
        exchange: str = 'NSE',
        product: str = 'I',  # I=Intraday, C=Delivery
        **kwargs
    ) -> Optional[Order]:
        """
        Place an order with Shoonya.
        
        Args:
            symbol: Trading symbol
            order_type: BUY or SELL
            volume: Quantity
            price: Limit price (None for market order)
            exchange: Exchange
            product: Product type (I/C/H/B)
            
        Returns:
            Order object or None
        """
        api = self.auth_manager.get_api()
        if not api:
            logger.error("Cannot place order - not authenticated")
            return None
        
        try:
            # Determine price type
            if price is None:
                price_type = 'MKT'
                order_price = '0'
            else:
                price_type = 'LMT'
                order_price = str(price)
            
            # Determine buy/sell
            buy_or_sell = 'B' if order_type == OrderType.BUY else 'S'
            
            # Place order via Shoonya API
            logger.info(f"Placing {order_type.value} order: {volume} {symbol} @ {price_type}")
            
            result = api.place_order(
                buy_or_sell=buy_or_sell,
                product_type=product,
                exchange=exchange,
                tradingsymbol=symbol,
                quantity=int(volume),
                discloseqty=0,
                price_type=price_type,
                price=order_price,
                trigger_price=None,
                retention='DAY',
                remarks=kwargs.get('comment', '')
            )
            
            if result and result.get('stat') == 'Ok':
                # Order placed successfully
                order_no = result.get('norenordno')
                
                order = Order(
                    ticket=int(order_no) if order_no else ticket_generator.generate(),
                    symbol=symbol,
                    order_type=order_type,
                    volume=volume,
                    open_price=price if price else 0.0,
                    open_time=datetime.now(),
                    sl=kwargs.get('sl', 0.0),
                    tp=kwargs.get('tp', 0.0),
                    status=OrderStatus.ACTIVE,
                    comment=kwargs.get('comment', '')
                )
                
                self.open_orders.append(order)
                logger.info(f"✅ Order placed: {order_no}")
                return order
            else:
                error_msg = result.get('emsg', 'Unknown error') if result else 'No response'
                logger.error(f"❌ Order failed: {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"Order placement error: {e}")
            return None
    
    def cancel_order(self, ticket: int) -> bool:
        """Cancel an order."""
        api = self.auth_manager.get_api()
        if not api:
            return False
        
        try:
            result = api.cancel_order(orderno=str(ticket))
            
            if result and result.get('stat') == 'Ok':
                # Remove from open orders
                self.open_orders = [o for o in self.open_orders if o.ticket != ticket]
                logger.info(f"Order {ticket} cancelled")
                return True
            else:
                logger.error(f"Failed to cancel order {ticket}")
                return False
                
        except Exception as e:
            logger.error(f"Cancel order error: {e}")
            return False
    
    def get_order_book(self) -> List[Order]:
        """Get full order book (all statuses)."""
        api = self.auth_manager.get_api()
        if not api:
            return []
        
        try:
            # Refresh from API
            result = api.get_order_book()
            
            orders = []
            if result:
                for order_data in result:
                    # Parse order
                    order = self._parse_order(order_data)
                    if order:
                        orders.append(order)
            
            return orders
            
        except Exception as e:
            logger.error(f"Error getting order book: {e}")
            return []

    def get_open_orders(self) -> List[Order]:
        """Get all open orders."""
        all_orders = self.get_order_book()
        self.open_orders = [o for o in all_orders if o.status in [OrderStatus.ACTIVE, OrderStatus.PENDING]]
        return self.open_orders
    
    def get_order_history(self) -> List[Order]:
        """Get order history."""
        all_orders = self.get_order_book()
        self.closed_orders = [o for o in all_orders if o.status in [OrderStatus.CLOSED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.FILLED]]
        return self.closed_orders
    
    def _parse_order(self, order_data: dict) -> Optional[Order]:
        """Parse Shoonya order data to Order model."""
        try:
            order_type = OrderType.BUY if order_data.get('trantype') == 'B' else OrderType.SELL
            
            # Map status
            status_map = {
                'OPEN': OrderStatus.ACTIVE,
                'PENDING': OrderStatus.PENDING,
                'TRIGGER_PENDING': OrderStatus.PENDING,
                'COMPLETE': OrderStatus.FILLED,
                'CANCELED': OrderStatus.CANCELLED,
                'REJECTED': OrderStatus.REJECTED
            }
            
            shoonya_status = order_data.get('status', 'OPEN')
            status = status_map.get(shoonya_status, OrderStatus.ACTIVE)
            
            # Handle rejection reason
            rej_reason = order_data.get('rejreason', '')
            
            return Order(
                ticket=int(order_data.get('norenordno', 0)),
                symbol=order_data.get('tsym', ''),
                order_type=order_type,
                volume=float(order_data.get('qty', 0)),
                open_price=float(order_data.get('prc', 0)),
                open_time=datetime.now(),  # Note: In real app, parse 'norentm'
                status=status,
                comment=order_data.get('remarks', ''),
                rejection_reason=rej_reason
            )
        except Exception as e:
            logger.error(f"Error parsing order: {e}")
            return None
