# src/config.py

import json
import os
import uuid
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from typing import Any
from src.models.models import SystemPrompt, ModelSettings, APIKeys


# Define config file path
CONFIG_FILE = "config.json"

class Config(BaseModel):
    model_settings: ModelSettings = Field(default_factory=lambda: ModelSettings(model_name="llama3-70b-8192", max_tokens=4096, temperature=0.7, top_p=0.9))
    api_keys: APIKeys = Field(default_factory=lambda: APIKeys(groq_api_key="", tavily_api_key=""))
    prompts: Dict[str, SystemPrompt] = Field(default_factory=dict)
    active_prompt_id: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)

    def _create_default_prompts(self):
        default_prompts = [
            SystemPrompt(
                id=str(uuid.uuid4()),
                title="General Assistant",
                content="You are a helpful assistant that provides clear and concise answers.",
                is_active=True,
                pinned=True,
                pin_order=0,
                list_order=0
            ),
            SystemPrompt(
                id=str(uuid.uuid4()),
                title="Code Helper",
                content="You are a coding assistant that helps with programming questions and debugging.",
                is_active=False,
                pinned=False,
                pin_order=None,
                list_order=1
            ),
            SystemPrompt(
                id=str(uuid.uuid4()),
                title="Technical Writer",
                content="You are a technical writing assistant that helps create documentation and explanations.",
                is_active=False,
                pinned=False,
                pin_order=None,
                list_order=2
            ),
            SystemPrompt(
                id=str(uuid.uuid4()),
                title="CLI Expert",
                content="You are a command-line expert that helps with shell commands and automation.",
                is_active=False,
                pinned=False,
                pin_order=None,
                list_order=3
            ),
            SystemPrompt(
                id=str(uuid.uuid4()),
                title="System Administrator",
                content="You are a system administration expert that helps with system management tasks.",
                is_active=False,
                pinned=False,
                pin_order=None,
                list_order=4
            )
        ]

        # Populate prompts dictionary
        for prompt in default_prompts:
            self.prompts[prompt.id] = prompt
        
        # Set the first prompt as active
        first_prompt = next(iter(self.prompts.values()))
        self.active_prompt_id = first_prompt.id

    @property
    def active_prompt(self) -> Optional[SystemPrompt]:
        if self.active_prompt_id:
            return self.prompts.get(self.active_prompt_id)
        return None

    def load_system_prompts(self, prompts_file="system_prompts.json"):
        try:
            with open(prompts_file, "r") as f:
                data = json.load(f)
                prompts_data = data.get("prompts", {})
                self.prompts = {pid: SystemPrompt(**pdata) for pid, pdata in prompts_data.items()}
                self.active_prompt_id = data.get("active_prompt_id")
                # Ensure is_active flags are consistent
                for prompt in self.prompts.values():
                     prompt.is_active = (prompt.id == self.active_prompt_id)
        except FileNotFoundError:
            print(f"System prompts file ({prompts_file}) not found. Creating defaults.")
            self._create_default_prompts() # Create defaults if file missing
            self.save_system_prompts() # Save the newly created defaults
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            print(f"Error loading system prompts from {prompts_file}: {e}. Using empty/defaults.")
            self.prompts = {}
            self.active_prompt_id = None
            self._create_default_prompts() # Attempt to create defaults even on load error
            # Decide if saving defaults here is appropriate after load error
            # self.save_system_prompts()

    def save_system_prompts(self, prompts_file="system_prompts.json"):
        try:
            with open(prompts_file, "w") as f:
                json.dump({
                    "prompts": {pid: p.model_dump() for pid, p in self.prompts.items()},
                    "active_prompt_id": self.active_prompt_id
                }, f, indent=4)
        except (IOError, TypeError) as e:
             print(f"Error: Failed to save system prompts to {prompts_file}: {str(e)}")
             # raise RuntimeError(f"Failed to save system prompts: {str(e)}")
             
    def save_config(self) -> None:
        """Saves the main configuration (settings, keys) to config.json."""
        CONFIG_FILE = "config.json" # Define locally just in case
        print("DEBUG: Attempting to save config...")
        # Print crucial settings to verify they are correct *before* dumping
        print(f"DEBUG: Saving API Keys: groq={self.api_keys.groq_api_key[:5]}..., tavily={self.api_keys.tavily_api_key[:5]}...")
        print(f"DEBUG: Saving Model Settings: name={self.model_settings.model_name}, tokens={self.model_settings.max_tokens}")
        try:
            # Exclude prompts data from this save, as they are saved separately
            config_data_to_save = self.model_dump(exclude={'prompts', 'active_prompt_id'}, mode='json')
            json_data_to_save = json.dumps(config_data_to_save, indent=4)
            print(f"DEBUG: JSON data to be written:\n{json_data_to_save[:500]}...") # Print beginning of JSON
            with open(CONFIG_FILE, "w") as f:
                 json.dump(config_data_to_save, f, indent=4)
            print(f"DEBUG: Successfully saved config to {CONFIG_FILE}")
        except (IOError, TypeError, ValueError) as e:
            print(f"DEBUG: Error during save_config: {e}")
            print(f"Error: Failed to save configuration to {CONFIG_FILE}: {str(e)}")

    def validate_configuration(self) -> bool:
        try:
            if not all(pid in self.prompts for pid in self.prompts.keys()):
                return False
            if self.active_prompt_id and self.active_prompt_id not in self.prompts:
                return False
            # Add checks for model_settings and api_keys if needed later
            return True
        except Exception:
            return False

    def add_prompt(self, title: str, content: str, make_active: bool = False) -> None:
        """Add a new prompt with the specified title and content"""
        if not title or not content:
            raise ValueError("Title and content cannot be empty")
            
        # Calculate the new list_order
        max_order = max((p.list_order for p in self.prompts.values() if not p.pinned), default=-1)
        
        # Create new prompt
        new_prompt = SystemPrompt(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            is_active=False,
            pinned=False,
            pin_order=None,
            list_order=max_order + 1
        )
        
        # Add to prompts dictionary
        self.prompts[new_prompt.id] = new_prompt
        
        # Set as active if requested
        if make_active:
            self.set_active_prompt(new_prompt.id)
        
        self.save_system_prompts()

    def set_active_prompt(self, prompt_id: Optional[str]) -> None:
        """Set the active prompt by its ID"""
        if prompt_id is not None and prompt_id not in self.prompts:
            raise ValueError("Invalid prompt ID")
            
        self.active_prompt_id = prompt_id
        
        # Update is_active status for all prompts
        for prompt in self.prompts.values():
            prompt.is_active = (prompt.id == prompt_id)
        
        self.save_system_prompts()

    def move_prompt_list_order(self, prompt_id: str, direction: int) -> None:
        """Move a non-pinned prompt up or down by one position"""
        if prompt_id not in self.prompts:
            raise ValueError("Invalid prompt ID")
            
        prompt = self.prompts[prompt_id]
        if prompt.pinned:
            raise ValueError("Cannot move pinned prompts using list_order")
            
        current_order = prompt.list_order
        target_order = current_order + direction
        
        # Find prompt at target order
        target_prompt = next(
            (p for p in self.prompts.values() 
             if not p.pinned and p.list_order == target_order),
            None
        )
        
        if target_prompt:
            # Swap list_order values
            prompt.list_order = target_order
            target_prompt.list_order = current_order
            self.save_system_prompts()

    def move_prompt_list_position(self, prompt_id: str, new_list_order: int) -> None:
        """Move a non-pinned prompt to a specific position"""
        if prompt_id not in self.prompts:
            raise ValueError("Invalid prompt ID")
            
        prompt = self.prompts[prompt_id]
        if prompt.pinned:
            raise ValueError("Cannot move pinned prompts using list_order")
            
        # Calculate maximum valid position
        max_valid_position = max(
            (p.list_order for p in self.prompts.values() 
             if not p.pinned and p.id != prompt_id),
            default=-1
        ) + 1
        
        # Validate new position
        if not (0 <= new_list_order <= max_valid_position):
            raise ValueError(f"Invalid list order. Must be between 0 and {max_valid_position}")
            
        current_order = prompt.list_order
        if new_list_order == current_order:
            return
            
        # Shift other prompts
        if new_list_order < current_order:  # Moving up
            for p in self.prompts.values():
                if not p.pinned and new_list_order <= p.list_order < current_order:
                    p.list_order += 1
        else:  # Moving down
            for p in self.prompts.values():
                if not p.pinned and current_order < p.list_order <= new_list_order:
                    p.list_order -= 1
                    
        # Set new position
        prompt.list_order = new_list_order
        self.save_system_prompts()

    def move_prompt_list_top(self, prompt_id: str) -> None:
        """Move a non-pinned prompt to the top of the list"""
        self.move_prompt_list_position(prompt_id, 0)

    def move_prompt_list_bottom(self, prompt_id: str) -> None:
        """Move a non-pinned prompt to the bottom of the list"""
        max_order = max(
            (p.list_order for p in self.prompts.values() 
             if not p.pinned and p.id != prompt_id),
            default=-1
        )
        self.move_prompt_list_position(prompt_id, max_order + 1)

    def edit_title(self, prompt_id: str, new_title: str) -> None:
        """Edit a prompt's title"""
        if prompt_id not in self.prompts:
            raise ValueError("Invalid prompt ID")
            
        if not new_title or not new_title.strip():
            raise ValueError("Title cannot be empty")
            
        self.prompts[prompt_id].title = new_title.strip()
        self.save_system_prompts()

    def edit_content(self, prompt_id: str, new_content: str) -> None:
        """Edit a prompt's content"""
        if prompt_id not in self.prompts:
            raise ValueError("Invalid prompt ID")
            
        if new_content is None:
            raise ValueError("Content cannot be None")
            
        self.prompts[prompt_id].content = new_content
        self.save_system_prompts()

    def toggle_pin_status(self, prompt_id: str, new_list_order_on_unpin: Optional[int] = None) -> None:
        """Toggle the pin status of a prompt and handle order recalculation"""
        if prompt_id not in self.prompts:
            raise ValueError("Invalid prompt ID")
            
        prompt = self.prompts[prompt_id]
        
        if not prompt.pinned:  # Pinning the prompt
            # Check pinned count limit
            pinned_count = sum(1 for p in self.prompts.values() if p.pinned)
            if pinned_count >= 6:
                raise ValueError("Maximum 6 pinned prompts allowed.")
                
            # Store current list order before pinning
            old_list_order = prompt.list_order
            
            # Update prompt to pinned status
            prompt.pinned = True
            prompt.pin_order = pinned_count
            prompt.list_order = -1  # No longer in numbered list
            
            # Recalculate list_order for affected non-pinned prompts
            for p in self.prompts.values():
                if not p.pinned and p.list_order > old_list_order:
                    p.list_order -= 1
                    
        else:  # Unpinning the prompt
            # Store current pin order before unpinning
            old_pin_order = prompt.pin_order
            
            # Update prompt to unpinned status
            prompt.pinned = False
            prompt.pin_order = None
            
            # Determine new list_order
            target_list_order = -1
            if new_list_order_on_unpin is not None and new_list_order_on_unpin >= 0:
                target_list_order = new_list_order_on_unpin
            else:
                # Calculate position at the end
                max_order = max((p.list_order for p in self.prompts.values() if not p.pinned), default=-1)
                target_list_order = max_order + 1
            
            # Shift other non-pinned prompts if inserting at specific position
            if new_list_order_on_unpin is not None:
                for p in self.prompts.values():
                    if not p.pinned and p.list_order >= target_list_order:
                        p.list_order += 1
            
            # Set the unpinned prompt's order
            prompt.list_order = target_list_order
            
            # Recalculate pin_order for remaining pinned prompts
            for p in self.prompts.values():
                if p.pinned and p.pin_order is not None and p.pin_order > old_pin_order:
                    p.pin_order -= 1
        
        self.save_system_prompts()

    def delete_prompt(self, prompt_id: str) -> None:
        """Delete a prompt by its ID and handle order recalculation"""
        if prompt_id not in self.prompts:
            raise ValueError("Invalid prompt ID")
            
        # Store prompt info before deletion
        prompt = self.prompts.get(prompt_id)
        if not prompt:
            print(f"ERROR: Prompt ID {prompt_id} not found in self.prompts despite initial check.")
            return
             
        old_list_order = prompt.list_order
        was_pinned = prompt.pinned
        old_pin_order = prompt.pin_order
        
        # Delete the prompt
        del self.prompts[prompt_id]
        
        # Handle active prompt
        active_prompt_was_deleted = False
        if self.active_prompt_id == prompt_id:
            active_prompt_was_deleted = True
            self.active_prompt_id = None
            
            # Find new prompt to activate
            remaining_prompts = sorted(
                self.prompts.values(),
                key=lambda p: (p.pin_order if p.pinned else float('inf'), p.list_order)
            )
            
            if remaining_prompts:
                self.set_active_prompt(remaining_prompts[0].id)
            else:
                self.active_prompt_id = None
                self.save_system_prompts() 

        # Recalculate orders only if the active prompt wasn't deleted (as set_active_prompt handles saving)
        if not active_prompt_was_deleted:
            if was_pinned:
                # Update pin_order for remaining pinned prompts
                for p in self.prompts.values():
                    if p.pinned and p.pin_order is not None and old_pin_order is not None and p.pin_order > old_pin_order:
                        p.pin_order -= 1
            else:
                # Update list_order for remaining non-pinned prompts
                for p in self.prompts.values():
                    if not p.pinned and old_list_order is not None and p.list_order > old_list_order:
                        p.list_order -= 1
            
            self.save_system_prompts()

