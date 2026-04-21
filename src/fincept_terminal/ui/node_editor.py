"""
Node Editor Widget for Fincept Terminal
Visual workflow editor for automation pipelines
"""

from typing import Dict, List, Optional, Any, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsRectItem, QGraphicsLineItem, QGraphicsTextItem,
    QPushButton, QComboBox, QLabel, QFrame, QGraphicsProxyWidget
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QPainter


class NodeItem(QGraphicsRectItem):
    """Visual node in the workflow editor"""
    
    def __init__(self, node_id: str, node_type: str, title: str, x: float, y: float):
        super().__init__(0, 0, 150, 80)
        
        self.node_id = node_id
        self.node_type = node_type
        self.title = title
        
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        
        # Node appearance
        self.setup_appearance()
        
        # Connection points
        self.input_ports = []
        self.output_ports = []
        self.setup_ports()
    
    def setup_appearance(self):
        """Setup node appearance based on type"""
        colors = {
            "data": QColor(52, 152, 219),      # Blue
            "analytics": QColor(46, 204, 113),  # Green
            "trading": QColor(231, 76, 60),     # Red
            "agent": QColor(155, 89, 182),      # Purple
            "output": QColor(241, 196, 15),     # Yellow
        }
        
        color = colors.get(self.node_type, QColor(100, 100, 100))
        
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor(200, 200, 200), 2))
    
    def setup_ports(self):
        """Setup connection ports"""
        # Input port (left side)
        input_port = QGraphicsRectItem(-10, 30, 10, 20, self)
        input_port.setBrush(QBrush(QColor(200, 200, 200)))
        self.input_ports.append(input_port)
        
        # Output port (right side)
        output_port = QGraphicsRectItem(150, 30, 10, 20, self)
        output_port.setBrush(QBrush(QBrush(QColor(200, 200, 200))))
        self.output_ports.append(output_port)
    
    def paint(self, painter, option, widget):
        """Custom paint for node"""
        super().paint(painter, option, widget)
        
        # Draw title
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.title)
    
    def get_output_pos(self) -> QPointF:
        """Get output port position"""
        return self.pos() + QPointF(155, 40)
    
    def get_input_pos(self) -> QPointF:
        """Get input port position"""
        return self.pos() + QPointF(-5, 40)


class ConnectionItem(QGraphicsLineItem):
    """Visual connection between nodes"""
    
    def __init__(self, start_node: NodeItem, end_node: NodeItem):
        super().__init__()
        
        self.start_node = start_node
        self.end_node = end_node
        
        self.setup_appearance()
        self.update_position()
    
    def setup_appearance(self):
        """Setup connection appearance"""
        self.setPen(QPen(QColor(100, 200, 100), 3))
        self.setZValue(-1)  # Draw behind nodes
    
    def update_position(self):
        """Update connection line position"""
        start_pos = self.start_node.get_output_pos()
        end_pos = self.end_node.get_input_pos()
        
        self.setLine(start_pos.x(), start_pos.y(), end_pos.x(), end_pos.y())


