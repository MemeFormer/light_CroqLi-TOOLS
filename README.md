# CroqLI - Simplified Version

This is a simplified version of the CroqLI project, focused on core functionality. Non-essential features such as cheat-sheet management, dynamic model settings, and special formatting have been removed to reduce the codebase size and improve performance.

## Features

- Basic chat mode with Groq API integration
- CLI assistant for executing shell commands
- Simple search functionality
- System information display

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
Set up environment variables in a .env file:

GROQ_API_KEY=your_groq_api_key
GROQ_API_URL=https://api.groq.com
Run the application:

python src/main.py
Usage
Chat Mode: Interact with the Groq API in chat mode.
CLI Assistant: Execute shell commands and get output directly in the terminal.
Search Mode: Search the Groq API with a query.
System Info: Display basic system information.
License
This project is licensed under the MIT License.
