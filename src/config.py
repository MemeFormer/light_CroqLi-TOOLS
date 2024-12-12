# src/config.py

import json
import os
import uuid
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from typing import Any
from src.models.models import MenuSystemPrompt, MenuSystemPromptModel



class Config(BaseModel):
    groq_model: str = "llama3-70b-8192"
    max_tokens: int = 1000
    temperature: float = 0.7
    top_p: float = 0.9
    system_prompt: str = ""
    active_prompt_index: int = 0
    load_systemprompts: List[Dict[str, Any]] = Field(default_factory=list)
    groq_api_key: Optional[str] = None
    prompts_U: Dict[str, MenuSystemPrompt] = Field(default_factory=dict)  # Changed to MenuSystemPrompt
    display_order_U: List[str] = Field(default_factory=list)
    active_prompt_id_U: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if not self.prompts_U:  # If no prompts exist, create default ones
            self._create_default_prompts()

    def _create_default_prompts(self):
        default_prompts = [
            MenuSystemPrompt(
                name="General Assistant",
                prompt_text="You are a helpful assistant that provides clear and concise answers.",
                is_active=True,
                priority=1  # Pinned
            ),
            MenuSystemPrompt(
                name="Code Helper",
                prompt_text="You are a coding assistant that helps with programming questions and debugging.",
                is_active=False,
                priority=0
            ),
            MenuSystemPrompt(
                name="Technical Writer",
                prompt_text="You are a technical writing assistant that helps create documentation and explanations.",
                is_active=False,
                priority=0
            ),
            MenuSystemPrompt(
                name="CLI Expert",
                prompt_text="You are a command-line expert that helps with shell commands and automation.",
                is_active=False,
                priority=0
            ),
            MenuSystemPrompt(
                name="System Administrator",
                prompt_text="You are a system administration expert that helps with system management tasks.",
                is_active=False,
                priority=0
            )
        ]

        for prompt in default_prompts:
            self.prompts_U[prompt.id] = prompt
            self.display_order_U.append(prompt.id)
        
        # Set the first prompt as active
        self.active_prompt_id_U = self.display_order_U[0]

    @property
    def prompts(self) -> List[MenuSystemPrompt]:
        return [self.prompts_U[prompt_id] for prompt_id in self.display_order_U]

    @property
    def active_prompt(self) -> Optional[MenuSystemPrompt]:
        if self.active_prompt_id_U:
            return self.prompts_U.get(self.active_prompt_id_U)
        return None

    def add_prompt(self, new_prompt: MenuSystemPrompt) -> None:
        """Add a new prompt from MenuSystemPrompt object"""
        if not new_prompt.name or not new_prompt.prompt_text:
            raise ValueError("Name and prompt text cannot be empty")
            
        prompt = MenuSystemPrompt(
            content=new_prompt.prompt_text,
            name=new_prompt.name,
            is_active=new_prompt.is_active,
            priority=new_prompt.priority
        )
        
        self.prompts_U[prompt.id] = new_prompt
        self.display_order_U.append(new_prompt.id)
        
        if new_prompt.is_active:
            self._set_active_prompt(len(self.display_order_U) - 1)
            
        self._update_display_indices()
        self.save_systemprompts_U()

    def update_prompt(self, display_idx: int, updated_prompt: MenuSystemPrompt) -> None:
        """Update an existing prompt"""
        if not (0 <= display_idx < len(self.display_order_U)):
            raise ValueError("Invalid display index")
            
        prompt_id = self.display_order_U[display_idx]
        prompt = self.prompts_U[prompt_id]
        
        prompt.name = updated_prompt.name
        prompt.content = updated_prompt.prompt_text
        
        if updated_prompt.is_active:
            self._set_active_prompt(display_idx)
        
        self.save_systemprompts_U()

    def _update_display_indices(self):
        for idx, prompt_id in enumerate(self.display_order_U):
            self.prompts_U[prompt_id].display_index = idx

    def set_active_prompt(self, display_idx: int) -> None:
        """Public method to set active prompt"""
        self._set_active_prompt(display_idx)

    def pin_prompt(self, display_idx: int) -> None:
        """Public method to toggle pin status"""
        self._pin_prompt(display_idx)
    def _set_active_prompt(self, display_idx: int):
        try:
            if display_idx is None:
                self.active_prompt_id_U = None
            elif 0 <= display_idx < len(self.display_order_U):
                prompt_id = self.display_order_U[display_idx]
                self.active_prompt_id_U = prompt_id
                self.prompts_U[prompt_id].is_active = True
                for pid in self.prompts_U:
                    if pid != prompt_id:
                        self.prompts_U[pid].is_active = False
            else:
                raise ValueError("Invalid display index")
            self.save_config()
        except Exception as e:
            raise RuntimeError(f"Failed to set active prompt: {str(e)}")

    def _pin_prompt(self, display_idx: int) -> None:
            """Toggle pin status of a prompt"""
            try:
                if not (0 <= display_idx < len(self.display_order_U)):
                    raise ValueError("Invalid display index")

                prompt_id = self.display_order_U[display_idx]
                prompt = self.prompts_U[prompt_id]

                # Toggle priority
                prompt.priority = 1 if prompt.priority == 0 else 0

                # Reorder the display order based on pin status
                self._reorder_after_pin_change(prompt_id)
                self._update_display_indices()
                self.save_systemprompts_U()

            except Exception as e:
                raise RuntimeError(f"Failed to toggle pin status: {str(e)}")

    def _reorder_after_pin_change(self, changed_prompt_id: str) -> None:
        """Reorder prompts after a pin status change"""
        # Remove the changed prompt from current order
        self.display_order_U.remove(changed_prompt_id)
        
        # Find insertion point for the prompt based on its new priority
        changed_prompt = self.prompts_U[changed_prompt_id]
        insertion_idx = 0
        
        if changed_prompt.priority == 1:  # If newly pinned
            # Find the last pinned prompt
            while (insertion_idx < len(self.display_order_U) and 
                   self.prompts_U[self.display_order_U[insertion_idx]].priority == 1):
                insertion_idx += 1
        else:  # If unpinned
            # Skip all pinned prompts
            while (insertion_idx < len(self.display_order_U) and 
                   self.prompts_U[self.display_order_U[insertion_idx]].priority == 1):
                insertion_idx += 1
            
        # Insert at the appropriate position
        self.display_order_U.insert(insertion_idx, changed_prompt_id)

    def move_prompt(self, display_idx: int, direction: int) -> None:
        """Public method to move prompt"""
        self._move_prompt(display_idx, direction)

    def _move_prompt(self, display_idx: int, direction: int) -> None:
        """Move a prompt up or down within its priority group"""
        try:
            if not (0 <= display_idx < len(self.display_order_U)):
                raise ValueError("Invalid display index")
            
            current_id = self.display_order_U[display_idx]
            current_prompt = self.prompts_U[current_id]
            
            # Calculate new index ensuring we stay within the same priority group
            new_idx = display_idx + direction
            while (0 <= new_idx < len(self.display_order_U)):
                target_id = self.display_order_U[new_idx]
                target_prompt = self.prompts_U[target_id]
                
                # Only swap if both prompts have the same priority
                if target_prompt.priority == current_prompt.priority:
                    self.display_order_U[display_idx], self.display_order_U[new_idx] = \
                        self.display_order_U[new_idx], self.display_order_U[display_idx]
                    break
                    
                new_idx += direction
                
            self._update_display_indices()
            self.save_systemprompts_U()
            
        except Exception as e:
            raise RuntimeError(f"Failed to move prompt: {str(e)}")

    def delete_prompt(self, display_idx: int):
        try:
            prompt_id = self.display_order_U.pop(display_idx)
            del self.prompts_U[prompt_id]
            self._update_display_indices()
            if self.active_prompt_id_U == prompt_id:
                self.set_active_prompt(0)
            self.save_config()
        except IndexError:
            pass

    def load_systemprompts_U(self, prompts_file="system_prompts_U.json"):
        try:
            with open(prompts_file, "r") as f:
                data = json.load(f)
                self.prompts_U = {pid: MenuSystemPrompt(**pdata) for pid, pdata in data.get("prompts", {}).items()}
                self.display_order_U = data.get("display_order", [])
                self.active_prompt_id_U = data.get("active_prompt_id")
                self._update_display_indices()
        except FileNotFoundError:
            self.prompts_U = {}
            self.display_order_U = []
            self.active_prompt_id_U = None

    def save_systemprompts_U(self, prompts_file="system_prompts_U.json"):
        try:
            with open(prompts_file, "w") as f:
                json.dump({
                    "prompts": {pid: p.dict() for pid, p in self.prompts_U.items()},
                    "display_order": self.display_order_U,
                    "active_prompt_id": self.active_prompt_id_U
                }, f, indent=4)
        except IOError as e:
            raise RuntimeError(f"Failed to save system prompts: {str(e)}")

    def rename_prompt(self, display_idx: int, new_name: str) -> None:
        """Rename a prompt"""
        if not (0 <= display_idx < len(self.display_order_U)):
            raise ValueError("Invalid display index")
        
        prompt_id = self.display_order_U[display_idx]
        self.prompts_U[prompt_id].name = new_name
        self.save_systemprompts_U()

    def edit_prompt_text(self, display_idx: int, new_text: str) -> None:
        """Edit prompt text"""
        if not (0 <= display_idx < len(self.display_order_U)):
            raise ValueError("Invalid display index")
        
        prompt_id = self.display_order_U[display_idx]
        self.prompts_U[prompt_id].content = new_text
        self.save_systemprompts_U()

    def get_prompt(self, display_idx: int) -> Optional[MenuSystemPrompt]:
        """Get prompt by display index"""
        if not (0 <= display_idx < len(self.display_order_U)):
            return None
        
        prompt_id = self.display_order_U[display_idx]
        return self.prompts_U.get(prompt_id)

    def save_config(self, config_file: str = "config.json") -> None:
        try:
            with open(config_file, "w") as f:
                config_data = self.dict()
                json.dump(config_data, f, indent=4)
        except (IOError, TypeError) as e:
            raise RuntimeError(f"Failed to save configuration: {str(e)}")

    
    def validate_configuration(self) -> bool:
        try:
            if not all(pid in self.prompts_U for pid in self.display_order_U):
                return False

            if self.active_prompt_id_U and self.active_prompt_id_U not in self.prompts_U:
                return False

            return True
        except Exception:
            return False

    def prompt_exists(self, display_idx: int) -> bool:
        return 0 <= display_idx < len(self.display_order_U)

    def to_db_model(self, menu_prompt: MenuSystemPrompt) -> MenuSystemPromptModel:
        """Convert MenuSystemPrompt to MenuSystemPromptModel for database storage"""
        return MenuSystemPromptModel(
            id=menu_prompt.id,
            name=menu_prompt.name,
            prompt_text=menu_prompt.prompt_text,
            pinned=(menu_prompt.priority == 1),
            is_active=menu_prompt.is_active
        )

    def from_db_model(self, db_model: MenuSystemPromptModel) -> MenuSystemPrompt:
        """Convert MenuSystemPromptModel to MenuSystemPrompt"""
        return MenuSystemPrompt(
            id=db_model.id,
            name=db_model.name,
            prompt_text=db_model.prompt_text,
            priority=1 if db_model.pinned else 0,
            is_active=db_model.is_active
        )

def load_config(config_file="config.json") -> Config: 
       if os.path.exists(config_file):
           with open(config_file, "r") as f:
               config_data = json.load(f)
               # Add the API key from the environment if it's not in the config file
               if "groq_api_key" not in config_data or not config_data["groq_api_key"]:
                   config_data["groq_api_key"] = os.getenv("GROQ_API_KEY")
               config = Config(**config_data)  # Create the Config object after potentially adding the API key
               return config
       else:
           api_key = os.getenv("GROQ_API_KEY")
           if not api_key:
               raise ValueError("GROQ_API_KEY environment variable not set.") # Raise an error if the API key is not found
           return Config(groq_api_key=api_key) # Create Config object with the API key
