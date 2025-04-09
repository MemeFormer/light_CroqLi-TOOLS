# src/assistant/chat.py
import json
from rich.console import Console
from src.services.groq_api import GroqService
from src.models.models import ChatMessage, ToolCall
from typing import List
from src.config import Config

def get_groq_response(groq_service: GroqService, input_text: str, history: List[ChatMessage], config: Config) -> ToolCall:
    messages = []
    if config.active_prompt:  # Use config.active_prompt (assuming it exists)
        messages.append(ChatMessage(role="system", content=config.active_prompt.content)) # Correct attribute
    messages.extend(history)
    messages.append(ChatMessage(role="user", content=input_text))

    return groq_service.generate_response(messages)


def chat_mode(config, console: Console, groq_service: GroqService): # Accept groq_service
    history = []

    while True:
        user_input = console.input("YOU: ")

        if user_input.lower() in ['/quit', '/back']:
            break

        if user_input.lower().startswith('/prompt'):
            try:
                prompt_index = int(user_input.split()[1])
                config.set_active_prompt(prompt_index)
                console.print(f"Switched to prompt {prompt_index}: {config.active_prompt.content if config.active_prompt else 'No active prompt'}") # Access via property
            except (IndexError, ValueError):
                console.print("Invalid prompt index. Usage: /prompt <index>")
            continue

        if user_input.strip() == '':
            console.print() # Print a newline if the input is empty
            continue # Jump to the next loop cycle

        try:
            response: ToolCall = get_groq_response(groq_service, user_input, history, config)
            
            if response.tool_calls:
                tool_call = response.tool_calls[0]
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                # Execute the tool and get the result
                tool_result = groq_service.execute_tool(tool_name, tool_args)
                
                # Add the tool result to the history
                history.append(ChatMessage(role="assistant", content=str(tool_result)))
                
                # Display the tool result to the user
                console.print(f"\nASSISTANT: {tool_result}\n")
            else:
                # If no tool calls, just display the response
                console.print(f"\nASSISTANT: {response.input}\n")
                history.append(ChatMessage(role="assistant", content=response.input))
                
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            continue

    console.print("Exiting chat mode.", style="bold blue")