# src/services/groq_api.py
import os
import json
import openai
from src.models.models import ChatMessage, ToolCall
from src.config import Config
from typing import List, Dict, Any, Callable
from dotenv import load_dotenv


class GroqService:
    def __init__(self, config: Config):
        print("Initializing GroqService with Config...")
        self.config = config
        self.client = None
        self._initialize_client()
        self.tools = {}  # Initialize an empty dictionary to store tools

    def _initialize_client(self):
        """Initializes the OpenAI client with the current API key from config."""
        api_key = self.config.api_keys.groq_api_key
        if not api_key:
            print("Warning: GROQ_API_KEY not found in config. Client not initialized.")
            self.client = None
            return

        print(f"DEBUG: Force creating new Groq client with key: {api_key[:5]}...")
        try:
            self.client = openai.Client(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1"
            )
            print("DEBUG: New Groq client created.")
        except Exception as e:
            print(f"Error creating Groq client: {str(e)}")
            self.client = None

    def register_tool(self, name: str, func: Callable[..., str]) -> None:
        """Registers a tool with the Groq service."""
        self.tools[name] = func

    def _get_tools(self, tool_schemas: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Formats tools for the Groq API."""
        if tool_schemas:
            return tool_schemas
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": func.__doc__ or "",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The query to process"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
            for name, func in self.tools.items()
        ]

    def generate_response(self, messages: List[ChatMessage], tools: List[str] = None, tool_schemas: List[Dict[str, Any]] = None) -> ToolCall:
        """Generates a response using the Groq API, optionally with tools."""
        if self.client is None:
             self._initialize_client()
        if self.client is None:
             print("Error: Groq client could not be initialized. Check API Key in config.")
             return ToolCall(input=None, tool_calls=[])
             
        selected_tools = {name: func for name, func in self.tools.items() if name in tools} if tools else {}
        groq_tools = self._get_tools(tool_schemas) if selected_tools or tool_schemas else None

        try:
            response = self.client.chat.completions.create(
                model=self.config.model_settings.model_name,
                messages=[{"role": msg.role, "content": msg.content} for msg in messages],
                tools=groq_tools,
                max_tokens=self.config.model_settings.max_tokens,
                temperature=self.config.model_settings.temperature,
                top_p=self.config.model_settings.top_p
            )
            print(f"API Response: {response}")

            response_message = response.choices[0].message if response.choices else None
            content = response_message.content if response_message else None
            tool_calls = response_message.tool_calls if response_message else []
            
            tool_call_obj = ToolCall(
                input=content,
                tool_calls=tool_calls
            )

            return tool_call_obj

        except Exception as e:
            print(f"Error in generate_response: {str(e)}")
            return ToolCall(input=f"Error generating response: {str(e)}", tool_calls=[])
