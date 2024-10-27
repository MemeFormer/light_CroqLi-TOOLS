import logging
import os
import traceback
import json
from rich.console import Console
from dotenv import load_dotenv
from src import config
from typing import List, Dict, Any
from src.services.groq_api import GroqService
from rich.console import Console
from src.models.models import ShellAndOS, AtuinHistoryEntry, HelpfulTip, ChatMessage # Import for type hinting
from src.tools.tools import Tools  # Import the Tools class

COMMAND_HISTORY_LENGTH = 10

def log_command(user_prompt, command, success, output=None, error=None):
    """Log command execution results."""
    result = "Success" if success else "Error"
    logging.info(f"User Prompt: {user_prompt}, Command: {command}, Result: {result}, Output: {output}, Error: {error}")

    
def process_ai_response(response_json, user_input, shell_and_os: ShellAndOS, tools: Tools, client, console):
    try:
        command_dict = json.loads(response_json)
        command = command_dict['command']
        console.print(f"Running command [{command}] ...")

        execute_tools = ["execute_command_tool"]
        messages = [{"role": "system", "content": f"Execute the following command: {command}"}]
        response = tools.generate_response(messages, tools=execute_tools)
        execution_results = json.loads(response.input)  # Parse the results
        stdout = execution_results.get("stdout", "")
        stderr = execution_results.get("stderr", "")
        exit_code = execution_results.get("exit_code", 1)

        if exit_code == 0:
            console.print("Command executed successfully.")
            if stdout:
                console.print("Command output:")
                console.print(stdout)
        else:
            console.print("Error executing command:")
            console.print(stderr)
            handle_error_and_retry(user_input, stderr, shell_and_os, tools, client, console)

        tools.update_command_history(user_input, command, exit_code == 0, stdout, stderr)  # Update history HERE, after command execution and error handling

    except json.JSONDecodeError as e:
        console.print(f"Error parsing response as JSON: {e}", style="bold red")
        console.print(f"Response JSON: {response_json}", style="red")
        console.print("Tip: Please ensure your input is clear, or try simplifying your request.", style="yellow")
    except Exception as e:
        console.print(f"Error: {e}", style="bold red")
        console.print(traceback.format_exc(), style="red")
        console.print("Tip: An unexpected error occurred. Please try again.", style="yellow")


def cli_assistant_mode(config, console: Console, groq_service: GroqService, tools: Tools):
    try:
        client = groq_service.client
        
        shell_and_os = ShellAndOS.model_validate_json(tools.detect_shell_and_os()) # Parse JSON output

        while True:
            user_input = console.input("Query:> ")
            if user_input.lower().strip() in ['exit', 'quit', '/menu']:
                break
            
            system_prompt = config.generate_system_prompt(shell_and_os.model_dump_json(), tools.command_history) # Use tools.generate_system_prompt and tools.command_history
            
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                model=config.groq_model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                response_format={"type": "json_object"}
            )
            
            response_json = chat_completion.choices[0].message.content

            process_ai_response(response_json, user_input, shell_and_os, tools, client, console)

    except Exception as e:
        console.print(f"Error: {e}", style="bold red")
        console.print(traceback.format_exc(), style="red")

def handle_error_and_retry(user_prompt, error_message, shell_and_os: ShellAndOS, tools: Tools, client, console):
    """Handle errors by requesting a new command based on the error message."""
    retry_prompt = f"The last command failed with the following error: {error_message}. Please modify the command to fix the error."
    
    # Perform a search on the command history based on the error message
    history_results = json.loads(tools.search_history(error_message, shell_and_os.shell))

    
    history_context = ""
    if history_results.get("results"):
        history_entries = [AtuinHistoryEntry.model_validate_json(entry) for entry in history_results["results"]]
        history_context = '\n'.join([
            f"Previous Command: {entry.command}, Timestamp: {entry.timestamp}"
            for entry in history_entries[:3]
        ])
        retry_prompt += f"\n\nRelevant Command History:\n{history_context}"

    system_prompt = tools.generate_system_prompt(shell_and_os.model_dump_json(), tools.command_history) # Use tools.generate_system_prompt and tools.command_history)
    
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

        execution_results = json.loads(tools.execute_command(command, shell_and_os.shell))
        stdout = execution_results.get("stdout", "")
        stderr = execution_results.get("stderr", "")
        exit_code = execution_results.get("exit_code", 1)
        
        

        if exit_code == 0:
            tools.update_command_history(user_prompt, command, True, stdout)
            console.print("Command executed successfully.")
            if stdout:
                console.print("Command output:")
                console.print(stdout)
        else:
            helpful_tips_json = tools.provide_helpful_tips(command, stderr, shell_and_os.model_dump_json())
            helpful_tips = HelpfulTip.model_validate_json(helpful_tips_json)
            tools.update_command_history(user_prompt, command, False, error=helpful_tips.json()) # Convert helpful_tips to JSON
            console.print("Error executing command:", style="bold red")
            console.print(helpful_tips.json(), style="yellow")  # Print helpful_tips as JSON

    except json.JSONDecodeError as e:
        console.print(f"Error parsing response as JSON: {e}", style="bold red")
        console.print(f"Response JSON: {response_json}", style="red")
        console.print("Tip: Please ensure your input is clear, or try simplifying your request.", style="yellow")
    except Exception as e:
        console.print(f"Error: {e}", style="bold red")
        console.print(traceback.format_exc(), style="red")
        console.print("Tip: An unexpected error occurred. Please try again.", style="yellow")
class Tools:
    def __init__(self, groq_service: GroqService):
        self.groq_service = groq_service
        self.command_history = [] # Initialize command history here



if __name__ == "__main__":
    
    cli_assistant_mode(config, Console())

# Export the cli_assistant_mode function
__all__ = ['cli_assistant_mode']