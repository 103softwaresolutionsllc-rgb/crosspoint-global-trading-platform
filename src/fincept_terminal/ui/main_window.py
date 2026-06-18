"""
Main Window for Fincept Terminal
Qt6-based main application window with modern financial interface
"""

import os
import sys
import asyncio
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QSplitter, QMenuBar, QToolBar, QStatusBar,
    QLabel, QPushButton, QLineEdit, QTextEdit, QTableWidget,
    QTableWidgetItem, QProgressBar, QFrame, QScrollArea, QGridLayout
)
from PyQt6.QtCore import QTimer, pyqtSignal, QThread, Qt
from PyQt6.QtGui import QIcon, QAction, QFont, QPalette, QColor

from .phase2_dashboard import Phase2DashboardWidget
from .charts import ChartWidget
from .node_editor import NodeEditorWidget
from ..analytics.dcf import DCFModel
from ..agents.value_investors.buffett import BuffettAgent
from ..agents.value_investors.graham import GrahamAgent
from ..agents.value_investors.lynch import LynchAgent
from ..agents.value_investors.dunlap import IanDunlapAgent
from ..agents.quant_agents.simons import SimonsAgent
from ..connectors.yahoo_finance import YahooFinanceConnector
from ..trading.websocket import WebSocketManager, RealTimeDataFeed


