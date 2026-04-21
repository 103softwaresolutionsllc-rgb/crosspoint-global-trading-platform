# Fincept Terminal

<div align="center">

[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-C06524)](https://github.com/Fincept-Corporation/FinceptTerminal/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Qt6](https://img.shields.io/badge/Qt-6-41CD52?logo=qt&logoColor=white)](https://www.qt.io/)

### **Your Thinking is the Only Limit. The Data Isn't.**

State-of-the-art financial intelligence platform with CFA-level analytics, AI automation, and unlimited data connectivity.

[📥 Download](https://github.com/Fincept-Corporation/FinceptTerminal/releases) · [📚 Docs](https://github.com/Fincept-Corporation/FinceptTerminal/tree/main/docs) · [💬 Discussions](https://github.com/Fincept-Corporation/FinceptTerminal/discussions) · [💬 Discord](https://discord.gg/ae87a8ygbN) · [🤝 Partner](https://github.com/Fincept-Corporation/FinceptTerminal/blob/main/docs/COMMERCIAL_LICENSE.md)

</div>

---

## About

**Fincept Terminal v4** is a comprehensive financial intelligence platform combining Python analytics, Qt6 UI, and embedded AI agents. It delivers Bloomberg-terminal-class performance with unlimited data connectivity and CFA-level analytics.

---

## Features

| **Feature** | **Description** |
|-------------|-----------------|
| 📊 **CFA-Level Analytics** | DCF models, portfolio optimization, risk metrics (VaR, Sharpe), derivatives pricing via embedded Python |
| 🤖 **AI Agents** | 37 agents across Trader/Investor (Buffett, Graham, Lynch, Munger, Klarman, Marks…), Economic, and Geopolitics frameworks; local LLM support; multi-provider (OpenAI, Anthropic, Gemini, Groq, DeepSeek, MiniMax, OpenRouter, Ollama) |
| 🌐 **100+ Data Connectors** | DBnomics, Polygon, Kraken, Yahoo Finance, FRED, IMF, World Bank, AkShare, government APIs, plus optional alternative-data overlays such as Adanos market sentiment for equity research |
| 📈 **Real-Time Trading** | Crypto (Kraken/HyperLiquid WebSocket), equity, algo trading, paper trading engine, 16 broker integrations (Zerodha, Angel One, Upstox, Fyers, Dhan, Groww, Kotak, IIFL, 5paisa, AliceBlue, Shoonya, Motilal, IBKR, Alpaca, Tradier, Saxo) |
| 🔬 **QuantLib Suite** | 18 quantitative analysis modules — pricing, risk, stochastic, volatility, fixed income |
| 🚢 **Global Intelligence** | Maritime tracking, geopolitical analysis, relationship mapping, satellite data |
| 🎨 **Visual Workflows** | Node editor for automation pipelines, MCP tool integration |
| 🧠 **AI Quant Lab** | ML models, factor discovery, HFT, reinforcement learning trading |

---

## Installation

### Quick Start (Python-based)

```bash
# Clone and setup
git clone https://github.com/Fincept-Corporation/FinceptTerminal.git
cd FinceptTerminal
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

---

## CLI Commands

```bash
# Core trading operations
fincept run-once
fincept reconcile
fincept crypto-once
fincept metrics

# AI agents
fincept agent --buffett
fincept agent --graham
fincept agent --lynch

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
├── fincept_terminal/           # Main application
│   ├── analytics/             # CFA-level analytics
│   │   ├── dcf.py            # Discounted Cash Flow models
│   │   ├── portfolio.py      # Portfolio optimization
│   │   └── risk.py           # Risk metrics (VaR, Sharpe)
│   ├── agents/               # AI trading agents
│   │   ├── value_investors/  # Buffett, Graham, Lynch
│   │   ├── quant_agents/     # Quantitative strategies
│   │   └── macro_agents/     # Economic/geopolitical
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
```

---

## Contributing

We're building the future of financial analysis — together.

**Contribute:** New data connectors, AI agents, analytics modules, UI components, documentation

- [Contributing Guide](docs/CONTRIBUTING.md)
- [Python Contributor Guide](docs/PYTHON_CONTRIBUTOR_GUIDE.md)
- [Report Bug](https://github.com/Fincept-Corporation/FinceptTerminal/issues)
- [Request Feature](https://github.com/Fincept-Corporation/FinceptTerminal/discussions)

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

© 2025-2026 Fincept Corporation. All rights reserved.

---

<div align="center">

### **Your Thinking is the Only Limit. The Data Isn't.**

⭐ **Star** · 🔄 **Share** · 🤝 **Contribute**

</div>
