

from src.ui.display import Console
from src.config import load_config
from src.assistant.chat import chat_mode
from src.assistant.search import search_mode
from src.assistant.cli_assistant import cli_assistant_mode

#
class MenuHelper:
    def __init__(self):
        self.config = load_config()
        self.console = Console()

    def display_main_menu(self):
        while True:
            self.console.print("\nWelcome to Light CroqLI!", style="bold green")
            self.console.print("1. Chat Mode")
            self.console.print("2. Search Mode")
            self.console.print("3. CLI-Assistant Mode")
            self.console.print("4. Settings")
            self.console.print("5. System Prompts")
            self.console.print("6. Quit")
            
            choice = self.console.input("Enter your choice (1-6): ")
            
            if choice == "1":
                chat_mode(self.config, self.console)
            elif choice == "2":
                search_mode(self.config, self.console)
            elif choice == "3":
                cli_assistant_mode(self.config, self.console)
            elif choice == "4":
                self.settings_menu()
            elif choice == "5":
                self.system_prompts_menu()
            elif choice == "6":
                self.console.print("Goodbye!", style="bold blue")
                return
            else:
                self.console.print("Invalid choice. Please try again.", style="bold red")

    def settings_menu(self):
        # Implement settings menu logic here
        self.console.print("Settings menu (to be implemented)", style="yellow")

    def system_prompts_menu(self):
        # Implement system prompts menu logic here
        self.console.print("System prompts menu (to be implemented)", style="yellow")


# src/utils/menu_helpers.py

