# src/ui/display.py

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text
from typing import List, Dict

from rich.theme import Theme

from rich.markdown import Markdown


def print_welcome_message():
    print("WelcOme to the CLI Assistant!")

def print_command_output(output):
    print(f"Output:\n{output}")

def print_error_message(error):
    print(f"Error:\n{error}")

def print_command_history(history):
    print("Command History:")
    for command in history:
        print(command)

def print_help_message():
    print("Help: Available commands are /quit, /back, and any shell command.")

def print_code_snippet(snippet):
    print(f"Code Snippet:\n{snippet}")