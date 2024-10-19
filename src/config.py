# src/config.py


# src/config.py

import json
import os

class Config:
    def __init__(self):
        self.groq_model = "default-model"
        self.max_tokens = 1000
        self.temperature = 0.7
        self.top_p = 0.9
        self.system_prompt = ""
        self.active_prompt_index = 0  # Keep track of the active prompt
        self.SYSTEM_PROMPTS = []  # Store all prompts

    def load_system_prompts(self):
        try:
            with open("system_prompts.json", "r") as f:
                prompts = json.load(f)
                self.SYSTEM_PROMPTS = prompts.get("prompts", [])
                self.set_active_prompt(self.active_prompt_index)  # Set the default active prompt
        except FileNotFoundError:
            self.SYSTEM_PROMPTS = []

    def set_active_prompt(self, index):
        """Set the active prompt by index."""
        if 0 <= index < len(self.SYSTEM_PROMPTS):
            self.active_prompt_index = index
            self.system_prompt = self.SYSTEM_PROMPTS[index].get("prompt_text", "")
        else:
            self.system_prompt = ""

    def save_system_prompts(self):
        """Save the current system prompts to the JSON file."""
        with open("system_prompts.json", "w") as f:
            json.dump({"prompts": self.SYSTEM_PROMPTS}, f, indent=4)

def load_config():
    config = Config()
    config.groq_api_key = os.getenv('GROQ_API_KEY')
    return Config()
