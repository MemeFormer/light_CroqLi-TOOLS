# src/assistant/utils/menu_helpers.py
from typing import Dict, Optional, Callable
from rich.console import Console
from src.config import Config, load_config
from src.models.models import APIKeys
from src.services.groq_api import GroqService
from src.tools.tools import Tools
from src.assistant.chat import chat_mode
from src.assistant.search import search_mode
from src.assistant.cli_assistant import cli_assistant_mode
from .menu_models import MenuItem, MenuState, SystemPrompt, ModelSettings
import inquirer
import json

class MenuSystem:
    def __init__(self, config: Config, groq_service: GroqService, tools: Tools):
        self.config = config
        self.groq_service = groq_service
        self.tools = tools
        self.console = Console()
        self.state = MenuState()
        self.menus = self._create_menu_structure()

    def _create_menu_structure(self) -> Dict[str, Dict[str, MenuItem]]:
        # Use a dictionary to store submenus for easier access
        self.submenus: Dict[str, Dict[str, MenuItem]] = {
            "settings": self._create_settings_menu(),
            "system_prompts": self._create_prompts_menu(),
            # ... Add other submenus here ...
        }

        return {
            "main": {
                "1": MenuItem(
                    title="Chat Mode",
                    action=self._start_chat,
                    key_binding="1",
                    enabled=True
                ),
                "2": MenuItem(
                    title="Search Mode",
                    action=self._start_search,
                    key_binding="2",
                    enabled=True
                ),
                "3": MenuItem(
                    title="CLI Assistant Mode",
                    action=self._start_cli_assistant,
                    key_binding="3",
                    enabled=True
                ),
                "4": MenuItem(
                    title="Settings",
                    submenu=self._create_settings_menu(),
                    key_binding="4",
                    enabled=True
                ),
                "5": MenuItem(
                    title="System Prompts",
                    submenu=self._create_prompts_menu(),
                    key_binding="5",
                    enabled=True
                ),
                "6": MenuItem(
                    title="Quit",
                    action=self._quit,
                    key_binding="6",
                    enabled=True
                )
            }
        }

    def _create_settings_menu(self) -> Dict[str, MenuItem]:
        return {  # Implement settings menu structure
            "1": MenuItem(title="Model Settings", action=self._model_settings, key_binding="1"),
            "2": MenuItem(title="API Keys", action=self._api_keys, key_binding="2"),
            "3": MenuItem(title="Back", action=lambda: "back", key_binding="3"), # Lambda for simple return
        }
    def _create_prompts_menu(self) -> Dict[str, MenuItem]:
        return {  # Implement prompts menu structure
            "1": MenuItem(title="Add New Prompt", action=self._add_new_prompt, key_binding="1"),
            "2": MenuItem(title="Switch Active Prompt", action=self._switch_active_prompt, key_binding="2"),
            # ... Add other prompt actions as needed ...
            "3": MenuItem(title="Back", action=lambda: "back", key_binding="3"), # Lambda for simple return
        }

    def _model_settings(self):
        """Model settings menu."""
        model_max_tokens = {
        "llama3-8b-8192": 8192,
        "llama3-70b-8192": 8192,
        "mixtral-8x7b-32768": 32768,
        "gemma-7b-it": 8192
        }

        while True:
            current_settings = ModelSettings.model_validate_json(self.tools.get_model_settings())
            setting = inquirer.prompt[
                inquirer.List(
                    "setting",
                    message="Choose a model setting to modify",
                    choices=[
                        "Model Name",
                        "Max Tokens",
                        "Temperature",
                        "Top P",
                        "Back",
                    ],
                ),
            ]
            setting = inquirer.prompt(questions)["setting"]

            if setting == "Back":
                break

            if setting == "Model Name":
                choices = list(model_max_tokens.keys())
                model_question = [
                        inquirer.List(
                        "model",
                        message="Choose the model to use",
                        choices=choices
                    )
                ]
                new_model = inquirer.prompt(model_question)["model"]
                if new_model:
                    current_settings.model_name = new_model

            elif setting == "Max Tokens":
                max_range = model_max_tokens[current_settings.model_name]
                token_question = [
                    inquirer.Text(
                        "max_tokens",
                        message=f"Enter max tokens (range: 0-{max_range}, current: {current_settings.max_tokens})",
                        validate=lambda _, x: x.isdigit() and 0 <= int(x) <= max_range
                    )
                ]
                new_tokens = inquirer.prompt(token_question)["max_tokens"]
                if new_tokens:
                    current_settings.max_tokens = int(new_tokens)

            elif setting == "Temperature":
                temp_question = [
                    inquirer.Text(
                        "temperature",
                        message=f"Enter temperature (range: 0.0-1.0, current: {current_settings.temperature})",
                        validate=lambda _, x: x.replace(".", "").isdigit() and 0.0 <= float(x) <= 1.0
                    )
                ]
                new_temp = inquirer.prompt(temp_question)["temperature"]
                if new_temp:
                    current_settings.temperature = float(new_temp)

            elif setting == "Top P":
                top_p_question = [
                    inquirer.Text(
                        "top_p",
                        message=f"Enter top P (range: 0.0-1.0, current: {current_settings.top_p})",
                        validate=lambda _, x: x.replace(".", "").isdigit() and 0.0 <= float(x) <= 1.0
                    )
                ]
                new_top_p = inquirer.prompt(top_p_question)["top_p"]
                if new_top_p:
                    current_settings.top_p = float(new_top_p)

            # After updating a setting, update the config and Groq service
            updated_settings_json = current_settings.model_dump_json()
            update_result = json.loads(self.tools.update_model_settings(updated_settings_json))
            if update_result["status"] == "success":
                self.console.print("Model settings updated successfully.", style="green")
            else:
                self.console.print(f"Error updating model settings: {update_result['message']}", style="red")

        return "settings"

    def display_current_menu(self):
        """Display the current menu with rich formatting"""
        menu = self.menus[self.state.current_menu]
        
        # Create breadcrumb trail
        breadcrumb = " > ".join(self.state.breadcrumb + [self.state.current_menu.title()])
        self.console.print(f"\n{breadcrumb}", style="bold blue")
        
        # Display menu items
        for key, item in menu.items():
            if item.enabled:
                prefix = "└─ " if key == list(menu.keys())[-1] else "├─ "
                style = "bold green" if item.submenu else "white"
                self.console.print(f"{prefix}{item.key_binding}. {item.title}", style=style)

    def handle_navigation(self, choice: str) -> bool:
        """Handle menu navigation with breadcrumb tracking"""
        if self.state.current_menu == "main":
            menu = self.menus[self.state.current_menu]
        else: # Access submenu
            menu = self.submenus[self.state.current_menu]

        if choice not in menu:
            self.console.print("Invalid choice", style="bold red")
            return True
            
        item = menu[choice]
        
        if item.submenu:
            self.state.breadcrumb.append(self.state.current_menu)
            self.state.current_menu = item.title.lower().replace(" ", "_")
        elif item.action:
            result = item.action()
            if result == "quit":
                return False
            elif result == "back" and self.state.breadcrumb:
                self.state.current_menu = self.state.breadcrumb.pop()
        
        return True

    def run(self):
        """Main menu loop with rich UI"""
        self.console.print("Welcome to Light CroqLI!", style="bold green")
        
        while True:
            self.display_current_menu()
            choice = self.console.input("\nEnter your choice: ")
            
            if not self.handle_navigation(choice):
                break

    def _start_chat(self):
        chat_mode(self.config, self.console, self.groq_service)
        return "main" # Return to main menu after chat mode

    def _start_search(self):
        search_mode(self.config, self.console, self.groq_service)
        return "main" # Return to main menu after search mode

    def _start_cli_assistant(self):
        cli_assistant_mode(self.config, self.console, self.groq_service, self.tools)
        return "main" # Return to main menu after CLI assistant mode

    def _quit(self):
        self.console.print("Goodbye!", style="bold blue")
        return "quit"

    def _model_settings(self):
        # Implement model settings logic here
        self.console.print("Model settings menu (to be implemented)", style="yellow")
        return "settings" # Return to settings menu after

    def _api_keys(self):
        """API keys menu."""
        while True:
            current_keys = APIKeys.model_validate_json(self.tools.get_api_keys())

            questions = [
                inquirer.Text(
                    "groq_api_key",
                    message="Enter your new GROQ API key (leave empty to keep current):",
                    default=current_keys.groq_api_key,
                ),
                # ... (Add input fields for other API keys as needed)
                inquirer.Confirm("confirm", message="Save changes?", default=False),
            ]
            answers = inquirer.prompt(questions)

            if not answers["confirm"]:
                break  # Return without saving

            try:
                # Update APIKeys model
                current_keys.groq_api_key = answers["groq_api_key"]
                # ... (Update other API keys in current_keys)

                # Update the API keys using the tool
                update_result = json.loads(self.tools.update_api_keys(current_keys.model_dump_json()))
                if update_result["status"] == "success":
                    self.console.print("API keys updated successfully.", style="green")
                    # You might want to re-initialize the GroqService here if the API key changed
                    self.groq_service = GroqService() # Re-initialize GroqService
                    self.tools.groq_service = self.groq_service # Update tools with new groq_service
                    break # Exit after successful update
                else:
                    self.console.print(f"Error updating API keys: {update_result['message']}", style="red")

            except Exception as e:
                self.console.print(f"An error occurred: {e}", style="red")


        return "settings"


    def _add_new_prompt(self):
        # Implement add new prompt logic here
        self.console.print("Add new prompt (to be implemented)", style="yellow")
        return "prompts" # Return to prompts menu after

    def _switch_active_prompt(self):
        # Implement switch active prompt logic here
        self.console.print("Switch active prompt (to be implemented)", style="yellow")
        return "prompts" # Return to prompts menu after

   