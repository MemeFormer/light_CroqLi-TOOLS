# src/models/models.py
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid
from pydantic import BaseModel, Field

class PromptPriority(Enum):
    NORMAL = 0
    PINNED = 1

class SystemPrompt(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    name: str
    priority: PromptPriority = PromptPriority.NORMAL
    is_active: bool = False
    display_index: int = 0

class Config(BaseModel):
    # ... (other fields remain the same)
    _prompts: Dict[str, SystemPrompt] = Field(default_factory=dict) # id -> prompt mapping
    _display_order: List[str] = Field(default_factory=list) # List of prompt IDs in display order
    _active_prompt_id: Optional[str] = None


    @property  # Access prompts through a property for easier handling
    def prompts(self) -> List[SystemPrompt]:
        return [self._prompts[prompt_id] for prompt_id in self._display_order]

    @property
    def active_prompt(self) -> Optional[SystemPrompt]:
        if self._active_prompt_id:
            return self._prompts.get(self._active_prompt_id)
        return None


    def add_prompt(self, name: str, prompt_text: str):
        prompt = SystemPrompt(content=prompt_text, name=name)
        self._prompts[prompt.id] = prompt
        self._display_order.append(prompt.id)
        self._update_display_indices()
        self.save_config()  # Save after adding

    def _update_display_indices(self):
        for idx, prompt_id in enumerate(self._display_order):
            self._prompts[prompt_id].display_index = idx

    def move_prompt(self, display_idx: int, direction: int):
        # ... (Implementation remains the same, using self._prompts and self._display_order)
        self.save_config() # Save after moving

    def set_active_prompt(self, display_idx: int):
        # ... (Implementation remains the same, using self._prompts, self._display_order, and self._active_prompt_id)
        self.save_config() # Save after setting active prompt

    def delete_prompt(self, display_idx: int):
        try:
            prompt_id = self._display_order.pop(display_idx)
            del self._prompts[prompt_id]
            self._update_display_indices()
            if self._active_prompt_id == prompt_id:
                self.set_active_prompt(0) # Reset active prompt if deleted
            self.save_config() # Save after deleting
        except IndexError:
            # Handle index error

    def load_system_prompts(self, prompts_file="system_prompts.json"): # Load prompts from prompts file
        try:
            with open(prompts_file, "r") as f:
                data = json.load(f)
                # Load prompts and display order
                self._prompts = {pid: SystemPrompt(**pdata) for pid, pdata in data.get("prompts", {}).items()}
                self._display_order = data.get("display_order", [])
                self._active_prompt_id = data.get("active_prompt_id")
                self._update_display_indices()
        except FileNotFoundError:
            self._prompts = {}
            self._display_order = []
            self._active_prompt_id = None

    def save_system_prompts(self, prompts_file="system_prompts.json"): # Save prompts to prompts file
        with open(prompts_file, "w") as f:
            json.dump({
                "prompts": {pid: p.dict() for pid, p in self._prompts.items()},
                "display_order": self._display_order,
                "active_prompt_id": self._active_prompt_id
            }, f, indent=4)


    def save_config(self, config_file="config.json"):
        with open(config_file, "w") as f:
            json.dump(self.dict(exclude={"groq_service", "client"}), f, indent=4) # Exclude GroqService attributes


# ... (load_config remains the same)