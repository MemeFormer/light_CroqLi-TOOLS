# src/config.py

import json
import os
import uuid
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from typing import Any
from src.models.models import SystemPrompt



class Config(BaseModel):
    groq_model: str = "llama3-70b-8192"
    max_tokens: int = 1000
    temperature: float = 0.7
    top_p: float = 0.9
    system_prompt: str = ""
    active_prompt_index: int = 0
    load_systemprompts: List[Dict[str, Any]] = Field(default_factory=list)
    groq_api_key: Optional[str] = None
    prompts: Dict[str, SystemPrompt] = Field(default_factory=dict)
    active_prompt_id: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if not self.prompts:
            self._create_default_prompts()

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

    def load_prompts(self, prompts_file="system_prompts.json"):
        try:
            with open(prompts_file, "r") as f:
                data = json.load(f)
                prompts_data = data.get("prompts", {})
                
                # Check if we're dealing with old or new format
                sample_prompt = next(iter(prompts_data.values())) if prompts_data else {}
                is_old_format = "priority" in sample_prompt
                
                if is_old_format:
                    # Migration from old format
                    display_order = data.get("display_order", [])
                    for idx, prompt_id in enumerate(display_order):
                        old_prompt = prompts_data[prompt_id]
                        self.prompts[prompt_id] = SystemPrompt(
                            id=prompt_id,
                            title=old_prompt["name"],
                            content=old_prompt["prompt_text"],
                            is_active=old_prompt["is_active"],
                            pinned=old_prompt["priority"] == 1,
                            pin_order=idx if old_prompt["priority"] == 1 else None,
                            list_order=idx
                        )
                else:
                    # New format
                    self.prompts = {pid: SystemPrompt(**pdata) for pid, pdata in prompts_data.items()}
                
                self.active_prompt_id = data.get("active_prompt_id")
                
        except FileNotFoundError:
            self._create_default_prompts()
            self.save_prompts()  # We'll implement this in the next step

    def add_prompt(self, new_prompt: SystemPrompt) -> None:
        """Add a new prompt from SystemPrompt object"""
        if not new_prompt.title or not new_prompt.content:
            raise ValueError("Name and prompt text cannot be empty")
            
        self.prompts[new_prompt.id] = new_prompt
        self.save_prompts()

    def update_prompt(self, display_idx: int, updated_prompt: SystemPrompt) -> None:
        """Update an existing prompt"""
        if not (0 <= display_idx < len(self.prompts)):
            raise ValueError("Invalid display index")
            
        prompt_id = self.prompts.keys()[display_idx]
        prompt = self.prompts[prompt_id]
        
        prompt.title = updated_prompt.title
        prompt.content = updated_prompt.content
        
        if updated_prompt.is_active:
            self._set_active_prompt(display_idx)
        
        self.save_prompts()

    def _set_active_prompt(self, display_idx: int):
        try:
            if display_idx is None:
                self.active_prompt_id = None
            elif 0 <= display_idx < len(self.prompts):
                prompt_id = self.prompts.keys()[display_idx]
                self.active_prompt_id = prompt_id
                for pid, prompt in self.prompts.items():
                    if pid != prompt_id:
                        prompt.is_active = False
            else:
                raise ValueError("Invalid display index")
            self.save_prompts()
        except Exception as e:
            raise RuntimeError(f"Failed to set active prompt: {str(e)}")

    def pin_prompt(self, display_idx: int) -> None:
        """Public method to toggle pin status"""
        self._pin_prompt(display_idx)

    def _pin_prompt(self, display_idx: int) -> None:
        """Toggle pin status of a prompt"""
        try:
            if not (0 <= display_idx < len(self.prompts)):
                raise ValueError("Invalid display index")

            prompt_id = self.prompts.keys()[display_idx]
            prompt = self.prompts[prompt_id]

            # Toggle pinned status
            prompt.pinned = not prompt.pinned

            # Reorder the display order based on pin status
            self._reorder_after_pin_change(prompt_id)
            self.save_prompts()

        except Exception as e:
            raise RuntimeError(f"Failed to toggle pin status: {str(e)}")

    def _reorder_after_pin_change(self, changed_prompt_id: str) -> None:
        """Reorder prompts after a pin status change"""
        # Remove the changed prompt from current order
        self.prompts.pop(changed_prompt_id)
        
        # Find insertion point for the prompt based on its new pin order
        changed_prompt = self.prompts[changed_prompt_id]
        insertion_idx = 0
        
        if changed_prompt.pinned:  # If newly pinned
            # Find the last pinned prompt
            while (insertion_idx < len(self.prompts) and 
                   self.prompts[self.prompts.keys()[insertion_idx]].pinned):
                insertion_idx += 1
        else:  # If unpinned
            # Skip all pinned prompts
            while (insertion_idx < len(self.prompts) and 
                   self.prompts[self.prompts.keys()[insertion_idx]].pinned):
                insertion_idx += 1
            
        # Insert at the appropriate position
        self.prompts.insert(insertion_idx, changed_prompt_id, changed_prompt)

    def move_prompt(self, display_idx: int, direction: int) -> None:
        """Public method to move prompt"""
        self._move_prompt(display_idx, direction)

    def _move_prompt(self, display_idx: int, direction: int) -> None:
        """Move a prompt up or down within its priority group"""
        try:
            if not (0 <= display_idx < len(self.prompts)):
                raise ValueError("Invalid display index")
            
            current_id = self.prompts.keys()[display_idx]
            current_prompt = self.prompts[current_id]
            
            # Calculate new index ensuring we stay within the same priority group
            new_idx = display_idx + direction
            while (0 <= new_idx < len(self.prompts)):
                target_id = self.prompts.keys()[new_idx]
                target_prompt = self.prompts[target_id]
                
                # Only swap if both prompts have the same pin order
                if target_prompt.pin_order == current_prompt.pin_order:
                    self.prompts.pop(current_id)
                    self.prompts.insert(new_idx, current_id, current_prompt)
                    break
                    
                new_idx += direction
                
            self.save_prompts()
            
        except Exception as e:
            raise RuntimeError(f"Failed to move prompt: {str(e)}")

    def delete_prompt(self, display_idx: int):
        try:
            prompt_id = self.prompts.pop(self.prompts.keys()[display_idx])
            if self.active_prompt_id == prompt_id:
                self._set_active_prompt(0)
            self.save_prompts()
        except IndexError:
            pass

    def save_prompts(self, prompts_file="system_prompts.json"):
        """Save prompts to JSON file using the new format"""
        try:
            with open(prompts_file, "w") as f:
                json.dump({
                    "prompts": {pid: p.model_dump() for pid, p in self.prompts.items()},
                    "active_prompt_id": self.active_prompt_id
                }, f, indent=4)
        except IOError as e:
            raise RuntimeError(f"Failed to save system prompts: {str(e)}")

    def rename_prompt(self, display_idx: int, new_name: str) -> None:
        """Rename a prompt"""
        if not (0 <= display_idx < len(self.prompts)):
            raise ValueError("Invalid display index")
        
        prompt_id = self.prompts.keys()[display_idx]
        self.prompts[prompt_id].title = new_name
        self.save_prompts()

    def edit_prompt_text(self, display_idx: int, new_text: str) -> None:
        """Edit prompt text"""
        if not (0 <= display_idx < len(self.prompts)):
            raise ValueError("Invalid display index")
        
        prompt_id = self.prompts.keys()[display_idx]
        self.prompts[prompt_id].content = new_text
        self.save_prompts()

    def get_prompt(self, display_idx: int) -> Optional[SystemPrompt]:
        """Get prompt by display index"""
        if not (0 <= display_idx < len(self.prompts)):
            return None
        
        prompt_id = self.prompts.keys()[display_idx]
        return self.prompts.get(prompt_id)

    def validate_configuration(self) -> bool:
        try:
            if not all(pid in self.prompts for pid in self.prompts.keys()):
                return False

            if self.active_prompt_id and self.active_prompt_id not in self.prompts:
                return False

            return True
        except Exception:
            return False

    def prompt_exists(self, display_idx: int) -> bool:
        return 0 <= display_idx < len(self.prompts)

def load_config():
    print("Loading config...")
    try:
        with open("config.json", "r") as f:
            print("Reading config.json...")
            config_data = json.load(f)
            print(f"Config data: {config_data}")
            return Config(**config_data)
    except FileNotFoundError:
        print("No config.json found, using default config")
        return Config()
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return Config()
