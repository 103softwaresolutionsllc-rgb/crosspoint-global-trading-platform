"""
Main entry point for Fincept Terminal
Launches the Qt6 UI application
"""

import sys
import asyncio
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from .ui.main_window import main as ui_main
from .cli import main as cli_main


def launch_gui():
    """Launch the GUI application"""
    app = QApplication(sys.argv)
    app.setApplicationName("Fincept Terminal")
    app.setApplicationVersion("4.0.2")
    app.setOrganizationName("Fincept Corporation")
    
    # Create main window
    window = ui_main()
    window.show()
    
    return app.exec()


def launch_cli():
    """Launch the CLI interface"""
    return asyncio.run(cli_main())


def main():
    """Main entry point - determines whether to launch GUI or CLI"""
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        return launch_cli()
    else:
        return launch_gui()


if __name__ == "__main__":
    sys.exit(main())
