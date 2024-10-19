# src/models/models.py

class LLMModelParams:
    def __init__(self, model_name, max_tokens, temperature, top_p):
        self.model_name = "llama3-70b-8192"
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p

class ChatMessage:
    def __init__(self, role, content):
        self.role = role
        self.content = content
