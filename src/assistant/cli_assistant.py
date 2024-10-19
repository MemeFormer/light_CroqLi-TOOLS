import os
import sys
import shlex
import subprocess
import traceback
import json
import platform
import logging
import sqlite3
from pathlib import Path
from groq import Client, Groq
from rich.console import Console
from src import config
from src.config import load_config
from dotenv import load_dotenv
from src.assistant.system_info import get_system_info


# Import your custom modules
from src.services.groq_api import GroqService
from src.ui.display import (
    print_welcome_message, print_command_output, print_error_message,
    print_command_history, print_help_message, print_code_snippet
)
from src.assistant.chat import chat_mode

load_dotenv()

# Setup logging
logging.basicConfig(filename='assistant.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize SystemInfo
system_info = get_system_info()


# Initialize an empty list to keep the history of commands and their contexts
command_history = []
COMMAND_HISTORY_LENGTH = 10


def detect_shell_and_os():
    """Detect the current shell and operating system."""
    # Detect the shell
    shell = os.getenv('SHELL', '/bin/bash')
    shell_name = os.path.basename(shell)

    # Detect the OS
    operating_system = platform.system().lower()

    return shell_name, operating_system

def search_atuin_history(query):
    db_path = os.path.expanduser("~/.local/share/atuin/history.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Execute a search query on the command history
    cursor.execute("SELECT * FROM history WHERE command LIKE ?", (f"%{query}%",))
    search_results = cursor.fetchall()

    conn.close()

    return search_results

def generate_system_prompt(shell_name, operating_system):
    """Generate the system prompt, incorporating command history and environment information."""
    platform_info = {
            "macos": {
                "open_command": "open",
            "browser": "Safari"
        },
        "linux": {
                "open_command": "xdg-open",
            "browser": "firefox"  
        }
    }

    platform_data = platform_info.get(operating_system, {})
    history_info = '\n'.join([
            f"Previous Command: {h['command']}, Success: {h['success']}, Error: {h['error'] or 'None'}"
        for h in command_history[-3:]
    ])  # Last 3 commands

    
    system_info = get_system_info()

    prompt = f"""
    You are a CLI assistant for {operating_system.capitalize()} using {shell_name} shell.
    Current system information:
    {json.dumps(system_info, indent=2)}

    Recent command history:
    {history_info}

    Platform-specific information:
    Open command: {platform_data.get('open_command', 'N/A')}
    Default browser: {platform_data.get('browser', 'N/A')}

    Please provide shell commands to help the user. Return your response as a JSON object with a 'command' key.
    """
    return prompt


def execute_command(command, console):
    """Execute a shell command and stream the output in real-time."""
    try:
        # Split the command into arguments
        args = shlex.split(command)
        
        # Start the process
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        # Stream the output in real-time
        output = []
        for line in iter(process.stdout.readline, ''):
            console.print(line, end='')
            output.append(line)
            sys.stdout.flush()  # Ensure the output is displayed immediately

        # Wait for the process to complete and get the exit code
        exit_code = process.wait()

        # Join the output lines into a single string
        full_output = ''.join(output)

        return full_output, '', exit_code
    except Exception as e:
        return "", str(e), 1

def update_command_history(user_prompt, command, success, output=None, error=None):
    command_history.append({
            'user_prompt': user_prompt,
        'command': command,
        'success': success,
        'output': output,
        'error': error
    })
    # Keep only the last N commands in memory to avoid unbounded growth
    if len(command_history) > COMMAND_HISTORY_LENGTH:
        command_history.pop(0)

    log_command(user_prompt, command, success, output, error)

def log_command(user_prompt, command, success, output=None, error=None):
    """Log command execution results."""
    result = "Success" if success else "Error"
    logging.info(f"User Prompt: {user_prompt}, Command: {command}, Result: {result}, Output: {output}, Error: {error}")

def process_ai_response(response_json, user_input, shell_name, operating_system, client, console):
    try:
        command_dict = json.loads(response_json)
        command = command_dict['command']
        console.print(f"Running command [{command}] ...")
        stdout, stderr, exit_code = execute_command(command, console)
        if exit_code == 0:
            console.print("Command executed successfully.")
            if stdout:
                console.print("Command output:")
                console.print(stdout)
        else:
            console.print("Error executing command:")
            console.print(stderr)
            handle_error_and_retry(user_input, stderr, shell_name, operating_system, client, console)
    except json.JSONDecodeError as e:
        console.print(f"Error parsing response as JSON: {e}", style="bold red")
        console.print(f"Response JSON: {response_json}", style="red")
        console.print("Tip: Please ensure your input is clear, or try simplifying your request.", style="yellow")
    except Exception as e:
        console.print(f"Error: {e}", style="bold red")
        console.print(traceback.format_exc(), style="red")
        console.print("Tip: An unexpected error occurred. Please try again.", style="yellow")


def cli_assistant_mode(config, console):
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables.")
        client = Groq(api_key=api_key)
        shell_name, operating_system = detect_shell_and_os()

        while True:
            user_input = console.input("Query:> ")
            if user_input.lower().strip() in ['exit', 'quit', '/menu']:
                break
            
            system_prompt = generate_system_prompt(shell_name, operating_system)
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                model="mixtral-8x7b-32768",
                temperature=0.1,
                max_tokens=32768,
                response_format={"type": "json_object"}
            )
            
            response_json = chat_completion.choices[0].message.content
            process_ai_response(response_json, user_input, shell_name, operating_system, client, console)

    except Exception as e:
        console.print(f"Error: {e}", style="bold red")
        console.print(traceback.format_exc(), style="red")

def handle_error_and_retry(user_prompt, error_message, shell_name, operating_system, client, console):
    """Handle errors by requesting a new command based on the error message."""
    retry_prompt = f"The last command failed with the following error: {error_message}. Please modify the command to fix the error."
    
    # Perform a search on the command history based on the error message
    search_query = error_message.lower()
    search_results = search_atuin_history(search_query)
    
    history_context = ""
    if search_results:
        history_context = '\n'.join([
            f"Previous Command: {row[1]}, Timestamp: {row[2]}"
            for row in search_results[:3]  # Limit to the top 3 relevant commands
        ])
        retry_prompt += f"\n\nRelevant Command History:\n{history_context}"

    system_prompt = generate_system_prompt(shell_name, operating_system)
    
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": retry_prompt}
        ],
        model="mixtral-8x7b-32768",
        temperature=0.1,
        max_tokens=32768,
        response_format={"type": "json_object"}
    )

    response_json = chat_completion.choices[0].message.content
    try:
        command_dict = json.loads(response_json)
        command = command_dict['command']
        
        console.print(f"Retrying command [{command}] ...")
        stdout, stderr, exit_code = execute_command(command, console)

        if exit_code == 0:
            update_command_history(user_prompt, command, True, stdout)
            console.print("Command executed successfully.")
            console.print("Command output:")
            console.print(stdout)
        else:
            helpful_tips = provide_helpful_tips(command, stderr, shell_name, operating_system, client)
            update_command_history(user_prompt, command, False, error=helpful_tips)
            console.print("Error executing command:", style="bold red")
            console.print(helpful_tips, style="yellow")
    except json.JSONDecodeError as e:
        console.print(f"Error parsing response as JSON: {e}", style="bold red")
        console.print(f"Response JSON: {response_json}", style="red")
        console.print("Tip: Please ensure your input is clear, or try simplifying your request.", style="yellow")
    except Exception as e:
        console.print(f"Error: {e}", style="bold red")
        console.print(traceback.format_exc(), style="red")
        console.print("Tip: An unexpected error occurred. Please try again.", style="yellow")



