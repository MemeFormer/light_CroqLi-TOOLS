# src/config.py

import json
import os
import uuid
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from typing import Any


class SystemPrompt(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    name: str
    priority: int = 0  # Assuming 0 for NORMAL, 1 for PINNED
    is_active: bool = False
    display_index: int = 0

class Config(BaseModel):
    groq_model: str = "llama3-70b-8192"
    max_tokens: int = 1000
    temperature: float = 0.7
    top_p: float = 0.9
    system_prompt: str = ""
    active_prompt_index: int = 0
    load_systemprompts: List[Dict[str, Any]] = Field(default_factory=list)  # Store all prompts
    groq_api_key: Optional[str] = None  # Make groq_api_key optional
    prompts_U: Dict[str, SystemPrompt] = Field(default_factory=dict)  # id -> prompt mapping
    display_order_U: List[str] = Field(default_factory=list)  # List of prompt IDs in display order
    active_prompt_id_U: Optional[str] = None

  
  
    @property
    def prompts(self) -> List[SystemPrompt]:
        return [self.prompts_U[prompt_id] for prompt_id in self.display_order_U]

    @property
    def active_prompt(self) -> Optional[SystemPrompt]:
        if self.active_prompt_id_U:
            return self.prompts_U.get(self.active_prompt_id_U)
        return None

    def add_prompt(self, name: str, prompt_text: str) -> None:
        if not name or not prompt_text:
            raise ValueError("Name and prompt text cannot be empty")
        prompt = SystemPrompt(content=prompt_text, name=name)
        self.prompts_U[prompt.id] = prompt
        self.display_order_U.append(prompt.id)
        self._update_display_indices()
        self.save_config()

    def _update_display_indices(self):
        for idx, prompt_id in enumerate(self.display_order_U):
            self.prompts_U[prompt_id].display_index = idx

    
    def set_active_prompt(self, display_idx: int):
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

    def pin_prompt(self, display_idx: int) -> None:
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
                self.prompts_U = {pid: SystemPrompt(**pdata) for pid, pdata in data.get("prompts", {}).items()}
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
