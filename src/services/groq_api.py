# src/services/groq_api.py
import os
import json
from groq import Groq
from src.models.models import LLMModelParams, ChatMessage, ToolCall
from src.config import load_config
from typing import List, Dict, Any, Callable
from dotenv import load_dotenv
from instructor import instructor, Mode
from pydantic import BaseModel


class GroqService:
    def __init__(self):
        load_dotenv()
        self.config = load_config()
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = instructor.from_groq(Groq(api_key=self.api_key), mode=Mode.JSON) # Initialize Instructor-wrapped client
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

    def _get_tools(self) -> List[Dict[str, Any]]:
        """Formats tools for the Groq API."""
        return [
            {"type": "function", "function": {"name": name, "description": func.__doc__ or ""}}
            for name, func in self.tools.items()
        ]


    def generate_response(self, messages: List[ChatMessage], tools: List[str] = None) -> ToolCall:
        """Generates a response using the Groq API, optionally with tools."""
        selected_tools = {name: func for name, func in self.tools.items() if name in tools} if tools else {}
        groq_tools = self._get_tools() if selected_tools else None

        response = self.client.chat.completions.create(
            model=self.model_params.model_name,
            messages=[{"role": msg.role, "content": msg.content} for msg in messages],
            tools=groq_tools,
            max_tokens=self.model_params.max_tokens,
            temperature=self.model_params.temperature,
            top_p=self.model_params.top_p,
            response_model=ToolCall # Use Pydantic model for structured output
        )
        # Execute and return tool calls if any
        if response.tool_calls:
            tool_call = response.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            # Check for specific tool arguments and call the tool accordingly
            if tool_name == "search_history_tool":
                tool_result = selected_tools[tool_name](**tool_args) # Pass all arguments
            else:
                tool_result = selected_tools[tool_name](**tool_args)

            return ToolCall(tool_calls=response.tool_calls, input=tool_result)
        else:
            return response
