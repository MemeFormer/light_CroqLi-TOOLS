# src/models/models.py
import json
import os
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from typing import List, Optional, Dict, Any

class ShellAndOS(BaseModel):
    shell: str
    os: str

class LLMModelParams(BaseModel):
    model_name: str = "llama3-70b-8192"
    max_tokens: int
    temperature: float
    top_p: float

class ChatMessage(BaseModel):
    role: str
    content: str

class ToolCall(BaseModel):
    tool_calls: Optional[List[dict]] = None
    input: Optional[str] = None

class CommandResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int

class HelpfulTip(BaseModel):
    explanation: str
    suggestion: str
    additional_info: str

class ModelSettings(BaseModel):
    model_name: str
    max_tokens: int
    temperature: float
    top_p: float

class APIKeys(BaseModel):
    groq_api_key: str

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

class Prompt(BaseModel):
    name: str
    prompt_text: str
    
class Config(BaseModel):
    groq_model: str = "default-model"
    max_tokens: int = 1000
    temperature: float = 0.7
    top_p: float = 0.9
    system_prompt: str = ""
    active_prompt_index: int = 0
    system_prompts: List[Prompt] = Field(default_factory=list)
    groq_api_key: str = Field(...)  # Required field
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
    def switch_active_prompt(self, index: int):
        """Switches the active prompt."""
        self.set_active_prompt(index) # Call set_active_prompt to update system_prompt
        self.save_system_prompts() # Save after switching

    def load_system_prompts(self, prompts_file="system_prompts.json"): # Added prompts_file parameter
        try:
            with open(prompts_file, "r") as f:
                data = json.load(f)
                self._prompts = {pid: SystemPrompt(**pdata) for pid, pdata in data.get("prompts", {}).items()}
                self._display_order = data.get("display_order", [])
                self._active_prompt_id = data.get("active_prompt_id")
                self._update_display_indices()
                
        except FileNotFoundError:
            self.system_prompts = []
            self._display_order = []
            self._active_prompt_id = None

    def _update_display_indices(self):
        for idx, prompt_id in enumerate(self._display_order):
            self._prompts[prompt_id].display_index = idx


    def move_prompt(self, display_idx: int, direction: int):
        # ... (Implementation remains the same, using self._prompts and self._display_order)
        self.save_config() # Save after moving


    def set_active_prompt(self, display_idx: int):
        if 0 <= index < len(self.system_prompts):
            self.active_prompt_index = index
            self.system_prompt = self.system_prompts[index].prompt_text
            self.save_config() # Save after setting active prompt

        else:
            self.system_prompt = ""

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


    def save_system_prompts(self, prompts_file: str = "system_prompts.json") -> None:
        """Save system prompts to a JSON file.
        Args:
            prompts_file (str, optional): Path to the file where prompts will be saved. Defaults to "system_prompts.json"
        """
        data = {
            "prompts": {
                pid: prompt.model_dump() 
                for pid, prompt in self._prompts.items()
            },
            "display_order": self._display_order,
            "active_prompt_id": self._active_prompt_id
        }
    
        with open(prompts_file, "w") as f:
            json.dump(data, f, indent=4)
            "prompts": {pid: p.dict() for pid, p in self._prompts.items()},
            "display_order": self._display_order,
            "active_prompt_id": self._active_prompt_id
            


    def save_config(self, config_file="config.json"):
        with open(config_file, "w") as f:
            json.dump(self.dict(exclude={"groq_service", "client"}), f, indent=4) # Exclude GroqService attributes


def load_config(config_file="config.json"):  # Added config_file parameter and loading from JSON
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            config_data = json.load(f)
            return Config(**config_data) # Use Pydantic for validation
    else:
        config = Config(groq_api_key=os.getenv('GROQ_API_KEY'))
        return config