def provide_helpful_tips(command, error_message, shell_name, operating_system, client):
    """Use AI to provide helpful tips based on the command and error message."""
    prompt = f"""
    The following command failed:
    Command: {command}
    Error message: {error_message}

    Please provide:
    1. An explanation of why the command failed.
    2. A detailed suggestion on how to fix the issue or an alternative approach.
    3. Any relevant information about the command or the error that might be helpful.

    Format your response as a JSON object with the following keys:
    - explanation: A clear explanation of why the command failed.
    - suggestion: A detailed suggestion on how to fix the issue or an alternative approach.
    - additional_info: Any additional relevant information about the command or error.
    """

    system_prompt = f"You are a CLI assistant helping with a failed command on {operating_system.capitalize()} using {shell_name} shell."

    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        model="mixtral-8x7b-32768",
        temperature=0.1,
        max_tokens=32768,
        response_format={"type": "json_object"}
    )

    try:
        response = json.loads(chat_completion.choices[0].message.content)
        return f"""
        Error Analysis:
        {response['explanation']}

        Suggestion:
        {response['suggestion']}

        Additional Information:
        {response['additional_info']}
        """
    except json.JSONDecodeError:
        return "Sorry, I couldn't generate a helpful tip at this time. Please try rephrasing your command or check the system documentation."



if __name__ == "__main__":
    cli_assistant_mode(config,Console)

# Export the cli_assistant_mode function
__all__ = ['cli_assistant_mode']