# --- MODIFIED load_config Function --- 
def load_config() -> Config:
    config_instance = None
    CONFIG_FILE = "config.json" # Define constant locally for safety
    try:
        print(f"Loading main configuration from {CONFIG_FILE}...")
        with open(CONFIG_FILE, "r") as f:
            config_data = json.load(f)
            print("DEBUG: Raw data loaded from config.json:")
            print(json.dumps(config_data, indent=2)) # Print loaded data nicely
            # We only load settings/keys from config.json
            # Prompts will be loaded separately by load_system_prompts
            config_instance = Config(**config_data)
            print("DEBUG: Config object created from loaded data:")
            print(f"DEBUG: Loaded API Keys: groq={config_instance.api_keys.groq_api_key[:5]}..., tavily={config_instance.api_keys.tavily_api_key[:5]}...")
            print(f"DEBUG: Loaded Model Settings: name={config_instance.model_settings.model_name}, tokens={config_instance.model_settings.max_tokens}")
            print(f"Main config loaded: {config_instance.model_settings}, {config_instance.api_keys}")
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e: # Added ValueError for Pydantic validation
        print(f"Failed to load or validate {CONFIG_FILE} ({e}). Using default settings.")
        config_instance = Config() # Create instance with default settings/keys
        print("DEBUG: Created default Config object:")
        print(f"DEBUG: Default API Keys: groq={config_instance.api_keys.groq_api_key[:5]}..., tavily={config_instance.api_keys.tavily_api_key[:5]}...")
        print(f"DEBUG: Default Model Settings: name={config_instance.model_settings.model_name}, tokens={config_instance.model_settings.max_tokens}")
        # Uncomment save call now that save_config exists
        print(f"Saving default main configuration to {CONFIG_FILE}...")
        config_instance.save_config() # Save the defaults immediately
    except Exception as e:
         print(f"Unexpected error loading main config: {e}. Using default settings.")
         config_instance = Config() # Fallback to defaults
         print("DEBUG: Created default Config object after unexpected error:")
         print(f"DEBUG: Default API Keys: groq={config_instance.api_keys.groq_api_key[:5]}..., tavily={config_instance.api_keys.tavily_api_key[:5]}...")
         print(f"DEBUG: Default Model Settings: name={config_instance.model_settings.model_name}, tokens={config_instance.model_settings.max_tokens}")
         # Decide if saving is safe after unexpected error
         # config_instance.save_config()
         
    # Ensure we have an instance
    if config_instance is None:
        print("Critical error: config_instance is None after load attempts. Creating defaults.")
        config_instance = Config()
        print("DEBUG: Created default Config object after critical error:")
        print(f"DEBUG: Default API Keys: groq={config_instance.api_keys.groq_api_key[:5]}..., tavily={config_instance.api_keys.tavily_api_key[:5]}...")
        print(f"DEBUG: Default Model Settings: name={config_instance.model_settings.model_name}, tokens={config_instance.model_settings.max_tokens}")
        # Consider saving here too, although it might indicate a deeper issue
        # config_instance.save_config()

    # --- Load system prompts AFTER loading/creating main config --- 
    print("Loading system prompts...")
    # Assuming load_system_prompts is defined in Config class
    if hasattr(config_instance, 'load_system_prompts') and callable(getattr(config_instance, 'load_system_prompts')):
         config_instance.load_system_prompts() # Call the separate prompt loading method
    else:
         print("Error: config_instance does not have load_system_prompts method.")
         # Handle this error appropriately - maybe create default prompts?
         if hasattr(config_instance, '_create_default_prompts'):
              config_instance._create_default_prompts()

    print("Configuration loading complete.")
    return config_instance
