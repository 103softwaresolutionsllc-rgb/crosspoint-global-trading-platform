"""
Dashboard Widget for Fincept Terminal
Main dashboard with real-time charts and market overview
"""

import asyncio
from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QFrame, QPushButton, QTableWidget, QTableWidgetItem,
    QProgressBar, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import QTimer, pyqtSignal, Qt, QThread
from PyQt6.QtGui import QFont, QPainter, QColor, QPen

from .charts import ChartWidget
from ..trading.websocket import RealTimeDataFeed, MarketData


class MetricCard(QFrame):
    """Card widget for displaying key metrics"""
    
    def __init__(self, title: str, value: str, change: str = "", color: str = "white"):
        super().__init__()
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 8px;
                padding: 10px;
            }}
            QLabel {{
                color: {color};
                font-family: Arial;
            }}
        """)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10))
        title_label.setStyleSheet("color: #888;")
        layout.addWidget(title_label)
        
        # Value
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        layout.addWidget(value_label)
        
        # Change
        if change:
            change_label = QLabel(change)
            change_label.setFont(QFont("Arial", 10))
            if "+" in change:
                change_label.setStyleSheet("color: #4CAF50;")
            elif "-" in change:
                change_label.setStyleSheet("color: #F44336;")
            layout.addWidget(change_label)


class MarketOverviewWidget(QWidget):
    """Market overview widget with key indices"""
    
    def __init__(self, data_feed: RealTimeDataFeed):
        super().__init__()
        self.data_feed = data_feed
        self.setup_ui()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_market_data)
        self.update_timer.start(5000)  # Update every 5 seconds
    
    def setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Market Overview")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: white; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Market cards grid
        cards_layout = QGridLayout()
        
        # Create market cards
        self.spy_card = MetricCard("S&P 500", "4,500.00", "+1.2%", "#4CAF50")
        self.qqq_card = MetricCard("NASDAQ", "14,200.00", "+1.8%", "#4CAF50")
        self.dia_card = MetricCard("DOW JONES", "35,000.00", "+0.8%", "#4CAF50")
        self.vix_card = MetricCard("VIX", "18.50", "-2.3%", "#F44336")
        
        cards_layout.addWidget(self.spy_card, 0, 0)
        cards_layout.addWidget(self.qqq_card, 0, 1)
        cards_layout.addWidget(self.dia_card, 1, 0)
        cards_layout.addWidget(self.vix_card, 1, 1)
        
        layout.addLayout(cards_layout)
        
        # Add some sample watchlist stocks
        watchlist_title = QLabel("Watchlist")
        watchlist_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        watchlist_title.setStyleSheet("color: white; margin: 10px 0;")
        layout.addWidget(watchlist_title)
        
        # Watchlist table
        self.watchlist_table = QTableWidget()
        self.watchlist_table.setColumnCount(4)
        self.watchlist_table.setHorizontalHeaderLabels(["Symbol", "Price", "Change", "Volume"])
        self.watchlist_table.setMaximumHeight(200)
        self.watchlist_table.setStyleSheet("""
            QTableWidget {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
                gridline-color: #444;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #333;
                color: white;
                padding: 5px;
                border: 1px solid #555;
            }
        """)
        
        # Add sample data
        self.add_watchlist_symbol("AAPL", "175.50", "+2.3%", "45.2M")
        self.add_watchlist_symbol("MSFT", "380.25", "+1.1%", "22.8M")
        self.add_watchlist_symbol("GOOGL", "142.80", "-0.5%", "15.6M")
        self.add_watchlist_symbol("AMZN", "145.30", "+1.7%", "38.9M")
        
        layout.addWidget(self.watchlist_table)
    
    def add_watchlist_symbol(self, symbol: str, price: str, change: str, volume: str):
        """Add a symbol to the watchlist"""
        row = self.watchlist_table.rowCount()
        self.watchlist_table.insertRow(row)
        
        self.watchlist_table.setItem(row, 0, QTableWidgetItem(symbol))
        self.watchlist_table.setItem(row, 1, QTableWidgetItem(price))
        
        change_item = QTableWidgetItem(change)
        if "+" in change:
            change_item.setStyleSheet("color: #4CAF50;")
        elif "-" in change:
            change_item.setStyleSheet("color: #F44336;")
        self.watchlist_table.setItem(row, 2, change_item)
        
        self.watchlist_table.setItem(row, 3, QTableWidgetItem(volume))
    
    def update_market_data(self):
        """Update market data"""
        # This would fetch real data from the data feed
        pass


class PortfolioWidget(QWidget):
    """Portfolio overview widget"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Portfolio Overview")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: white; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Portfolio metrics
        metrics_layout = QGridLayout()
        
        self.total_value_label = QLabel("Total Value: $125,000")
        self.total_value_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.total_value_label.setStyleSheet("color: #4CAF50;")
        metrics_layout.addWidget(self.total_value_label, 0, 0)
        
        self.daily_pnl_label = QLabel("Daily P&L: +$1,250 (+1.0%)")
        self.daily_pnl_label.setFont(QFont("Arial", 12))
        self.daily_pnl_label.setStyleSheet("color: #4CAF50;")
        metrics_layout.addWidget(self.daily_pnl_label, 0, 1)
        
        self.total_pnl_label = QLabel("Total P&L: +$15,000 (+13.6%)")
        self.total_pnl_label.setFont(QFont("Arial", 12))
        self.total_pnl_label.setStyleSheet("color: #4CAF50;")
        metrics_layout.addWidget(self.total_pnl_label, 1, 0)
        
        self.cash_label = QLabel("Cash: $12,500")
        self.cash_label.setFont(QFont("Arial", 12))
        self.cash_label.setStyleSheet("color: white;")
        metrics_layout.addWidget(self.cash_label, 1, 1)
        
        layout.addLayout(metrics_layout)
        
        # Positions table
        positions_title = QLabel("Top Positions")
        positions_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        positions_title.setStyleSheet("color: white; margin: 10px 0;")
        layout.addWidget(positions_title)
        
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(5)
        self.positions_table.setHorizontalHeaderLabels(["Symbol", "Shares", "Avg Price", "Current", "P&L"])
        self.positions_table.setMaximumHeight(200)
        self.positions_table.setStyleSheet("""
            QTableWidget {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
                gridline-color: #444;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #333;
                color: white;
                padding: 5px;
                border: 1px solid #555;
            }
        """)
        
        # Add sample positions
        self.add_position("AAPL", 50, 165.20, 175.50, "+$515.00")
        self.add_position("MSFT", 30, 350.00, 380.25, "+$907.50")
        self.add_position("GOOGL", 25, 135.80, 142.80, "+$175.00")
        self.add_position("BRK.B", 10, 320.50, 345.00, "+$245.00")
        
        layout.addWidget(self.positions_table)
    
    def add_position(self, symbol: str, shares: str, avg_price: str, current: str, pnl: str):
        """Add a position to the table"""
        row = self.positions_table.rowCount()
        self.positions_table.insertRow(row)
        
        self.positions_table.setItem(row, 0, QTableWidgetItem(symbol))
        self.positions_table.setItem(row, 1, QTableWidgetItem(shares))
        self.positions_table.setItem(row, 2, QTableWidgetItem(avg_price))
        self.positions_table.setItem(row, 3, QTableWidgetItem(current))
        
        pnl_item = QTableWidgetItem(pnl)
        if "+" in pnl:
            pnl_item.setStyleSheet("color: #4CAF50;")
        elif "-" in pnl:
            pnl_item.setStyleSheet("color: #F44336;")
        self.positions_table.setItem(row, 4, pnl_item)


