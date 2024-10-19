import os
from groq import Groq
from src.models.models import LLMModelParams, ChatMessage
from src.config import load_config
from typing import List
from dotenv import load_dotenv


class GroqService:
    def __init__(self):
        load_dotenv()
        
        self.config = load_config()
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key)
        self.model_params = LLMModelParams(
            model_name=self.config.groq_model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p
        )

    def generate_response(self, messages: List[ChatMessage]) -> str:
        response = self.client.chat.completions.create(
            model=self.model_params.model_name,
            messages=[{"role": msg.role, "content": msg.content} for msg in messages],
            max_tokens=self.model_params.max_tokens,
            temperature=self.model_params.temperature,
            top_p=self.model_params.top_p
        )
        return response.choices[0].message.content
