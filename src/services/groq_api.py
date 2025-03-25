# src/services/groq_api.py
import os
import json
import openai
from src.models.models import LLMModelParams, ChatMessage, ToolCall
from src.config import load_config
from typing import List, Dict, Any, Callable
from dotenv import load_dotenv


class GroqService:
    def __init__(self):
        print("Initializing GroqService...")
        load_dotenv()
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        print(f"API Key loaded: {self.api_key[:5]}...")
        try:
            print("Creating Groq client...")
            self.client = openai.Client(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1"
            )
            print("Groq client created successfully")
        except Exception as e:
            print(f"Error creating Groq client: {str(e)}")
            raise
        print("Loading config...")
        self.config = load_config()
        print("Config loaded")
        self.model_params = LLMModelParams(
            model_name=self.config.groq_model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p
        )
        self.tools = {}  # Initialize an empty dictionary to store tools

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
        selected_tools = {name: func for name, func in self.tools.items() if name in tools} if tools else {}
        groq_tools = self._get_tools(tool_schemas) if selected_tools or tool_schemas else None

        try:
            response = self.client.chat.completions.create(
                model=self.model_params.model_name,
                messages=[{"role": msg.role, "content": msg.content} for msg in messages],
                tools=groq_tools,
                max_tokens=self.model_params.max_tokens,
                temperature=self.model_params.temperature,
                top_p=self.model_params.top_p
            )
            print(f"API Response: {response}")

            # Create a ToolCall object with the response
            tool_call = ToolCall(
                input=response.choices[0].message.content if response.choices and response.choices[0].message else None,
                tool_calls=response.choices[0].message.tool_calls if response.choices and response.choices[0].message.tool_calls else []
            )

            return tool_call

        except Exception as e:
            print(f"Error in generate_response: {str(e)}")
            raise