class WorkflowScene(QGraphicsScene):
    """Scene for workflow editing"""
    
    connection_created = pyqtSignal(str, str)  # start_node_id, end_node_id
    
    def __init__(self):
        super().__init__()
        self.setSceneRect(0, 0, 1000, 800)
        
        self.nodes = {}
        self.connections = []
        
        # Connection state
        self.connecting = False
        self.connection_start = None
        self.temp_line = None
        
        # Background
        self.setBackgroundBrush(QBrush(QColor(40, 40, 40)))
    
    def add_node(self, node_type: str, title: str, x: float, y: float) -> str:
        """Add a node to the scene"""
        node_id = f"node_{len(self.nodes)}"
        node = NodeItem(node_id, node_type, title, x, y)
        
        self.addItem(node)
        self.nodes[node_id] = node
        
        return node_id
    
    def add_connection(self, start_node_id: str, end_node_id: str):
        """Add a connection between nodes"""
        if start_node_id in self.nodes and end_node_id in self.nodes:
            start_node = self.nodes[start_node_id]
            end_node = self.nodes[end_node_id]
            
            connection = ConnectionItem(start_node, end_node)
            self.addItem(connection)
            self.connections.append(connection)
            
            self.connection_created.emit(start_node_id, end_node_id)
    
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        item = self.itemAt(event.scenePos(), self.views()[0].transform())
        
        if isinstance(item, NodeItem):
            # Check if clicking on output port
            if item.output_ports[0].contains(event.scenePos() - item.pos()):
                self.start_connection(item)
                return
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events"""
        if self.connecting and self.connection_start:
            # Update temporary connection line
            if self.temp_line:
                self.removeItem(self.temp_line)
            
            start_pos = self.connection_start.get_output_pos()
            self.temp_line = QGraphicsLineItem(
                start_pos.x(), start_pos.y(),
                event.scenePos().x(), event.scenePos().y()
            )
            self.temp_line.setPen(QPen(QColor(150, 150, 150), 2, Qt.PenStyle.DashLine))
            self.addItem(self.temp_line)
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        if self.connecting and self.connection_start:
            # Check if releasing on input port
            item = self.itemAt(event.scenePos(), self.views()[0].transform())
            
            if isinstance(item, NodeItem) and item != self.connection_start:
                if item.input_ports[0].contains(event.scenePos() - item.pos()):
                    # Create connection
                    self.add_connection(self.connection_start.node_id, item.node_id)
            
            # Clean up temporary line
            if self.temp_line:
                self.removeItem(self.temp_line)
                self.temp_line = None
            
            # Reset connection state
            self.connecting = False
            self.connection_start = None
        
        super().mouseReleaseEvent(event)
    
    def start_connection(self, node: NodeItem):
        """Start creating a connection from a node"""
        self.connecting = True
        self.connection_start = node


class NodeEditorWidget(QWidget):
    """Main node editor widget"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_sample_workflow()
    
    def setup_ui(self):
        """Setup the node editor UI"""
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QFrame()
        toolbar.setFrameStyle(QFrame.Shape.Box)
        toolbar.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #555;
                padding: 5px;
            }
        """)
        
        toolbar_layout = QHBoxLayout(toolbar)
        
        # Node type selector
        self.node_type_combo = QComboBox()
        self.node_type_combo.addItems([
            "Data Source", "Analytics", "Trading", "AI Agent", "Output"
        ])
        self.node_type_combo.setStyleSheet("color: white; background-color: #404040;")
        toolbar_layout.addWidget(QLabel("Add Node:"))
        toolbar_layout.addWidget(self.node_type_combo)
        
        # Add node button
        self.add_node_btn = QPushButton("Add Node")
        self.add_node_btn.clicked.connect(self.add_node)
        self.add_node_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        toolbar_layout.addWidget(self.add_node_btn)
        
        # Clear button
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_workflow)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        toolbar_layout.addWidget(self.clear_btn)
        
        toolbar_layout.addStretch()
        
        # Run button
        self.run_btn = QPushButton("Run Workflow")
        self.run_btn.clicked.connect(self.run_workflow)
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        toolbar_layout.addWidget(self.run_btn)
        
        layout.addWidget(toolbar)
        
        # Graphics view
        self.view = QGraphicsView()
        self.scene = WorkflowScene()
        self.view.setScene(self.scene)
        
        self.view.setStyleSheet("""
            QGraphicsView {
                background-color: #1e1e1e;
                border: 1px solid #555;
            }
        """)
        
        layout.addWidget(self.view)
        
        # Status bar
        self.status_label = QLabel("Ready - Click 'Add Node' to start building workflow")
        self.status_label.setStyleSheet("color: white; padding: 5px;")
        layout.addWidget(self.status_label)
    
    def add_node(self):
        """Add a new node to the workflow"""
        node_type_text = self.node_type_combo.currentText()
        
        # Map display text to internal type
        type_mapping = {
            "Data Source": "data",
            "Analytics": "analytics", 
            "Trading": "trading",
            "AI Agent": "agent",
            "Output": "output"
        }
        
        node_type = type_mapping.get(node_type_text, "data")
        
        # Generate title
        titles = {
            "data": ["Yahoo Finance", "FRED Data", "Kraken Crypto"],
            "analytics": ["DCF Analysis", "Risk Metrics", "Portfolio Opt"],
            "trading": ["Buy Order", "Sell Order", "Risk Check"],
            "agent": ["Buffett Agent", "Graham Agent", "Lynch Agent"],
            "output": ["Alert", "Report", "Dashboard"]
        }
        
        title_options = titles.get(node_type, ["Node"])
        title = title_options[len(self.scene.nodes) % len(title_options)]
        
        # Random position
        import random
        x = random.randint(50, 500)
        y = random.randint(50, 400)
        
        # Add node
        node_id = self.scene.add_node(node_type, title, x, y)
        
        self.status_label.setText(f"Added {title} node")
    
    def clear_workflow(self):
        """Clear the entire workflow"""
        self.scene.clear()
        self.scene.nodes = {}
        self.scene.connections = []
        self.status_label.setText("Workflow cleared")
    
    def run_workflow(self):
        """Run the current workflow"""
        if not self.scene.nodes:
            self.status_label.setText("No workflow to run")
            return
        
        self.status_label.setText("Running workflow...")
        
        # Simulate workflow execution
        node_count = len(self.scene.nodes)
        connection_count = len(self.scene.connections)
        
        self.status_label.setText(
            f"Workflow executed: {node_count} nodes, {connection_count} connections"
        )
    
    def setup_sample_workflow(self):
        """Create a sample workflow for demonstration"""
        # Add sample nodes
        data_node = self.scene.add_node("data", "Yahoo Finance", 100, 100)
        analytics_node = self.scene.add_node("analytics", "DCF Analysis", 300, 100)
        agent_node = self.scene.add_node("agent", "Buffett Agent", 500, 100)
        output_node = self.scene.add_node("output", "Alert", 700, 100)
        
        # Add connections
        self.scene.add_connection(data_node, analytics_node)
        self.scene.add_connection(analytics_node, agent_node)
        self.scene.add_connection(agent_node, output_node)
        
        self.status_label.setText("Sample workflow loaded")
