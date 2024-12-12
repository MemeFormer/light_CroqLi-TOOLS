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
from .menu_models import MenuItem, MenuState, MenuSystemPrompt, ModelSettings
from src.models.models import MenuSystemPromptModel, MenuSystemPrompt, APIKeys
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
        # Create submenus first
        settings_menu = self._create_settings_menu()
        prompts_menu = {
        "1": MenuItem(title="System Prompts", action=self._display_prompts_list, key_binding="1", enabled=True),
        "2": MenuItem(title="Back", action=lambda: "back", key_binding="2", enabled=True)
    }
        
    
        
        main_menu = {
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
                title="settings",
                submenu=settings_menu,
                key_binding="4",
                enabled=True
            ),
            "5": MenuItem(
                title="System Prompts",
                submenu=prompts_menu,
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
    
        return {
            "main": main_menu,
            "settings": settings_menu,
            "system_prompts": prompts_menu
        }

    def _create_settings_menu(self) -> Dict[str, MenuItem]:
        return {  # Implement settings menu structure
            "1": MenuItem(title="Model Settings", action=self._model_settings, key_binding="1"),
            "2": MenuItem(title="API Keys", action=self._api_keys, key_binding="2"),
            "3": MenuItem(title="Back", action=lambda: "back", key_binding="3"), # Lambda for simple return
        }
    
    def _create_prompts_menu(self) -> Dict[str, MenuItem]:
        """Shows the list of available system prompts with their active status and pin state"""
        
        prompts_menu = {
            "1": MenuItem(title="Add New Prompt", action=self._add_new_prompt, key_binding="1"),
            "2": MenuItem(title="Switch Active Prompt", action=self._switch_active_prompt, key_binding="2"),
            "3": MenuItem(title="Pin/Unpin Prompt", action=self._pin_prompt, key_binding="3"),
            "4": MenuItem(title="Move Prompt", action=self._move_prompt, key_binding="4"),
            "5": MenuItem(title="Delete Prompt", action=self._delete_prompt, key_binding="5"),
            "6": MenuItem(title="Back", action=lambda: "back", key_binding="6")
        }
        return prompts_menu
    

    def _display_prompts_list(self):
        self.config.load_systemprompts_U()

        if not self.config.prompts:
            self.console.print("No prompts available.", style="yellow")
            return "system_prompts"

        while True:
            self._display_prompts()
            choice = self.console.input("Enter prompt number (or 'b' to go back): ")

            if choice.lower() == 'b':
                return "system_prompts"

            try:
                prompt_index = int(choice) - 1
                if 0 <= prompt_index < len(self.config.prompts):
                    return self._show_prompt_actions_menu(prompt_index)
                else:
                    self.console.print("Invalid prompt number.", style="red")
            except ValueError:
                self.console.print("Invalid input. Please enter a number or 'b'.", style="red")

    def _add_new_prompt(self):
        """Add a new system prompt."""
        questions = [
            inquirer.Text(
                "name",
                message="Enter the prompt name",
                validate=lambda _, x: bool(x.strip())
            ),
            inquirer.Text(
                "prompt_text",
                message="Enter the prompt text",
                validate=lambda _, x: bool(x.strip())
            ),
            inquirer.Confirm(
                "is_active",
                message="Make this prompt active?",
                default=False
            )
        ]

        answers = inquirer.prompt(questions)
        if answers:
            try:
                new_prompt = MenuSystemPrompt(
                    name=answers["name"],
                    prompt_text=answers["prompt_text"],
                    is_active=answers["is_active"],
                    priority=0  # Default to unpinned
                )
                self.config.add_prompt(new_prompt)
                self.console.print("New prompt added successfully", style="green")
            except Exception as e:
                self.console.print(f"Error adding prompt: {e}", style="red")

        return "system_prompts"
    
    def get_status_markers(prompt):
        """Create status indicators for a prompt"""
        active = "●" if prompt.is_active else "○"  # Filled/empty circle for active status
        pinned = "📌" if prompt.priority == 1 else "  "  # Pin emoji for pinned, spaces for unpinned
        return f"{active} {pinned}"    
        
    def _display_prompts(self):
        for i, prompt in enumerate(self.config.prompts):
            markers = self._get_status_markers(prompt)
            self.console.print(f"{i+1}. {markers} {prompt.name}")

    def _get_status_markers(self, prompt):
            active = "●" if prompt.is_active else "○"
            pinned = "📌" if prompt.priority == 1 else "  "
            return f"{active} {pinned}"


    def _show_prompt_actions_menu(self, selected_idx: int) -> str:
        """Shows the actions menu for a selected prompt."""
        if not self.config.prompt_exists(selected_idx):
            self.console.print("Invalid prompt index.", style="red")
            return "system_prompts"

        while True:
            prompt = self.config.prompts[selected_idx]
            actions = {
                "1": ("Activate", self.config.set_active_prompt),
                "2": ("Pin/Unpin", self.config.pin_prompt),
                "3": ("Move Up", lambda: self.config.move_prompt(selected_idx, -1)),
                "4": ("Move Down", lambda: self.config.move_prompt(selected_idx, 1)),
                "5": ("Delete", self.config.delete_prompt),
                "6": ("Back", lambda: None), # Return to prompts menu
            }

            self.console.print(f"\nPrompt: {prompt.name}", style="bold")
            for key, (action_name, _) in actions.items():
                self.console.print(f"{key}. {action_name}")

            choice = self.console.input("Choose action: ")

            if choice == "6":
                break

            action_name, action_func = actions.get(choice, (None, None))
            if action_func:
                try:
                    if action_name in ("Move Up", "Move Down", "Delete"):
                        action_func()  # These actions don't take an index argument
                        self._update_display_indices()
                    else:
                        action_func(selected_idx)
                    self.config.save_systemprompts_U()  # Save changes
                    self.console.print(f"Action '{action_name}' completed successfully.", style="green")

                except Exception as e:
                    self.console.print(f"Error: {e}", style="red")
            else:
                self.console.print("Invalid choice.", style="red")

        return "system_prompts"

    def _move_prompt(self):
        """Move a system prompt up or down."""
        try:
            prompts = self.config.prompts
            if not prompts:
                self.console.print("No prompts available", style="yellow")
                return "system_prompts"

            choices = [f"{idx}. {prompt.name}" for idx, prompt in enumerate(prompts)]
            questions = [
                inquirer.List(
                    "prompt_index",
                    message="Select prompt to move:",
                    choices=choices
                ),
                inquirer.List(
                    "direction",
                    message="Move direction:",
                    choices=["Up", "Down"]
                )
            ]

            answer = inquirer.prompt(questions)
            if answer:
                idx = int(answer["prompt_index"].split(".")[0])
                direction = -1 if answer["direction"] == "Up" else 1
                self.config.move_prompt(idx, direction)
                self._update_display_indices()
                self.console.print("Prompt moved successfully", style="green")

            return "system_prompts"
        except Exception as e:
            self.console.print(f"Error: {e}", style="red")
            return "system_prompts"

    def _delete_prompt(self):
        """Delete a system prompt."""
        try:
            prompts = self.config.prompts
            if not prompts:
                self.console.print("No prompts available", style="yellow")
                return "system_prompts"

            choices = [f"{idx}. {prompt.name}" for idx, prompt in enumerate(prompts)]
            questions = [
                inquirer.List(
                    "prompt_index",
                    message="Select prompt to delete:",
                    choices=choices
                ),
                inquirer.Confirm(
                    "confirm",
                    message="Are you sure you want to delete this prompt?",
                    default=False
                )
            ]

            answer = inquirer.prompt(questions)
            if answer and answer["confirm"]:
                idx = int(answer["prompt_index"].split(".")[0])
                self.config.delete_prompt(idx)
                self.console.print("Prompt deleted successfully", style="green")

            return "system_prompts"
        except Exception as e:
            self.console.print(f"Error: {e}", style="red")
            return "system_prompts"

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
            questions = [
                inquirer.List(
                    "Setting",
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
            setting = inquirer.prompt(questions)["Setting"]


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
       
        menu = self.menus[self.state.current_menu]
    
        if choice not in menu:
            self.console.print("Invalid choice", style="bold red")
            return True

        item = menu[choice]

        if item.submenu:
            self.state.breadcrumb.append(self.state.current_menu)
            if item.title == "System Prompts":
                self.state.current_menu = "system_prompts"
            else:
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
        self.console.print("WelcOme to Light CroqLI TOOL!", style="bold green")
        
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
        shell_and_os = self.tools._detect_shell_and_os() # Get shell_and_os from tools
        cli_assistant_mode(self.config, self.console, self.groq_service, self.tools, shell_and_os)
        return "main" # Return to main menu after CLI assistant mode

    def _quit(self):
        self.console.print("Goodbye!", style="bold blue")
        return "quit"

    def _model_settings(self):
        try:
            current_settings = ModelSettings.model_validate_json(self.tools.get_model_settings())
        
        # Implement model settings logic here
            self.console.print("Model settings menu (to be implemented)", style="yellow")
            return "settings" # Return to settings menu after
        except Exception as e:
            self.console.print(f"Error loading model settings: {e}", style="red")
            return "settings"

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
        """Add a new system prompt."""
        questions = [
            inquirer.Text(
                "name",
                message="Enter the prompt name",
                validate=lambda _, x: bool(x.strip())
            ),
            inquirer.Text(
                "prompt_text",
                message="Enter the prompt text",
                validate=lambda _, x: bool(x.strip())
            ),
            inquirer.Confirm(
                "is_active",
                message="Make this prompt active?",
                default=False
            )
        ]

        answers = inquirer.prompt(questions)
        if answers:
            try:
                prompt = MenuSystemPrompt(
                    name=answers["name"],
                    prompt_text=answers["prompt_text"],
                    is_active=answers["is_active"]
                )
                self.config.add_prompt(prompt)
                self.console.print("New prompt added successfully", style="green")
            except Exception as e:
                self.console.print(f"Error adding prompt: {e}", style="red")

        return "system_prompts"

    def _pin_prompt(self):
        """Pin/Unpin a system prompt."""
        try:
            prompts = self.config.prompts
            if not prompts:
                self.console.print("No prompts available", style="yellow")
                return "system_prompts"
                
            choices = [f"{idx}. {prompt.name}" for idx, prompt in enumerate(prompts)]
            questions = [
                inquirer.List(
                    "prompt_index",
                    message="Select prompt to pin/unpin:",
                    choices=choices
                )
            ]
            
            answer = inquirer.prompt(questions)
            if answer:
                idx = int(answer["prompt_index"].split(".")[0])
                self.config.pin_prompt(idx)
                self.console.print("Prompt pin status toggled", style="green")
                
            return "system_prompts"
        except Exception as e:
            self.console.print(f"Error: {e}", style="red")
            return "system_prompts"

    def _switch_active_prompt(self):
        """Switch the active system prompt."""
        try:
            prompts = self.config.prompts
            if not prompts:
                self.console.print("No prompts available", style="yellow")
                return "system_prompts"
                
            choices = [f"{idx}. {prompt.name}" for idx, prompt in enumerate(prompts)]
            questions = [
                inquirer.List(
                    "prompt_index",
                    message="Select prompt to activate:",
                    choices=choices
                )
            ]
            
            answer = inquirer.prompt(questions)
            if answer:
                idx = int(answer["prompt_index"].split(".")[0])
                self.config.set_active_prompt(idx)
                self.console.print("Active prompt updated", style="green")
                
            return "system_prompts"
        except Exception as e:
            self.console.print(f"Error: {e}", style="red")
            return "system_prompts"

    
   
    def _update_display_indices(self):
         for idx, prompt_id in enumerate(self.config.display_order_U):
             self.config.prompts_U[prompt_id].display_index = idx
