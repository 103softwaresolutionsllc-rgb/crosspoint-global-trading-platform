"""
Charts Widget for Fincept Terminal
Real-time financial charts with technical indicators
"""

import asyncio
from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox
from PyQt6.QtCore import QTimer, pyqtSignal, Qt, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QPainterPath
import numpy as np


class ChartWidget(QWidget):
    """Real-time financial chart widget"""
    
    def __init__(self):
        super().__init__()
        self.current_symbol = "SPY"
        self.price_data = []
        self.volume_data = []
        self.indicators = {}
        self.time_range = "1D"  # 1D, 1W, 1M, 3M, 1Y
        
        self.setup_ui()
        self.setup_chart_data()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_chart)
        self.update_timer.start(1000)  # Update every second
    
    def setup_ui(self):
        """Setup the chart UI"""
        layout = QVBoxLayout(self)
        
        # Chart controls
        controls_layout = QHBoxLayout()
        
        # Symbol selector
        self.symbol_label = QLabel("Symbol:")
        self.symbol_label.setStyleSheet("color: white;")
        controls_layout.addWidget(self.symbol_label)
        
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "BTC-USD"])
        self.symbol_combo.setCurrentText(self.current_symbol)
        self.symbol_combo.currentTextChanged.connect(self.change_symbol)
        controls_layout.addWidget(self.symbol_combo)
        
        # Time range selector
        self.range_label = QLabel("Range:")
        self.range_label.setStyleSheet("color: white;")
        controls_layout.addWidget(self.range_label)
        
        self.range_combo = QComboBox()
        self.range_combo.addItems(["1D", "1W", "1M", "3M", "1Y"])
        self.range_combo.setCurrentText(self.time_range)
        self.range_combo.currentTextChanged.connect(self.change_time_range)
        controls_layout.addWidget(self.range_combo)
        
        # Indicator buttons
        self.sma_btn = QPushButton("SMA")
        self.sma_btn.setCheckable(True)
        self.sma_btn.clicked.connect(lambda: self.toggle_indicator("SMA"))
        controls_layout.addWidget(self.sma_btn)
        
        self.rsi_btn = QPushButton("RSI")
        self.rsi_btn.setCheckable(True)
        self.rsi_btn.clicked.connect(lambda: self.toggle_indicator("RSI"))
        controls_layout.addWidget(self.rsi_btn)
        
        self.macd_btn = QPushButton("MACD")
        self.macd_btn.setCheckable(True)
        self.macd_btn.clicked.connect(lambda: self.toggle_indicator("MACD"))
        controls_layout.addWidget(self.macd_btn)
        
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Current price display
        self.price_label = QLabel("$4,500.00")
        self.price_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.price_label.setStyleSheet("color: white;")
        layout.addWidget(self.price_label)
        
        # Change display
        self.change_label = QLabel("+$45.00 (+1.0%)")
        self.change_label.setFont(QFont("Arial", 12))
        self.change_label.setStyleSheet("color: #4CAF50;")
        layout.addWidget(self.change_label)
        
        # Chart area
        self.chart_area = QWidget()
        self.chart_area.setMinimumHeight(300)
        self.chart_area.setStyleSheet("background-color: #1e1e1e; border: 1px solid #555;")
        layout.addWidget(self.chart_area)
        
        # Volume chart area
        self.volume_area = QWidget()
        self.volume_area.setMinimumHeight(100)
        self.volume_area.setStyleSheet("background-color: #1e1e1e; border: 1px solid #555;")
        layout.addWidget(self.volume_area)
    
    def setup_chart_data(self):
        """Setup initial chart data"""
        # Generate sample data
        np.random.seed(42)
        base_price = 4500
        
        for i in range(100):
            # Simulate price movement
            change = np.random.normal(0, 0.01)  # 1% daily volatility
            new_price = base_price * (1 + change)
            self.price_data.append(new_price)
            base_price = new_price
            
            # Generate volume data
            volume = np.random.randint(1000000, 5000000)
            self.volume_data.append(volume)
    
    def set_symbol(self, symbol: str):
        """Set the current symbol"""
        self.current_symbol = symbol
        self.symbol_combo.setCurrentText(symbol)
        self.setup_chart_data()
        self.update()
    
    def change_symbol(self, symbol: str):
        """Handle symbol change"""
        self.current_symbol = symbol
        self.setup_chart_data()
        self.update()
    
    def change_time_range(self, time_range: str):
        """Handle time range change"""
        self.time_range = time_range
        self.setup_chart_data()
        self.update()
    
    def toggle_indicator(self, indicator: str):
        """Toggle technical indicator"""
        if indicator in self.indicators:
            del self.indicators[indicator]
        else:
            self.indicators[indicator] = self.calculate_indicator(indicator)
        self.update()
    
    def calculate_indicator(self, indicator: str) -> List[float]:
        """Calculate technical indicator"""
        prices = np.array(self.price_data)
        
        if indicator == "SMA":
            # Simple Moving Average (20 period)
            window = 20
            sma = []
            for i in range(len(prices)):
                if i >= window - 1:
                    avg = np.mean(prices[i-window+1:i+1])
                    sma.append(avg)
                else:
                    sma.append(prices[i])
            return sma
        
        elif indicator == "RSI":
            # Relative Strength Index (14 period)
            rsi = []
            window = 14
            
            for i in range(len(prices)):
                if i >= window:
                    gains = []
                    losses = []
                    
                    for j in range(i-window+1, i+1):
                        change = prices[j] - prices[j-1]
                        if change > 0:
                            gains.append(change)
                        else:
                            losses.append(abs(change))
                    
                    avg_gain = np.mean(gains) if gains else 0
                    avg_loss = np.mean(losses) if losses else 0
                    
                    if avg_loss > 0:
                        rs = avg_gain / avg_loss
                        rsi_value = 100 - (100 / (1 + rs))
                    else:
                        rsi_value = 100
                    
                    rsi.append(rsi_value)
                else:
                    rsi.append(50)  # Neutral
            
            return rsi
        
        elif indicator == "MACD":
            # MACD (12, 26, 9)
            ema12 = self.calculate_ema(prices, 12)
            ema26 = self.calculate_ema(prices, 26)
            
            macd_line = [ema12[i] - ema26[i] for i in range(len(ema12))]
            signal_line = self.calculate_ema(np.array(macd_line), 9)
            
            return macd_line
        
        return []
    
    def calculate_ema(self, prices: np.ndarray, window: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        multiplier = 2 / (window + 1)
        ema = []
        
        # Start with SMA
        ema.append(np.mean(prices[:window]))
        
        # Calculate EMA
        for i in range(window, len(prices)):
            ema_value = (prices[i] * multiplier) + (ema[-1] * (1 - multiplier))
            ema.append(ema_value)
        
        return ema
    
    def update_chart(self):
        """Update the chart display"""
        self.update()
    
    def paintEvent(self, event):
        """Paint the chart"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw main chart
        self.draw_price_chart(painter)
        
        # Draw volume chart
        self.draw_volume_chart(painter)
    
    def draw_price_chart(self, painter: QPainter):
        """Draw the price chart"""
        # Chart area
        chart_rect = QRectF(50, 80, self.width() - 100, 250)
        
        # Background
        painter.fillRect(chart_rect, QColor(30, 30, 30))
        
        # Grid lines
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        
        # Horizontal grid lines
        for i in range(5):
            y = chart_rect.top() + (chart_rect.height() / 4) * i
            painter.drawLine(chart_rect.left(), y, chart_rect.right(), y)
        
        # Vertical grid lines
        for i in range(6):
            x = chart_rect.left() + (chart_rect.width() / 5) * i
            painter.drawLine(x, chart_rect.top(), x, chart_rect.bottom())
        
        if not self.price_data:
            return
        
        # Price data
        prices = np.array(self.price_data)
        min_price = np.min(prices)
        max_price = np.max(prices)
        price_range = max_price - min_price
        
        if price_range == 0:
            price_range = 1
        
        # Draw price line
        painter.setPen(QPen(QColor(0, 255, 100), 2))
        
        path = QPainterPath()
        
        for i, price in enumerate(prices):
            x = chart_rect.left() + (chart_rect.width() / len(prices)) * i
            y = chart_rect.bottom() - ((price - min_price) / price_range) * chart_rect.height()
            
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        
        painter.drawPath(path)
        
        # Draw indicators
        if "SMA" in self.indicators:
            sma_data = self.indicators["SMA"]
            painter.setPen(QPen(QColor(255, 165, 0), 2))
            
            sma_path = QPainterPath()
            for i, sma_value in enumerate(sma_data):
                x = chart_rect.left() + (chart_rect.width() / len(sma_data)) * i
                y = chart_rect.bottom() - ((sma_value - min_price) / price_range) * chart_rect.height()
                
                if i == 0:
                    sma_path.moveTo(x, y)
                else:
                    sma_path.lineTo(x, y)
            
            painter.drawPath(sma_path)
        
        # Draw RSI in separate area if enabled
        if "RSI" in self.indicators:
            rsi_rect = QRectF(chart_rect.left(), chart_rect.bottom() + 10, chart_rect.width(), 50)
            painter.fillRect(rsi_rect, QColor(30, 30, 30))
            
            rsi_data = self.indicators["RSI"]
            painter.setPen(QPen(QColor(255, 255, 0), 1))
            
            rsi_path = QPainterPath()
            for i, rsi_value in enumerate(rsi_data):
                x = rsi_rect.left() + (rsi_rect.width() / len(rsi_data)) * i
                y = rsi_rect.bottom() - (rsi_value / 100) * rsi_rect.height()
                
                if i == 0:
                    rsi_path.moveTo(x, y)
                else:
                    rsi_path.lineTo(x, y)
            
            painter.drawPath(rsi_path)
            
            # RSI levels
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.drawLine(rsi_rect.left(), rsi_rect.top() + rsi_rect.height() * 0.3, 
                           rsi_rect.right(), rsi_rect.top() + rsi_rect.height() * 0.3)
            painter.drawLine(rsi_rect.left(), rsi_rect.top() + rsi_rect.height() * 0.7, 
                           rsi_rect.right(), rsi_rect.top() + rsi_rect.height() * 0.7)
        
        # Y-axis labels
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.setFont(QFont("Arial", 8))
        
        for i in range(5):
            price_value = max_price - (price_range / 4) * i
            y = chart_rect.top() + (chart_rect.height() / 4) * i
            painter.drawText(5, y + 3, f"${price_value:.2f}")
        
        # Current price line
        current_price = prices[-1]
        current_y = chart_rect.bottom() - ((current_price - min_price) / price_range) * chart_rect.height()
        
        painter.setPen(QPen(QColor(255, 255, 255), 1, Qt.PenStyle.DashLine))
        painter.drawLine(chart_rect.left(), current_y, chart_rect.right(), current_y)
        
        painter.drawText(chart_rect.right() + 5, current_y + 3, f"${current_price:.2f}")
    
    def draw_volume_chart(self, painter: QPainter):
        """Draw the volume chart"""
        volume_rect = QRectF(50, 380, self.width() - 100, 80)
        
        # Background
        painter.fillRect(volume_rect, QColor(30, 30, 30))
        
        if not self.volume_data:
            return
        
        # Volume data
        volumes = np.array(self.volume_data)
        max_volume = np.max(volumes)
        
        if max_volume == 0:
            max_volume = 1
        
        # Draw volume bars
        bar_width = volume_rect.width() / len(volumes)
        
        for i, volume in enumerate(volumes):
            x = volume_rect.left() + bar_width * i
            bar_height = (volume / max_volume) * volume_rect.height()
            y = volume_rect.bottom() - bar_height
            
            # Color based on price change
            if i > 0 and self.price_data[i] > self.price_data[i-1]:
                color = QColor(0, 200, 0)  # Green
            else:
                color = QColor(200, 0, 0)  # Red
            
            painter.fillRect(x, y, bar_width - 1, bar_height, color)
        
        # Volume label
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(5, volume_rect.center().y(), "Volume")
        
        # Max volume label
        painter.drawText(volume_rect.right() + 5, volume_rect.top() + 10, f"{max_volume:,.0f}")


class TechnicalChart(ChartWidget):
    """Advanced technical analysis chart"""
    
    def __init__(self):
        super().__init__()
        self.show_candlesticks = True
        self.show_grid = True
        
    def paintEvent(self, event):
        """Paint the technical chart with candlesticks"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.show_candlesticks:
            self.draw_candlestick_chart(painter)
        else:
            self.draw_price_chart(painter)
        
        self.draw_volume_chart(painter)
    
    def draw_candlestick_chart(self, painter: QPainter):
        """Draw candlestick chart"""
        chart_rect = QRectF(50, 80, self.width() - 100, 250)
        
        # Background
        painter.fillRect(chart_rect, QColor(30, 30, 30))
        
        if not self.price_data:
            return
        
        # Generate OHLC data from close prices (simplified)
        ohlc_data = []
        for i in range(len(self.price_data)):
            close = self.price_data[i]
            # Simulate OHLC
            high = close * (1 + np.random.uniform(0, 0.02))
            low = close * (1 - np.random.uniform(0, 0.02))
            open_price = close * (1 + np.random.uniform(-0.01, 0.01))
            
            ohlc_data.append((open_price, high, low, close))
        
        # Price range
        all_prices = [item[1] for item in ohlc_data] + [item[2] for item in ohlc_data]
        min_price = min(all_prices)
        max_price = max(all_prices)
        price_range = max_price - min_price
        
        if price_range == 0:
            price_range = 1
        
        # Draw candlesticks
        candle_width = max(1, (chart_rect.width() / len(ohlc_data)) * 0.8)
        
        for i, (open_price, high, low, close) in enumerate(ohlc_data):
            x = chart_rect.left() + (chart_rect.width() / len(ohlc_data)) * i + candle_width / 2
            
            # Wick
            wick_top = chart_rect.bottom() - ((high - min_price) / price_range) * chart_rect.height()
            wick_bottom = chart_rect.bottom() - ((low - min_price) / price_range) * chart_rect.height()
            
            if close >= open_price:
                # Green candle
                color = QColor(0, 200, 0)
                body_top = chart_rect.bottom() - ((close - min_price) / price_range) * chart_rect.height()
                body_bottom = chart_rect.bottom() - ((open_price - min_price) / price_range) * chart_rect.height()
            else:
                # Red candle
                color = QColor(200, 0, 0)
                body_top = chart_rect.bottom() - ((open_price - min_price) / price_range) * chart_rect.height()
                body_bottom = chart_rect.bottom() - ((close - min_price) / price_range) * chart_rect.height()
            
            # Draw wick
            painter.setPen(QPen(color, 1))
            painter.drawLine(x, wick_top, x, wick_bottom)
            
            # Draw body
            body_height = abs(body_top - body_bottom)
            if body_height < 1:
                body_height = 1
            
            painter.fillRect(x - candle_width/2, min(body_top, body_bottom), 
                           candle_width, body_height, color)


class SparklineWidget(QWidget):
    """Minimal 30-day sparkline for position chart drawers."""

    def __init__(self, prices: List[float], positive: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.prices = prices or [1.0, 1.0]
        self.color = QColor(0, 255, 136) if positive else QColor(255, 71, 87)
        self.fill = QColor(0, 255, 136, 20) if positive else QColor(255, 71, 87, 20)
        self.setMinimumHeight(60)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        if w < 2 or not self.prices:
            return

        mn, mx = min(self.prices), max(self.prices)
        rng = mx - mn or 1.0
        step = w / max(len(self.prices) - 1, 1)

        path = QPainterPath()
        fill_path = QPainterPath()
        for i, p in enumerate(self.prices):
            x = i * step
            y = h - ((p - mn) / rng) * (h - 4) - 2
            if i == 0:
                path.moveTo(x, y)
                fill_path.moveTo(x, h)
                fill_path.lineTo(x, y)
            else:
                path.lineTo(x, y)
                fill_path.lineTo(x, y)
        fill_path.lineTo((len(self.prices) - 1) * step, h)
        fill_path.closeSubpath()

        painter.fillPath(fill_path, QBrush(self.fill))
        painter.setPen(QPen(self.color, 1.5))
        painter.drawPath(path)