#import inquirer
#from src.config import Config
#
#def model_settings_menu(config):
#    model_max_tokens = {
#        "llama3-8b-8192": 8192,
#        "llama3-70b-8192": 8192,
#        "mixtral-8x7b-32768": 32768,
#        "gemma-7b-it": 8192
#    }
#
#    while True:
#        setting = inquirer.prompt([
#            inquirer.List('setting',
#                          message="Choose a model setting to modify",
#                          choices=['BACK', 'Model Name', 'Max Tokens', 'Temperature', 'Top P', 'Back'])
#        ])['setting']
#
#        if setting == 'BACK' or setting == 'Back':
#            break
#
#        elif setting == 'Model Name':
#            choices = list(config.model_max_tokens.keys()) + ['Back']
#            new_model = inquirer.prompt([
#                inquirer.List('model', 
#                            message="Choose the model to use", 
#                            choices=choices)
#            ])['model']
#            if new_model != 'Back':
#                config.update_model_settings(model=new_model)
#        elif setting == 'Max Tokens':
#            new_max_tokens = inquirer.prompt([
#                inquirer.Text('max_tokens', 
#                              message=f"Enter max tokens (current: {config.max_tokens}, range: 0-{model_max_tokens[config.groq_model]}, default: {config.DEFAULT_SETTINGS['MAX_TOKENS']}):", 
#                              default=str(config.max_tokens))
#            ])['max_tokens']
#            if new_max_tokens.strip():
#                config.update_model_settings(max_tokens=int(new_max_tokens))
#
#        elif setting == 'Temperature':
#            new_temperature = inquirer.prompt([
#                inquirer.Text('temperature', 
#                              message=f"Enter temperature (current: {config.temperature}, range: 0.0-1.0, default: {config.DEFAULT_SETTINGS['TEMPERATURE']}):", 
#                              default=str(config.temperature))
#            ])['temperature']
#            if new_temperature.strip():
#                config.update_model_settings(temperature=float(new_temperature))
#
#        elif setting == 'Top P':
#            new_top_p = inquirer.prompt([
#                inquirer.Text('top_p', 
#                              message=f"Enter top P (current: {config.top_p}, range: 0.0-1.0, default: {config.DEFAULT_SETTINGS['TOP_P']}):", 
#                              default=str(config.top_p))
#            ])['top_p']
#            if new_top_p.strip():
#                config.update_model_settings(top_p=float(new_top_p))
#
#def is_float(value):
#    try:
#        float(value)
#        return True
#    except ValueError:
#        return False
#
#
#def validate_max_tokens(answers, current):
#    max_range = model_max_tokens[answers.get('model', config.groq_model)]
#    return current.isdigit() and 0 <= int(current) <= max_range
#
#def validate_float_range(answers, current):
#    return is_float(current) and 0.0 <= float(current) <= 1.0
#
#model_max_tokens = {
#    "llama3-8b-8192": 8192,
#    "llama3-70b-8192": 8192,
#    "mixtral-8x7b-32768": 32768,
#    "gemma-7b-it": 8192
#}
#
#def validate_max_tokens(answers, current):
#    max_range = model_max_tokens[config.groq_model]
#    return current.isdigit() and 0 <= int(current) <= max_range
#
#def validate_float_range(answers, current):
#    return is_float(current) and 0.0 <= float(current) <= 1.0
#
#
#
#def settings_menu(config: Config):
#    while True:
#        choices = ['BACK', 'Model Settings', 'API Keys', 'System Prompts', 'Back']
#        choice = inquirer.prompt([
#            inquirer.List('setting',
#                          message="Choose a setting to modify:",
#                          choices=choices)
#        ])['setting']
#
#        if choice == 'BACK' or choice == 'Back':
#            return 'back'
#        elif choice == 'Model Settings':
#            model_settings_menu(config)
#        elif choice == 'API Keys':
#            api_keys_menu(config)
#        elif choice == 'System Prompts':
#            result = system_prompts_menu(config)
#            if result == 'chat':
#                return 'chat'
#
#def api_keys_menu(config: Config):
#    while True:
#        new_groq_key = inquirer.prompt([
#            inquirer.Text('groq_key',
#                          message="Enter your new GROQ API key (leave empty to keep current):",
#                          default='')
#        ])['groq_key']
#        
#        new_tavily_key = inquirer.prompt([
#            inquirer.Text('tavily_key',
#                          message="Enter your new Tavily API key (leave empty to keep current):",
#                          default='')
#        ])['tavily_key']
#
#        # Adding a "BACK" option to exit the API keys menu
#        back_choice = inquirer.prompt([
#            inquirer.List('back', message="Go back?", choices=['BACK', 'Back'])
#        ])['back']
#
#        if back_choice == 'BACK' or back_choice == 'Back':
#            break
#
#def prompt_actions_menu(config: Config, index: int):
#    while True:
#        choices = ['BACK', 'Edit Prompt', 'Change Title', 'Move Up', 'Move Down', 'Pin/Unpin', 'Delete', 'Use', 'Back']
#        action = inquirer.prompt([
#            inquirer.List('action',
#                          message=f"Actions for '{config.SYSTEM_PROMPTS[index]['title']}':",
#                          choices=choices)
#        ])['action']
#
#        if action == 'BACK' or action == 'Back':
#            return 'back'
#        elif action == 'Edit Prompt':
#            edit_prompt(config, index)
#        elif action == 'Change Title':
#            change_title(config, index)
#        elif action == 'Move Up':
#            index = move_prompt(config, index, -1)
#        elif action == 'Move Down':
#            index = move_prompt(config, index, 1)
#        elif action == 'Pin/Unpin':
#            pin_unpin_prompt(config, index)
#        elif action == 'Delete':
#            if delete_prompt(config, index):
#                return 'back'
#        elif action == 'Use':
#            use_prompt(config, index)
#            return 'chat'
#        
#        config.save_system_prompts() 
#
#def system_prompts_menu(config: Config):
#    while True:
#        choices = ['BACK']
#        choices += [f"{'[*] ' if i == config.active_prompt_index else '    '}{prompt['title']}" for i, prompt in enumerate(config.SYSTEM_PROMPTS)]
#        choices += ['Add New Prompt', 'Switch Active Prompt', 'Back']
#        
#        choice = inquirer.prompt([
#            inquirer.List('prompt',
#                          message="Choose an action:",
#                          choices=choices)
#        ])['prompt']
#
#        if choice == 'BACK' or choice == 'Back':
#            return 'back'
#        elif choice == 'Add New Prompt':
#            add_new_prompt(config)
#        elif choice == 'Switch Active Prompt':
#            result = switch_active_prompt(config)
#            if result == 'chat':
#                return 'chat'
#        elif '[*]' in choice or choice.strip():
#            index = next((i for i, prompt in enumerate(config.SYSTEM_PROMPTS) if prompt['title'] in choice), None)
#            if index is not None:
#                result = prompt_actions_menu(config, index)
#                if result == 'chat':
#                    return 'chat'
#
#        config.save_system_prompts() 
#
#def switch_active_prompt(config: Config):
#    prompt_choices = [f"{i+1}. {prompt['title']}" for i, prompt in enumerate(config.SYSTEM_PROMPTS)]
#    
#    # Adding a "BACK" option to exit the switch prompt menu
#    prompt_choices.insert(0, 'BACK')
#
#    choice = inquirer.prompt([
#        inquirer.List('prompt', message="Choose a prompt to activate:", choices=prompt_choices)
#    ])['prompt']
#
#    if choice == 'BACK':
#        return 'back'
#    else:
#        # Logic to switch the active prompt
#        pass
#
#def use_prompt(config: Config, index: int):
#    config.set_active_prompt(index)
#    set_key('.env', 'SYSTEM_PROMPT', config.system_prompt)
#    set_key('.env', 'SYSTEM_PROMPT_TITLE', config.SYSTEM_PROMPTS[index]['title'])
#    print(f"Active system prompt switched to: {config.SYSTEM_PROMPTS[index]['title']}")
#    return 'chat'
#
#
#def add_new_prompt(config: Config):
#    new_title = inquirer.prompt([
#        inquirer.Text('title', message="Enter the title for the new prompt:")
#    ])['title']
#    new_prompt = inquirer.prompt([
#        inquirer.Text('prompt', message="Enter the new system prompt:")
#    ])['prompt']
#    config.SYSTEM_PROMPTS.append({'title': new_title, 'prompt': new_prompt, 'pinned': False})
#    config.update_system_prompts(config.SYSTEM_PROMPTS)
#
#
#def edit_prompt(config: Config, index: int):
#    updated_prompt = inquirer.prompt([
#        inquirer.Text('prompt',
#                      message="Edit the system prompt:",
#                      default=config.SYSTEM_PROMPTS[index]['prompt'])
#    ])['prompt']
#    config.SYSTEM_PROMPTS[index]['prompt'] = updated_prompt
#    config.update_system_prompts(config.SYSTEM_PROMPTS)
#
#def change_title(config: Config, index: int):
#    updated_title = inquirer.prompt([
#        inquirer.Text('title',
#                      message="Edit the prompt title:",
#                      default=config.SYSTEM_PROMPTS[index]['title'])
#    ])['title']
#    config.SYSTEM_PROMPTS[index]['title'] = updated_title
#    config.update_system_prompts(config.SYSTEM_PROMPTS)
#
#def move_prompt(config: Config, index: int, direction: int):
#    new_index = index + direction
#    if 0 <= new_index < len(config.SYSTEM_PROMPTS):
#        config.SYSTEM_PROMPTS[index], config.SYSTEM_PROMPTS[new_index] = config.SYSTEM_PROMPTS[new_index], config.SYSTEM_PROMPTS[index]
#        config.update_system_prompts(config.SYSTEM_PROMPTS)
#        return new_index
#    return index
#
#def pin_unpin_prompt(config: Config, index: int):
#    config.SYSTEM_PROMPTS[index]['pinned'] = not config.SYSTEM_PROMPTS[index].get('pinned', False)
#    pinned = [p for p in config.SYSTEM_PROMPTS if p.get('pinned', False)]
#    unpinned = [p for p in config.SYSTEM_PROMPTS if not p.get('pinned', False)]
#    config.SYSTEM_PROMPTS = pinned + unpinned
#    config.update_system_prompts(config.SYSTEM_PROMPTS)
#
#def delete_prompt(config: Config, index: int):
#    if len(config.SYSTEM_PROMPTS) > 1:
#        del config.SYSTEM_PROMPTS[index]
#        if config.active_prompt_index == index:
#            config.active_prompt_index = 0
#        elif config.active_prompt_index > index:
#            config.active_prompt_index -= 1
#        config.update_system_prompts(config.SYSTEM_PROMPTS)
#        return True
#    else:
#        print("Cannot delete the last prompt.")
#        return False
#
#def use_prompt(config: Config, index: int):
#    config.set_active_prompt(index)
#    set_key('.env', 'SYSTEM_PROMPT', config.system_prompt)
#    set_key('.env', 'SYSTEM_PROMPT_TITLE', config.SYSTEM_PROMPTS[index]['title'])
#    print(f"Active system prompt switched to: {config.SYSTEM_PROMPTS[index]['title']}")
#    return 'main_menu'
