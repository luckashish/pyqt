You are an expert Python architect and GUI designer. 
Your task is to generate a modular PyQt5 application that mimics the workflow of MetaTrader 5 (MT5) but remains minimalist and extensible.

### Requirements:
1. **Core Structure**
   - Use QMainWindow as the app shell.
   - Central widget: chart area (PyQtGraph candlestick chart).
   - Dockable panels: Market Watch (QTableWidget), Order Manager, Strategy Tester.
   - Menu bar: Broker connections, Strategies, Settings.
   - Toolbar: Quick actions (new order, indicators, timeframe).

2. **Modules**
   - User login to Broker
   - Chart Module: real-time candlestick chart with zoom/pan, overlays for indicators.
   - Market Watch Module: table with symbols, bid/ask, spread, live updates.
   - Order Manager Module: open trades, SL/TP, PnL, modify/close orders.
   - Strategy Tester Module: backtesting UI with equity curve visualization.

3. **Data Layer**
   - BrokerInterface (abstract class).
   - Example connector (dummy broker) streaming OHLC data.
   - FeedManager normalizes tick/candle data and pushes to Event Bus.

4. **Plugin System**
   - Indicators: Moving Average, RSI, Bollinger Bands (loaded dynamically).
   - Strategies: Intraday SL/TP logic, AI signals (loaded dynamically).
   - Broker connectors: modular, pluggable.

5. **Utilities**
   - Logger for trades/events.
   - ConfigManager for JSON/YAML configs.
   - Scheduler for timed tasks.

6. **Architecture**
   - Event Bus for communication between modules (signals/slots).
   - Folder structure:
     core/, ui/, data/, plugins/, utils/, resources/

7. **Deliverables**
   - Provide Python code with clear class separation.
   - Include one working candlestick chart example using PyQtGraph with dummy OHLC data.
   - Show how Market Watch and Order Manager docks are added.
   - Demonstrate plugin loading with a sample Moving Average indicator.

### Output:
Generate clean, modular Python code with comments explaining each part. 
Ensure the app runs with `python main.py` and opens a window with chart + dockable panels.