# src/tools/tools.py

import logging
import os
import platform
import sqlite3
import subprocess
import shlex
import json
import requests
from typing import List, Dict, Any, Union
from pydantic import BaseModel
from src.services.groq_api import GroqService  # Correct import
from src.models.models import ShellAndOS, CommandResult, HelpfulTip, ModelSettings, APIKeys, AtuinHistoryEntry
from src.assistant.system_info import get_system_info
from src.services.tavily_api import TavilyService  # Import TavilyService


class ShellHistoryEntry(BaseModel):
    command: str
    timestamp: str = ""  # Default empty timestamp



class Tools:
    COMMAND_HISTORY_LENGTH = 100  # Define as class constant, adjust number as needed

    def __init__(self, groq_service: GroqService):
        self.groq_service = groq_service
        self.command_history: List[Dict[str, Any]] = [] # Initialize command_history here
        self.shell_and_os: ShellAndOS = self._detect_shell_and_os() # Detect shell and OS on initialization

    def _detect_shell_and_os(self) -> ShellAndOS:
        """Detect the current shell and operating system."""
        shell = os.getenv('SHELL', '/bin/bash')
        shell_name = os.path.basename(shell)
        operating_system = platform.system().lower()
        return ShellAndOS(shell=shell_name, os=operating_system)
    
    def search_history(self, query: str, use_atuin: bool = True)  -> Union[str, Dict]:
        if use_atuin:
            result = self._search_atuin_history(query) # Call the helper method
            if "error" not in result:  # Check for errors
                return json.dumps(result) # Return JSON on success
            else:
                return result # Return error dict directly

        return json.dumps(self._search_standard_shell_history(query, self.shell_and_os.shell)) # Use self.shell_and_os

    def _search_atuin_history(self, query: str) -> Dict: # 
        """Searches Atuin history."""
        db_path = os.path.expanduser("~/.local/share/atuin/history.db")
        if not os.path.exists(db_path):
            return {"results": [], "error": "Atuin history database not found."}

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM history WHERE command LIKE ?", (f"%{query}%",))
            search_results = cursor.fetchall()
            conn.close()

        # Convert to Pydantic models and then to JSON
            results = [entry.model_dump() for entry in search_results] # Use model_dump() without mode argument
            return {"results": results}
        except Exception as e:
            return {"results": [], "error": str(e)}  # Consistent error handling

    def _get_history_file_path(self, shell_name: str) -> str:
        home = os.path.expanduser("~")
        if shell_name == "bash":
            return os.path.join(home, ".bash_history")
        elif shell_name == "zsh":
            return os.path.join(home, ".zsh_history")
        elif shell_name == "fish":
            return os.path.join(home, ".local", "share", "fish", "fish_history")
        else:
            return ""
  
    def _search_standard_shell_history(self, query: str, shell_name: str) -> Dict: 
        """Searches standard shell history."""
        history_file = self._get_history_file_path(shell_name)
        if not history_file or not os.path.exists(history_file):
            return json.dumps({"results": [], "error": f"History file not found for {shell_name}"})
    
        try:
            with open(history_file, 'r') as f:
                history_lines = f.readlines()
        
            results = [
                ShellHistoryEntry(command=line.strip()).model_dump()  # Use Pydantic model
                for line in history_lines
                if query.lower() in line.strip().lower() # Added strip() for consistency and to prevent errors if there are extra whitespaces
            ]
            return {"results": results}

        except Exception as e:
            return {"results": [], "error": str(e)}

    
    def generate_system_prompt(self) -> str:
        """Generates the system prompt."""

        history_info = '\n'.join([
            f"Previous Command: {h['command']}, Success: {h['success']}, Error: {h['error'] or 'None'}"
            for h in self.command_history[-3:]
        ]) if self.command_history else "No command history available."

        system_info_result = get_system_info()

        prompt = f"""
        You are a CLI assistant for {self.shell_and_os.os.capitalize()} using {self.shell_and_os.shell} shell.
        Current system information:
        {system_info_result}  # Use the result of get_system_info directly

        Recent command history:
        {history_info}

        Please provide shell commands to help the user. Return your response as a JSON object with a 'command' key.
        """
        return prompt    
    
    def generate_response(self, messages, tools=None):
        return self.groq_service.generate_response(messages, tools)


    def execute_command(self, command: str) -> str:
        """Executes a shell command."""
        try:
            args = shlex.split(command)
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # Capture stderr separately
                universal_newlines=True,
                bufsize=1
            )
            stdout, stderr = process.communicate() # Capture both stdout and stderr
            exit_code = process.returncode

            result = CommandResult(stdout=stdout, stderr=stderr, exit_code=exit_code)
            return result.model_dump_json()

        except Exception as e:
            result = CommandResult(stdout="", stderr=str(e), exit_code=1)
            return result.model_dump_json()
    
    def provide_helpful_tips(self, command: str, error_message: str) -> str:
        """Provides helpful tips for a failed command.  Accepts ShellAndOS as JSON string."""
        shell_and_os = self.shell_and_os
        prompt = f"""
        The following command failed:
        Command: {command}
        Error message: {error_message}

        Please provide:
        . An explanation of why the command failed.
        . A detailed suggestion on how to fix the issue or an alternative approach.
        . Any relevant information about the command or the error that might be helpful.

        Format your response as a JSON object with the following keys:
        - explanation: A clear explanation of why the command failed.
        - suggestion: A detailed suggestion on how to fix the issue or an alternative approach.
        - additional_info: Any additional relevant information about the command or error.
        """

        system_prompt = f"You are a CLI assistant helping with a failed command on {shell_and_os.os.capitalize()} using {shell_and_os.shell} shell."

        # Instead of calling the Groq API directly, construct a JSON representation of the API call
        # This will be executed by the GroqService
        api_call = {
                "model": "mixtral-8x7b-32768",  # Or use config.groq_model
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 32768,
            "response_format": {"type": "json_object"}
        }
        # Execute the API call using GroqService
        response = self.groq_service.client.chat.completions.create(**api_call) # use groq_service.client

        try:
            response_data = json.loads(response.choices[0].message.content)
            tip = HelpfulTip(
                explanation=response_data['explanation'],
                suggestion=response_data['suggestion'],
                additional_info=response_data['additional_info']
            )
            return tip.model_dump_json()

        except json.JSONDecodeError:
            return json.dumps({"explanation": "Error parsing response.", "suggestion": "Check the command and error message.", "additional_info": ""})

    
    def update_command_history(self, user_prompt, command, success, output=None, error=None):
        self.command_history.append({
            'user_prompt': user_prompt,
        'command': command,
        'success': success,
        'output': output,
        'error': error
    })
    # Keep only the last N commands in memory to avoid unbounded growth
        if len(self.command_history) > self.COMMAND_HISTORY_LENGTH:
            self.command_history.pop(0)

    def log_command(self, user_prompt, command, success, output=None, error=None):
        """Log command execution results."""
        result = "Success" if success else "Error"
        logging.info(f"User Prompt: {user_prompt}, Command: {command}, Result: {result}, Output: {output}, Error: {error}")

    def get_model_settings(self) -> str:
        """Gets the current model settings."""
        settings = ModelSettings(
            model_name=self.groq_service.model_params.model_name,
            max_tokens=self.groq_service.model_params.max_tokens,
            temperature=self.groq_service.model_params.temperature,
            top_p=self.groq_service.model_params.top_p
        )
        return settings.model_dump_json()

    def update_model_settings(self, model_settings_json: str) -> str:
        """Updates the model settings."""
        try:
            model_settings = ModelSettings.model_validate_json(model_settings_json)
            self.groq_service.model_params.model_name = model_settings.model_name
            self.groq_service.model_params.max_tokens = model_settings.max_tokens
            self.groq_service.model_params.temperature = model_settings.temperature
            self.groq_service.model_params.top_p = model_settings.top_p
            return json.dumps({"status": "success"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
   
    def get_api_keys(self) -> str:
        """Gets the current API keys."""
        keys = APIKeys(groq_api_key=self.groq_service.api_key) # Get Groq API key from GroqService
        return keys.model_dump_json()

    def update_api_keys(self, api_keys_json: str) -> str:
        """Updates the API keys."""
        try:
            api_keys = APIKeys.model_validate_json(api_keys_json)
            self.groq_service.api_key = api_keys.groq_api_key # Update Groq API key in GroqService
            # ... (Update other API keys as needed)
            return json.dumps({"status": "success"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})
        
    def search_tavily(self, query: str) -> str: # Add search_tavily method
        """Searches Tavily API with the given query."""
        try:
            tavily_service = TavilyService()
            json_body = {"query": query} # Construct the request body
            response = tavily_service.post("/search", json=json_body) # Make the request
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response.text # Return the response as text (or JSON if needed)
        except requests.exceptions.RequestException as e: # Catch request exceptions
            return json.dumps({"error": str(e)}) # Return JSON error message
