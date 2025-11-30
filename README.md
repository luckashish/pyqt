# MT5-Style PyQt5 Trading Platform

A comprehensive trading application built with PyQt5, inspired by MetaTrader 5, featuring real-time price updates, order management, and a professional dark-themed UI.

![Platform Status](https://img.shields.io/badge/status-functional-brightgreen)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15.10-green)

## Features

### ✅ Fully Implemented

- **Real-Time Market Data**: 8 currency pairs with tick-by-tick updates
- **Order Management**: Market orders with instant execution
- **Account Tracking**: Balance, Equity, Margin, Free Margin, Margin Level
- **Profit & Loss**: Real-time P/L calculation for all positions
- **MT5-Style UI**:
  - Market Watch with color indicators
  - Navigator with indicator/EA hierarchy
  - Terminal with 6 tabs (Trade, History, News, Calendar, Alerts, Journal)
  - Tabbed chart interface
  - One-click trading panels
- **Professional Dark Theme**: Complete QSS stylesheet
- **Event-Driven Architecture**: Qt signals/slots based communication

## Screenshots

### Main Window Layout
```
┌─────────────────────────────────────────────────────────┐
│ File | View | Insert | Charts | Tools | Window | Help  │
├──────┬──────────────────────────────────────────────────┤
│Market│ [Chart Tabs: EURUSD | GBPUSD | USDJPY | ...]    │
│Watch │                                                  │
│──────│         Chart Area                               │
│EURUSD│    [One-Click Trading ->]                       │
│G BPUSD│         BUY | SELL                               │
│──────│                                                  │
│Navig.│                                                  │
├──────┴──────────────────────────────────────────────────┤
│ Balance: 10,000 | Equity: 10,000 | Margin: 0.00       │
│ Trade | History | News | Calendar | Alerts | Journal   │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Windows/Linux/macOS

### Installation

1. Clone or extract the project:
```bash
cd d:/pyqt_app
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

### First Steps

1. **Observe Real-Time Prices**: Market Watch updates every second
2. **Place an Order**: Click BUY or SELL on the one-click trading panel
3. **Monitor Positions**: Check the Trade tab in Terminal
4. **Track Account**: Watch Balance/Equity/Margin update automatically

## Project Structure

```
d:/pyqt_app/
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies  
├── config.yaml               # Configuration settings
├── core/                     # Core architecture
│   ├── event_bus.py         # Event communication system
│   ├── broker_interface.py  # Abstract broker interface
│   ├── feed_manager.py      # Data normalization
│   └── account_manager.py   # Account management
├── ui/                       # UI components
├── data/                     # Data layer
│   ├── models.py            # Data models
│   ├── dummy_broker.py      # Simulated broker
│   ├── news_provider.py     # Market news
│   └── calendar_provider.py # Economic calendar
├── utils/                    # Utilities
│   ├── logger.py            # Logging system
│   ├── config_manager.py    # Config management
│   ├── scheduler.py         # Task scheduling
│   └── ticket_generator.py  # Ticket IDs
└── resources/
    └── styles.qss           # Dark theme stylesheet
```

## Architecture

### Event Bus Pattern
All components communicate via Qt signals/slots:
```python
# Price update event
event_bus.tick_received.connect(on_tick_update)

# Order events
event_bus.order_placed.connect(on_order_placed)
event_bus.order_closed.connect(on_order_closed)

# Account updates
event_bus.account_updated.connect(on_account_update)
```

### Broker Interface
Abstract interface for broker connectors:
- `connect()` / `disconnect()`
- `get_symbols()` / `subscribe()`
- `place_order()` / `close_order()`
- `get_account_info()`

### Data Models
- `Symbol`: Bid, Ask, Spread, Trend
- `Order`: Ticket, Type, Volume, Price, SL/TP, P/L
- `OHLCData`: Open, High, Low, Close, Volume
- `NewsItem` / `CalendarEvent` / `Alert`

## Configuration

Edit `config.yaml` to customize:

```yaml
account:
  initial_balance: 10000.0
  currency: "USD"
  leverage: 100

trading:
  default_lot_size: 0.1
  one_click_enabled: true

chart:
  default_symbol: "EURUSD"
  default_timeframe: "H1"

market_watch:
  symbols:
    - "EURUSD"
    - "GBPUSD"
    # ... add more
```

## Key Components

### Market Watch
- Real-time Bid/Ask prices
- Color indicators (green ● = up, red ● = down)
- Spread calculation
- Multiple tabs (Symbols, Details, Trading, Ticks)

### Navigator
- Hierarchical tree structure
- Accounts
- Indicators (Trend, Oscillators)
- Expert Advisors
- Scripts

### Terminal
- **Trade Tab**: Active positions with real-time P/L
- **History Tab**: Closed trades
- **News Tab**: Market news feed
- **Calendar Tab**: Economic events
- **Alerts Tab**: Price alerts
- **Journal Tab**: System logs

### One-Click Trading
- BUY button (red) with ask price
- SELL button (blue) with bid price
- Adjustable lot size
- Instant execution

## Technical Details

### Real-Time Updates
- Price simulation: 1000ms interval (QTimer)
- Random walk algorithm
- Realistic spreads (2 pips for majors)

### Order Execution
- Market orders filled instantly
- Automatic SL/TP monitoring
- P/L calculation using pip value method
- Margin calculation (100:1 leverage)

### Account Calculations
```
Equity = Balance + Floating P/L
Margin = (Volume × Contract Size × Price) / Leverage
Free Margin = Equity - Margin
Margin Level = (Equity / Margin) × 100%
```

## Development Roadmap

### ✅ Phase 1-7 (Complete)
- Core architecture
- UI foundation
- Market Watch & Navigator
- Terminal with tabs
- Data layer
- Order management

### ⏳ Phase 8: Plugin System
- [ ] Plugin loader framework
- [ ] Dynamic indicator loading
- [ ] Expert Advisor execution
- [ ] Script runner

### ⏳ Phase 9: Advanced Trading
- [ ] Pending orders (limit/stop)
- [ ] Order modification dialog
- [ ] Trailing stop
- [ ] Breakeven automation

### ⏳ Phase 10: Charts
- [ ] PyQtGraph candlestick rendering
- [ ] Indicator overlays (MA, RSI, Bollinger)
- [ ] Drawing tools (lines, channels, Fibonacci)
- [ ] Crosshair with info panel
- [ ] Zoom/pan controls

### ⏳ Phase 11: Integration
- [ ] Real broker API integration
- [ ] Live news feed
- [ ] Economic calendar with real data
- [ ] Price alerts with notifications
- [ ] Strategy tester/backtester

## Logs

Application logs are saved to `logs/trading_app.log`:

```
2025-11-30 09:12:54 - TradingApp - INFO - UI initialized successfully
2025-11-30 09:12:54 - TradingApp - INFO - Connected to Demo Server
2025-11-30 09:12:54 - TradingApp - INFO - Subscribed to EURUSD
2025-11-30 09:13:15 - TradingApp - INFO - Order placed: 100000001 buy 0.1 EURUSD @ 1.09582
```

## Dependencies

- **PyQt5** (5.15.10): GUI framework
- **pyqtgraph** (0.13.3): Charting library
- **numpy** (1.24.3): Numerical operations
- **pandas** (2.0.3): Data manipulation
- **PyYAML** (6.0.1): Configuration files

## Contributing

This is a demo/educational project. Feel free to:
- Add new indicators
- Implement real broker connectors
- Enhance the UI
- Add backtesting features
- Improve chart rendering

## License

This is an educational project. Use at your own risk. Not for production trading.

## Disclaimer

⚠️ This application uses a **dummy broker with simulated data**. It is for educational and testing purposes only. Do not use for real trading without implementing proper broker integration and risk management.

## Contact & Support

For questions or issues, check the logs directory or review the code documentation.

---

**Status**: ✅ Functional | 🚀 Active Development | 📚 Educational

Built with ❤️ using PyQt5
