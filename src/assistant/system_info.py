# src/assistant/system_info.py

import platform
import os

def get_system_info():
    """Returns basic system information."""
    return {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "current_directory": os.getcwd()
    }

def display_system_info(console):
    """Displays system information."""
    info = get_system_info()
    console.print("System Information:")
    for key, value in info.items():
        console.print(f"{key}: {value}")