class DashboardWidget(QWidget):
    """Main dashboard widget combining all components"""
    
    def __init__(self, data_feed: RealTimeDataFeed):
        super().__init__()
        self.data_feed = data_feed
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dashboard UI"""
        layout = QVBoxLayout(self)
        
        # Top section - Market Overview and Portfolio
        top_layout = QHBoxLayout()
        
        # Market overview (left)
        self.market_overview = MarketOverviewWidget(self.data_feed)
        self.market_overview.setMaximumWidth(400)
        top_layout.addWidget(self.market_overview)
        
        # Portfolio overview (right)
        self.portfolio_widget = PortfolioWidget()
        self.portfolio_widget.setMaximumWidth(400)
        top_layout.addWidget(self.portfolio_widget)
        
        # Chart (center)
        self.chart_widget = ChartWidget()
        top_layout.addWidget(self.chart_widget)
        
        layout.addLayout(top_layout)
        
        # Bottom section - Recent Activity and News
        bottom_layout = QHBoxLayout()
        
        # Recent activity
        activity_frame = QFrame()
        activity_frame.setFrameStyle(QFrame.Shape.Box)
        activity_frame.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        activity_layout = QVBoxLayout(activity_frame)
        
        activity_title = QLabel("Recent Activity")
        activity_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        activity_title.setStyleSheet("color: white;")
        activity_layout.addWidget(activity_title)
        
        # Activity list (simplified)
        activity_text = """
        09:30: BUY 100 SPY @ $450.25
        09:45: SELL 50 QQQ @ $420.10
        10:15: BUY 25 AAPL @ $175.30
        10:30: DCF Analysis: AAPL - BUY
        10:45: Buffett Agent: MSFT - BUY
        11:00: Risk Analysis: Portfolio - OK
        """
        
        activity_label = QLabel(activity_text.strip())
        activity_label.setStyleSheet("color: white; font-family: monospace; font-size: 10px;")
        activity_layout.addWidget(activity_label)
        
        bottom_layout.addWidget(activity_frame)
        
        # Market news
        news_frame = QFrame()
        news_frame.setFrameStyle(QFrame.Shape.Box)
        news_frame.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        news_layout = QVBoxLayout(news_frame)
        
        news_title = QLabel("Market News")
        news_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        news_title.setStyleSheet("color: white;")
        news_layout.addWidget(news_title)
        
        # News list (simplified)
        news_text = """
        Fed Signals Rate Hold Amid Economic Uncertainty
        Tech Stocks Rally on AI Optimism
        Oil Prices Surge on Supply Concerns
        Bitcoin Reaches New Monthly High
        Earnings Season Beats Expectations
        """
        
        news_label = QLabel(news_text.strip())
        news_label.setStyleSheet("color: white; font-size: 10px;")
        news_layout.addWidget(news_label)
        
        bottom_layout.addWidget(news_frame)
        
        layout.addLayout(bottom_layout)
        
        # Set stretch factors
        top_layout.setStretch(0, 1)
        top_layout.setStretch(1, 1)
        top_layout.setStretch(2, 2)
        
        bottom_layout.setStretch(0, 1)
        bottom_layout.setStretch(1, 1)
    
    def update_dashboard(self):
        """Update all dashboard components"""
        # This would update all components with real data
        self.market_overview.update_market_data()
        # Update other components as needed