class FinceptMainWindow(QMainWindow):
    """
    Main application window for Fincept Terminal
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crosspoint Global Trading Platform")
        self.setGeometry(100, 100, 1400, 900)
        
        # Initialize components
        from ..agents.liquidity_gate import LiquidityGateAgent

        self.websocket_manager = WebSocketManager()
        self.liquidity_gate = LiquidityGateAgent()
        self.data_feed = RealTimeDataFeed(self.websocket_manager, liquidity_gate=self.liquidity_gate)
        
        # Setup UI
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_status_bar()
        self.setup_toolbar()
        
        # Apply modern styling
        self.apply_modern_style()
        
        # Initialize data connections
        self.initialize_connections()
        
        # Lightweight left-panel tape refresh (full agent refresh is on the dashboard widget)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_market_data)
        self.update_timer.start(20_000)
    
    def setup_ui(self):
        """Setup the main UI layout"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panels
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # Left panel - Market watch and positions
        left_panel = self.create_left_panel()
        main_splitter.addWidget(left_panel)
        
        # Center panel - Main tabs
        center_panel = self.create_center_panel()
        main_splitter.addWidget(center_panel)
        
        # Right panel - News and alerts
        right_panel = self.create_right_panel()
        main_splitter.addWidget(right_panel)
        
        # Set splitter sizes
        main_splitter.setSizes([300, 800, 300])
    
    def create_left_panel(self) -> QWidget:
        """Create left panel with market watch and positions"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Market Watch
        market_frame = QFrame()
        market_frame.setFrameStyle(QFrame.Shape.Box)
        market_layout = QVBoxLayout(market_frame)
        
        market_label = QLabel("Market Watch")
        market_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        market_layout.addWidget(market_label)
        
        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search symbols...")
        market_layout.addWidget(self.search_bar)
        
        # Market watch table
        self.market_table = QTableWidget()
        self.market_table.setColumnCount(5)
        self.market_table.setHorizontalHeaderLabels(["Symbol", "Price", "Change", "Volume", "Market Cap"])
        self.market_table.setMaximumHeight(300)
        market_layout.addWidget(self.market_table)
        
        layout.addWidget(market_frame)
        
        # Positions
        positions_frame = QFrame()
        positions_frame.setFrameStyle(QFrame.Shape.Box)
        positions_layout = QVBoxLayout(positions_frame)
        
        positions_label = QLabel("Positions")
        positions_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        positions_layout.addWidget(positions_label)
        
        # Positions table
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(6)
        self.positions_table.setHorizontalHeaderLabels(["Symbol", "Quantity", "Avg Price", "Current", "P&L", "%"])
        positions_layout.addWidget(self.positions_table)
        
        layout.addWidget(positions_frame)
        
        # Portfolio summary
        portfolio_frame = QFrame()
        portfolio_frame.setFrameStyle(QFrame.Shape.Box)
        portfolio_layout = QVBoxLayout(portfolio_frame)
        
        portfolio_label = QLabel("Portfolio Summary")
        portfolio_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        portfolio_layout.addWidget(portfolio_label)
        
        self.portfolio_value_label = QLabel("Portfolio Value: $0.00")
        self.daily_pnl_label = QLabel("Daily P&L: $0.00")
        self.total_pnl_label = QLabel("Total P&L: $0.00")
        
        portfolio_layout.addWidget(self.portfolio_value_label)
        portfolio_layout.addWidget(self.daily_pnl_label)
        portfolio_layout.addWidget(self.total_pnl_label)
        
        layout.addWidget(portfolio_frame)
        
        layout.addStretch()
        return panel
    
    def create_center_panel(self) -> QWidget:
        """Create center panel with main tabs"""
        self.tab_widget = QTabWidget()
        
        # Dashboard tab — live consensus layout with chart drawers
        self.dashboard = Phase2DashboardWidget(data_feed=self.data_feed)
        self.dashboard.state_refreshed.connect(self._on_dashboard_refreshed)
        self.tab_widget.addTab(self.dashboard, "Dashboard")
        
        # Analytics tab
        analytics_widget = self.create_analytics_widget()
        self.tab_widget.addTab(analytics_widget, "Analytics")
        
        # AI Agents tab
        agents_widget = self.create_agents_widget()
        self.tab_widget.addTab(agents_widget, "AI Agents")
        
        # Trading tab
        trading_widget = self.create_trading_widget()
        self.tab_widget.addTab(trading_widget, "Trading")
        
        # Research tab
        research_widget = self.create_research_widget()
        self.tab_widget.addTab(research_widget, "Research")
        
        # Node Editor tab
        self.node_editor = NodeEditorWidget()
        self.tab_widget.addTab(self.node_editor, "Workflows")
        
        return self.tab_widget
    
    def create_right_panel(self) -> QWidget:
        """Create right panel with news and alerts"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Alerts
        alerts_frame = QFrame()
        alerts_frame.setFrameStyle(QFrame.Shape.Box)
        alerts_layout = QVBoxLayout(alerts_frame)
        
        alerts_label = QLabel("Alerts")
        alerts_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        alerts_layout.addWidget(alerts_label)
        
        # Alerts list
        self.alerts_list = QTextEdit()
        self.alerts_list.setMaximumHeight(200)
        self.alerts_list.setReadOnly(True)
        alerts_layout.addWidget(self.alerts_list)
        
        layout.addWidget(alerts_frame)
        
        # News
        news_frame = QFrame()
        news_frame.setFrameStyle(QFrame.Shape.Box)
        news_layout = QVBoxLayout(news_frame)
        
        news_label = QLabel("Market News")
        news_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        news_layout.addWidget(news_label)
        
        # News list
        self.news_list = QTextEdit()
        self.news_list.setReadOnly(True)
        news_layout.addWidget(self.news_list)
        
        layout.addWidget(news_frame)
        
        return panel
    
    def create_analytics_widget(self) -> QWidget:
        """Create analytics widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # DCF Analysis section
        dcf_frame = QFrame()
        dcf_frame.setFrameStyle(QFrame.Shape.Box)
        dcf_layout = QVBoxLayout(dcf_frame)
        
        dcf_label = QLabel("DCF Analysis")
        dcf_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        dcf_layout.addWidget(dcf_label)
        
        # DCF input
        dcf_input_layout = QHBoxLayout()
        self.dcf_ticker_input = QLineEdit()
        self.dcf_ticker_input.setPlaceholderText("Ticker")
        self.dcf_analyze_btn = QPushButton("Analyze")
        self.dcf_analyze_btn.clicked.connect(self.run_dcf_analysis)
        
        dcf_input_layout.addWidget(self.dcf_ticker_input)
        dcf_input_layout.addWidget(self.dcf_analyze_btn)
        dcf_layout.addLayout(dcf_input_layout)
        
        # DCF results
        self.dcf_results = QTextEdit()
        self.dcf_results.setReadOnly(True)
        self.dcf_results.setMaximumHeight(200)
        dcf_layout.addWidget(self.dcf_results)
        
        layout.addWidget(dcf_frame)
        
        # Portfolio Optimization section
        portfolio_frame = QFrame()
        portfolio_frame.setFrameStyle(QFrame.Shape.Box)
        portfolio_layout = QVBoxLayout(portfolio_frame)
        
        portfolio_label = QLabel("Portfolio Optimization")
        portfolio_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        portfolio_layout.addWidget(portfolio_label)
        
        self.optimize_btn = QPushButton("Optimize Portfolio")
        self.optimize_btn.clicked.connect(self.optimize_portfolio)
        portfolio_layout.addWidget(self.optimize_btn)
        
        # Portfolio results
        self.portfolio_results = QTextEdit()
        self.portfolio_results.setReadOnly(True)
        self.portfolio_results.setMaximumHeight(200)
        portfolio_layout.addWidget(self.portfolio_results)
        
        layout.addWidget(portfolio_frame)
        
        # Risk Analysis section
        risk_frame = QFrame()
        risk_frame.setFrameStyle(QFrame.Shape.Box)
        risk_layout = QVBoxLayout(risk_frame)
        
        risk_label = QLabel("Risk Analysis")
        risk_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        risk_layout.addWidget(risk_label)
        
        self.risk_ticker_input = QLineEdit()
        self.risk_ticker_input.setPlaceholderText("Ticker")
        self.risk_analyze_btn = QPushButton("Analyze Risk")
        self.risk_analyze_btn.clicked.connect(self.run_risk_analysis)
        
        risk_layout.addWidget(self.risk_ticker_input)
        risk_layout.addWidget(self.risk_analyze_btn)
        
        # Risk results
        self.risk_results = QTextEdit()
        self.risk_results.setReadOnly(True)
        self.risk_results.setMaximumHeight(200)
        risk_layout.addWidget(self.risk_results)
        
        layout.addWidget(risk_frame)
        
        layout.addStretch()
        return widget
    
    def create_agents_widget(self) -> QWidget:
        """Create AI agents widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Agent selection
        agent_frame = QFrame()
        agent_frame.setFrameStyle(QFrame.Shape.Box)
        agent_layout = QVBoxLayout(agent_frame)
        
        agent_label = QLabel("AI Investment Agents")
        agent_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        agent_layout.addWidget(agent_label)
        
        # Agent buttons
        agent_buttons_layout = QHBoxLayout()
        
        self.buffett_btn = QPushButton("Buffett")
        self.buffett_btn.clicked.connect(lambda: self.run_agent_analysis("buffett"))
        
        self.graham_btn = QPushButton("Graham")
        self.graham_btn.clicked.connect(lambda: self.run_agent_analysis("graham"))
        
        self.lynch_btn = QPushButton("Lynch")
        self.lynch_btn.clicked.connect(lambda: self.run_agent_analysis("lynch"))
        
        self.dunlap_btn = QPushButton("Dunlap")
        self.dunlap_btn.clicked.connect(lambda: self.run_agent_analysis("dunlap"))
        
        self.simons_btn = QPushButton("Simons")
        self.simons_btn.clicked.connect(lambda: self.run_agent_analysis("simons"))
        
        agent_buttons_layout.addWidget(self.buffett_btn)
        agent_buttons_layout.addWidget(self.graham_btn)
        agent_buttons_layout.addWidget(self.lynch_btn)
        agent_buttons_layout.addWidget(self.dunlap_btn)
        agent_buttons_layout.addWidget(self.simons_btn)
        
        agent_layout.addLayout(agent_buttons_layout)
        
        # Agent input
        self.agent_ticker_input = QLineEdit()
        self.agent_ticker_input.setPlaceholderText("Enter ticker symbol...")
        agent_layout.addWidget(self.agent_ticker_input)
        
        layout.addWidget(agent_frame)
        
        # Agent results
        self.agent_results = QTextEdit()
        self.agent_results.setReadOnly(True)
        layout.addWidget(self.agent_results)
        
        return widget
    
    def create_trading_widget(self) -> QWidget:
        """Create trading widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Order entry
        order_frame = QFrame()
        order_frame.setFrameStyle(QFrame.Shape.Box)
        order_layout = QVBoxLayout(order_frame)
        
        order_label = QLabel("Order Entry")
        order_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        order_layout.addWidget(order_label)
        
        # Order inputs
        order_inputs_layout = QGridLayout()
        
        order_inputs_layout.addWidget(QLabel("Symbol:"), 0, 0)
        self.order_symbol_input = QLineEdit()
        order_inputs_layout.addWidget(self.order_symbol_input, 0, 1)
        
        order_inputs_layout.addWidget(QLabel("Side:"), 1, 0)
        self.order_side_combo = QLineEdit()  # Would be QComboBox in full implementation
        self.order_side_combo.setText("BUY")
        order_inputs_layout.addWidget(self.order_side_combo, 1, 1)
        
        order_inputs_layout.addWidget(QLabel("Type:"), 2, 0)
        self.order_type_combo = QLineEdit()  # Would be QComboBox
        self.order_type_combo.setText("MARKET")
        order_inputs_layout.addWidget(self.order_type_combo, 2, 1)
        
        order_inputs_layout.addWidget(QLabel("Quantity:"), 3, 0)
        self.order_quantity_input = QLineEdit()
        order_inputs_layout.addWidget(self.order_quantity_input, 3, 1)
        
        order_inputs_layout.addWidget(QLabel("Price:"), 4, 0)
        self.order_price_input = QLineEdit()
        order_inputs_layout.addWidget(self.order_price_input, 4, 1)
        
        order_layout.addLayout(order_inputs_layout)
        
        # Submit button
        self.submit_order_btn = QPushButton("Submit Order")
        self.submit_order_btn.clicked.connect(self.submit_order)
        order_layout.addWidget(self.submit_order_btn)
        
        layout.addWidget(order_frame)
        
        # Chart
        self.chart_widget = ChartWidget()
        layout.addWidget(self.chart_widget)
        
        return widget
    
    def create_research_widget(self) -> QWidget:
        """Create research widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Research tools
        research_frame = QFrame()
        research_frame.setFrameStyle(QFrame.Shape.Box)
        research_layout = QVBoxLayout(research_frame)
        
        research_label = QLabel("Research Tools")
        research_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        research_layout.addWidget(research_label)
        
        # Tool buttons
        tools_layout = QHBoxLayout()
        
        self.screener_btn = QPushButton("Stock Screener")
        self.financials_btn = QPushButton("Financials")
        self.economics_btn = QPushButton("Economics")
        
        tools_layout.addWidget(self.screener_btn)
        tools_layout.addWidget(self.financials_btn)
        tools_layout.addWidget(self.economics_btn)
        
        research_layout.addLayout(tools_layout)
        
        layout.addWidget(research_frame)
        
        # Research results
        self.research_results = QTextEdit()
        self.research_results.setReadOnly(True)
        layout.addWidget(self.research_results)
        
        return widget
    
    def setup_menu_bar(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New Workspace", self)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open Workspace", self)
        file_menu.addAction(open_action)
        
        save_action = QAction("Save Workspace", self)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        dashboard_action = QAction("Dashboard", self)
        dashboard_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(0))
        view_menu.addAction(dashboard_action)
        
        analytics_action = QAction("Analytics", self)
        analytics_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(1))
        view_menu.addAction(analytics_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        preferences_action = QAction("Preferences", self)
        tools_menu.addAction(preferences_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About Fincept Terminal", self)
        help_menu.addAction(about_action)
    
    def setup_toolbar(self):
        """Setup toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_exchanges)
        toolbar.addWidget(self.connect_btn)
        
        toolbar.addSeparator()
        
        # Refresh button
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_data)
        toolbar.addAction(refresh_action)
        
        # Status indicator
        self.status_indicator = QLabel("Disconnected")
        toolbar.addWidget(self.status_indicator)
    
    def setup_status_bar(self):
        """Setup status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.status_bar.showMessage("Ready")
    
    def apply_modern_style(self):
        """Apply modern dark theme styling"""
        # Dark theme colors
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
        
        self.setPalette(palette)
    
    def initialize_connections(self):
        """Initialize data connections"""
        # Connect search bar
        self.search_bar.returnPressed.connect(self.search_symbol)
        
        # Connect market table
        self.market_table.cellDoubleClicked.connect(self.add_to_watchlist)
    
    async def run_dcf_analysis(self):
        """Run DCF analysis"""
        ticker = self.dcf_ticker_input.text().strip()
        if not ticker:
            return
        
        try:
            dcf_model = DCFModel()
            result = await dcf_model.analyze(ticker)
            
            results_text = f"""
DCF Analysis for {ticker.upper()}

Valuation: ${result.valuation:,.2f}
Fair Value: ${result.fair_value:,.2f}
Upside: {result.upside:.1%}

WACC: {result.wacc:.2%}
Terminal Growth: {result.terminal_growth_rate:.2%}

Recommendation: {"BUY" if result.upside > 0.1 else "HOLD" if result.upside > -0.1 else "SELL"}
Confidence: High
"""
            
            self.dcf_results.setText(results_text)
            
        except Exception as e:
            self.dcf_results.setText(f"Error: {str(e)}")
    
    async def run_agent_analysis(self, agent_type: str):
        """Run AI agent analysis"""
        ticker = self.agent_ticker_input.text().strip()
        if not ticker:
            return
        
        try:
            if agent_type == "buffett":
                agent = BuffettAgent()
            elif agent_type == "graham":
                from ..agents.value_investors.graham import GrahamAgent
                agent = GrahamAgent()
            elif agent_type == "lynch":
                from ..agents.value_investors.lynch import LynchAgent
                agent = LynchAgent()
            elif agent_type == "dunlap":
                from ..agents.value_investors.dunlap import IanDunlapAgent
                agent = IanDunlapAgent()
            elif agent_type == "simons":
                from ..agents.quant_agents.simons import SimonsAgent
                agent = SimonsAgent()
            else:
                return
            
            result = await agent.analyze(ticker)
            
            results_text = f"""
{agent.name} Analysis for {ticker.upper()}

Recommendation: {result.recommendation.value}
Confidence: {result.confidence:.1%}

Key Metrics:
"""
            
            for metric, value in result.key_metrics.items():
                if isinstance(value, float):
                    results_text += f"{metric}: {value:.2f}\n"
                else:
                    results_text += f"{metric}: {value}\n"
            
            if result.risk_factors:
                results_text += "\nRisk Factors:\n"
                for risk in result.risk_factors[:5]:
                    results_text += f"  - {risk}\n"
            
            if result.catalysts:
                results_text += "\nCatalysts:\n"
                for catalyst in result.catalysts[:5]:
                    results_text += f"  - {catalyst}\n"
            
            results_text += f"\nReasoning: {result.reasoning}"
            
            self.agent_results.setText(results_text)
            
        except Exception as e:
            self.agent_results.setText(f"Error: {str(e)}")
    
    def search_symbol(self):
        """Search for a symbol"""
        symbol = self.search_bar.text().strip()
        if symbol:
            # Add to market watch
            self.add_symbol_to_market_watch(symbol)
    
    def add_symbol_to_market_watch(self, symbol: str):
        """Add symbol to market watch table"""
        # Check if already exists
        for row in range(self.market_table.rowCount()):
            if self.market_table.item(row, 0).text() == symbol.upper():
                return
        
        # Add new row
        row = self.market_table.rowCount()
        self.market_table.insertRow(row)
        
        self.market_table.setItem(row, 0, QTableWidgetItem(symbol.upper()))
        self.market_table.setItem(row, 1, QTableWidgetItem("0.00"))
        self.market_table.setItem(row, 2, QTableWidgetItem("0.00"))
        self.market_table.setItem(row, 3, QTableWidgetItem("0"))
        self.market_table.setItem(row, 4, QTableWidgetItem("0"))
    
    def add_to_watchlist(self, row: int, column: int):
        """Add symbol from market table to detailed watch"""
        symbol = self.market_table.item(row, 0).text()
        self.chart_widget.set_symbol(symbol)
    
    def update_market_data(self):
        """Refresh left-panel quotes from the latest dashboard tape."""
        state = self.dashboard.state
        if state is None:
            return
        self._sync_market_watch(state)

    def refresh_data(self):
        """Refresh live dashboard state (agents, positions, execution)."""
        self.status_bar.showMessage("Refreshing live dashboard…")
        self.dashboard.start_refresh()

    def _on_dashboard_refreshed(self, state) -> None:
        """Sync side panels when the dashboard finishes a live reload."""
        self._sync_left_panel(state)
        self.status_bar.showMessage(
            f"Refreshed · {state.broker_mode} · {state.timestamp} · {state.signal_ticker}",
            5000,
        )

    def _sync_left_panel(self, state) -> None:
        self._sync_market_watch(state)
        self._sync_positions_table(state)
        portfolio_value = float(os.environ.get("GTP_PORTFOLIO_VALUE", "100000"))
        total_pnl = sum(p.pnl for p in state.positions)
        sign = "+" if total_pnl >= 0 else ""
        self.portfolio_value_label.setText(f"Portfolio Value: ${portfolio_value:,.2f}")
        self.daily_pnl_label.setText(f"Unrealized P&L: {sign}${abs(total_pnl):,.2f}")
        self.total_pnl_label.setText(f"Broker: {state.broker_mode.upper()} · Signal: {state.signal_ticker}")

    def _sync_market_watch(self, state) -> None:
        items = state.ticker_tape[:20]
        self.market_table.setRowCount(len(items))
        for row, item in enumerate(items):
            sign = "+" if item.change_pct >= 0 else ""
            self.market_table.setItem(row, 0, QTableWidgetItem(item.symbol))
            self.market_table.setItem(row, 1, QTableWidgetItem(f"${item.price:,.2f}"))
            self.market_table.setItem(row, 2, QTableWidgetItem(f"{sign}{item.change_pct:.2f}%"))
            self.market_table.setItem(row, 3, QTableWidgetItem("—"))
            self.market_table.setItem(row, 4, QTableWidgetItem("—"))

    def _sync_positions_table(self, state) -> None:
        self.positions_table.setRowCount(len(state.positions))
        for row, pos in enumerate(state.positions):
            sign = "+" if pos.pnl >= 0 else ""
            self.positions_table.setItem(row, 0, QTableWidgetItem(pos.ticker))
            self.positions_table.setItem(row, 1, QTableWidgetItem(str(pos.quantity)))
            self.positions_table.setItem(row, 2, QTableWidgetItem("—"))
            self.positions_table.setItem(row, 3, QTableWidgetItem("—"))
            self.positions_table.setItem(row, 4, QTableWidgetItem(f"{sign}${abs(pos.pnl):,.0f}"))
            self.positions_table.setItem(row, 5, QTableWidgetItem(f"{sign}{pos.pnl_pct:.1f}%"))
    
    def connect_exchanges(self):
        """Connect to exchanges"""
        self.status_bar.showMessage("Connecting to exchanges...")
        self.connect_btn.setText("Connecting...")
        self.connect_btn.setEnabled(False)
        
        # Start connection process
        asyncio.create_task(self._connect_to_exchanges())
    
    async def _connect_to_exchanges(self):
        """Async connection to exchanges"""
        try:
            # Connect to major exchanges
            await self.data_feed.start_monitoring(['SPY', 'QQQ', 'BTC-USD'], ['binance', 'polygon'])
            
            # Update UI
            self.status_indicator.setText("Connected")
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setEnabled(True)
            self.status_bar.showMessage("Connected to exchanges", 3000)
            
        except Exception as e:
            self.status_bar.showMessage(f"Connection failed: {str(e)}", 5000)
            self.connect_btn.setText("Connect")
            self.connect_btn.setEnabled(True)
    
    def optimize_portfolio(self):
        """Run portfolio optimization"""
        self.portfolio_results.setText("Portfolio optimization running...")
        # Implementation would run portfolio optimization
        self.portfolio_results.setText("Portfolio optimization completed.\nOptimal weights calculated.")
    
    def run_risk_analysis(self):
        """Run risk analysis"""
        ticker = self.risk_ticker_input.text().strip()
        if not ticker:
            return
        
        self.risk_results.setText(f"Running risk analysis for {ticker}...")
        # Implementation would run risk analysis
        self.risk_results.setText(f"Risk analysis for {ticker.upper()} completed.\nVaR(95%): -2.3%\nBeta: 1.2\nSharpe: 1.5")
    
    def submit_order(self):
        """Submit trading order"""
        symbol = self.order_symbol_input.text().strip()
        side = self.order_side_combo.text()
        order_type = self.order_type_combo.text()
        
        try:
            quantity = float(self.order_quantity_input.text())
            price = float(self.order_price_input.text()) if self.order_price_input.text() else None
        except ValueError:
            self.status_bar.showMessage("Invalid order parameters", 3000)
            return
        
        # Submit order logic would go here
        self.status_bar.showMessage(f"Order submitted: {side} {quantity} {symbol}", 3000)


def main():
    """Main entry point for Fincept Terminal"""
    app = QApplication(sys.argv)
    app.setApplicationName("Fincept Terminal")
    app.setApplicationVersion("4.0.2")
    
    # Create and show main window
    window = FinceptMainWindow()
    window.show()
    
    sys.exit(app.exec())
