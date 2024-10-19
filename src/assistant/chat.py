from rich.console import Console
from src.services.groq_api import GroqService
from src.config import load_config
from src.models.models import ChatMessage
from src.ui.display import Console

def get_groq_response(groq_service, input_text, history, config):
    config.load_system_prompts()  # Refresh prompts before each interaction
    messages = []
    if config.system_prompt:
        messages.append(ChatMessage(role="system", content=config.system_prompt))
    messages.extend(history)
    messages.append(ChatMessage(role="user", content=input_text))

    return groq_service.generate_response(messages)

def chat_mode(config, console):
    """Initiates the chat mode with configuration and console support."""
    try:
        groq_service = GroqService()
    except Exception as e:
        console.print(f"Error initializing GroqService: {str(e)}", style="bold red")
        return

    history = []

    while True:
        user_input = console.input("YOU: ")

        if user_input.lower() in ['/quit', '/back']:
            break

        if user_input.lower().startswith('/prompt'):
            # Switch active prompt based on user input (e.g., /prompt 2)
            try:
                prompt_index = int(user_input.split()[1])
                config.set_active_prompt(prompt_index)
                console.print(f"Switched to prompt {prompt_index}: {config.system_prompt}")
            except (IndexError, ValueError):
                console.print("Invalid prompt index. Usage: /prompt <index>")
            continue

        if user_input.strip() == '':
            console.print()  # Add an empty line for better readability
        else:
            try:
                response = get_groq_response(groq_service, user_input, history, config)
                console.print(f"Assistant: {response}")
                history.append(ChatMessage(role="user", content=user_input))
                history.append(ChatMessage(role="assistant", content=response))
            except Exception as e:
                console.print(f"An error occurred: {str(e)}", style="bold red")

    console.print("Exiting chat mode.", style="bold blue")

if __name__ == "__main__":
    config = load_config()
    console = Console()
    chat_mode(config, console)
