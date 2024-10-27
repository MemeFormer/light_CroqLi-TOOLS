# src/assistant/chat.py
from rich.console import Console
from src.services.groq_api import GroqService
from src.config import load_config
from src.models.models import ChatMessage, ToolCall
from typing import List

def get_groq_response(groq_service: GroqService, input_text: str, history: List[ChatMessage], config) -> ToolCall:
    config.load_system_prompts()
    messages = []
    if config.system_prompt:
        messages.append(ChatMessage(role="system", content=config.system_prompt))
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
                console.print(f"Switched to prompt {prompt_index}: {config.system_prompt}")
            except (IndexError, ValueError):
                console.print("Invalid prompt index. Usage: /prompt <index>")
            continue

        if user_input.strip() == '':
            console.print()
        else:
            try:
                response: ToolCall = get_groq_response(groq_service, user_input, history, config)
                if response.tool_calls:
                    console.print(f"Tool Call Result: {response.input}")
                else:
                    console.print(f"Assistant: {response.content}")
                history.append(ChatMessage(role="user", content=user_input))
                history.append(ChatMessage(role="assistant", content=response.content or ""))
            except Exception as e:
                console.print(f"An error occurred: {str(e)}", style="bold red")

    console.print("Exiting chat mode.", style="bold blue")