# src/assistant/chat.py
import json
from rich.console import Console
from src.services.groq_api import GroqService
from src.models.models import ChatMessage, ToolCall
from typing import List
from src.config import Config

def get_groq_response(groq_service: GroqService, input_text: str, history: List[ChatMessage], config: Config) -> ToolCall:
    config.load_systemprompts_U() 
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
                # ... Code to execute the tool and get tool_result ...
                console.print(f"Tool Call Result: {response.input if response.input else 'No tool input'}")

                # Construct the next message to send to Groq, including the tool result

                history.append(ChatMessage(role="assistant", content=json.dumps({"tool_code":response.input})))


            elif isinstance(response, ToolCall) and response.input:

                    # For now just print tool input. Implement handling for tool input in next steps
                    console.print(f"Tool input: {response.input}")  

            else:  # Standard response (no tool call)
                try:
                    content = response.choices[0].message.content
                    console.print(f"Assistant: {content}")
                    history.append(ChatMessage(role="assistant", content=content))
                    print(f"Response keys: {response.model_dump().keys()}") # Print available keys
                    print(f"Response choices: {response.choices}") # Print the choices

                except AttributeError as e:
                    console.print(f"Error: Invalid response format: {e}", style="bold red")
                    console.print(f"Full response: {response}")
                    print(f"Full response: {response.model_dump()}") # Print the full dumped response for debugging


            history.append(ChatMessage(role="user", content=user_input))


        except Exception as e:
            console.print(f"An error occurred: {str(e)}", style="bold red")

    console.print("Exiting chat mode.", style="bold blue")