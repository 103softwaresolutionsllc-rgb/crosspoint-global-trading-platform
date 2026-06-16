#!/usr/bin/env python3
"""
Simple launcher for Crosspoint Global Trading Platform
Demonstrates basic functionality without complex dependencies
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def print_banner():
    """Print application banner"""
    print("=" * 60)
    print("    Crosspoint Global Trading Platform")
    print("    Enhanced with FinceptTerminal Technology")
    print("=" * 60)
    print()

def test_basic_imports():
    """Test basic functionality"""
    try:
        print("Testing basic imports...")
        
        # Test basic Python packages
        import numpy as np
        import pandas as pd
        import yfinance as yf
        print("✓ NumPy, Pandas, yfinance imported successfully")
        
        # Test basic data retrieval
        print("\nTesting market data retrieval...")
        ticker = yf.Ticker("AAPL")
        data = ticker.history(period="5d")
        print(f"✓ Retrieved {len(data)} days of AAPL data")
        print(f"  Latest close: ${data['Close'].iloc[-1]:.2f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_env_config():
    """Test environment configuration"""
    try:
        print("\nTesting environment configuration...")
        
        # Load settings from original Crosspoint system
        from global_trading.settings import load_settings
        settings = load_settings()
        
        print(f"✓ Settings loaded successfully")
        print(f"  Jurisdictions: {settings.jurisdictions}")
        print(f"  Paper trading: {settings.paper_first}")
        print(f"  Base currency: {settings.base_currency}")
        print(f"  IBKR stub mode: {settings.ibkr_use_stub}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error loading settings: {e}")
        return False

def show_available_commands():
    """Show available commands"""
    print("\nAvailable Commands:")
    print("  fincept --cli              - Launch CLI interface")
    print("  fincept agent --dunlap     - Run Ian Dunlap agent")
    print("  fincept agent --buffett    - Run Buffett agent")
    print("  fincept agent --graham     - Run Graham agent")
    print("  fincept agent --lynch      - Run Lynch agent")
    print()

def main():
    """Main launcher"""
    print_banner()
    
    # Test basic functionality
    basic_ok = test_basic_imports()
    env_ok = test_env_config()
    
    if basic_ok and env_ok:
        print("\n✓ Crosspoint Global Trading Platform is ready!")
        print("✓ Environment configuration loaded")
        print("✓ Market data connectivity verified")
        show_available_commands()
        
        print("\nTo run the full FinceptTerminal interface:")
        print("  pip install PyQt6 plotly dash sqlalchemy")
        print("  python -m fincept_terminal")
        
    else:
        print("\n⚠ Some components need attention")
        print("Check the error messages above for details")
    
    return 0 if basic_ok else 1

if __name__ == "__main__":
    sys.exit(main())
