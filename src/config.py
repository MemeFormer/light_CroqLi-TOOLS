# src/config.py

import json
import os
import uuid
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from typing import Any
from src.models.models import SystemPrompt, ModelSettings, APIKeys

# Define the configuration file path
CONFIG_FILE = "config.json"
# Define the (now legacy) system prompts file path for migration
LEGACY_PROMPTS_FILE = "system_prompts.json"

class Config(BaseModel):
    # Removed old fields: groq_model, max_tokens, temperature, top_p, system_prompt, active_prompt_index, load_systemprompts, groq_api_key
    
    # New fields for consolidated settings
    model_settings: ModelSettings = Field(default_factory=lambda: ModelSettings(model_name="llama3-70b-8192", max_tokens=4096, temperature=0.7, top_p=0.9))
    api_keys: APIKeys = Field(default_factory=lambda: APIKeys(groq_api_key="", tavily_api_key=""))
    # TODO (Multi-Vendor): Add selected_vendor: str = "groq" here later.
    # TODO (Multi-Vendor): Change api_keys to Dict[str, str] later.
    
    # Prompt management fields
    prompts: Dict[str, SystemPrompt] = Field(default_factory=dict)
    active_prompt_id: Optional[str] = None

    # No custom __init__ needed anymore, Pydantic handles defaults
    # If prompts is empty after potential loading, create defaults (handled in load_config)

    def _create_default_prompts(self):
        default_prompts = [
            SystemPrompt(
                id=str(uuid.uuid4()),
                title="General Assistant",
                content="You are a helpful assistant that provides clear and concise answers.",
                is_active=True,
                pinned=True,
                pin_order=0,
                list_order=0 # list_order starts from 0 now
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
        # Set the first prompt as active if none is set yet
        if not self.active_prompt_id and self.prompts:
             first_prompt_id = next(iter(self.prompts.keys()), None)
             self.active_prompt_id = first_prompt_id
             if first_prompt_id:
                 self.prompts[first_prompt_id].is_active = True

    @property
    def active_prompt(self) -> Optional[SystemPrompt]:
        if self.active_prompt_id:
            return self.prompts.get(self.active_prompt_id)
        return None

    # --- Prompt Management Methods (Update to use self.save_config()) --- 
    def add_prompt(self, title: str, content: str, make_active: bool = False) -> None:
        """Add a new prompt with the specified title and content"""
        if not title or not content:
            raise ValueError("Title and content cannot be empty")
        max_order = max((p.list_order for p in self.prompts.values() if not p.pinned), default=-1)
        new_prompt = SystemPrompt(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            is_active=False,
            pinned=False,
            pin_order=None,
            list_order=max_order + 1
        )
        self.prompts[new_prompt.id] = new_prompt
        if make_active:
            self.set_active_prompt(new_prompt.id) # This will save
        else:
            self.save_config() # Save if not setting active

    def set_active_prompt(self, prompt_id: Optional[str]) -> None:
        """Set the active prompt by its ID"""
        if prompt_id is not None and prompt_id not in self.prompts:
            raise ValueError("Invalid prompt ID")
        self.active_prompt_id = prompt_id
        for prompt in self.prompts.values():
            prompt.is_active = (prompt.id == prompt_id)
        self.save_config() # Save config after updating active status

    def move_prompt_list_order(self, prompt_id: str, direction: int) -> None:
        """Move a non-pinned prompt up or down by one position"""
        if prompt_id not in self.prompts: raise ValueError("Invalid prompt ID")
        prompt = self.prompts[prompt_id]
        if prompt.pinned: raise ValueError("Cannot move pinned prompts")
        current_order = prompt.list_order
        target_order = current_order + direction
        target_prompt = next((p for p in self.prompts.values() if not p.pinned and p.list_order == target_order), None)
        if target_prompt:
            prompt.list_order = target_order
            target_prompt.list_order = current_order
            self.save_config() # Save config

    def move_prompt_list_position(self, prompt_id: str, new_list_order: int) -> None:
        """Move a non-pinned prompt to a specific position"""
        if prompt_id not in self.prompts: raise ValueError("Invalid prompt ID")
        prompt = self.prompts[prompt_id]
        if prompt.pinned: raise ValueError("Cannot move pinned prompts")
        max_valid_position = max((p.list_order for p in self.prompts.values() if not p.pinned and p.id != prompt_id), default=-1) + 1
        if not (0 <= new_list_order <= max_valid_position): raise ValueError(f"Invalid list order.")
        current_order = prompt.list_order
        if new_list_order == current_order: return
        if new_list_order < current_order:
            for p in self.prompts.values():
                if not p.pinned and new_list_order <= p.list_order < current_order: p.list_order += 1
        else:
            for p in self.prompts.values():
                if not p.pinned and current_order < p.list_order <= new_list_order: p.list_order -= 1
        prompt.list_order = new_list_order
        self.save_config() # Save config

    def move_prompt_list_top(self, prompt_id: str) -> None:
        """Move a non-pinned prompt to the top of the list"""
        self.move_prompt_list_position(prompt_id, 0) # This calls save_config

    def move_prompt_list_bottom(self, prompt_id: str) -> None:
        """Move a non-pinned prompt to the bottom of the list"""
        max_order = max((p.list_order for p in self.prompts.values() if not p.pinned and p.id != prompt_id), default=-1)
        self.move_prompt_list_position(prompt_id, max_order + 1) # This calls save_config

    def edit_title(self, prompt_id: str, new_title: str) -> None:
        """Edit a prompt's title"""
        if prompt_id not in self.prompts: raise ValueError("Invalid prompt ID")
        if not new_title or not new_title.strip(): raise ValueError("Title cannot be empty")
        self.prompts[prompt_id].title = new_title.strip()
        self.save_config() # Save config

    def edit_content(self, prompt_id: str, new_content: str) -> None:
        """Edit a prompt's content"""
        if prompt_id not in self.prompts: raise ValueError("Invalid prompt ID")
        if new_content is None: raise ValueError("Content cannot be None")
        self.prompts[prompt_id].content = new_content
        self.save_config() # Save config

    def toggle_pin_status(self, prompt_id: str, new_list_order_on_unpin: Optional[int] = None) -> None:
        """Toggle the pin status of a prompt and handle order recalculation"""
        if prompt_id not in self.prompts: raise ValueError("Invalid prompt ID")
        prompt = self.prompts[prompt_id]
        if not prompt.pinned:
            pinned_count = sum(1 for p in self.prompts.values() if p.pinned)
            if pinned_count >= 6: raise ValueError("Maximum 6 pinned prompts allowed.")
            old_list_order = prompt.list_order
            prompt.pinned = True
            prompt.pin_order = pinned_count
            prompt.list_order = -1
            for p in self.prompts.values():
                if not p.pinned and p.list_order > old_list_order: p.list_order -= 1
        else:
            old_pin_order = prompt.pin_order
            prompt.pinned = False
            prompt.pin_order = None
            target_list_order = -1
            if new_list_order_on_unpin is not None and new_list_order_on_unpin >= 0:
                target_list_order = new_list_order_on_unpin
            else:
                max_order = max((p.list_order for p in self.prompts.values() if not p.pinned), default=-1)
                target_list_order = max_order + 1
            if new_list_order_on_unpin is not None:
                for p in self.prompts.values():
                    if not p.pinned and p.list_order >= target_list_order: p.list_order += 1
            prompt.list_order = target_list_order
            for p in self.prompts.values():
                if p.pinned and p.pin_order is not None and old_pin_order is not None and p.pin_order > old_pin_order: p.pin_order -= 1
        self.save_config() # Save config

    def delete_prompt(self, prompt_id: str) -> None:
        """Delete a prompt by its ID and handle order recalculation"""
        if prompt_id not in self.prompts: raise ValueError("Invalid prompt ID")
        prompt = self.prompts.get(prompt_id)
        if not prompt: return
        old_list_order = prompt.list_order
        was_pinned = prompt.pinned
        old_pin_order = prompt.pin_order
        del self.prompts[prompt_id]
        active_prompt_was_deleted = False
        if self.active_prompt_id == prompt_id:
            active_prompt_was_deleted = True
            self.active_prompt_id = None
            remaining_prompts = sorted(self.prompts.values(), key=lambda p: (p.pin_order if p.pinned else float('inf'), p.list_order))
            if remaining_prompts:
                self.set_active_prompt(remaining_prompts[0].id) # This will save
            else:
                self.active_prompt_id = None
                self.save_config() # Save if no prompts left to set active
        if not active_prompt_was_deleted:
            if was_pinned:
                for p in self.prompts.values():
                    if p.pinned and p.pin_order is not None and old_pin_order is not None and p.pin_order > old_pin_order: p.pin_order -= 1
            else:
                for p in self.prompts.values():
                    if not p.pinned and old_list_order is not None and p.list_order > old_list_order: p.list_order -= 1
            self.save_config() # Save config

    # --- REMOVED load_prompts and save_prompts --- 

    # --- NEW save_config method --- 
    def save_config(self):
        """Save the entire config object to config.json"""
        try:
            with open(CONFIG_FILE, "w") as f:
                # Use model_dump_json for direct JSON string output
                f.write(self.model_dump_json(indent=4))
        except IOError as e:
            # Consider more specific error handling or logging
            print(f"[ERROR] Failed to save configuration to {CONFIG_FILE}: {str(e)}")
            # raise RuntimeError(f"Failed to save configuration: {str(e)}") # Optional: re-raise

    # --- REMOVED validate_configuration --- (Pydantic handles validation on load)

# --- UPDATED load_config function --- 
def load_config() -> Config:
    """Load the entire configuration from config.json"""
    config_instance = None
    try:
        print(f"Attempting to load configuration from {CONFIG_FILE}...")
        with open(CONFIG_FILE, "r") as f:
            config_data = json.load(f)
            config_instance = Config(**config_data)
            print("Configuration loaded successfully.")
            # Optional: Migrate legacy prompts if config.json exists but prompts are empty 
            # AND system_prompts.json exists
            if not config_instance.prompts and os.path.exists(LEGACY_PROMPTS_FILE):
                 print("Config loaded but no prompts found, attempting legacy migration...")
                 _migrate_legacy_prompts(config_instance)
                 config_instance.save_config() # Save migrated config
                 print("Legacy prompts migrated and config saved.")
                 # Optionally remove or rename legacy file after migration
                 # os.rename(LEGACY_PROMPTS_FILE, LEGACY_PROMPTS_FILE + ".migrated")

    except FileNotFoundError:
        print(f"{CONFIG_FILE} not found. Creating default configuration.")
        config_instance = Config() # Uses default_factory for fields
        config_instance._create_default_prompts() # Populate default prompts
        config_instance.save_config() # Save the new default config
    except (json.JSONDecodeError, TypeError, ValueError) as e: # Catch Pydantic validation errors too (ValueError)
        print(f"Error loading or validating {CONFIG_FILE}: {str(e)}. Creating default configuration.")
        config_instance = Config()
        config_instance._create_default_prompts()
        config_instance.save_config() # Attempt to save defaults even if load failed
    except Exception as e:
        print(f"An unexpected error occurred during config load: {str(e)}. Using in-memory defaults.")
        # Fallback to in-memory defaults without saving if unexpected error
        config_instance = Config()
        config_instance._create_default_prompts()
        
    # Final check: Ensure prompts exist even if loading somehow failed partially
    if not config_instance.prompts:
        print("No prompts found after load attempt, ensuring defaults.")
        config_instance._create_default_prompts()
        # Decide if saving here is appropriate after a partial failure
        # config_instance.save_config()

    return config_instance

# Helper function for legacy migration (internal use)
def _migrate_legacy_prompts(config_instance: Config):
    """Loads prompts from legacy system_prompts.json into the config instance."""
    try:
        with open(LEGACY_PROMPTS_FILE, "r") as f:
            data = json.load(f)
            prompts_data = data.get("prompts", {})
            
            # Basic check for old format structure (presence of 'name' or 'prompt_text')
            sample_prompt = next(iter(prompts_data.values())) if prompts_data else {}
            is_old_format = "name" in sample_prompt or "prompt_text" in sample_prompt

            if is_old_format:
                migrated_prompts = {}
                # Simple migration: try to map fields, assign default orders
                list_idx = 0
                pin_idx = 0
                for pid, pdata in prompts_data.items():
                    is_pinned = pdata.get("priority") == 1 # Old priority field
                    new_p = SystemPrompt(
                        id=pid,
                        title=pdata.get("name", "Untitled"),
                        content=pdata.get("prompt_text", ""),
                        is_active=pdata.get("is_active", False),
                        pinned=is_pinned,
                        pin_order=pin_idx if is_pinned else None,
                        list_order=list_idx if not is_pinned else -1
                    )
                    migrated_prompts[pid] = new_p
                    if is_pinned:
                        pin_idx += 1
                    else:
                        list_idx += 1
                config_instance.prompts = migrated_prompts
                config_instance.active_prompt_id = data.get("active_prompt_id")
                # Ensure active_id is valid
                if config_instance.active_prompt_id not in config_instance.prompts:
                    config_instance.active_prompt_id = next(iter(config_instance.prompts.keys()), None)
                # Correct is_active flags
                for p in config_instance.prompts.values():
                    p.is_active = (p.id == config_instance.active_prompt_id)
                print(f"Successfully migrated {len(migrated_prompts)} prompts from {LEGACY_PROMPTS_FILE}.")
            else:
                 print(f"{LEGACY_PROMPTS_FILE} does not appear to be in the expected legacy format.")

    except FileNotFoundError:
        print(f"Legacy prompts file {LEGACY_PROMPTS_FILE} not found for migration.")
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        print(f"Error reading or parsing legacy prompts file {LEGACY_PROMPTS_FILE}: {e}")
    except Exception as e:
         print(f"An unexpected error occurred during legacy prompt migration: {e}")
