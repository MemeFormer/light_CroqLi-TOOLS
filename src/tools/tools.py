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
from src.config import Config # Import Config
from src.services.groq_api import GroqService  # Correct import
from src.models.models import ShellAndOS, CommandResult, HelpfulTip, AtuinHistoryEntry
from src.assistant.system_info import get_system_info
from src.services.tavily_api import TavilyService  # Import TavilyService


class ShellHistoryEntry(BaseModel):
    command: str
    timestamp: str = ""  # Default empty timestamp



class Tools:
    COMMAND_HISTORY_LENGTH = 100  # Define as class constant, adjust number as needed

    def __init__(self, config: Config, groq_service: GroqService):
        self.config = config # Store config
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
        """Provides helpful tips for a failed command. Reads settings from Config."""
        shell_and_os = self.shell_and_os
        # Read model name from config
        model_name = self.config.model_settings.model_name 
        # Read temperature from config - use a low temp for factual tips
        temperature = 0.1 # Hardcode low temp for tips, or make configurable
        # Read max_tokens from config
        max_tokens = self.config.model_settings.max_tokens # Or a specific lower value for tips
        
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

        # Construct the API call payload using values read from config
        api_call = {
                "model": model_name, 
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens, 
            "response_format": {"type": "json_object"}
        }
        
        # Ensure Groq client is initialized before use
        if self.groq_service.client is None:
             self.groq_service._initialize_client() # Call the service's initializer
        if self.groq_service.client is None:
             return json.dumps({"explanation": "Error: Groq client not initialized.", "suggestion": "Check API Key.", "additional_info": ""})
             
        # Execute the API call using GroqService client
        try:
            response = self.groq_service.client.chat.completions.create(**api_call) 
            response_data = json.loads(response.choices[0].message.content)
            tip = HelpfulTip(
                explanation=response_data.get('explanation', "N/A"),
                suggestion=response_data.get('suggestion', "N/A"),
                additional_info=response_data.get('additional_info', "N/A")
            )
            return tip.model_dump_json()
        except json.JSONDecodeError:
            return json.dumps({"explanation": "Error parsing LLM response.", "suggestion": "Could not get helpful tips.", "additional_info": ""})
        except Exception as e:
             print(f"Error during helpful tips generation: {e}")
             return json.dumps({"explanation": f"Error generating tips: {e}", "suggestion": "N/A", "additional_info": ""})

    
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

    def search_tavily(self, query: str) -> str:
        """
        Search the web using Tavily API and return formatted results.
        Reads API key from config.
        """
        print(f"Executing Tavily search...")
        print(f"Sending search request to Tavily API for query: {query}")
        
        # Get Tavily API key from config
        tavily_api_key = self.config.api_keys.tavily_api_key
        if not tavily_api_key:
            return "Search failed: Tavily API key not found in configuration."
            
        try:
            # Pass the API key when creating the service
            tavily_service = TavilyService(api_key=tavily_api_key)
            search_params = {
                "query": query,
                "search_depth": "advanced",
                "include_answer": True,
                "include_raw_content": False,
                "include_images": False,
                "max_results": 5
            }
            
            response = tavily_service.post("/search", search_params)
            
            if not response:
                return "No results found."
            
            answer = response.get("answer", "")
            results = response.get("results", [])
            formatted_response = f"Answer: {answer}\n\nSources:\n"
            for idx, source in enumerate(results, 1):
                title = source.get("title", "Untitled")
                url = source.get("url", "No URL")
                content = source.get("content", "").strip()
                if len(content) > 200: content = content[:197] + "..."
                formatted_response += f"\n{idx}. {title}\n   URL: {url}\n   Summary: {content}\n"
            return formatted_response
            
        except Exception as e:
            error_msg = str(e)
            print(f"Tavily API request failed: {error_msg}")
            return f"Search failed: {error_msg}"
