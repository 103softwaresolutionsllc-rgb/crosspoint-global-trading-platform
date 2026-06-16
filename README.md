# Crosspoint Global Trading Platform

<div align="center">

[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-C06524)](https://github.com/103softwaresolutionsllc-rgb/global-trading-platform/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Qt6](https://img.shields.io/badge/Qt-6-41CD52?logo=qt&logoColor=white)](https://www.qt.io/)

### **Advanced Multi-Agent Trading Platform**

Enterprise-grade trading platform with AI-powered analytics, real-time execution, and comprehensive market intelligence.

[📥 Download](https://github.com/Fincept-Corporation/FinceptTerminal/releases) · [📚 Docs](https://github.com/Fincept-Corporation/FinceptTerminal/tree/main/docs) · [💬 Discussions](https://github.com/Fincept-Corporation/FinceptTerminal/discussions) · [💬 Discord](https://discord.gg/ae87a8ygbN) · [🤝 Partner](https://github.com/Fincept-Corporation/FinceptTerminal/blob/main/docs/COMMERCIAL_LICENSE.md)

</div>

---

## About

**Crosspoint Global Trading Platform** is a sophisticated multi-agent trading system enhanced with FinceptTerminal's advanced analytics engine. Originally developed as a multi-agent trading platform, it now includes CFA-level analytics, AI investment agents, real-time WebSocket trading, and a modern Qt6 interface.

**🤝 Enhanced with FinceptTerminal Technology**
- Integrated FinceptTerminal v4 analytics engine
- CFA-level financial modeling and portfolio optimization
- AI agents from famous investors (Buffett, Graham, Lynch, Dunlap)
- Real-time trading with 16+ broker integrations
- Advanced quantitative analysis suite (QuantLib)
- Modern Qt6 dashboard with visual workflow editor

---

## Features

| **Feature** | **Description** |
|-------------|-----------------|
| 🤖 **Multi-Agent Trading** | Original autonomous trading agents with enhanced AI investor strategies |
| 📊 **CFA-Level Analytics** | DCF models, portfolio optimization, risk metrics (VaR, Sharpe), derivatives pricing |
| 🤖 **AI Investment Agents** | Buffett, Graham, Lynch, Dunlap agents with value/growth strategies |
| 🌐 **100+ Data Connectors** | Yahoo Finance, FRED, Kraken, Polygon, IMF, World Bank, and more |
| 📈 **Real-Time Trading** | WebSocket streaming,16 broker integrations, algorithmic execution |
| 🔬 **QuantLib Suite** | 18 quantitative modules - pricing, risk, volatility, stochastic models |
| 🎨 **Modern Qt6 UI** | Professional dashboard with real-time charts and workflow editor |
| 🚢 **Visual Workflows** | Node-based automation pipelines for trading strategies |
| 🧠 **AI Quant Lab** | Machine learning models, factor discovery, HFT capabilities |

---

## Installation

### Quick Start (Python-based)

```bash
# Clone repository
git clone https://github.com/103softwaresolutionsllc-rgb/global-trading-platform.git
cd global-trading-platform
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# Install with all features
pip install -e ".[all]"
```

### Development Setup

```bash
# Install development dependencies
pip install -e ".[dev,all]"

# Run tests
pytest

# Start the platform
python -m fincept_terminal
```

### Go live (paper or production)

1. Copy the production template and set secrets:

```bash
copy config\production.example.env .env   # Windows
# cp config/production.example.env .env  # Linux/macOS
```

2. Required settings in `.env`:

| Variable | Purpose |
|----------|---------|
| `FRED_API_KEY` | Live macro regime (FRED); omit uses Yahoo fallback |
| `GTP_IBKR_USE_STUB=0` | Real IBKR positions and order routing |
| `GTP_IBKR_PORT=7497` | Paper TWS/Gateway (7496 for live) |
| `GTP_WATCHLIST` | Tickers screened by agent consensus |
| `GTP_SIGNAL_TICKER` | Primary signal for execution bridge |
| `GTP_PORTFOLIO_VALUE` | Portfolio value for VaR sizing |
| `GTP_DASHBOARD_AUTH_ENABLED` | `1` to require login on the web dashboard |
| `GTP_DASHBOARD_USER` / `GTP_DASHBOARD_PASSWORD` | Credentials shared with ngrok visitors |

3. Quick paper setup (creates `.env` from template):

```powershell
pwsh scripts/setup-paper.ps1
# Add FRED_API_KEY to .env, then start IBKR Gateway on port 7497
```

4. Start IBKR TWS or Gateway, then launch the web dashboard:

```powershell
pwsh scripts/dev.ps1 -Paper
# Or manually: $env:PYTHONPATH="src"; python web_dashboard.py
# Open http://127.0.0.1:8050
```

Qt desktop app (auto-refreshes every 3 minutes):

```powershell
$env:PYTHONPATH="src"
python -m fincept_terminal
```

5. Run one live consensus workflow (paper):

```bash
crosspoint run-once --ticker AAPL
# Legacy demo signal: crosspoint run-once --demo
```

### Autopilot & dynamic watchlist

Autopilot is started as a script (not a background `.env` toggle). Settings in `.env`:

| Variable | Purpose |
|----------|---------|
| `GTP_AUTOPILOT_IBKR=1` | Route autopilot orders through IBKR paper |
| `GTP_AUTOPILOT_INTERVAL_MINUTES` | Minutes between full watchlist cycles |
| `GTP_WATCHLIST` | Comma-separated tickers agents screen and trade |

```powershell
# Start scheduled trading (reads .env; Ctrl+C to stop)
powershell -ExecutionPolicy Bypass -File scripts/autopilot.ps1

# Dashboard + autopilot together
powershell -ExecutionPolicy Bypass -File scripts/start-all.ps1 -Autopilot
```

Refresh the watchlist from Yahoo (most active, day gainers, or day losers):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/update-watchlist.ps1
powershell -ExecutionPolicy Bypass -File scripts/update-watchlist.ps1 -Screener day_gainers -Count 20
powershell -ExecutionPolicy Bypass -File scripts/update-watchlist.ps1 -Merge -DryRun
```

Restart autopilot after updating `GTP_WATCHLIST`. Logs: `var/autopilot.log`.

### Trading without an IBKR account

Set `GTP_IBKR_USE_STUB=1` and `GTP_AUTOPILOT_IBKR=0` in `.env` (default for new setups). You get:

- Live agent consensus, macro (FRED), and Yahoo quotes
- Simulated order routing for **stocks, futures, options, and FX** tokens in `GTP_WATCHLIST`
- No IBKR signup or Gateway required

When ready for real paper broker routing, open a **free** [IBKR paper account](https://www.interactivebrokers.com), set `GTP_IBKR_USE_STUB=0`, start Gateway on port 7497, and enable trading permissions in Client Portal.

### Live data vs loading shell

| Source | Live? |
|--------|-------|
| Agent consensus, macro (FRED), IBKR positions/balances | Yes, after 30–60s refresh |
| First paint ("Loading live data…") | Temporary shell only |
| `GTP_PORTFOLIO_VALUE` | Config fallback when IBKR equity unavailable |
| Autopilot watchlist cycling | **Not in the web UI** — run `scripts/autopilot.ps1` in a terminal |

The web dashboard **Execute** dropdown picks one ticker from `GTP_WATCHLIST`. Autopilot loops the full watchlist on a schedule in a separate process.

### Options, futures, FX

Use **watchlist tokens** in `GTP_WATCHLIST` and `GTP_SIGNAL_TICKER`:

| Token | Asset |
|-------|--------|
| `AAPL` | Stock (default) |
| `ES:future:202506` | Futures (YYYYMM or YYYYMMDD expiry) |
| `AAPL:option:20250620:200:C` | Call option |
| `EURUSD:fx` | Forex |

Default contract fields in `.env` (used when omitted from token):

```env
GTP_ASSET_CLASS=equity
GTP_CONTRACT_EXCHANGE=GLOBEX
GTP_CONTRACT_EXPIRY=202506
GTP_OPTION_STRIKE=200
GTP_OPTION_RIGHT=C
```

Examples:

```env
GTP_WATCHLIST=AAPL,NVDA,ES:future:202506,EURUSD:fx
GTP_SIGNAL_TICKER=ES:future:202506
```

```powershell
crosspoint run-once --ticker "ES:future:202506" --ibkr
crosspoint run-once --ticker "AAPL:option:20250620:200:C" --ibkr
```

Agents score via Yahoo using the **underlying/continuous** symbol (`ES=F`, `AAPL`, `EURUSD=X`). IBKR orders use full contract specs.

### Public dashboard (ngrok + login)

Set a username/password in `.env`, restart the dashboard, then tunnel port 8050:

```powershell
ngrok http 8050
```

Visitors open your `https://….ngrok-free.app` URL, click through the ngrok warning once, then enter the dashboard login in the browser prompt. Set `GTP_DASHBOARD_AUTH_ENABLED=0` to disable login for local-only use.

### Deploy on Railway

The repo includes `Dockerfile.railway` and `railway.toml` for the **web dashboard only** (simulated trading — IBKR Gateway cannot run on Railway).

1. Push this repo to GitHub.
2. In [Railway](https://railway.com): **New Project → Deploy from GitHub repo**.
3. Railway detects `railway.toml` and builds `Dockerfile.railway`.
4. Add **Variables** (Settings → Variables) — do not commit secrets:

| Variable | Example |
|----------|---------|
| `FRED_API_KEY` | your FRED key |
| `GTP_IBKR_USE_STUB` | `1` |
| `GTP_WATCHLIST` | `AAPL,NVDA,ES:future:202609,EURUSD:fx` |
| `GTP_SIGNAL_TICKER` | `AAPL` |
| `GTP_DASHBOARD_AUTH_ENABLED` | `1` |
| `GTP_DASHBOARD_USER` | `crosspoint` |
| `GTP_DASHBOARD_PASSWORD` | strong password |
| `GTP_DASHBOARD_SECRET` | random secret string |
| `GTP_KILL_SWITCH` | `false` |

5. **Settings → Networking → Generate Domain** for a public HTTPS URL.
6. Open `https://your-app.up.railway.app/login` and sign in.

**Railway limits:**

- **No IBKR** — Gateway must run on your PC; cloud uses simulated orders (`GTP_IBKR_USE_STUB=1`).
- **Autopilot** — not included in the dashboard container; run `scripts/autopilot.ps1` locally or add a second Railway **worker** service later.
- **First load** — can take 30–60s while agents fetch data.
- **Disk** — SQLite audit log is ephemeral unless you attach a Railway volume at `/app/var`.

**CLI deploy (optional):**

```bash
npm i -g @railway/cli
railway login
railway link
railway up
```

---

## CLI Commands

```bash
# Core trading operations (live consensus by default)
crosspoint run-once
crosspoint run-once --ticker NVDA
crosspoint run-once --demo          # legacy DEMO signal only
crosspoint reconcile
fincept crypto-once
fincept metrics

# Enhanced AI agents
fincept agent --buffett --ticker AAPL
fincept agent --graham --ticker MSFT
fincept agent --lynch --ticker NVDA
fincept agent --dunlap --ticker GOOGL

# Analytics
fincept dcf --ticker AAPL
fincept portfolio-optimize
fincept risk-analysis

# Data connectors
fincept data --source yahoo --ticker SPY
fincept data --source fred --series GDP
fincept data --source kraken --pair BTC/USD
```

---

## Project Structure

```
src/
├── fincept_terminal/           # Enhanced FinceptTerminal engine
│   ├── analytics/             # CFA-level analytics
│   │   ├── dcf.py            # Discounted Cash Flow models
│   │   ├── portfolio.py      # Portfolio optimization
│   │   └── risk.py           # Risk metrics (VaR, Sharpe)
│   ├── agents/               # AI trading agents
│   │   ├── value_investors/  # Buffett, Graham, Lynch, Dunlap
│   │   └── base.py          # Base agent framework
│   ├── connectors/           # Data connectors
│   │   ├── yahoo_finance.py
│   │   ├── fred.py
│   │   ├── kraken.py
│   │   └── polygon.py
│   ├── quantlib/             # Quantitative analysis
│   │   ├── pricing.py
│   │   ├── risk.py
│   │   └── volatility.py
│   ├── trading/              # Real-time trading
│   │   ├── brokers/          # 16 broker integrations
│   │   ├── websocket.py      # Real-time data
│   │   └── execution.py
│   └── ui/                   # Qt6 interface
│       ├── dashboard.py
│       ├── node_editor.py
│       └── charts.py

---

## Contributing

We're building the future of automated trading — together.

**Contribute:** New trading strategies, data connectors, analytics modules, UI improvements

- [Report Bug](https://github.com/103softwaresolutionsllc-rgb/global-trading-platform/issues)
- [Request Feature](https://github.com/103softwaresolutionsllc-rgb/global-trading-platform/discussions)
- [Request Feature](https://github.com/Fincept-Corporation/FinceptTerminal/discussions)

---

## Technology Stack

### Core Technologies
- **Python 3.11+**: Core language and analytics
- **Qt6**: Modern cross-platform GUI framework
- **AsyncIO**: Real-time data processing and WebSocket handling
- **Pandas/NumPy**: Financial data analysis and modeling
- **SciPy**: Statistical analysis and optimization

### Financial Libraries
- **yfinance**: Yahoo Finance data integration
- **websockets**: Real-time market data streaming
- **QuantLib**: Advanced quantitative finance models
- **scikit-learn**: Machine learning for trading strategies

---

## Acknowledgments

**Enhanced with FinceptTerminal Technology**
This platform incorporates advanced analytics and AI agent frameworks inspired by FinceptTerminal's innovative approach to financial intelligence. The integration brings institutional-grade capabilities to our multi-agent trading system.

**Original Crosspoint Development**
- Multi-agent trading architecture
- Real-time risk management
- Broker integration framework
- Audit and reconciliation systems

---

## License

**Dual Licensed: AGPL-3.0 (Open Source) + Commercial**

### Open Source (AGPL-3.0)
- Free for personal, educational, and non-commercial use
- Requires sharing modifications when distributed or used as network service
- Full source code transparency

### Commercial License
- Required for business use or to access Fincept Data/APIs commercially
- Contact: **support@fincept.in**
- Details: [Commercial License Guide](https://github.com/Fincept-Corporation/FinceptTerminal/blob/main/docs/COMMERCIAL_LICENSE.md)

### Trademarks
"Fincept Terminal" and "Fincept" are trademarks of Fincept Corporation.

---

<div align="center">

### **Enterprise Trading Platform**
### **Enhanced with Advanced Analytics**

⭐ **Star** · 🔄 **Share** · 🤝 **Contribute**

</div>
