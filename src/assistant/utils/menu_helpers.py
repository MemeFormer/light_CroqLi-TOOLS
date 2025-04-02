# src/assistant/utils/menu_helpers.py
from typing import Dict, Optional, Callable
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from src.config import Config, load_config
from src.models.models import APIKeys
from src.services.groq_api import GroqService
from src.tools.tools import Tools
from src.assistant.chat import chat_mode
from src.assistant.search import search_mode
from src.assistant.cli_assistant import cli_assistant_mode
from .menu_models import MenuItem, MenuState, ModelSettings
from src.models.models import SystemPrompt, APIKeys
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
                action=self._manage_system_prompts,
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
            "settings": settings_menu
        }

    def _create_settings_menu(self) -> Dict[str, MenuItem]:
        return {  # Implement settings menu structure
            "1": MenuItem(title="Model Settings", action=self._model_settings, key_binding="1"),
            "2": MenuItem(title="API Keys", action=self._api_keys, key_binding="2"),
            "3": MenuItem(title="Back", action=lambda: "back", key_binding="3"), # Lambda for simple return
        }
    
    def _display_prompts_list(self):
        self.config.load_prompts()

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
                prompts_list = sorted(
                    self.config.prompts.values(),
                    key=lambda p: (p.pin_order if p.pinned else float('inf'), p.list_order)
                )
                if 0 <= prompt_index < len(prompts_list):
                    return self._show_prompt_actions_menu(prompts_list[prompt_index])
                else:
                    self.console.print("Invalid prompt number.", style="red")
            except ValueError:
                self.console.print("Invalid input. Please enter a number or 'b'.", style="red")

    def _add_new_prompt(self):
        """Add a new system prompt."""
        # Remove 'content' question from here
        questions = [
            inquirer.Text(
                "title",
                message="Enter the prompt title",
                validate=lambda _, x: bool(x.strip())
            ),
            # inquirer.Text('content', message="Enter prompt content (single line for now, use Edit Content for multi-line):"),
            inquirer.Confirm(
                "is_active",
                message="Make this prompt active?",
                default=False
            )
        ]

        try:
            # Get title and is_active first
            answers = inquirer.prompt(questions)
            if answers:
                # Now get content using the custom loop
                self.console.print("Enter prompt content. Type EOF on a new line by itself and press Enter to finish:")
                content_lines = []
                try:
                    while True:
                        try:
                            line = input("> ")
                            if line.strip().upper() == 'EOF':
                                break
                            content_lines.append(line)
                        except EOFError:  # Handle Ctrl+D
                            break
                        except KeyboardInterrupt: # Handle Ctrl+C
                            self.console.print("\nInput cancelled.", style="yellow")
                            content_lines = None
                            break # Exit the input loop
                
                    if content_lines is not None:
                        new_content = "\n".join(content_lines)
                        # Now add the prompt with the gathered content
                        try:
                            self.config.add_prompt(
                                title=answers["title"],
                                content=new_content, 
                                make_active=answers["is_active"]
                            )
                            self.console.print("New prompt added successfully.", style="green")
                        except ValueError as e:
                            self.console.print(f"Error adding prompt: {e}", style="red")
                        except Exception as e:
                            self.console.print(f"An unexpected error occurred: {e}", style="red")
                    else:
                        # Input was cancelled via Ctrl+C during content entry
                        self.console.print("Prompt creation cancelled.", style="yellow")
                except Exception as e: # Catch potential issues with the input() itself if needed
                    self.console.print(f"An error occurred during content input: {e}", style="red")

        except KeyboardInterrupt:
            # Ctrl+C during title/is_active input
            self.console.print("\nPrompt creation cancelled.", style="yellow")
            
        # No explicit return - allows _manage_system_prompts to continue its loop

    def _get_status_markers(self, prompt):
        """Create status indicators for a prompt"""
        active = "●" if prompt.is_active else "○"
        pinned = "📌" if prompt.pinned else "  "
        return f"{active} {pinned}"

    def _display_prompts(self):
        # Sort prompts by pin_order and list_order
        all_prompts = list(self.config.prompts.values())
        pinned_prompts = sorted(
            [p for p in all_prompts if p.pinned],
            key=lambda x: x.pin_order if x.pin_order is not None else float('inf')
        )
        numbered_prompts = sorted(
            [p for p in all_prompts if not p.pinned],
            key=lambda x: x.list_order
        )

        # Display pinned prompts first
        for prompt in pinned_prompts:
            markers = self._get_status_markers(prompt)
            self.console.print(f"📌 {markers} {prompt.title}")

        # Display numbered prompts
        for i, prompt in enumerate(numbered_prompts, 1):
            markers = self._get_status_markers(prompt)
            self.console.print(f"{i}. {markers} {prompt.title}")

    def _show_prompt_actions_menu(self, prompt: SystemPrompt) -> Optional[str]:
        """Shows the actions menu for a selected prompt, looping until an exit condition."""
        while True: # Outer loop for staying in the action menu
            
            # Determine the display identifier for the prompt title
            prompt_display_id = ""
            pinned_keys = ['D', 'F', 'G', 'H', 'J', 'K'] # Keep consistent with _manage_system_prompts
            if prompt.pinned:
                if prompt.pin_order is not None and 0 <= prompt.pin_order < len(pinned_keys):
                    prompt_display_id = f"{pinned_keys[prompt.pin_order]}:"
                else:
                     prompt_display_id = "Pinned:" # Fallback if pin_order is invalid
            else:
                # Assuming list_order is 0-based, add 1 for display
                prompt_display_id = f"{prompt.list_order + 1}:"
                
            # Include status markers too
            markers = self._get_status_markers(prompt)
            full_display_prefix = f"{markers} {prompt_display_id}" # e.g., "● D:" or "○ 3:"
            
            # Build dynamic action list based on prompt state
            actions_available = []

            # Add activation actions
            if not prompt.is_active:
                actions_available.append(("Set as Active", "set_active"))
                actions_available.append(("Activate and Chat", "activate_chat"))
            else:
                actions_available.append(("Start Chat with this Prompt", "activate_chat"))

            # Add pin/unpin actions
            if prompt.pinned:
                actions_available.append(("Unpin Prompt", "unpin"))
            else:
                pinned_count = sum(1 for p in self.config.prompts.values() if p.pinned)
                if pinned_count < 6:
                    actions_available.append(("Pin Prompt", "pin"))
                else:
                    actions_available.append(("[Max Pinned Reached]", "noop"))

            # Add reordering actions (only for non-pinned prompts)
            if not prompt.pinned:
                numbered_prompts = sorted(
                    [p for p in self.config.prompts.values() if not p.pinned],
                    key=lambda x: x.list_order
                )
                current_index = next((i for i, p in enumerate(numbered_prompts) if p.id == prompt.id), -1)

                if current_index > 0:
                    actions_available.append(("Move Up", "move_up"))
                    actions_available.append(("Move to Top", "move_top"))
                if current_index < len(numbered_prompts) - 1:
                    actions_available.append(("Move Down", "move_down"))
                    actions_available.append(("Move to Bottom", "move_bottom"))
                if len(numbered_prompts) > 1:
                    actions_available.append(("Move to Position...", "move_pos"))

            # Add edit actions
            actions_available.append(("Edit Title", "edit_title"))
            actions_available.append(("Edit Content", "edit_content"))

            # Add delete action
            actions_available.append(("Delete Prompt", "delete"))

            # Add back action
            actions_available.append(("(Back to Prompt List)", "back"))

            # Present actions with inquirer
            questions = [
                inquirer.List(
                    'action',
                    # Update message to include the identifier
                    message=f"Actions for {full_display_prefix} '{prompt.title}'",
                    choices=actions_available,
                    carousel=True
                )
            ]

            try:
                answers = inquirer.prompt(questions)
                if not answers: # Handle Ctrl+C during inquirer prompt
                    return None # Exit function entirely

                chosen_action_key = answers['action']

                if chosen_action_key == "noop":
                    continue # Restart the while loop (stay in action menu)
                elif chosen_action_key == "back":
                    break # Exit the while loop, implicitly returns None
                elif chosen_action_key == "set_active":
                    try:
                        self.config.set_active_prompt(prompt.id)
                        self.console.print("Prompt set as active.", style="green")
                        break # Exit the while loop, implicitly returns None
                    except ValueError as e:
                        self.console.print(f"Error setting active prompt: {e}", style="red")
                        continue # Stay in action menu on error
                    except Exception as e:
                        self.console.print(f"An unexpected error occurred: {e}", style="red")
                        continue # Stay in action menu on error
                elif chosen_action_key == "activate_chat":
                    try:
                        # Ensure prompt is set active even if already active (harmless)
                        self.config.set_active_prompt(prompt.id) 
                        return "start_chat" # Exit function immediately
                    except ValueError as e:
                        self.console.print(f"Error activating prompt for chat: {e}", style="red")
                        continue # Stay in action menu on error
                    except Exception as e:
                         self.console.print(f"An unexpected error occurred: {e}", style="red")
                         continue # Stay in action menu on error
                elif chosen_action_key == "pin":
                    try:
                        self.config.toggle_pin_status(prompt.id)
                        self.console.print("Prompt pinned.", style="green")
                        break # Exit the while loop, implicitly returns None
                    except ValueError as e:
                        self.console.print(f"Error pinning prompt: {e}", style="red")
                        continue # Stay in action menu on error
                    except Exception as e:
                         self.console.print(f"An unexpected error occurred: {e}", style="red")
                         continue # Stay in action menu on error
                elif chosen_action_key == "unpin":
                    try:
                        # Handle guided placement
                        position_q = [
                            inquirer.Text(
                                'position',
                                message="Enter desired position in list (leave empty for end)",
                                validate=lambda _, x: not x or x.isdigit()
                            )
                        ]
                        pos_answer = inquirer.prompt(position_q)
                        if pos_answer: # User provided input (didn't Ctrl+C)
                            target_order = int(pos_answer['position']) - 1 if pos_answer['position'] else None
                            self.config.toggle_pin_status(prompt.id, new_list_order_on_unpin=target_order)
                            self.console.print("Prompt unpinned.", style="green")
                            break # Exit the while loop, implicitly returns None
                        else: # User Ctrl+C'd the position prompt
                            self.console.print("Unpin cancelled.", style="yellow")
                            continue # Stay in action menu
                    except ValueError as e:
                        self.console.print(f"Error unpinning prompt: {e}", style="red")
                        continue # Stay in action menu on error
                    except Exception as e:
                         self.console.print(f"An unexpected error occurred: {e}", style="red")
                         continue # Stay in action menu on error
                elif chosen_action_key == "move_up":
                    try:
                        self.config.move_prompt_list_order(prompt.id, -1)
                        break # Exit the while loop, implicitly returns None
                    except ValueError as e:
                        self.console.print(f"Error moving prompt: {e}", style="red")
                        continue # Stay in action menu on error
                    except Exception as e:
                         self.console.print(f"An unexpected error occurred: {e}", style="red")
                         continue # Stay in action menu on error
                elif chosen_action_key == "move_down":
                    try:
                        self.config.move_prompt_list_order(prompt.id, 1)
                        break # Exit the while loop, implicitly returns None
                    except ValueError as e:
                        self.console.print(f"Error moving prompt: {e}", style="red")
                        continue # Stay in action menu on error
                    except Exception as e:
                         self.console.print(f"An unexpected error occurred: {e}", style="red")
                         continue # Stay in action menu on error
                elif chosen_action_key == "move_top":
                    try:
                        self.config.move_prompt_list_top(prompt.id)
                        break # Exit the while loop, implicitly returns None
                    except ValueError as e:
                        self.console.print(f"Error moving prompt: {e}", style="red")
                        continue # Stay in action menu on error
                    except Exception as e:
                         self.console.print(f"An unexpected error occurred: {e}", style="red")
                         continue # Stay in action menu on error
                elif chosen_action_key == "move_bottom":
                    try:
                        self.config.move_prompt_list_bottom(prompt.id)
                        break # Exit the while loop, implicitly returns None
                    except ValueError as e:
                        self.console.print(f"Error moving prompt: {e}", style="red")
                        continue # Stay in action menu on error
                    except Exception as e:
                         self.console.print(f"An unexpected error occurred: {e}", style="red")
                         continue # Stay in action menu on error
                elif chosen_action_key == "move_pos":
                    try:
                        position_q = [
                            inquirer.Text(
                                'position',
                                message="Enter target position number",
                                validate=lambda _, x: x.isdigit() and int(x) > 0
                            )
                        ]
                        pos_answer = inquirer.prompt(position_q)
                        if pos_answer: # User provided input
                            target_position = int(pos_answer['position']) - 1  # Convert to 0-based index
                            self.config.move_prompt_list_position(prompt.id, target_position)
                            break # Exit the while loop, implicitly returns None
                        else: # User Ctrl+C'd position prompt
                            self.console.print("Move cancelled.", style="yellow")
                            continue # Stay in action menu
                    except ValueError as e:
                        self.console.print(f"Error moving prompt: {e}", style="red")
                        continue # Stay in action menu on error
                    except Exception as e:
                         self.console.print(f"An unexpected error occurred: {e}", style="red")
                         continue # Stay in action menu on error
                elif chosen_action_key == "edit_title":
                    try:
                        title_q = [
                            inquirer.Text(
                                'title',
                                message="Enter new title",
                                default=prompt.title
                            )
                        ]
                        title_answer = inquirer.prompt(title_q)
                        if title_answer and title_answer['title'].strip(): # Check if input provided and not just whitespace
                            self.config.edit_title(prompt.id, title_answer['title'])
                            self.console.print("Title updated.", style="green")
                            # Reload the prompt object to reflect title change in the menu message
                            prompt = self.config.prompts.get(prompt.id) 
                            if not prompt:
                                self.console.print("Error reloading prompt after edit, returning to list.", style="red")
                                break # Exit loop if prompt disappears unexpectedly
                            continue # Stay in action menu to allow further edits
                        else: # User cancelled or entered empty title
                            self.console.print("Title edit cancelled.", style="yellow")
                            continue # Stay in action menu
                    except ValueError as e:
                        self.console.print(f"Error editing title: {e}", style="red")
                        continue # Stay in action menu on error
                    except Exception as e:
                         self.console.print(f"An unexpected error occurred: {e}", style="red")
                         continue # Stay in action menu on error
                elif chosen_action_key == "edit_content":
                    # Display current content before editing
                    self.console.print(Panel(prompt.content, title=f"Current Content for [bold]'{prompt.title}'[/bold]", border_style="dim", expand=False))
                    self.console.print() # Add a blank line for spacing
                    
                    # Modify instruction to include Ctrl+C hint
                    self.console.print("Enter new content below. Type EOF on a new line by itself and press Enter to finish. Press Ctrl+C to cancel:")
                    content_lines = []
                    input_cancelled = False
                    try:
                        while True:
                            try:
                                line = input("> ")
                                if line.strip().upper() == 'EOF':
                                    break
                                content_lines.append(line)
                            except EOFError:  # Handle Ctrl+D
                                break
                            except KeyboardInterrupt: # Handle Ctrl+C
                                self.console.print("\nInput cancelled.", style="yellow")
                                content_lines = None
                                input_cancelled = True
                                break # Exit the input loop
                        
                        if not input_cancelled and content_lines is not None:
                            new_content = "\n".join(content_lines)
                            try:
                                self.config.edit_content(prompt.id, new_content)
                                self.console.print("Content updated.", style="green")
                                # Reload prompt content for next potential edit display
                                prompt = self.config.prompts.get(prompt.id)
                                if not prompt:
                                     self.console.print("Error reloading prompt after edit, returning to list.", style="red")
                                     break # Exit loop if prompt disappears unexpectedly
                                continue # Stay in action menu
                            except ValueError as e:
                                self.console.print(f"Error updating content: {e}", style="red")
                                continue # Stay in action menu
                            except Exception as e:
                                self.console.print(f"An unexpected error occurred: {e}", style="red")
                                continue # Stay in action menu
                        else:
                            # Input was cancelled via Ctrl+C or other issue
                            # Message already printed in KeyboardInterrupt handler
                            # self.console.print("Edit operation cancelled.", style="yellow") 
                            continue # Stay in action menu
                    except Exception as e: # Catch potential issues with the input() itself if needed
                        self.console.print(f"An error occurred during input: {e}", style="red")
                        continue # Stay in action menu
                        
                elif chosen_action_key == "delete":
                    try:
                        if prompt.is_active:
                            self.console.print("Warning: This is the active prompt!", style="yellow")
                        
                        confirm_q = [
                            inquirer.Confirm(
                                'confirm',
                                message="Are you sure you want to delete this prompt?",
                                default=False
                            )
                        ]
                        confirm_answer = inquirer.prompt(confirm_q)
                        if confirm_answer and confirm_answer['confirm']:
                            self.config.delete_prompt(prompt.id)
                            self.console.print("Prompt deleted.", style="green")
                            return None  # Exit function immediately
                        else:
                             self.console.print("Deletion cancelled.", style="yellow")
                             continue # Stay in action menu
                    except ValueError as e:
                         self.console.print(f"Error deleting prompt: {e}", style="red")
                         continue # Stay in action menu
                    except Exception as e:
                         self.console.print(f"An unexpected error occurred: {e}", style="red")
                         continue # Stay in action menu

            except KeyboardInterrupt: # Handle Ctrl+C during main action selection
                return None # Exit function entirely
            except Exception as e: # Catch any other unexpected errors in the main loop
                 self.console.print(f"An unexpected error occurred in action menu: {e}", style="red")
                 continue # Stay in action menu

        # If the loop is exited via 'break', return None to refresh caller
        return None

    def _move_prompt(self):
        """Move a system prompt up or down."""
        try:
            prompts = sorted(
                [p for p in self.config.prompts.values() if not p.pinned],
                key=lambda x: x.list_order
            )
            if not prompts:
                self.console.print("No movable prompts available", style="yellow")
                return "system_prompts"

            choices = [f"{idx + 1}. {prompt.title}" for idx, prompt in enumerate(prompts)]
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
                idx = int(answer["prompt_index"].split(".")[0]) - 1
                prompt = prompts[idx]
                direction = -1 if answer["direction"] == "Up" else 1
                self.config.move_prompt_list_order(prompt.id, direction)
                self.console.print("Prompt moved successfully", style="green")

            return "system_prompts"
        except Exception as e:
            self.console.print(f"Error: {e}", style="red")
            return "system_prompts"

    def _delete_prompt(self):
        """Delete a system prompt."""
        try:
            all_prompts = list(self.config.prompts.values())
            if not all_prompts:
                self.console.print("No prompts available", style="yellow")
                return "system_prompts"

            # Sort prompts by pin status and order
            prompts = sorted(
                all_prompts,
                key=lambda p: (p.pin_order if p.pinned else float('inf'), p.list_order)
            )

            choices = [f"{idx + 1}. {prompt.title}" for idx, prompt in enumerate(prompts)]
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
                idx = int(answer["prompt_index"].split(".")[0]) - 1
                prompt = prompts[idx]
                self.config.delete_prompt(prompt.id)
                self.console.print("Prompt deleted successfully", style="green")

            return "system_prompts"
        except Exception as e:
            self.console.print(f"Error: {e}", style="red")
            return "system_prompts"

    def _pin_prompt(self):
        """Pin/Unpin a system prompt."""
        try:
            all_prompts = list(self.config.prompts.values())
            if not all_prompts:
                self.console.print("No prompts available", style="yellow")
                return "system_prompts"

            # Sort prompts by pin status and order
            prompts = sorted(
                all_prompts,
                key=lambda p: (p.pin_order if p.pinned else float('inf'), p.list_order)
            )

            choices = [f"{idx + 1}. {prompt.title} {'(Pinned)' if prompt.pinned else ''}" 
                      for idx, prompt in enumerate(prompts)]
            questions = [
                inquirer.List(
                    "prompt_index",
                    message="Select prompt to pin/unpin:",
                    choices=choices
                )
            ]

            answer = inquirer.prompt(questions)
            if answer:
                idx = int(answer["prompt_index"].split(".")[0]) - 1
                prompt = prompts[idx]
                self.config.toggle_pin_status(prompt.id)
                action = "unpinned" if prompt.pinned else "pinned"
                self.console.print(f"Prompt {action}", style="green")

            return "system_prompts"
        except Exception as e:
            self.console.print(f"Error: {e}", style="red")
            return "system_prompts"

    def _switch_active_prompt(self):
        """Switch the active system prompt."""
        try:
            all_prompts = list(self.config.prompts.values())
            if not all_prompts:
                self.console.print("No prompts available", style="yellow")
                return "system_prompts"

            # Sort prompts by pin status and order
            prompts = sorted(
                all_prompts,
                key=lambda p: (p.pin_order if p.pinned else float('inf'), p.list_order)
            )

            choices = [f"{idx + 1}. {prompt.title} {'(Active)' if prompt.is_active else ''}" 
                      for idx, prompt in enumerate(prompts)]
            questions = [
                inquirer.List(
                    "prompt_index",
                    message="Select prompt to activate:",
                    choices=choices
                )
            ]

            answer = inquirer.prompt(questions)
            if answer:
                idx = int(answer["prompt_index"].split(".")[0]) - 1
                prompt = prompts[idx]
                self.config.set_active_prompt(prompt.id)
                self.console.print("Active prompt updated", style="green")

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
        """(Deprecated/Simplified) Display the current menu breadcrumb."""
        # menu = self.menus[self.state.current_menu] # No longer needed
        
        # Create breadcrumb trail
        breadcrumb = " > ".join(self.state.breadcrumb + [self.state.current_menu.title()])
        self.console.print(f"\n{breadcrumb}", style="bold blue")
        
        # # Display menu items - Now handled by inquirer
        # for key, item in menu.items():
        #     if item.enabled:
        #         prefix = "└─ " if key == list(menu.keys())[-1] else "├─ "
        #         style = "bold green" if item.submenu else "white"
        #         self.console.print(f"{prefix}{item.key_binding}. {item.title}", style=style)

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
            if result == "start_chat":
                self._start_chat()
                return True # Action handled, stop further processing in handle_navigation
            
            # Existing checks
            if result == "quit": 
                return False
            elif result == "back" and self.state.breadcrumb:
                self.state.current_menu = self.state.breadcrumb.pop()

        return True

    def run(self):
        """Main menu loop using inquirer for navigation."""
        self.console.print("WelcOme to Light CroqLI TOOL!", style="bold green")
        
        while True:
            # Display Breadcrumbs
            breadcrumb = " > ".join(self.state.breadcrumb + [self.state.current_menu.title()])
            self.console.print(f"\n{breadcrumb}", style="bold blue")
            
            # Prepare Inquirer Choices
            menu = self.menus[self.state.current_menu]
            choices = []
            for key, item in menu.items():
                if item.enabled:
                    # Put number/key first, use colon separator
                    choice_str = f"{item.key_binding}: {item.title}"
                    choices.append((choice_str, item.key_binding)) # Use key_binding as the value
            
            # Create and execute inquirer prompt
            questions = [
                inquirer.List(
                    'selection',
                    message="Select an option:", # Simple message
                    choices=choices,
                    carousel=True # Keep carousel for longer menus
                )
            ]
            
            try:
                answers = inquirer.prompt(questions)
                if not answers: # Handle Ctrl+C
                    # Decide if Ctrl+C should quit or go back. Let's quit for now.
                    self._quit()
                    break # Exit the main loop
                    
                choice = answers['selection'] # Get the selected key_binding

                if not self.handle_navigation(choice):
                    break # Exit loop if handle_navigation returns False (e.g., Quit action)
            except KeyboardInterrupt: # Should be caught by inquirer, but as fallback
                 self._quit()
                 break
            except Exception as e:
                 self.console.print(f"An unexpected error occurred in main loop: {e}", style="red")
                 # Decide whether to continue or break on unexpected errors
                 # continue # Option to try again
                 break # Option to exit safely

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
                inquirer.Text(
                    "tavily_api_key",
                    message="Enter your Tavily API key (leave empty to keep current):",
                    default=current_keys.tavily_api_key,
                ),
                inquirer.Confirm("confirm", message="Save changes?", default=False),
            ]
            answers = inquirer.prompt(questions)

            if not answers["confirm"]:
                break  # Return without saving

            try:
                # Update APIKeys model
                current_keys.groq_api_key = answers["groq_api_key"]
                current_keys.tavily_api_key = answers["tavily_api_key"]

                # Update the API keys using the tool
                update_result = json.loads(self.tools.update_api_keys(current_keys.model_dump_json()))
                if update_result["status"] == "success":
                    self.console.print("API keys updated successfully.", style="green")
                    # Re-initialize services with new API keys
                    self.groq_service = GroqService()  # Re-initialize GroqService
                    self.tools.groq_service = self.groq_service  # Update tools with new groq_service
                    break  # Exit after successful update
                else:
                    self.console.print(f"Error updating API keys: {update_result['message']}", style="red")

            except Exception as e:
                self.console.print(f"An error occurred: {e}", style="red")

        return "settings"

    def _manage_system_prompts(self) -> Optional[str]:
        """Manage system prompts using a single interactive inquirer list."""
        # Define pinned prompt hotkeys
        pinned_keys = ['D', 'F', 'G', 'H', 'J', 'K']

        while True:  # Loop to allow re-display after actions
            # Refresh data inside the loop
            self.config.load_prompts()
            all_prompts = list(self.config.prompts.values())

            if not all_prompts:
                self.console.print("No system prompts configured yet. Add one!", style="yellow")
                # Still show Add/Back options even if list is empty
                # continue # Old behavior: would return immediately
            
            # Filter and sort prompts
            pinned_prompts = sorted(
                [p for p in all_prompts if p.pinned],
                key=lambda x: x.pin_order if x.pin_order is not None else -1
            )
            numbered_prompts = sorted(
                [p for p in all_prompts if not p.pinned],
                key=lambda x: x.list_order
            )

            # Prepare choices for inquirer
            choices = []

            # Add pinned prompt choices
            for i, p in enumerate(pinned_prompts):
                if i < len(pinned_keys):
                    markers = self._get_status_markers(p)
                    # Put key first
                    choice_str = f"{pinned_keys[i]}: {markers} {p.title}"
                    choices.append((choice_str, p.id))

            # Add numbered prompt choices
            for i, p in enumerate(numbered_prompts):
                markers = self._get_status_markers(p)
                # Put number first
                choice_str = f"{i + 1}: {markers} {p.title}"
                choices.append((choice_str, p.id))

            # Add special actions
            choices.append(("- Add New Prompt -", "add_new"))
            choices.append(("(Back to Main Menu)", "back"))

            # Create and execute inquirer prompt
            questions = [
                inquirer.List(
                    'selection',
                    message="Select prompt (use arrows, DFG keys, or numbers), or choose an action",
                    choices=choices,
                    carousel=True
                )
            ]

            try:
                answers = inquirer.prompt(questions)
                if not answers:
                    return None  # Handle Ctrl+C or other interruption

                selected_value = answers['selection']

                if selected_value == "back":
                    return None # Exit function
                elif selected_value == "add_new":
                    self._add_new_prompt()
                    continue # Re-enter the loop to show updated list
                else:
                    # Find the selected prompt
                    selected_prompt = self.config.prompts.get(selected_value)
                    if selected_prompt:
                        action_result = self._show_prompt_actions_menu(selected_prompt)
                        if action_result == "start_chat":
                            return "start_chat" # Exit function
                        # If action menu returns None (due to break/back), we simply continue the loop here
                        continue # Re-enter the loop to show potentially updated list
                    else:
                        self.console.print("Error: Selected prompt not found.", style="red")
                        continue # Re-enter the loop

            except KeyboardInterrupt:
                return None  # Handle Ctrl+C gracefully

        # This return is likely unreachable now due to the loop structure
        # return None 
